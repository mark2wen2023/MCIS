import { useMemo, useState, type Dispatch, type SetStateAction } from 'react'
import { useSearchParams } from 'react-router-dom'
import { api, ApiError, CASE_ID } from '../api'
import { ColregView } from '../colreg/ColregView'
import { evaluateDoneText, normalizeDraftResponse, reviewBody, type ColregEvaluateResult, type DraftDisplay } from '../colreg/derive'
import { useToast } from '../components/Toast'
import { useLoad } from '../hooks'
import '../styles/w6.css'
import type {
  AuditEvent, CaseDef, CaseListItem, ColregAnalysis, ColregCompare, ColregRunList, ColregRunView,
  ColregVerdict, CpaSeries, EvidenceItem, ReviewAction, TimelineEvent, Vessel,
} from '../types'

const HAILI = 'CASE-2025-HAILI5-WANA17'
/** 章节草稿接口由 W16（Codex）实现（openapi：POST /cases/{caseId}/reports/sections/colreg:draft）；这里只留调用处。 */
export const REPORT_DRAFT_PATH = (caseId: string) => `/cases/${caseId}/reports/sections/colreg:draft`
export const DRAFT_UNAVAILABLE = '章节草稿生成服务尚未上线（W16 开发中）。当前页面的核查项与证据已可复核，接口上线后此按钮直接生成 Draft 章节。'

const REVIEW_ERR: Record<string, string> = {
  colreg_review_reason_required: '驳回或修改须填写理由',
  colreg_review_verdict_not_allowed: '确认/驳回时不能改判定，要改判定请用“修改”',
  colreg_review_verdict_required: '修改须选择新的判定',
  colreg_review_no_change: '新判定与当前判定相同，不构成修改',
  evidence_not_registered: '有证据编号未在本案件登记，请先到证据中心登记',
}

export function ColregPage() {
  const [params] = useSearchParams()
  return <ColregWorkspace key={params.get('case') || CASE_ID} />
}

type WorkspaceState = {
  compare: ColregCompare | null; setCompare: Dispatch<SetStateAction<ColregCompare | null>>
  draft: DraftDisplay | null; setDraft: Dispatch<SetStateAction<DraftDisplay | null>>
  draftNotice: string | null; setDraftNotice: Dispatch<SetStateAction<string | null>>
}

// Case-scoped work survives version navigation; fetched version state remains isolated.
function ColregWorkspace() {
  const [params] = useSearchParams()
  const [compare, setCompare] = useState<ColregCompare | null>(null)
  const [draft, setDraft] = useState<DraftDisplay | null>(null)
  const [draftNotice, setDraftNotice] = useState<string | null>(null)
  return <ColregSession key={JSON.stringify([params.get('check'), params.get('run')])}
    compare={compare} setCompare={setCompare} draft={draft} setDraft={setDraft}
    draftNotice={draftNotice} setDraftNotice={setDraftNotice} />
}

function ColregSession({ compare, setCompare, draft, setDraft, draftNotice, setDraftNotice }: WorkspaceState) {
  const { run, show } = useToast()
  const [params, setParams] = useSearchParams()
  const caseId = params.get('case') || CASE_ID
  const [sel, setSel] = useState<string | null>(params.get('check') || null)
  const [evaluating, setEvaluating] = useState(false)
  const [viewRunId, setViewRunId] = useState<string | null>(params.get('run') === 'active' ? null : params.get('run') || null)

  const cases = useLoad(() => api.get<CaseListItem[]>('/cases'))
  const caseRes = useLoad(() => api.get<CaseDef>(`/cases/${caseId}`), [caseId])
  const vessels = useLoad(() => api.get<Vessel[]>(`/cases/${caseId}/vessels`), [caseId])
  const runs = useLoad(() => api.get<ColregRunList>(`/cases/${caseId}/colreg/runs`), [caseId])
  const runView = useLoad(() => api.get<ColregRunView>(`/cases/${caseId}/colreg/runs/${encodeURIComponent(viewRunId ?? 'active')}`), [caseId, viewRunId])
  const current = useLoad(() => api.get<ColregAnalysis>(`/cases/${caseId}/colreg`), [caseId])
  const evidence = useLoad(() => api.get<EvidenceItem[]>(`/cases/${caseId}/evidence`), [caseId])
  const audit = useLoad(() => api.get<AuditEvent[]>(`/cases/${caseId}/audit?action=colreg.review&order=asc&limit=500`), [caseId])
  const timeline = useLoad(() => api.get<{ events: TimelineEvent[] }>(`/cases/${caseId}/timeline`), [caseId])
  const cpa = useLoad(() => api.get<CpaSeries>(`/cases/${caseId}/cpa?stepSec=10`), [caseId])

  // 仅未指定版本时兼容旧服务；明确版本不得静默回退当前文档。
  const analysis = viewRunId ? runView.data?.analysis : runView.data?.analysis ?? current.data

  const switcher = useMemo(() => {
    const list = cases.data ?? []
    const wanted = [CASE_ID, HAILI]
    const out = wanted.map((id) => list.find((c) => c.caseId === id)).filter((c): c is CaseListItem => !!c)
    return out.length ? out : list
  }, [cases.data])

  const reloadAll = () => { runView.reload(); runs.reload(); current.reload(); audit.reload(); caseRes.reload() }

  const onReview = (checkId: string, action: ReviewAction, verdict: ColregVerdict | null, reason: string, evidenceIds?: string[]) => {
    const label = { confirm: '确认', dismiss: '驳回', modify: '修改' }[action]
    void run(async () => {
      const body = reviewBody(action, verdict, reason, evidenceIds)
      const q = viewRunId ? `?runId=${encodeURIComponent(viewRunId)}` : ''
      try {
        await api.patch(`/cases/${caseId}/colreg/checks/${checkId}${q}`, body)
      } catch (e) {
        if (e instanceof ApiError && REVIEW_ERR[e.code]) throw new Error(`${REVIEW_ERR[e.code]}（${e.message}）`)
        throw e
      }
      reloadAll()
    }, `已${label} ${checkId}，已写入审计`)
  }

  const onEvaluate = (confirmed: boolean) => {
    setEvaluating(true)
    void (async () => {
      try {
        const path = `/cases/${caseId}/colreg:evaluate`
        let doc: ColregEvaluateResult
        try {
          doc = await api.post<ColregEvaluateResult>(path, {})
        } catch (e) {
          if (!(e instanceof ApiError) || e.code !== 'colreg_evaluate_confirm_required') throw e
          // 后端二次确认：只有用户已在确认框里确认，才带一次性令牌重发
          if (!confirmed) throw new Error('该案例不是虚构演示数据，运行规则引擎需要二次确认')
          const tok = (e.detail as { confirmToken?: string } | undefined)?.confirmToken
          if (!tok) throw e
          doc = await api.post<ColregEvaluateResult>(`${path}?confirmToken=${encodeURIComponent(tok)}`, {})
        }
        setViewRunId(null)
        setCompare(null)
        reloadAll()
        show(evaluateDoneText(doc), 'ok')
      } catch (e) {
        show(e instanceof ApiError ? `${e.code}：${e.message}` : String(e), 'err')
      } finally {
        setEvaluating(false)
      }
    })()
  }

  const onActivateRun = (runId: string) => {
    void run(async () => {
      await api.post(`/cases/${caseId}/colreg/runs/${runId}:activate`, {})
      setViewRunId(null)
      reloadAll()
    }, `已把 ${runId} 设为当前版本（已写审计）`)
  }

  const onCompare = (baseRunId: string, otherRunId: string) => {
    void run(async () => {
      setCompare(await api.get<ColregCompare>(`/cases/${caseId}/colreg/compare?base=${baseRunId}&other=${otherRunId}`))
    }, '版本对比已生成')
  }

  const onGenerateDraft = () => {
    void (async () => {
      try {
        // 请求体按 openapi（additionalProperties=false）：只传 lang
        const d = normalizeDraftResponse(await api.post<unknown>(REPORT_DRAFT_PATH(caseId), { lang: 'zh' }))
        setDraft(d)
        setDraftNotice(null)
        show(`已生成章节草稿（${d.status}）`)
      } catch (e) {
        if (e instanceof ApiError && [404, 405, 501].includes(e.status)) {
          setDraftNotice(DRAFT_UNAVAILABLE)
          show('章节草稿服务尚未上线（W16），已在页面给出说明')
        } else {
          setDraftNotice(`生成章节草稿失败：${(e as Error).message}`)
        }
      }
    })()
  }

  const citation = params.has('check') || params.has('run')
  const targetUnavailable = viewRunId && (runView.error || (runView.data && (runView.data.runId !== viewRunId || runView.data.analysis.caseId !== caseId)))
  const missingCheck = analysis && sel && !analysis.checks.some(c => c.checkId === sel)
  if (targetUnavailable || missingCheck) return <div role="alert" className="p6-card">
    <p>{targetUnavailable ? '指定核查版本暂不可读取或返回版本不符。' : '指定核查项不在已读取的版本中。'}未自动改选当前版本或其他核查项。</p>
    <button type="button" onClick={() => setParams({ case: caseId })}>离开引用定位，查看本案当前核查</button>
  </div>
  const err = caseRes.error || (viewRunId ? runView.error : current.error && runView.error) || vessels.error
  if (!caseRes.data || !analysis) {
    return (
      <div>
        {err && <div className="p6-card" style={{ borderColor: 'var(--red)' }}>后端错误：{err}</div>}
        {!err && <div className="empty">正在载入避碰规则对照…</div>}
      </div>
    )
  }

  return (
    <>
    {citation && <p role="note">引用定位仅打开本案登记的版本与核查项，不证明生成报告时的内容或原始证据已核验。未带版本或使用 active 别名的引用仅打开当前台账。</p>}
    {(draft || draftNotice || compare) && <p role="note">本案已有草稿、提示及对比结果在切换查看版本时保留，不会自动更新为所选版本；离开本案或刷新后不保留页面状态。</p>}
    <ColregView
      caseDef={caseRes.data}
      vessels={vessels.data ?? []}
      analysis={analysis}
      evidence={evidence.data ?? []}
      audit={audit.data ?? []}
      selectedId={sel ?? analysis.checks[0]?.checkId ?? null}
      onSelect={setSel}
      onReview={onReview}
      onEvaluate={onEvaluate}
      evaluating={evaluating}
      cases={switcher}
      onSwitchCase={(id) => { setSel(null); setViewRunId(null); setCompare(null); setDraft(null); setDraftNotice(null); setParams(id === CASE_ID ? {} : { case: id }); show(`已切换到 ${id}`) }}
      runs={runs.data}
      runView={runView.data}
      onViewRun={(id) => setParams({ case: caseId, run: id })}
      onActivateRun={onActivateRun}
      compare={compare}
      onCompare={onCompare}
      onCloseCompare={() => setCompare(null)}
      cpa={cpa.data}
      cpaError={cpa.error}
      timeline={timeline.data?.events ?? []}
      onGenerateDraft={onGenerateDraft}
      draft={draft}
      draftNotice={draftNotice}
    />
    </>
  )
}
