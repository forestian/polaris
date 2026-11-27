import React, { useEffect, useState, useMemo } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { RefreshCw, Globe, Search, X, Lock, ArrowRight, AlertTriangle, CheckCircle2, Clock, Layers } from 'lucide-react'
import { buildApps, filterApps, workloadHealth, kindLabel, FILTERS, USE_LABEL } from '../topologyApps.js'

/**
 * 토폴로지 (v1.4.31 전면 개편) — 앱 단위 지도.
 *
 * 예전: 클러스터 전체를 6열 그래프 하나로 — 열마다 위에서부터 쌓아 선이 화면을 가로질러 엉켰다(「보기가 복잡해 잘 안 보게 된다」).
 * 지금: 서로 이어진 Ingress → Service → 워크로드를 **앱 하나**로 묶어 카드로. 카드 안은 왼쪽에서 오른쪽으로
 * 「외부 진입 → 서비스 → 워크로드 → 쓰는 것(설정 · 저장소)」 만 읽으면 된다. 문제 있는 앱이 맨 위.
 * 묶는 규칙은 topologyApps.js, 데이터는 src/api/topology.py.
 */

const PAGE = 60          // 앱이 많으면 이만큼씩 — 카드 수백 개를 한꺼번에 그리면 느리다

// 상태 색 — 밝은 테마에서도 읽히게 테마 글자색과 섞는다
const ink = (c) => `color-mix(in srgb, ${c} 65%, var(--text-bright))`
const LEVEL = {
  // hue — 점 · 테두리에 그대로, 글자에는 ink() 로 섞어서만 쓴다(밝은 테마 대비)
  bad:  { hue: '#ef4444', label: '문제' },
  warn: { hue: '#f59e0b', label: '주의' },
  ok:   { hue: '#22c55e', label: '정상' },
  idle: { hue: '#94a3b8', label: '대기' },
}
const KIND_TEXT = { exposed: '외부 노출', internal: '내부 서비스', batch: '배치 작업', background: '백그라운드' }
const NAV = {
  Deployment: 'deployments', StatefulSet: 'statefulsets', DaemonSet: 'daemonsets', Job: 'jobs', CronJob: 'cronjobs',
  service: 'services', ingress: 'ingresses', configmap: 'configmaps', secret: 'secrets', pvc: 'pvcs',
}

export default function TopologyPage() {
  const { connected, namespaces, namespace: globalNs, navigate } = useApp()
  const [ns, setNs] = useState(() => (globalNs === 'All Namespaces' ? '' : globalNs))
  const [raw, setRaw] = useState(null)
  const [loading, setLoading] = useState(false)
  const [errMsg, setErrMsg] = useState('')
  const [filter, setFilter] = useState('all')
  const [q, setQ] = useState('')
  const [sel, setSel] = useState(null)          // {item, role}
  const [limit, setLimit] = useState(PAGE)

  async function load() {
    if (!connected) return
    setLoading(true); setErrMsg(''); setSel(null)
    try {
      const d = await api.getTopologyData(ns)
      if (d?.ok === false) { setErrMsg(d.error || '데이터를 모으지 못했습니다'); setRaw(null) }
      else setRaw(d)
    } catch (e) { setErrMsg(String(e)); setRaw(null) }
    setLoading(false)
  }
  useEffect(() => { load() }, [connected, ns])            // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => { setLimit(PAGE) }, [filter, q, ns])

  const { apps, counts } = useMemo(() => buildApps(raw), [raw])
  const shown = useMemo(() => filterApps(apps, filter, q), [apps, filter, q])

  function open(item, role) {
    const key = role === 'workload' || role === 'cronjob' ? item.kind : role === 'use' ? item.type : role
    const res = NAV[key]
    if (res) navigate('resources', res)
  }

  if (!connected) return (
    <div className="empty-state" style={{ height: '100%' }}>
      <Globe size={40} opacity={0.25} />
      <p style={{ fontWeight: 600, marginTop: 10 }}>클러스터에 연결되지 않았습니다.</p>
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 머리 — 무엇을 보는 화면인지 · 네임스페이스 · 찾기 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '10px 16px', borderBottom: '1px solid var(--border)',
                    background: 'var(--bg-1)', flexShrink: 0, flexWrap: 'wrap' }}>
        <Globe size={16} color="var(--nimbus)" />
        <div>
          <div style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-bright)' }}>토폴로지</div>
          <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>앱마다 외부 진입 → 서비스 → 워크로드 → 쓰는 설정 · 저장소</div>
        </div>
        <div style={{ flex: 1 }} />
        <select className="select" value={ns} onChange={e => setNs(e.target.value)} style={{ fontSize: 12, minWidth: 160 }}
          title="네임스페이스">
          <option value="">모든 네임스페이스</option>
          {(namespaces ?? []).filter(n => n !== 'All Namespaces').map(n => <option key={n} value={n}>{n}</option>)}
        </select>
        <div style={{ position: 'relative' }}>
          <Search size={12} style={{ position: 'absolute', left: 8, top: 8, color: 'var(--text-dim)' }} />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder="앱 · 주소 · 리소스 이름"
            onKeyDown={e => { if (e.key === 'Escape') setQ('') }}
            style={{ width: 220, padding: '5px 26px', fontSize: 12, background: 'var(--bg-0)', color: 'var(--text)',
                     border: '1px solid var(--border)', borderRadius: 5, fontFamily: 'var(--font)' }} />
          {q && <button onClick={() => setQ('')} className="btn btn-ghost btn-sm"
            style={{ position: 'absolute', right: 2, top: 1, padding: '2px 5px' }}><X size={11} /></button>}
        </div>
        <button className="btn btn-default btn-sm" onClick={load} disabled={loading}>
          <RefreshCw size={12} className={loading ? 'spin' : ''} /> 새로고침
        </button>
      </div>

      {/* 거르기 — 수와 함께 */}
      {raw && !loading && (
        <div style={{ display: 'flex', gap: 6, padding: '8px 16px', borderBottom: '1px solid var(--border)', flexShrink: 0, flexWrap: 'wrap' }}>
          {FILTERS.map(f => {
            const n = counts[f.id] ?? 0
            const on = filter === f.id
            const alert = f.id === 'problem' && n > 0
            return (
              <button key={f.id} onClick={() => setFilter(f.id)} style={{
                display: 'flex', alignItems: 'center', gap: 6, padding: '4px 11px', borderRadius: 14, cursor: 'pointer', fontSize: 12,
                fontFamily: 'var(--font)',
                border: `1px solid ${on ? 'var(--nimbus)' : alert ? ink(LEVEL.bad.hue) : 'var(--border)'}`,
                background: on ? 'color-mix(in srgb, var(--nimbus) 14%, transparent)' : 'transparent',
                color: alert ? ink(LEVEL.bad.hue) : on ? 'var(--text-bright)' : 'var(--text-mid)' }}>
                {f.id === 'problem' && n > 0 && <AlertTriangle size={11} />}
                {f.label} <b>{n}</b>
              </button>
            )
          })}
          {(q || filter !== 'all') && <span style={{ fontSize: 11.5, color: 'var(--text-dim)', alignSelf: 'center' }}>— {shown.length}개 보임</span>}
        </div>
      )}

      <div style={{ flex: 1, minHeight: 0, display: 'flex' }}>
        <div style={{ flex: 1, minWidth: 0, overflow: 'auto', padding: '12px 16px', background: 'var(--bg-0)' }}>
          {loading ? (
            <div className="empty-state" style={{ minHeight: 300 }}><div className="spinner" /><span>클러스터에서 모으는 중…</span></div>
          ) : errMsg ? (
            <div className="empty-state" style={{ minHeight: 300 }}><p style={{ color: 'var(--red)' }}>{errMsg}</p></div>
          ) : !apps.length ? (
            <div className="empty-state" style={{ minHeight: 300 }}>
              <Layers size={36} opacity={0.2} />
              <p style={{ fontWeight: 600, marginTop: 10 }}>보여 줄 앱이 없습니다.</p>
              <p style={{ fontSize: 12, color: 'var(--text-dim)' }}>다른 네임스페이스를 고르세요.</p>
            </div>
          ) : !shown.length ? (
            <div className="empty-state" style={{ minHeight: 200 }}>
              <p style={{ color: 'var(--text-dim)' }}>{filter === 'problem' ? '문제 있는 앱이 없습니다.' : '조건에 맞는 앱이 없습니다.'}</p>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {shown.slice(0, limit).map(app => (
                <AppCard key={app.id} app={app} showNs={!ns} selId={sel?.item?.id} onPick={(item, role) => setSel({ item, role, app })} />
              ))}
              {shown.length > limit && (
                <button className="btn btn-default" onClick={() => setLimit(l => l + PAGE)} style={{ alignSelf: 'center' }}>
                  {shown.length - limit}개 더 보기</button>)}
            </div>
          )}
        </div>
        {sel && <Detail sel={sel} onClose={() => setSel(null)} onOpen={open} />}
      </div>
    </div>
  )
}

// ── 앱 카드 ─────────────────────────────────────────────────────────────────
export function AppCard({ app, showNs, selId, onPick }) {
  const lv = LEVEL[app.health.level]
  const batch = app.kind === 'batch'
  // 외부 진입 · 서비스가 둘 다 없는 앱(DaemonSet · 백그라운드 작업)은 그 칸을 빼고 워크로드부터 — 「없음」 두 칸은 읽을 거리가 없다
  const bare = !batch && !app.ingresses.length && !app.services.length
  const cols = batch ? 'minmax(0,1fr) 18px minmax(0,1.4fr) 18px minmax(0,1.2fr)'
    : bare ? 'minmax(0,1.3fr) 18px minmax(0,1.2fr) minmax(0,2.1fr)'
    : 'minmax(0,1.1fr) 18px minmax(0,1fr) 18px minmax(0,1.3fr) 18px minmax(0,1.2fr)'
  return (
    <div style={{ borderRadius: 8, background: 'var(--bg-1)',
                  border: `1px solid ${app.health.level === 'bad' ? `color-mix(in srgb, ${lv.hue} 55%, var(--border))` : 'var(--border)'}` }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '9px 12px', borderBottom: '1px solid var(--border)', flexWrap: 'wrap' }}>
        <span title={lv.label} style={{ width: 9, height: 9, borderRadius: '50%', background: lv.hue, flexShrink: 0 }} />
        <b style={{ fontSize: 13.5, color: 'var(--text-bright)' }}>{app.name}</b>
        {showNs && app.ns && <span style={tag}>{app.ns}</span>}
        <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>{KIND_TEXT[app.kind]}</span>
        {app.health.text && <span style={{ fontSize: 11.5, color: ink(lv.hue), fontWeight: 600 }}>{app.health.text}</span>}
        <div style={{ flex: 1 }} />
        {app.hosts.slice(0, 3).map(h => {
          const tls = app.ingresses.some(i => (i.tls_hosts || []).includes(h))
          return <span key={h} style={{ ...tag, fontFamily: 'var(--font-mono)', color: 'var(--text)' }}
            title={tls ? 'TLS(https)' : 'TLS 없음(http)'}>{tls && <Lock size={9} style={{ verticalAlign: -1, marginRight: 3 }} />}{h}</span>
        })}
        {app.hosts.length > 3 && <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>외 {app.hosts.length - 3}</span>}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: cols, gap: 6, padding: '10px 12px', alignItems: 'start' }}>
        {bare ? (
          <>
            <Lane title="워크로드" empty="없음">{app.workloads.map(w => <Item key={w.id} item={w} role="workload" selId={selId} onPick={onPick} />)}</Lane>
            <Arrow dim={!app.uses.length} />
            <Lane title="쓰는 것" empty="없음">{app.uses.map(u => <Item key={u.id} item={u} role="use" selId={selId} onPick={onPick} />)}</Lane>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', paddingTop: 22, lineHeight: 1.6 }}>
              Service · Ingress 가 없어 밖에서 부르지 않는 워크로드입니다(노드마다 도는 수집기 · 백그라운드 작업 등).</div>
          </>
        ) : batch ? (
          <>
            <Lane title="일정">{app.cronjobs.map(c => <Item key={c.id} item={c} role="cronjob" selId={selId} onPick={onPick} />)}</Lane>
            <Arrow />
            <Lane title="최근 실행" empty="아직 실행된 적 없음"><Jobs jobs={app.jobs} selId={selId} onPick={onPick} /></Lane>
            <Arrow />
            <Lane title="쓰는 것" empty="없음">{app.uses.map(u => <Item key={u.id} item={u} role="use" selId={selId} onPick={onPick} />)}</Lane>
          </>
        ) : (
          <>
            <Lane title="외부 진입" empty={app.services.length ? '없음(클러스터 안에서만)' : '없음'}>
              {app.ingresses.map(i => <Item key={i.id} item={i} role="ingress" selId={selId} onPick={onPick} />)}
            </Lane>
            <Arrow dim={!app.ingresses.length} />
            <Lane title="서비스" empty="없음">{app.services.map(s => <Item key={s.id} item={s} role="service" selId={selId} onPick={onPick} />)}</Lane>
            <Arrow dim={!app.services.length} />
            <Lane title="워크로드" empty="없음">{app.workloads.map(w => <Item key={w.id} item={w} role="workload" selId={selId} onPick={onPick} />)}</Lane>
            <Arrow dim={!app.uses.length} />
            <Lane title="쓰는 것" empty="없음">{app.uses.map(u => <Item key={u.id} item={u} role="use" selId={selId} onPick={onPick} />)}</Lane>
          </>
        )}
      </div>
    </div>
  )
}

function Lane({ title, children, empty }) {
  const items = React.Children.toArray(children).filter(Boolean)
  return (
    <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: 5 }}>
      <div style={{ fontSize: 10.5, color: 'var(--text-dim)', fontWeight: 600 }}>{title}</div>
      {items.length ? items : <div style={{ fontSize: 11.5, color: 'var(--text-dim)', padding: '6px 0' }}>{empty}</div>}
    </div>
  )
}

const Arrow = ({ dim }) => (
  <div style={{ paddingTop: 26, color: 'var(--text-dim)', opacity: dim ? 0.3 : 0.8, display: 'flex', justifyContent: 'center' }}>
    <ArrowRight size={14} /></div>)

// ── 항목 하나(누르면 상세) ─────────────────────────────────────────────────
function Item({ item, role, selId, onPick }) {
  const on = selId === item.id
  let head, body = null, level = null
  if (role === 'ingress') {
    head = 'Ingress'
    body = (item.rules || []).slice(0, 4).map((r, i) => (
      <div key={i} style={{ ...mono, color: 'var(--text-mid)' }}>{(r.host || '*') + (r.path || '/')} <span style={{ color: 'var(--text-dim)' }}>→ {r.svc}</span></div>))
  } else if (role === 'service') {
    head = `Service · ${item.type || 'ClusterIP'}`
    if (item.ports?.length) body = <div style={{ ...mono, color: 'var(--text-mid)' }}>{item.ports.join(', ')}</div>
  } else if (role === 'workload') {
    const h = workloadHealth(item)
    level = h.level
    head = kindLabel(item)
    body = (
      <>
        <Pods w={item} />
        <div style={{ color: ink(LEVEL[h.level].hue), fontSize: 11 }}>{h.text}</div>
        {item.images?.[0] && <div style={{ ...mono, color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}
          title={item.images.join('\n')}>{item.images[0]}{item.images.length > 1 ? ` 외 ${item.images.length - 1}` : ''}</div>}
      </>)
  } else if (role === 'cronjob') {
    head = 'CronJob'
    body = <div style={{ ...mono, color: 'var(--text-mid)' }}><Clock size={10} style={{ verticalAlign: -1 }} /> {item.schedule}</div>
  } else {
    head = USE_LABEL[item.type] || item.type
    body = (
      <>
        {item.pv && <div style={{ ...mono, color: 'var(--text-dim)' }}>→ PV {item.pv.name}{item.pv.status ? ` (${item.pv.status})` : ''}</div>}
        {item.sharedBy > 1 && <div style={{ fontSize: 11, color: ink(LEVEL.warn.hue) }}>{item.sharedBy}개 앱이 함께 씀</div>}
      </>)
  }
  const lc = level ? LEVEL[level].hue : null
  return (
    <button onClick={() => onPick(item, role)} title="누르면 자세히" style={{
      textAlign: 'left', width: '100%', padding: '6px 8px', borderRadius: 6, cursor: 'pointer', fontFamily: 'var(--font)',
      background: on ? 'var(--bg-3)' : 'var(--bg-2)', fontSize: 11.5, display: 'flex', flexDirection: 'column', gap: 2,
      border: `1px solid ${on ? 'var(--nimbus)' : level === 'bad' ? ink(lc) : 'var(--border)'}` }}>
      <div style={{ fontSize: 10, color: 'var(--text-dim)' }}>{head}</div>
      <div style={{ color: 'var(--text-bright)', fontWeight: 600, wordBreak: 'break-all' }}>{item.name}</div>
      {body}
    </button>
  )
}

/** 파드 점 — 준비 ● 초록, 안 됨 ● 주황/빨강. 많으면 수로 */
function Pods({ w }) {
  const total = w.total || 0
  if (!total) return null
  const ready = w.ready ?? w.running ?? 0
  const bad = (w.waiting || []).length > 0
  if (total > 12) return <div style={{ fontSize: 11, color: 'var(--text-mid)' }}>파드 {ready}/{total}</div>
  return (
    <div style={{ display: 'flex', gap: 3, flexWrap: 'wrap', margin: '2px 0' }} title={`파드 ${ready}/${total} 준비`}>
      {Array.from({ length: total }, (_, i) => (
        <span key={i} style={{ width: 8, height: 8, borderRadius: '50%',
          background: i < ready ? LEVEL.ok.hue : bad ? LEVEL.bad.hue : LEVEL.warn.hue }} />))}
    </div>
  )
}

function Jobs({ jobs, selId, onPick }) {
  if (!jobs.length) return null
  return (
    <>
      {jobs.slice(0, 4).map(j => <Item key={j.id} item={j} role="workload" selId={selId} onPick={onPick} />)}
      {jobs.length > 4 && <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>지난 실행 {jobs.length - 4}개 더</div>}
    </>
  )
}

// ── 상세 ───────────────────────────────────────────────────────────────────
export function Detail({ sel, onClose, onOpen }) {
  const { item, role, app } = sel
  const rows = []
  const kv = (k, v) => { if (v !== undefined && v !== null && v !== '' && !(Array.isArray(v) && !v.length)) rows.push([k, v]) }
  kv('종류', role === 'workload' || role === 'cronjob' ? kindLabel(item) : role === 'use' ? USE_LABEL[item.type] : role === 'ingress' ? 'Ingress' : 'Service')
  kv('이름', item.name)
  kv('네임스페이스', item.ns)
  kv('앱', app?.name)
  if (role === 'workload') {
    const h = workloadHealth(item)
    kv('상태', h.text)
    if (item.kind !== 'Job') {
      kv('파드', `${item.ready ?? item.running ?? 0}/${item.total || 0} 준비${item.replicas != null ? ` · 바라는 수 ${item.replicas}` : ''}`)
      kv('재시작', item.restarts || 0)
      kv('대기 사유', (item.waiting || []).join(', '))
    } else {
      kv('성공 · 실패 · 실행 중', `${item.succeeded || 0} · ${item.failed || 0} · ${item.active || 0}`)
    }
    kv('이미지', (item.images || []).join('\n'))
    kv('Selector', Object.entries(item.sel || {}).map(([k, v]) => `${k}=${v}`).join('\n'))
  }
  if (role === 'service') { kv('유형', item.type); kv('포트', (item.ports || []).join('\n')); kv('Selector', Object.entries(item.sel || {}).map(([k, v]) => `${k}=${v}`).join('\n')) }
  if (role === 'ingress') {
    kv('IngressClass', item.class)
    kv('주소', (item.rules || []).map(r => `${(item.tls_hosts || []).includes(r.host) ? 'https' : 'http'}://${r.host || '*'}${r.path} → ${r.svc}`).join('\n'))
  }
  if (role === 'cronjob') kv('일정', item.schedule)
  if (role === 'use') { kv('PV', item.pv ? `${item.pv.name}${item.pv.status ? ` (${item.pv.status})` : ''}` : ''); if (item.sharedBy > 1) kv('함께 쓰는 앱', `${item.sharedBy}개`) }
  const navKey = role === 'workload' || role === 'cronjob' ? item.kind : role === 'use' ? item.type : role
  const canOpen = !!NAV[navKey] && item.ns
  const h = role === 'workload' ? workloadHealth(item) : null

  return (
    <div style={{ width: 300, flexShrink: 0, borderLeft: '1px solid var(--border)', background: 'var(--bg-1)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 13px', borderBottom: '1px solid var(--border)' }}>
        {h ? (h.level === 'ok' ? <CheckCircle2 size={14} color={ink(LEVEL.ok.hue)} /> : <AlertTriangle size={14} color={ink(LEVEL[h.level].hue)} />) : null}
        <b style={{ flex: 1, fontSize: 12.5, color: 'var(--text-bright)', wordBreak: 'break-all' }}>{item.name}</b>
        <button className="btn btn-ghost btn-sm" onClick={onClose}><X size={12} /></button>
      </div>
      <div style={{ flex: 1, overflow: 'auto', padding: '10px 13px' }}>
        {rows.map(([k, v]) => (
          <div key={k} style={{ marginBottom: 8 }}>
            <div style={{ fontSize: 10.5, color: 'var(--text-dim)' }}>{k}</div>
            <div style={{ fontSize: 12, color: 'var(--text)', whiteSpace: 'pre-wrap', wordBreak: 'break-all', fontFamily: ['이름', '종류', '앱', '상태', '파드', '재시작'].includes(k) ? undefined : 'var(--font-mono)' }}>{String(v)}</div>
          </div>
        ))}
      </div>
      {canOpen && (
        <div style={{ padding: '10px 13px', borderTop: '1px solid var(--border)' }}>
          <button className="btn btn-default" style={{ width: '100%' }} onClick={() => onOpen(item, role)}>리소스 브라우저에서 열기</button>
        </div>)}
    </div>
  )
}

const tag = { fontSize: 10.5, padding: '1px 7px', borderRadius: 9, border: '1px solid var(--border)', color: 'var(--text-mid)', background: 'var(--bg-2)' }
const mono = { fontFamily: 'var(--font-mono)', fontSize: 10.5, wordBreak: 'break-all' }
