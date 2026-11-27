import React, { useEffect, useState, useCallback, useRef } from 'react'
import { api } from '../api.js'
import { startPoll } from '../poll.js'
import { useApp } from '../store.jsx'
import ResourceTable from '../components/ResourceTable.jsx'
import ResourcePanel from '../components/ResourcePanel.jsx'
import { RefreshCw, Trash2, X, ChevronDown, Radio } from 'lucide-react'

// ── 컬럼 정의 ────────────────────────────────────────────────────────────────
const COLUMNS = {
  pods: [
    { key: 'name',      label: '이름',        width: 240 },
    { key: 'namespace', label: '네임스페이스', width: 120 },
    { key: 'status',    label: '상태',         width: 100 },
    { key: 'ready',     label: 'Ready',        width: 75  },
    { key: 'restarts',  label: '재시작',       width: 65  },
    { key: 'node',      label: '노드',         width: 150 },
    { key: 'age',       label: 'Age',          width: 70  },
  ],
  deployments: [
    { key: 'name',       label: '이름',         width: 200 },
    { key: 'namespace',  label: '네임스페이스', width: 120 },
    { key: 'ready',      label: 'Ready',        width: 80  },
    { key: 'up-to-date', label: 'Up-to-date',   width: 90  },
    { key: 'available',  label: 'Available',    width: 90  },
    { key: 'age',        label: 'Age',          width: 70  },
  ],
  statefulsets: [
    { key: 'name',      label: '이름',         width: 200 },
    { key: 'namespace', label: '네임스페이스', width: 120 },
    { key: 'ready',     label: 'Ready',        width: 80  },
    { key: 'age',       label: 'Age',          width: 70  },
  ],
  daemonsets: [
    { key: 'name',      label: '이름',         width: 200 },
    { key: 'namespace', label: '네임스페이스', width: 120 },
    { key: 'desired',   label: 'Desired',      width: 80  },
    { key: 'ready',     label: 'Ready',        width: 80  },
    { key: 'age',       label: 'Age',          width: 70  },
  ],
  replicasets: [
    { key: 'name',      label: '이름',         width: 200 },
    { key: 'namespace', label: '네임스페이스', width: 120 },
    { key: 'desired',   label: 'Desired',      width: 80  },
    { key: 'ready',     label: 'Ready',        width: 80  },
    { key: 'age',       label: 'Age',          width: 70  },
  ],
  jobs: [
    { key: 'name',        label: '이름',         width: 200 },
    { key: 'namespace',   label: '네임스페이스', width: 120 },
    { key: 'completions', label: 'Completions',  width: 100 },
    { key: 'status',      label: '상태',         width: 100 },
    { key: 'age',         label: 'Age',          width: 70  },
  ],
  cronjobs: [
    { key: 'name',          label: '이름',         width: 200 },
    { key: 'namespace',     label: '네임스페이스', width: 120 },
    { key: 'schedule',      label: 'Schedule',     width: 130 },
    { key: 'suspend',       label: 'Suspend',      width: 70  },
    { key: 'last-schedule', label: 'Last Run',     width: 120 },
    { key: 'age',           label: 'Age',          width: 70  },
  ],
  nodes: [
    { key: 'name',    label: '이름',     width: 180 },
    { key: 'status',  label: '상태',     width: 80  },
    { key: 'roles',   label: '역할',     width: 100 },
    { key: 'version', label: 'Version',  width: 120 },
    { key: 'os',      label: 'OS',       width: 160 },
    { key: 'age',     label: 'Age',      width: 70  },
  ],
  namespaces: [
    { key: 'name',   label: '이름', width: 200 },
    { key: 'status', label: '상태', width: 100 },
    { key: 'age',    label: 'Age',  width: 70  },
  ],
  services: [
    { key: 'name',        label: '이름',         width: 180 },
    { key: 'namespace',   label: '네임스페이스', width: 110 },
    { key: 'type',        label: '타입',         width: 85  },
    { key: 'cluster-ip',  label: 'Cluster IP',   width: 110 },
    { key: 'external-ip', label: 'External IP',  width: 120 },
    { key: 'ports',       label: 'Port(s)',       width: 130 },
    { key: 'age',         label: 'Age',          width: 70  },
  ],
  ingresses: [
    { key: 'name',      label: '이름',         width: 180 },
    { key: 'namespace', label: '네임스페이스', width: 110 },
    { key: 'class',     label: 'Class',        width: 90  },
    { key: 'hosts',     label: 'Hosts',        width: 200 },
    { key: 'address',   label: 'Address',      width: 130 },
    { key: 'age',       label: 'Age',          width: 70  },
  ],
  configmaps: [
    { key: 'name',      label: '이름',         width: 200 },
    { key: 'namespace', label: '네임스페이스', width: 120 },
    { key: 'data',      label: 'Data',         width: 60  },
    { key: 'age',       label: 'Age',          width: 70  },
  ],
  secrets: [
    { key: 'name',      label: '이름',         width: 200 },
    { key: 'namespace', label: '네임스페이스', width: 120 },
    { key: 'type',      label: '타입',         width: 150 },
    { key: 'data',      label: 'Data',         width: 60  },
    { key: 'age',       label: 'Age',          width: 70  },
  ],
  pvcs: [
    { key: 'name',         label: '이름',         width: 180 },
    { key: 'namespace',    label: '네임스페이스', width: 110 },
    { key: 'status',       label: '상태',         width: 80  },
    { key: 'volume',       label: 'Volume',       width: 160 },
    { key: 'capacity',     label: 'Capacity',     width: 80  },
    { key: 'access-modes', label: 'Access Modes', width: 110 },
    { key: 'age',          label: 'Age',          width: 70  },
  ],
  pvs: [
    { key: 'name',           label: '이름',        width: 180 },
    { key: 'capacity',       label: 'Capacity',    width: 80  },
    { key: 'access-modes',   label: 'Access Modes',width: 110 },
    { key: 'reclaim-policy', label: 'Reclaim',     width: 85  },
    { key: 'status',         label: '상태',        width: 80  },
    { key: 'claim',          label: 'Claim',       width: 180 },
    { key: 'age',            label: 'Age',         width: 70  },
  ],
}

const NO_NS_RESOURCES = new Set(['nodes', 'namespaces', 'pvs'])

const PAGE_LABELS = {
  pods: '파드', deployments: '디플로이먼트', statefulsets: '스테이트풀셋',
  daemonsets: '데몬셋', replicasets: '레플리카셋', jobs: '잡', cronjobs: '크론잡',
  nodes: '노드', namespaces: '네임스페이스', services: '서비스',
  ingresses: '인그레스', configmaps: '컨피그맵', secrets: '시크릿',
  pvcs: 'PVC', pvs: 'PV',
}

// ── 삭제 확인 모달 ────────────────────────────────────────────────────────────
function DeleteConfirm({ item, kind, onConfirm, onCancel }) {
  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onCancel()}>
      <div className="modal" style={{ width: 420 }}>
        <div className="modal-header">
          <h2 style={{ color: 'var(--red)' }}>🗑 리소스 삭제</h2>
          <button className="btn btn-ghost btn-sm" onClick={onCancel}><X size={14} /></button>
        </div>
        <div className="modal-body">
          <p style={{ fontSize: 13, color: 'var(--text)', lineHeight: 1.6 }}>
            다음 리소스를 삭제하시겠습니까?
          </p>
          <div style={{
            background: 'var(--bg-3)', borderRadius: 6, padding: '10px 14px',
            marginTop: 12, fontSize: 12, fontFamily: 'var(--font-mono)',
          }}>
            <div><span style={{ color: 'var(--text-dim)' }}>Kind: </span>
              <span style={{ color: 'var(--text-bright)' }}>{kind}</span></div>
            <div><span style={{ color: 'var(--text-dim)' }}>Name: </span>
              <span style={{ color: 'var(--text-bright)' }}>{item.name}</span></div>
            {item.namespace && (
              <div><span style={{ color: 'var(--text-dim)' }}>Namespace: </span>
                <span style={{ color: 'var(--text-bright)' }}>{item.namespace}</span></div>
            )}
          </div>
          <p style={{ fontSize: 12, color: 'var(--red)', marginTop: 12 }}>
            ⚠ 이 작업은 되돌릴 수 없습니다.
          </p>
        </div>
        <div className="modal-footer">
          <button className="btn btn-default" onClick={onCancel}>취소</button>
          <button className="btn btn-danger" onClick={onConfirm}>삭제</button>
        </div>
      </div>
    </div>
  )
}

// ── 메인 페이지 ──────────────────────────────────────────────────────────────
export default function ResourceBrowser() {
  const { connected, namespace, setNamespace, namespaces, activeResource, refreshNamespaces,
          clusterSwitchKey } = useApp()
  const [rows, setRows]         = useState([])
  const [loading, setLoading]   = useState(false)
  const [selected, setSelected] = useState(null)
  const [panelOpen, setPanelOpen] = useState(false)
  const [delTarget, setDelTarget] = useState(null)
  const [deleting, setDeleting]   = useState(false)
  const [toast, setToast]         = useState(null)

  // 실시간 갱신(watch API) — v1: 지원 kind(현재 pods)만. 기본은 꺼짐(명시적 옵트인).
  const [liveKinds, setLiveKinds] = useState([])
  const [live, setLive] = useState(false)
  const watchIdRef = useRef(null)
  const watchTimerRef = useRef(null)

  const kind    = activeResource || 'pods'
  const columns = COLUMNS[kind]  || COLUMNS.pods
  const noNs    = NO_NS_RESOURCES.has(kind)
  const nsParam = noNs ? '' : (namespace === 'All Namespaces' ? '' : namespace)

  // 늦게 온 앞 목록이 새 목록을 덮지 않게(v1.5.28 검토) — Service 목록이 Deployment 제목 아래 남은 채로 [삭제] 하면
  // 지금 kind(Deployment)의 같은 이름이 지워졌다. 부를 때마다 번호를 올리고, 마지막 번호의 응답만 쓴다
  const loadSeqRef = useRef(0)
  const load = useCallback(async () => {
    if (!connected) return
    const seq = ++loadSeqRef.current
    setLoading(true)
    setSelected(null)
    setPanelOpen(false)
    setRows([])
    let data = null
    try { data = await api.getResource(kind, nsParam) } catch { data = null }
    if (seq !== loadSeqRef.current) return
    setRows(Array.isArray(data) ? data : [])
    setLoading(false)
  }, [connected, kind, nsParam])

  useEffect(() => { load() }, [load])

  // 리소스 화면 진입 시 네임스페이스 목록 최신화 — 밖에서 새로 생긴 NS 를 셀렉터에 반영
  useEffect(() => { refreshNamespaces() }, [refreshNamespaces])

  // watch 지원 kind 목록(현재 pods) — 마운트 시 1회 조회. 백엔드가 나중에 kind 를
  // 늘려도 프론트 수정 없이 토글이 자동으로 나타난다.
  useEffect(() => {
    let alive = true
    api.resourceWatchKinds().then(r => { if (alive && Array.isArray(r)) setLiveKinds(r) })
    return () => { alive = false }
  }, [])

  const canWatch = liveKinds.includes(kind)

  // 실시간 이벤트를 rows 에 반영 — namespace+name 키로 upsert/삭제(watch 는 이미
  // 서버에서 같은 namespace 로 스코프됨 → 추가 필터 불필요).
  function applyWatchEvents(events) {
    if (!events || !events.length) return
    setRows(prev => {
      const map = new Map(prev.map(r => [`${r.namespace}::${r.name}`, r]))
      for (const { type, row } of events) {
        const key = `${row.namespace}::${row.name}`
        if (type === 'DELETED') map.delete(key)
        else map.set(key, row)
      }
      return Array.from(map.values())
    })
  }

  const stopWatch = useCallback(() => {
    if (watchTimerRef.current) { watchTimerRef.current(); watchTimerRef.current = null }
    if (watchIdRef.current) { api.stopResourceWatch(watchIdRef.current); watchIdRef.current = null }
  }, [])

  // live 토글 또는 kind/namespace/클러스터 변경 시 watch 재시작. off 면 정리만.
  useEffect(() => {
    stopWatch()
    if (!live || !connected || !canWatch) return
    let cancelled = false
    ;(async () => {
      const r = await api.startResourceWatch(kind, nsParam)
      // 응답 전에 kind·ns 를 바꾸거나 떠났으면 방금 만든 watch 를 닫는다 (v1.3.73 — 남으면
      // 스레드와 이벤트 버퍼가 앱 종료까지 남았다)
      if (cancelled) { if (r?.ok && r.watch_id) api.stopResourceWatch(r.watch_id); return }
      if (!r?.ok) { setLive(false); return }
      watchIdRef.current = r.watch_id
      // 겹치지 않는 폴러(v1.3.41) — 이벤트 순서(ADDED→MODIFIED→DELETED)가 뒤집히면 안 된다
      watchTimerRef.current = startPoll(async () => {
        const wid = watchIdRef.current
        if (!wid) return
        const res = await api.recvResourceWatch(wid)
        // 응답을 기다리는 사이 kind · ns 가 바뀌었으면(watch 가 바뀌었다) 옛 이벤트를 새 목록에 넣지 않는다(v1.5.28 검토)
        if (cancelled || watchIdRef.current !== wid) return
        if (res?.ok) applyWatchEvents(res.events)
      }, 1000)
    })()
    return () => { cancelled = true; stopWatch() }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [live, connected, canWatch, kind, nsParam, clusterSwitchKey])

  function handleSelect(row) {
    if (selected === row && panelOpen) {
      // 같은 행 재클릭 → 패널 닫기
      setPanelOpen(false)
    } else {
      setSelected(row)
      setPanelOpen(true)
    }
  }

  function showToast(msg, type = 'ok') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3200)
  }

  async function handleDelete() {
    if (!delTarget) return
    setDeleting(true)
    try {
      const res = await api.deleteResource(kind, delTarget.namespace || '', delTarget.name)
      if (res?.ok !== false) {
        showToast(`${delTarget.name} 삭제 완료`)
        setDelTarget(null)
        if (selected?.name === delTarget.name) {
          setSelected(null)
          setPanelOpen(false)
        }
        load()
      } else {
        showToast(res.error || '삭제 실패', 'err')
        setDelTarget(null)
      }
    } catch (e) {
      showToast(String(e), 'err')
      setDelTarget(null)
    }
    setDeleting(false)
  }

  const toolbar = (
    <>
      {!noNs && (
        <div style={{ position: 'relative' }}>
          <select className="select" value={namespace}
            onChange={e => setNamespace(e.target.value)}
            style={{ paddingRight: 28, minWidth: 160 }}>
            {namespaces.length === 0
              ? <option>All Namespaces</option>
              : namespaces.map(ns => <option key={ns}>{ns}</option>)
            }
          </select>
          <ChevronDown size={11} style={{
            position: 'absolute', right: 8, top: '50%',
            transform: 'translateY(-50%)', pointerEvents: 'none',
            color: 'var(--text-dim)',
          }} />
        </div>
      )}
      <button className="btn btn-danger" disabled={!selected}
        onClick={() => selected && setDelTarget(selected)} style={{ gap: 4 }}>
        <Trash2 size={12} />
        삭제
      </button>
    </>
  )

  // KPI 카운트 (파드일 때만)
  const podKpi = kind === 'pods' && rows.length > 0 ? [
    { label: '총 파드',  value: rows.length, color: 'var(--text-bright)' },
    { label: 'Running',  value: rows.filter(r => r.status === 'Running').length,   color: 'var(--green)'  },
    { label: 'Pending',  value: rows.filter(r => r.status === 'Pending').length,   color: 'var(--yellow)' },
    { label: '비정상',   value: rows.filter(r => !['Running','Succeeded','Completed','Pending'].includes(r.status)).length, color: 'var(--red)' },
  ] : null

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>

      {/* ── 헤더 ── */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '10px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-1)', flexShrink: 0,
      }}>
        <h1 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-bright)', margin: 0 }}>
          {PAGE_LABELS[kind] || kind}
        </h1>
        {selected && panelOpen && (
          <span style={{ fontSize: 11, color: 'var(--nimbus)',
            fontFamily: 'var(--font-mono)' }}>
            — {selected.name}
          </span>
        )}
        <span style={{ flex: 1 }} />
        {panelOpen && (
          <button className="btn btn-ghost btn-sm" onClick={() => setPanelOpen(false)}>
            <X size={12} /> 패널 닫기
          </button>
        )}
        {canWatch && (
          <button className="btn btn-default btn-sm" onClick={() => setLive(v => !v)}
            title={live ? '실시간 갱신 끄기' : '실시간 갱신 켜기 (kubernetes watch API)'}
            style={{
              gap: 4,
              background: live ? 'rgba(52,211,153,0.15)' : undefined,
              borderColor: live ? 'var(--nimbus)' : undefined,
              color: live ? 'var(--nimbus)' : undefined,
            }}>
            <Radio size={12} />
            실시간{live ? ' ON' : ''}
          </button>
        )}
        <button className="btn btn-default btn-sm" onClick={load} disabled={loading}>
          <RefreshCw size={12} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
          새로고침
        </button>
      </div>

      {/* ── KPI 스트립 (파드 전용) ── */}
      {podKpi && (
        <div style={{
          display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10,
          padding: '12px 16px', borderBottom: '1px solid var(--border)',
          background: 'var(--bg-1)', flexShrink: 0,
        }}>
          {podKpi.map(({ label, value, color }) => (
            <div key={label} style={{
              background: 'var(--bg-2)', border: '1px solid var(--border)',
              borderRadius: 8, padding: '10px 14px',
            }}>
              <div style={{ fontSize: 10, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 600, marginBottom: 4 }}>
                {label}
              </div>
              <div style={{ fontSize: 22, fontWeight: 700, color, fontVariantNumeric: 'tabular-nums', letterSpacing: '-0.02em' }}>
                {value}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* ── 본문: 테이블 + 패널 ── */}
      <div style={{ flex: 1, overflow: 'hidden', display: 'flex' }}>

        {/* 테이블 영역 */}
        <div style={{ flex: 1, overflow: 'hidden', minWidth: 0 }}>
          <ResourceTable
            columns={columns}
            rows={rows}
            loading={loading}
            selected={selected}
            onSelect={handleSelect}
            toolbar={toolbar}
            emptyMsg={`${PAGE_LABELS[kind] || kind} 리소스가 없습니다.`}
          />
        </div>

        {/* 상세 패널 */}
        {panelOpen && selected && (
          // key — 다른 객체를 고르면 패널을 새로 만든다(v1.5.28 검토). 늦게 온 앞 객체의 YAML 이 새 객체 이름 아래 남아
          // [적용] 이 앞 객체를 고치던 것을 막는다(로그 · 이벤트 · 상세도 같은 이유)
          <ResourcePanel
            key={`${kind}/${selected.namespace || ''}/${selected.name}`}
            item={selected}
            kind={kind}
            onClose={() => setPanelOpen(false)}
            onDelete={item => setDelTarget(item)}
          />
        )}
      </div>

      {/* ── 삭제 확인 모달 ── */}
      {delTarget && (
        <DeleteConfirm
          item={delTarget}
          kind={kind}
          onConfirm={handleDelete}
          onCancel={() => setDelTarget(null)}
        />
      )}

      {/* ── 토스트 ── */}
      {toast && (
        <div style={{
          position: 'fixed', bottom: 40, left: '50%', transform: 'translateX(-50%)',
          background: toast.type === 'err' ? 'var(--red-bg)' : 'var(--bg-4)',
          color: toast.type === 'err' ? 'var(--red)' : 'var(--green)',
          border: `1px solid ${toast.type === 'err' ? '#7f1d1d' : 'var(--border-bright)'}`,
          borderRadius: 6, padding: '8px 18px', fontSize: 12,
          boxShadow: '0 4px 16px rgba(0,0,0,0.5)', zIndex: 9999,
        }}>
          {toast.msg}
        </div>
      )}
    </div>
  )
}
