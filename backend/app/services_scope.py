"""角色与数据范围。

生产环境由网关写入请求头(与智多星的 loggedInUserId 方案一致)：
  X-Role: super_admin | da_admin | other      缺省 = super_admin(本地开发)
  X-Managed-DAs: BC,LC                        da_admin/other 可见的 DA，逗号分隔
所有查询与导出都在服务端把 DA 范围与 managed 取交集——前端传什么参数都不会越权(验收 5)。
"""
from __future__ import annotations

from dataclasses import dataclass

from fastapi import Header, HTTPException

from . import config
from .etl.da_dict import ALL_DAS


@dataclass
class Scope:
    role: str
    managed: list[str] | None  # None = 不限

    @property
    def is_super(self) -> bool:
        return self.role == "super_admin"

    @property
    def can_cost(self) -> bool:
        return self.role in ("super_admin", "da_admin")

    @property
    def level(self) -> str:
        return "da" if self.is_super else "region"


def get_scope(x_role: str | None = Header(None), x_managed_das: str | None = Header(None),
              logged_in_user_id: str | None = Header(None, alias="loggedInUserId")) -> Scope:
    if config.DATA_SOURCE == "vendor":
        # 生产：只信任网关注入的 loggedInUserId，经乙方 userRoleInfo 解析角色与可见 DA；忽略前端可伪造的 X-Role
        if not logged_in_user_id:
            raise HTTPException(401, "缺少 loggedInUserId")
        from .vendor.vendor_adapter import VendorError, resolve_role
        try:
            r = resolve_role(logged_in_user_id)
        except VendorError as e:
            raise HTTPException(502, str(e))
        return Scope(r["role"], r["managed"])
    role = x_role or "super_admin"
    if role not in ("super_admin", "da_admin", "other"):
        raise HTTPException(400, "unknown role")
    if role == "super_admin":
        return Scope(role, None)
    managed = [d.strip() for d in (x_managed_das or "").split(",") if d.strip() and d.strip() in ALL_DAS]
    return Scope(role, managed)
