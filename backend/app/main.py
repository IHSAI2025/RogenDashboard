from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .api import admin, insight, report, uploads, vm_cost, vm_da, vm_overview, vm_users
from .database import SessionLocal, init_db
from .etl.exclusions import seed_default_exclusion_rules

app = FastAPI(title="神笔小罗管理后台 · Insight 分析")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def on_startup():
    init_db()
    db = SessionLocal()
    try:
        seed_default_exclusion_rules(db)
        db.commit()
    finally:
        db.close()


app.include_router(insight.router)
app.include_router(uploads.router)
app.include_router(admin.router)
app.include_router(report.router)
for _m in (vm_overview, vm_da, vm_users, vm_cost):
    app.include_router(_m.router)


@app.get("/api/health")
def health():
    return {"status": "ok"}
