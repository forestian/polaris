import React, { useState, useRef, useEffect } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { FileText, Download, ChevronDown, Bot, Check, ChevronRight } from 'lucide-react'

const SECTIONS = [
  { key: 'nodes',       label: '노드',           desc: '노드 상태, 역할, 리소스 용량' },
  { key: 'pods',        label: '파드',           desc: '전체 파드 목록 및 상태' },
  { key: 'deployments', label: '디플로이먼트',  desc: '배포 상태 및 레플리카 수' },
  { key: 'services',    label: '서비스',         desc: '서비스 타입 및 포트 정보' },
  { key: 'events',      label: '이벤트',         desc: '경고/오류 이벤트 목록' },
  { key: 'resources',   label: '리소스 요약',    desc: 'CPU/메모리 할당 현황' },
]

// LLM URL 이 로컬(localhost / 127.0.0.1 / ::1) 인지 판별 — 외부 URL 사용 시 UI 경고용
function isLocalLlmUrl(url) {
  try {
    const u = new URL(url)
    const h = (u.hostname || '').toLowerCase()
    return h === 'localhost' || h === '127.0.0.1' || h === '[::1]' || h === '::1'
  } catch {
    return true  // 입력 도중 파싱 실패는 경고를 띄우지 않음 (UX 노이즈 방지)
  }
}

function StepHeader({ step, current }) {
  const done = current > step.num
  const active = current === step.num
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
      <div style={{
        width: 24, height: 24, borderRadius: '50%', flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        fontSize: 11, fontWeight: 700,
        background: done ? 'var(--nimbus)' : active ? 'rgba(52,211,153,0.15)' : 'var(--bg-3)',
        border: `1.5px solid ${done || active ? 'var(--nimbus)' : 'var(--border)'}`,
        color: done ? '#000' : active ? 'var(--nimbus)' : 'var(--text-dim)',
      }}>
        {done ? <Check size={12} strokeWidth={3} /> : step.num}
      </div>
      <span style={{
        fontSize: 12, fontWeight: active ? 600 : 400,
        color: active ? 'var(--text-bright)' : done ? 'var(--text)' : 'var(--text-dim)',
      }}>
        {step.label}
      </span>
    </div>
  )
}

export default function ReportPage() {
  const { connected, namespaces, namespace, setNamespace } = useApp()

  const [step, setStep]         = useState(1)
  const [sections, setSections] = useState(
    Object.fromEntries(SECTIONS.map(s => [s.key, true]))
  )
  const [useAI, setUseAI]       = useState(false)
  const [llmUrl, setLlmUrl]     = useState('http://localhost:1234')
  const [llmModel, setLlmModel] = useState('local-model')
  const [loading, setLoading]   = useState(false)
  const [logs, setLogs]         = useState([])
  const [status, setStatus]     = useState(null)
  const pollRef  = useRef(null)
  const logEndRef = useRef(null)

  useEffect(() => {
    if (logEndRef.current) logEndRef.current.scrollIntoView({ behavior: 'smooth' })
  }, [logs])

  useEffect(() => {
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  function toggleSection(key) {
    setSections(prev => ({ ...prev, [key]: !prev[key] }))
  }

  async function generate() {
    if (pollRef.current) clearInterval(pollRef.current)
    setLoading(true)
    setLogs([])
    setStatus(null)

    const filename = `Polaris-report-${new Date().toISOString().slice(0, 10)}.docx`
    let savePath
    try {
      savePath = await api.openSaveDialog(filename)
    } catch (e) {
      setStatus({ ok: false, msg: String(e) }); setLoading(false); return
    }
    if (!savePath) { setLoading(false); return }

    const ns = namespace === 'All Namespaces' ? '' : namespace
    let res
    try {
      res = await api.startReport({
        namespace: ns,
        save_path: savePath,
        use_ai:    useAI,
        llm_url:   llmUrl,
        llm_model: llmModel,
        sections:  Object.entries(sections).filter(([, v]) => v).map(([k]) => k),
      })
    } catch (e) {
      setStatus({ ok: false, msg: String(e) }); setLoading(false); return
    }

    if (!res?.ok) {
      setStatus({ ok: false, msg: res?.error || '시작 실패' }); setLoading(false); return
    }

    const jobId = res.job_id
    pollRef.current = setInterval(async () => {
      try {
        const s = await api.getJobStatus(jobId)
        if (s.logs) setLogs([...s.logs])
        if (s.status === 'done') {
          clearInterval(pollRef.current)
          setStatus({ ok: true, msg: `저장 완료: ${s.path || savePath}` })
          setLoading(false)
        } else if (s.status === 'error') {
          clearInterval(pollRef.current)
          setStatus({ ok: false, msg: s.error || '오류 발생' })
          setLoading(false)
        }
      } catch (e) {
        clearInterval(pollRef.current)
        setStatus({ ok: false, msg: String(e) }); setLoading(false)
      }
    }, 1000)
  }

  if (!connected) return (
    <div className="empty-state" style={{ height: '100%' }}>
      <FileText size={40} opacity={0.3} />
      <p>클러스터에 연결되지 않았습니다.</p>
    </div>
  )

  const STEPS = [
    { num: 1, label: '대상 선택' },
    { num: 2, label: '포함 섹션' },
    { num: 3, label: 'AI 분석 · 생성' },
  ]

  return (
    <div style={{ display: 'flex', height: '100%', overflow: 'hidden' }}>

      {/* ── 메인 영역 ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

        {/* 헤더 */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 10,
          padding: '10px 20px', borderBottom: '1px solid var(--border)',
          background: 'var(--bg-1)', flexShrink: 0,
        }}>
          <FileText size={15} color="var(--nimbus)" />
          <h1 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-bright)', margin: 0 }}>
            클러스터 보고서
          </h1>
          <span style={{ flex: 1 }} />
          <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>DOCX(Word) 형식으로 저장</span>
        </div>

        {/* 스텝 헤더 */}
        <div style={{
          display: 'flex', alignItems: 'center', gap: 6,
          padding: '14px 24px', borderBottom: '1px solid var(--border)',
          background: 'var(--bg-1)', flexShrink: 0,
        }}>
          {STEPS.map((s, i) => (
            <React.Fragment key={s.num}>
              <button
                onClick={() => setStep(s.num)}
                style={{ background: 'none', border: 'none', cursor: 'pointer', padding: 0 }}
              >
                <StepHeader step={s} current={step} />
              </button>
              {i < STEPS.length - 1 && (
                <ChevronRight size={14} color="var(--border)" style={{ flexShrink: 0 }} />
              )}
            </React.Fragment>
          ))}
        </div>

        {/* 스텝 본문 */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 24px' }}>

          {/* ─── Step 1: 대상 선택 ─── */}
          {step === 1 && (
            <div style={{ maxWidth: 480 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-bright)', marginBottom: 4 }}>
                보고서 대상 선택
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 20 }}>
                보고서를 생성할 네임스페이스 범위를 선택하세요.
              </div>

              <div className="form-row">
                <label className="form-label">네임스페이스</label>
                <div style={{ position: 'relative', display: 'inline-block' }}>
                  <select className="select" value={namespace}
                    onChange={e => setNamespace(e.target.value)}
                    style={{ minWidth: 220, paddingRight: 28 }}>
                    {(namespaces.length ? namespaces : ['All Namespaces']).map(ns => (
                      <option key={ns}>{ns}</option>
                    ))}
                  </select>
                  <ChevronDown size={11} style={{
                    position: 'absolute', right: 8, top: '50%',
                    transform: 'translateY(-50%)', pointerEvents: 'none',
                    color: 'var(--text-dim)',
                  }} />
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 6 }}>
                  All Namespaces 선택 시 전체 클러스터 대상으로 수집
                </div>
              </div>

              <button className="btn btn-primary" onClick={() => setStep(2)}
                style={{ marginTop: 28, gap: 8 }}>
                다음: 포함 섹션 선택
                <ChevronRight size={14} />
              </button>
            </div>
          )}

          {/* ─── Step 2: 포함 섹션 ─── */}
          {step === 2 && (
            <div style={{ maxWidth: 560 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-bright)', marginBottom: 4 }}>
                포함할 섹션 선택
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 20 }}>
                보고서에 포함할 항목을 선택하세요. 선택 해제된 섹션은 수집하지 않습니다.
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
                {SECTIONS.map(sec => {
                  const on = sections[sec.key]
                  return (
                    <label key={sec.key} style={{
                      display: 'flex', alignItems: 'flex-start', gap: 10,
                      padding: '12px 14px', borderRadius: 8, cursor: 'pointer',
                      background: on ? 'rgba(52,211,153,0.06)' : 'var(--bg-2)',
                      border: `1px solid ${on ? 'rgba(52,211,153,0.3)' : 'var(--border)'}`,
                      transition: 'background 0.15s, border-color 0.15s',
                    }}>
                      <input
                        type="checkbox"
                        checked={on}
                        onChange={() => toggleSection(sec.key)}
                        style={{ accentColor: 'var(--nimbus)', width: 14, height: 14, marginTop: 1, flexShrink: 0 }}
                      />
                      <div>
                        <div style={{ fontSize: 12, fontWeight: 600, color: on ? 'var(--text-bright)' : 'var(--text)', marginBottom: 2 }}>
                          {sec.label}
                        </div>
                        <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.4 }}>
                          {sec.desc}
                        </div>
                      </div>
                    </label>
                  )
                })}
              </div>

              <div style={{ display: 'flex', gap: 10, marginTop: 24 }}>
                <button className="btn btn-default" onClick={() => setStep(1)}>이전</button>
                <button className="btn btn-primary" onClick={() => setStep(3)} style={{ gap: 8 }}>
                  다음: AI 분석 설정
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}

          {/* ─── Step 3: AI 분석 + 생성 ─── */}
          {step === 3 && (
            <div style={{ maxWidth: 480 }}>
              <div style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-bright)', marginBottom: 4 }}>
                AI 분석 및 보고서 생성
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-dim)', marginBottom: 20 }}>
                LLM 연동 시 수집된 데이터를 AI가 분석하여 요약과 권장사항을 추가합니다.
              </div>

              {/* AI 토글 */}
              <div style={{
                background: useAI ? 'rgba(52,211,153,0.06)' : 'var(--bg-2)',
                border: `1px solid ${useAI ? 'rgba(52,211,153,0.3)' : 'var(--border)'}`,
                borderRadius: 8, padding: '14px 16px', marginBottom: 16,
              }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 10, cursor: 'pointer' }}>
                  <input type="checkbox" checked={useAI} onChange={e => setUseAI(e.target.checked)}
                    style={{ accentColor: 'var(--nimbus)', width: 14, height: 14 }} />
                  <Bot size={14} color={useAI ? 'var(--nimbus)' : 'var(--text-dim)'} />
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: useAI ? 'var(--text-bright)' : 'var(--text)' }}>
                      LLM AI 분석 포함
                    </div>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 1 }}>
                      LM Studio, Ollama 등 OpenAI 호환 API
                    </div>
                  </div>
                </label>

                {useAI && (
                  <div style={{ marginTop: 14, display: 'flex', flexDirection: 'column', gap: 10, paddingTop: 12, borderTop: '1px solid var(--border)' }}>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>LLM API URL</div>
                      <input className="input" value={llmUrl} onChange={e => setLlmUrl(e.target.value)}
                        placeholder="http://localhost:1234"
                        style={{ width: '100%', fontSize: 12, fontFamily: 'var(--font-mono)' }} />
                      <div style={{
                        fontSize: 10.5,
                        color: isLocalLlmUrl(llmUrl) ? 'var(--text-dim)' : '#f59e0b',
                        marginTop: 6,
                        lineHeight: 1.5,
                      }}>
                        {isLocalLlmUrl(llmUrl)
                          ? '✓ localhost — 클러스터 데이터는 외부로 전송되지 않습니다.'
                          : '⚠️ 외부 URL — 수집된 클러스터 정보(노드/파드/리소스 메타데이터)가 해당 서버로 전송됩니다. 신뢰하는 호스트만 사용하세요.'}
                      </div>
                    </div>
                    <div>
                      <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>모델명</div>
                      <input className="input" value={llmModel} onChange={e => setLlmModel(e.target.value)}
                        placeholder="local-model"
                        style={{ width: '100%', fontSize: 12, fontFamily: 'var(--font-mono)' }} />
                    </div>
                  </div>
                )}
              </div>

              {/* 요약 확인 */}
              <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8, padding: '12px 14px', marginBottom: 20, fontSize: 12 }}>
                <div style={{ fontWeight: 600, color: 'var(--text-bright)', marginBottom: 8 }}>생성 요약</div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 4, color: 'var(--text-dim)' }}>
                  <div>대상: <span style={{ color: 'var(--text)' }}>{namespace}</span></div>
                  <div>섹션: <span style={{ color: 'var(--text)' }}>
                    {SECTIONS.filter(s => sections[s.key]).map(s => s.label).join(', ') || '없음'}
                  </span></div>
                  <div>AI 분석: <span style={{ color: useAI ? 'var(--nimbus)' : 'var(--text)' }}>{useAI ? '포함' : '미포함'}</span></div>
                </div>
              </div>

              <div style={{ display: 'flex', gap: 10 }}>
                <button className="btn btn-default" onClick={() => setStep(2)}>이전</button>
                <button className="btn btn-primary" onClick={generate} disabled={loading} style={{ gap: 8, padding: '8px 20px' }}>
                  {loading
                    ? <><div className="spinner" style={{ width: 14, height: 14 }} />생성 중...</>
                    : <><Download size={14} />보고서 생성 및 저장</>
                  }
                </button>
              </div>

              {/* 진행 로그 */}
              {logs.length > 0 && (
                <div style={{ marginTop: 20 }}>
                  <div style={{ fontSize: 11, fontWeight: 600, color: 'var(--text-dim)', marginBottom: 6 }}>진행 로그</div>
                  <div style={{
                    background: 'var(--bg-0)', border: '1px solid var(--border)', borderRadius: 6,
                    padding: '10px 14px', fontFamily: 'var(--font-mono)', fontSize: 11,
                    maxHeight: 200, overflowY: 'auto', color: 'var(--text)', lineHeight: 1.7,
                  }}>
                    {logs.map((line, i) => <div key={i}>{line}</div>)}
                    <div ref={logEndRef} />
                  </div>
                </div>
              )}

              {/* 상태 메시지 */}
              {status && (
                <div style={{
                  marginTop: 16,
                  background: status.ok ? 'var(--bg-3)' : 'var(--red-bg)',
                  color: status.ok ? 'var(--green)' : 'var(--red)',
                  border: `1px solid ${status.ok ? 'var(--border-bright)' : '#7f1d1d'}`,
                  borderRadius: 6, padding: '10px 14px', fontSize: 12, wordBreak: 'break-all',
                }}>
                  {status.ok ? '✓ ' : '✕ '}{status.msg}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
