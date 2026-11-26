import * as React from "react"
import { IconBulb, IconPresentation } from "@tabler/icons-react"
import { CheckIcon, CopyIcon, PencilIcon, RocketIcon, RotateCcwIcon, Trash2Icon, XIcon } from "lucide-react"
import { toast } from "sonner"

import aiIllustrationUrl from "@/assets/figma/ai-illustration.png"
import { api } from "@/api/client"
import { useScopeParams } from "@/api/params"
import { HgAlertCircle, HgChartLineData02 } from "@/components/dashboard/hugeicons"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { CURRENT_USER } from "@/lib/auth"
import { cn } from "@/lib/utils"

type Segment = { text: string; bold?: boolean; highlight?: boolean }
type SectionKind = "conclusion" | "risk" | "highlight" | "other"

interface InsightSection {
  id: string
  kind: SectionKind
  title: string
  body: Segment[]
}

const SECTION_ICON: Record<SectionKind, { bg: string; icon: React.ReactNode }> = {
  conclusion: {
    bg: "bg-[#dbeafe]",
    icon: <IconBulb className="size-4 text-primary" stroke={1.75} />,
  },
  risk: { bg: "bg-[#fff7f8]", icon: <HgAlertCircle /> },
  highlight: {
    bg: "bg-[#fefbe9]",
    icon: <RocketIcon className="size-4 text-[#e2a336]" strokeWidth={1.75} />,
  },
  other: {
    bg: "bg-[#f0f0f0]",
    icon: <IconPresentation className="size-4 text-[#646464]" stroke={1.75} />,
  },
}

function plainText(body: Segment[]) {
  return body.map((s) => s.text).join("")
}

interface InsightResponse {
  key: string
  sections: InsightSection[]
  generated: InsightSection[]
  edited: boolean
  editable: boolean
}

/** 洞察文案由后端按规则生成（只陈述事实，口径同看板指标）；超管编辑后落库，按角色+周期+筛选条件区分。 */
function useInsight(scope: "overview" | "da") {
  const params = useScopeParams()
  const key = JSON.stringify([params, scope])
  const [tick, setTick] = React.useState(0)
  const [data, setData] = React.useState<{ key: string; res: InsightResponse | null }>({ key, res: null })
  React.useEffect(() => {
    let off = false
    api<InsightResponse>("/vm/overview/insight", { ...params, scope })
      .then((res) => !off && setData({ key, res }))
      .catch(() => !off && setData({ key, res: null }))
    return () => {
      off = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, tick])
  const save = async (sections: InsightSection[]) => {
    await api("/vm/overview/insight", { ...params, scope }, {
      method: "PUT",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ sections }),
    })
    setTick((t) => t + 1)
  }
  return { res: data.key === key ? data.res : null, save, signature: key }
}

/** AI 诊断及洞察：内容随筛选条件实时更新；超管可编辑，DA 管理员只读 */
export function AiInsightCard({ scope = "overview" }: { scope?: "overview" | "da" }) {
  const { res, save, signature } = useInsight(scope)
  const [draft, setDraft] = React.useState<InsightSection[] | null>(null)

  const sections = res?.sections ?? []
  const editing = draft != null
  // 仅超级管理员可编辑（后端同样校验）
  const canEdit = CURRENT_USER.role === "super_admin" && !!res?.editable

  // 筛选变化时退出编辑态
  React.useEffect(() => {
    setDraft(null)
  }, [signature])

  const copy = async () => {
    const text = sections.map((s) => `${s.title}\n${plainText(s.body)}`).join("\n\n")
    try {
      await navigator.clipboard.writeText(`AI 诊断及洞察\n\n${text}`)
      toast.success("已复制到剪贴板")
    } catch {
      toast.error("复制失败，请手动选择文本复制")
    }
  }

  const updateDraft = (id: string, patch: Partial<Pick<InsightSection, "title">> & { bodyText?: string }) => {
    setDraft((prev) =>
      prev
        ? prev.map((s) =>
            s.id === id
              ? {
                  ...s,
                  title: patch.title ?? s.title,
                  body: patch.bodyText != null ? [{ text: patch.bodyText }] : s.body,
                }
              : s
          )
        : prev
    )
  }

  return (
    <section className="relative flex min-h-[340px] flex-col gap-4 overflow-hidden rounded-xl bg-surface-ai py-6">
      <div className="relative z-10 flex items-center gap-2 px-6">
        {!editing && <HgChartLineData02 />}
        <h2 className="flex-1 text-lg leading-7 font-semibold text-card-foreground">AI 诊断及洞察</h2>
        {editing ? (
          <>
            {res?.edited && (
              <Button
                variant="outline"
                onClick={() => {
                  save([])
                    .then(() => toast.success("已恢复为自动生成的文案"))
                    .catch(() => toast.error("操作失败"))
                  setDraft(null)
                }}
              >
                <RotateCcwIcon />
                恢复自动生成
              </Button>
            )}
            <Button variant="outline" onClick={() => setDraft(null)}>
              <XIcon />
              取消
            </Button>
            <Button
              onClick={() => {
                save(draft)
                  .then(() => toast.success("洞察内容已保存"))
                  .catch(() => toast.error("保存失败"))
                setDraft(null)
              }}
            >
              <CheckIcon />
              完成
            </Button>
          </>
        ) : (
          <>
            {canEdit && (
              <Button variant="outline" onClick={() => setDraft(sections.map((s) => ({ ...s })))}>
                <PencilIcon />
                编辑
              </Button>
            )}
            <Button variant="outline" onClick={copy}>
              <CopyIcon />
              一键复制
            </Button>
          </>
        )}
      </div>

      <div className="relative z-10 flex flex-col gap-4 px-6">
        {(editing ? draft : sections).map((section) =>
          editing ? (
            <div key={section.id} className="flex items-center gap-3">
              <div className="flex flex-1 flex-col gap-1">
                <div className="flex items-center gap-3">
                  <SectionIcon kind={section.kind} />
                  <input
                    value={section.title}
                    onChange={(e) => updateDraft(section.id, { title: e.target.value })}
                    aria-label="段落标题"
                    className="min-w-0 flex-1 bg-transparent text-sm leading-5 font-bold text-secondary-foreground outline-none"
                  />
                </div>
                <Textarea
                  value={plainText(section.body)}
                  onChange={(e) => updateDraft(section.id, { bodyText: e.target.value })}
                  aria-label={`${section.title}内容`}
                  className="field-sizing-content min-h-0 resize-none rounded-md border-0 bg-muted px-2 py-1.5 text-sm leading-5 text-secondary-foreground shadow-none focus-visible:ring-2"
                />
              </div>
              <Button
                variant="outline"
                size="icon"
                aria-label={`删除「${section.title}」`}
                onClick={() => setDraft((prev) => prev?.filter((s) => s.id !== section.id) ?? prev)}
              >
                <Trash2Icon />
              </Button>
            </div>
          ) : (
            <div key={section.id} className="flex items-start gap-3">
              <SectionIcon kind={section.kind} />
              <div className="flex flex-1 flex-col gap-1 text-secondary-foreground">
                <p className="text-sm leading-5 font-bold">{section.title}</p>
                <p className="text-sm leading-5">
                  {section.body.map((seg, i) => (
                    <span
                      key={i}
                      className={cn(seg.bold && "font-semibold", seg.highlight && "text-primary")}
                    >
                      {seg.text}
                    </span>
                  ))}
                </p>
              </div>
            </div>
          )
        )}
        {editing && draft.length === 0 && (
          <p className="text-sm text-muted-foreground">所有段落已删除，点击「完成」保存或「取消」恢复。</p>
        )}
      </div>

      {!editing && (
        <img
          src={aiIllustrationUrl}
          alt=""
          width={311}
          height={207}
          className="pointer-events-none absolute top-[160px] right-0 h-[207px] w-[311px] object-cover"
        />
      )}
    </section>
  )
}

function SectionIcon({ kind }: { kind: SectionKind }) {
  const { bg, icon } = SECTION_ICON[kind]
  return (
    <div className={cn("flex shrink-0 items-center justify-center rounded-[4px] p-1", bg)}>{icon}</div>
  )
}
