import React, { useState, useEffect } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { buildPodExecCommand, buildPodLogTarget } from '../navigationTargets.js'
import { X, RefreshCw, ChevronDown, Copy, Maximize2, Terminal, Play } from 'lucide-react'
import MetricsTab from './MetricsTab.jsx'

const TABS_POD     = ['개요', '이벤트', '메트릭', '로그', 'YAML', 'Describe']
const TABS_DEFAULT = ['개요', '이벤트', 'YAML', 'Describe']

// ── 복사 가능한 모노스페이스 블록 ─────────────────────────────────────────────
function MonoBlock({ text, maxHeight = 480 }) {
  const [copied, setCopied] = useState(false)
  async function copy() {
    try { await navigator.clipboard.writeText(text || '') } catch {}
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }
  return (
    <div style={{ position: 'relative' }}>
      <button onClick={copy} style={{
        position: 'absolute', top: 6, right: 14, zIndex: 1,
        background: 'var(--bg-3)', border: '1px solid var(--border)',
        borderRadius: 4, padding: '2px 8px', cursor: 'pointer',
        fontSize: 10, color: 'var(--text-dim)',
        display: 'flex', alignItems: 'center', gap: 4,
      }}>
        <Copy size={9} />
        {copied ? '복사됨' : '복사'}
      </button>
      <pre style={{
        fontFamily: 'var(--font-mono)', fontSize: 11,
        lineHeight: 1.6, padding: '10px 12px',
        background: 'var(--bg-0)', border: '1px solid var(--border)',
        borderRadius: 6, overflowY: 'auto', maxHeight,
        whiteSpace: 'pre-wrap', wordBreak: 'break-all', margin: 0,
        color: 'var(--text)',
      }}>
        {text || '(내용 없음)'}
      </pre>
    </div>
  )
}

// ── 정보 행 ──────────────────────────────────────────────────────────────────
function InfoRow({ label, value }) {
  return (
    <div style={{ display: 'flex', gap: 8, marginBottom: 5, fontSize: 12 }}>
      <span style={{ color: 'var(--text-dim)', minWidth: 90, flexShrink: 0,
        fontWeight: 600, fontSize: 11 }}>{label}</span>
      <span style={{ color: 'var(--text)', wordBreak: 'break-all' }}>{value ?? 'N/A'}</span>
    </div>
  )
}

// ── 섹션 타이틀 ──────────────────────────────────────────────────────────────
function SectionTitle({ children }) {
  return (
    <div style={{
      fontSize: 10, fontWeight: 700, color: 'var(--text-dim)',
      textTransform: 'uppercase', letterSpacing: '0.08em',
      marginBottom: 8, marginTop: 4,
      paddingBottom: 4, borderBottom: '1px solid var(--border)',
    }}>
      {children}
    </div>
  )
}

// ── 로딩 스피너 ──────────────────────────────────────────────────────────────
function Loading() {
  return (
    <div className="empty-state" style={{ height: 80 }}>
      <div className="spinner" />
    </div>
  )
}

// ── 에러 표시 ────────────────────────────────────────────────────────────────
function ErrMsg({ msg }) {
  return <div style={{ color: 'var(--red)', fontSize: 12, padding: '10px 0' }}>{msg}</div>
}

// ── 메인 패널 ────────────────────────────────────────────────────────────────
export default function ResourcePanel({ item, kind, onClose, onDelete }) {
  const isPod     = kind === 'pods'
  const isCronJob = kind === 'cronjobs'
  const TABS  = isPod ? TABS_POD : TABS_DEFAULT
  const { navigate, setLogTarget, setTerminalCommand } = useApp()

  const [tab, setTab]           = useState('개요')
  const [detail, setDetail]     = useState(null)   // pod detail
  const [events, setEvents]     = useState(null)
  const [logs, setLogs]         = useState(null)
  const [yaml, setYaml]         = useState(null)
  const [describe, setDescribe] = useState(null)
  const [container, setContainer] = useState('')
  const [tail, setTail]         = useState(200)
  const [busy, setBusy]         = useState(false)
  const [triggerMsg, setTriggerMsg] = useState(null)   // {ok, text} CronJob 트리거 결과

  const ns   = item?.namespace || ''
  const name = item?.name      || ''

  // item 변경 시 상태 초기화 + 초기 로드
  useEffect(() => {
    if (!item) return
    setTab('개요')
    setDetail(null); setEvents(null); setLogs(null)
    setYaml(null);   setDescribe(null); setContainer('')
    setTriggerMsg(null)

    if (isPod) loadDetail()
    loadEvents()
  }, [name, ns, kind])

  // ── CronJob 즉시 실행 ─────────────────────────────────────────────────────
  async function triggerCronJob() {
    if (!isCronJob || !ns || !name) return
    if (!window.confirm(`CronJob "${name}"을(를) 지금 1회 실행하시겠습니까?\n\n` +
                        `네임스페이스: ${ns}\n` +
                        `새 Job이 생성됩니다 (이름: ${name}-manual-<timestamp>)`)) {
      return
    }
    setBusy(true)
    setTriggerMsg(null)
    try {
      const r = await api.triggerCronjob(ns, name)
      if (r?.ok) {
        setTriggerMsg({ ok: true, text: `Job 생성됨: ${r.job_name}` })
        loadEvents()  // 새로 트리거된 이벤트 보일 수 있도록 새로고침
      } else {
        setTriggerMsg({ ok: false, text: r?.error || '실행 실패 (응답 없음)' })
      }
    } catch (e) {
      setTriggerMsg({ ok: false, text: String(e) })
    } finally {
      setBusy(false)
    }
  }

  // 탭 클릭 시 lazy 로드
  useEffect(() => {
    if (!item) return
    if (tab === 'YAML'    && !yaml)    loadYaml()
    if (tab === 'Describe'&& !describe) loadDescribe()
    if (tab === '로그' && isPod && !detail) loadDetail()
  }, [tab])

  // container가 결정되면 로그 탭에 있을 때 자동 로드
  useEffect(() => {
    if (tab === '로그' && container && !logs) loadLogs()
  }, [container])

  async function loadDetail() {
    setBusy(true)
    try {
      const d = await api.getPodDetail(ns, name)
      setDetail(d)
      if (!container && d?.containers?.length > 0) {
        setContainer(d.containers[0].name)
      }
    } catch (e) { setDetail({ ok: false, error: String(e) }) }
    setBusy(false)
  }

  async function loadEvents() {
    if (!ns) { setEvents([]); return }
    try {
      const e = await api.getResourceEvents(kind, ns, name)
      setEvents(Array.isArray(e) ? e : [])
    } catch { setEvents([]) }
  }

  async function loadLogs() {
    setBusy(true)
    try {
      const r = await api.getResourceLogs(ns, name, container, tail)
      setLogs(r)
    } catch (e) { setLogs({ ok: false, error: String(e), logs: '' }) }
    setBusy(false)
  }

  async function loadYaml() {
    setBusy(true)
    try {
      const r = await api.getResourceYaml(kind, ns, name)
      setYaml(r)
    } catch (e) { setYaml({ ok: false, error: String(e), yaml: '' }) }
    setBusy(false)
  }

  async function loadDescribe() {
    setBusy(true)
    try {
      const r = await api.getResourceDescribe(kind, ns, name)
      setDescribe(r)
    } catch (e) { setDescribe({ ok: false, error: String(e), describe: '' }) }
    setBusy(false)
  }

  function selectedContainer() {
    return container || detail?.containers?.[0]?.name || ''
  }

  function openLogViewer() {
    setLogTarget(buildPodLogTarget({
      namespace: ns,
      name,
      container: selectedContainer(),
      tail,
    }))
    navigate('logs')
  }

  async function openExecShell() {
    const selected = selectedContainer()
    const fallback = buildPodExecCommand({ namespace: ns, name, container: selected })
    try {
      const res = await api.openPodShell(ns, name, selected)
      if (res?.ok) return
    } catch {}
    setTerminalCommand(fallback)
    navigate('terminal')
  }

  if (!item) return null

  // row 데이터에서 내부 키(_로 시작) 제거
  const rowInfo = Object.entries(item).filter(([k]) => !k.startsWith('_'))

  return (
    <div style={{
      width: 500, flexShrink: 0,
      display: 'flex', flexDirection: 'column',
      borderLeft: '1px solid var(--border)',
      background: 'var(--bg-1)',
      overflow: 'hidden',
    }}>

      {/* ── 패널 헤더 ── */}
      <div style={{
        padding: '9px 14px',
        borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 8,
        background: 'var(--bg-2)', flexShrink: 0,
      }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{
            fontSize: 12, fontWeight: 700, color: 'var(--text-bright)',
            fontFamily: 'var(--font-mono)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
          }} title={name}>{name}</div>
          {ns && (
            <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>{ns}</div>
          )}
        </div>
        {isPod && (
          <>
            <button className="btn btn-default btn-sm" onClick={openLogViewer}
              title="Open in Log Viewer" style={{ flexShrink: 0, gap: 4 }}>
              <Maximize2 size={12} /> Logs
            </button>
            <button className="btn btn-default btn-sm" onClick={openExecShell}
              title="Open interactive pod shell" style={{ flexShrink: 0, gap: 4 }}>
              <Terminal size={12} /> Exec
            </button>
          </>
        )}
        {isCronJob && (
          <button className="btn btn-primary btn-sm" onClick={triggerCronJob}
            disabled={busy} title="CronJob을 스케줄과 무관하게 즉시 1회 실행"
            style={{ flexShrink: 0, gap: 4 }}>
            <Play size={11} /> 지금 실행
          </button>
        )}
        <button className="btn btn-danger btn-sm" onClick={() => onDelete?.(item)}
          style={{ flexShrink: 0, fontSize: 11 }}>삭제</button>
        <button className="btn btn-ghost btn-sm" onClick={onClose}
          style={{ flexShrink: 0 }}><X size={13} /></button>
      </div>

      {/* ── 탭 바 ── */}
      <div style={{
        display: 'flex', borderBottom: '1px solid var(--border)',
        background: 'var(--bg-2)', flexShrink: 0, overflowX: 'auto',
      }}>
        {TABS.map(t => (
          <button key={t} onClick={() => setTab(t)} style={{
            padding: '6px 13px', fontSize: 12,
            fontWeight: tab === t ? 700 : 400,
            color: tab === t ? 'var(--nimbus)' : 'var(--text-dim)',
            background: 'none', border: 'none', cursor: 'pointer',
            borderBottom: tab === t
              ? '2px solid var(--nimbus)' : '2px solid transparent',
            whiteSpace: 'nowrap', flexShrink: 0,
            transition: 'color 0.15s',
          }}>{t}</button>
        ))}
        {busy && (
          <div className="spinner" style={{
            width: 12, height: 12, margin: 'auto 8px', flexShrink: 0,
          }} />
        )}
      </div>

      {/* CronJob 트리거 결과 (inline 알림) */}
      {triggerMsg && (
        <div style={{
          padding: '8px 14px',
          background: triggerMsg.ok ? 'rgba(52,211,153,0.10)' : 'rgba(248,113,113,0.10)',
          borderBottom: '1px solid var(--border)',
          color: triggerMsg.ok ? 'var(--nimbus)' : 'var(--red)',
          fontSize: 11.5, display: 'flex', alignItems: 'center', gap: 8,
          flexShrink: 0,
        }}>
          <span style={{ flex: 1 }}>{triggerMsg.text}</span>
          <button onClick={() => setTriggerMsg(null)} className="btn btn-ghost btn-sm">
            <X size={11} />
          </button>
        </div>
      )}

      {/* ── 탭 내용 ── */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '12px 14px' }}>

        {/* ════ 개요 ════ */}
        {tab === '개요' && (
          <div>
            {/* 기본 row 데이터 */}
            <SectionTitle>기본 정보</SectionTitle>
            {rowInfo.map(([k, v]) => (
              <InfoRow key={k} label={k} value={String(v ?? '')} />
            ))}

            {/* 파드 상세 */}
            {isPod && !detail && <Loading />}
            {isPod && detail && !detail.ok && <ErrMsg msg={detail.error} />}
            {isPod && detail?.ok && (
              <>
                <SectionTitle style={{ marginTop: 16 }}>파드 상세</SectionTitle>
                <InfoRow label="Phase"    value={detail.phase} />
                <InfoRow label="Pod IP"   value={detail.pod_ip} />
                <InfoRow label="Host IP"  value={detail.host_ip} />
                <InfoRow label="Node"     value={detail.node} />
                <InfoRow label="QoS"      value={detail.qos} />
                <InfoRow label="Started"  value={detail.start_time} />

                {/* 컨테이너 */}
                {detail.containers?.length > 0 && (
                  <>
                    <SectionTitle>컨테이너</SectionTitle>
                    {detail.containers.map(c => (
                      <div key={c.name} style={{
                        background: 'var(--bg-3)', borderRadius: 6,
                        padding: '8px 10px', marginBottom: 7,
                        border: `1px solid ${c.ready ? 'var(--border)' : 'rgba(220,38,38,.3)'}`,
                      }}>
                        <div style={{
                          display: 'flex', justifyContent: 'space-between',
                          alignItems: 'center', marginBottom: 5,
                        }}>
                          <span style={{
                            fontWeight: 700, fontSize: 12,
                            fontFamily: 'var(--font-mono)', color: 'var(--text-bright)',
                          }}>{c.name}</span>
                          <span className={`chip ${c.ready ? 'chip-green' : 'chip-red'}`}>
                            {c.ready ? 'Ready' : 'Not Ready'}
                          </span>
                        </div>
                        <div style={{
                          fontSize: 10, color: 'var(--text-dim)', marginBottom: 4,
                          fontFamily: 'var(--font-mono)', wordBreak: 'break-all',
                        }}>{c.image}</div>
                        <div style={{
                          fontSize: 11, color: 'var(--text)',
                          display: 'flex', gap: 16,
                        }}>
                          <span>상태: <span style={{ color: 'var(--nimbus)' }}>{c.state}</span></span>
                          <span>재시작: <span style={{
                            color: c.restarts > 20 ? 'var(--red)'
                                 : c.restarts > 5  ? 'var(--yellow)' : 'var(--text)',
                            fontWeight: c.restarts > 5 ? 700 : 400,
                          }}>{c.restarts}</span></span>
                        </div>
                      </div>
                    ))}
                  </>
                )}

                {/* Init 컨테이너 */}
                {detail.init_containers?.length > 0 && (
                  <>
                    <SectionTitle>Init 컨테이너</SectionTitle>
                    {detail.init_containers.map(c => (
                      <div key={c.name} style={{
                        background: 'var(--bg-3)', borderRadius: 6,
                        padding: '7px 10px', marginBottom: 6,
                        border: '1px solid var(--border)',
                        fontSize: 12,
                      }}>
                        <span style={{ fontWeight: 700, fontFamily: 'var(--font-mono)' }}>
                          {c.name}
                        </span>
                        <span style={{ color: 'var(--text-dim)', marginLeft: 10 }}>
                          {c.state}
                        </span>
                      </div>
                    ))}
                  </>
                )}

                {/* 컨디션 */}
                {detail.conditions?.length > 0 && (
                  <>
                    <SectionTitle>컨디션</SectionTitle>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                      {detail.conditions.map((c, i) => (
                        <span key={i} className={`chip ${c.status === 'True' ? 'chip-green' : 'chip-dim'}`}>
                          {c.type}
                        </span>
                      ))}
                    </div>
                  </>
                )}

                {/* 볼륨 */}
                {detail.volumes?.length > 0 && (
                  <>
                    <SectionTitle>볼륨 ({detail.volumes.length})</SectionTitle>
                    <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.8,
                      fontFamily: 'var(--font-mono)' }}>
                      {detail.volumes.join(' · ')}
                    </div>
                  </>
                )}

                {/* 레이블 */}
                {Object.keys(detail.labels || {}).length > 0 && (
                  <>
                    <SectionTitle>레이블</SectionTitle>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4 }}>
                      {Object.entries(detail.labels).slice(0, 20).map(([k, v]) => (
                        <span key={k} style={{
                          fontSize: 10, padding: '2px 7px',
                          background: 'var(--bg-4)', borderRadius: 20,
                          color: 'var(--text-dim)', fontFamily: 'var(--font-mono)',
                        }}>{k}={v}</span>
                      ))}
                    </div>
                  </>
                )}
              </>
            )}
          </div>
        )}

        {/* ════ 이벤트 ════ */}
        {tab === '이벤트' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
              <button className="btn btn-ghost btn-sm" onClick={loadEvents}>
                <RefreshCw size={11} /> 새로고침
              </button>
            </div>
            {events === null ? <Loading /> :
             events.length === 0 ? (
              <div style={{ color: 'var(--text-dim)', fontSize: 12,
                textAlign: 'center', marginTop: 30 }}>이벤트 없음</div>
            ) : (
              events.map((e, i) => (
                <div key={i} style={{
                  padding: '8px 10px', marginBottom: 6,
                  background: 'var(--bg-2)', borderRadius: 6,
                  border: `1px solid ${e.type === 'Warning'
                    ? 'rgba(220,38,38,.25)' : 'var(--border)'}`,
                }}>
                  <div style={{
                    display: 'flex', justifyContent: 'space-between',
                    alignItems: 'center', marginBottom: 5,
                  }}>
                    <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
                      <span className={`chip ${e.type === 'Warning' ? 'chip-red' : 'chip-blue'}`}>
                        {e.reason || e.type}
                      </span>
                      {e.source && (
                        <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>
                          {e.source}
                        </span>
                      )}
                    </div>
                    <span style={{ fontSize: 10, color: 'var(--text-dim)', flexShrink: 0 }}>
                      {e.age} · ×{e.count}
                    </span>
                  </div>
                  <div style={{
                    fontSize: 11, color: 'var(--text)', lineHeight: 1.5,
                    wordBreak: 'break-word',
                  }}>{e.message}</div>
                </div>
              ))
            )}
          </div>
        )}

        {/* ════ 메트릭 (파드 전용) ════ */}
        {tab === '메트릭' && isPod && (
          <MetricsTab ns={ns} name={name} />
        )}

        {/* ════ 로그 (파드 전용) ════ */}
        {tab === '로그' && isPod && (
          <div>
            {/* 컨트롤 바 */}
            <div style={{
              display: 'flex', gap: 8, alignItems: 'center',
              marginBottom: 10, flexWrap: 'wrap',
            }}>
              {/* 컨테이너 선택 */}
              {detail?.containers?.length > 0 && (
                <div style={{ position: 'relative' }}>
                  <select className="select" value={container}
                    onChange={e => setContainer(e.target.value)}
                    style={{ fontSize: 11, paddingRight: 22 }}>
                    {detail.containers.map(c => (
                      <option key={c.name} value={c.name}>{c.name}</option>
                    ))}
                  </select>
                  <ChevronDown size={10} style={{
                    position: 'absolute', right: 6, top: '50%',
                    transform: 'translateY(-50%)', pointerEvents: 'none',
                    color: 'var(--text-dim)',
                  }} />
                </div>
              )}
              {/* Tail 줄 수 */}
              <div style={{ position: 'relative' }}>
                <select className="select" value={tail}
                  onChange={e => setTail(Number(e.target.value))}
                  style={{ fontSize: 11, paddingRight: 22, width: 100 }}>
                  {[50, 100, 200, 500, 1000].map(n => (
                    <option key={n} value={n}>최근 {n}줄</option>
                  ))}
                </select>
                <ChevronDown size={10} style={{
                  position: 'absolute', right: 6, top: '50%',
                  transform: 'translateY(-50%)', pointerEvents: 'none',
                  color: 'var(--text-dim)',
                }} />
              </div>
              <button className="btn btn-default btn-sm" onClick={loadLogs} disabled={busy}>
                <RefreshCw size={11} /> 로드
              </button>
              <button className="btn btn-default btn-sm" onClick={openLogViewer}>
                <Maximize2 size={11} /> Log Viewer
              </button>
            </div>

            {logs === null ? (
              <div style={{ color: 'var(--text-dim)', fontSize: 12 }}>
                로드 버튼을 눌러 로그를 가져오세요.
              </div>
            ) : logs.ok === false ? (
              <ErrMsg msg={logs.error} />
            ) : (
              <MonoBlock text={logs.logs} maxHeight={500} />
            )}
          </div>
        )}

        {/* ════ YAML ════ */}
        {tab === 'YAML' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
              <button className="btn btn-ghost btn-sm" onClick={loadYaml} disabled={busy}>
                <RefreshCw size={11} /> 새로고침
              </button>
            </div>
            {yaml === null ? <Loading /> :
             yaml.ok === false ? <ErrMsg msg={yaml.error} /> :
             <MonoBlock text={yaml.yaml} maxHeight={520} />}
          </div>
        )}

        {/* ════ Describe ════ */}
        {tab === 'Describe' && (
          <div>
            <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 8 }}>
              <button className="btn btn-ghost btn-sm" onClick={loadDescribe} disabled={busy}>
                <RefreshCw size={11} /> 새로고침
              </button>
            </div>
            {describe === null ? <Loading /> :
             describe.ok === false ? <ErrMsg msg={describe.error} /> :
             <MonoBlock text={describe.describe} maxHeight={520} />}
          </div>
        )}

      </div>
    </div>
  )
}
