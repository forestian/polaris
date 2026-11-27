import React, { Suspense, lazy, useState, useEffect, useRef } from 'react'
import { AppProvider, useApp } from './store.jsx'
import Sidebar from './components/Sidebar.jsx'
import StatusBar from './components/StatusBar.jsx'
import ConnectionModal from './components/ConnectionModal.jsx'
import CommandPalette from './components/CommandPalette.jsx'
import SettingsModal  from './components/SettingsModal.jsx'
import VaultGate      from './components/VaultGate.jsx'
import VaultPanel     from './components/VaultPanel.jsx'
import ModeSwitcher   from './components/ModeSwitcher.jsx'
import CheckSidebar from './components/CheckSidebar.jsx'
import { checkPage, resolveCheckPage } from './checkPages.js'
import { AlertCircle, Settings } from 'lucide-react'
import PolarisMark from './components/PolarisMark.jsx'
import { api } from './api.js'

// K8s 모드 페이지 lazy 로드
const Dashboard       = lazy(() => import('./pages/Dashboard.jsx'))
const ResourceBrowser = lazy(() => import('./pages/ResourceBrowser.jsx'))
const ArgoPage        = lazy(() => import('./pages/ArgoPage.jsx'))
const HelmPage        = lazy(() => import('./pages/HelmPage.jsx'))
const TerminalPage    = lazy(() => import('./pages/TerminalPage.jsx'))
const TopologyPage    = lazy(() => import('./pages/TopologyPage.jsx'))
const ReportPage      = lazy(() => import('./pages/ReportPage.jsx'))
const K9sPage         = lazy(() => import('./pages/K9sPage.jsx'))
const LogPage         = lazy(() => import('./pages/LogPage.jsx'))
const EventsPage      = lazy(() => import('./pages/EventsPage.jsx'))
const PortForwardPage = lazy(() => import('./pages/PortForwardPage.jsx'))
const CrdPage         = lazy(() => import('./pages/CrdPage.jsx'))
const RbacPage        = lazy(() => import('./pages/RbacPage.jsx'))
const SnapshotPage    = lazy(() => import('./pages/SnapshotPage.jsx'))
const MultiClusterPage = lazy(() => import('./pages/MultiClusterPage.jsx'))
const HealthScanPage  = lazy(() => import('./pages/HealthScanPage.jsx'))
const UpgradeCheckPage = lazy(() => import('./pages/UpgradeCheckPage.jsx'))   // CHECK (v1.4.1)
const YamlLabPage     = lazy(() => import('./pages/YamlLabPage.jsx'))

// 타이틀바 빈 공간 더블클릭 → 최대화/복원 (네이티브 타이틀바 관습).
// 반환된 maximized 상태를 이벤트로 발행해 캡션 버튼 아이콘과 동기화.
function toggleMaximizeFromTitlebar() {
  try {
    Promise.resolve(window.pywebview?.api?.window_toggle_maximize?.())
      .then(r => {
        if (r && typeof r.maximized === 'boolean')
          window.dispatchEvent(new CustomEvent('polaris:maximized', { detail: r.maximized }))
      })
      .catch(() => {})
  } catch {}
}

// ── 제목표시줄 드래그 (v1.2.151) ──────────────────────────────────────────────
// pywebview 내장 drag-region 을 쓰지 않고 직접 처리한다. 내장 드래그는 mousedown
// 시점의 clientX/Y 를 잡은 지점으로 고정하는데, 최대화 상태에서 드래그를 시작하면
// 그 순간 창을 복원해야 하고(브라우저와 같은 동작) 그러면 잡은 지점이 어긋난다.
// 여기서 직접 다루면 복원 후 커서 아래로 창을 맞춰 넣을 수 있다.
// 리사이즈 핸들(WindowResizeHandles)과 같은 방식 — window_set_bounds + rAF.
// 실제로 이 정도(CSS px)는 움직여야 드래그로 본다. 누르자마자 시작하면
// ① 클릭·더블클릭까지 드래그가 되고 ② 최대화 창이 더블클릭 전에 복원돼
// 더블클릭 복원이 곧바로 다시 최대화되는 어긋남이 생긴다.
const TITLEBAR_DRAG_THRESHOLD = 6

function useTitlebarDrag() {
  const press = useRef(null)    // 누르고 있는 중(아직 드래그 아님)
  const drag = useRef(null)     // 실제 이동 중
  const raf = useRef(0)
  const pending = useRef(null)

  const flush = () => {
    raf.current = 0
    const b = pending.current
    if (!b) return
    pending.current = null
    try { window.pywebview?.api?.window_set_bounds(b.x, b.y, b.w, b.h) } catch { /* noop */ }
  }

  function endDrag() {
    const p = press.current
    press.current = null
    if (p) { try { p.el.releasePointerCapture(p.id) } catch { /* noop */ } }
    if (!drag.current) return
    drag.current = null
    if (raf.current) { cancelAnimationFrame(raf.current); raf.current = 0 }
    flush()
  }

  function onPointerDown(ev) {
    // 좌클릭만, 그리고 타이틀바 안의 버튼/입력에서 시작한 눌림은 드래그가 아니다
    if (ev.button !== 0) return
    if (ev.target.closest?.('button, input, select, a, [data-no-drag]')) return
    if (!window.pywebview?.api?.window_drag_begin) return
    // 여기서는 아무것도 시작하지 않는다 — 문턱을 넘는 이동이 있어야 드래그다
    press.current = { el: ev.currentTarget, id: ev.pointerId,
                      sx: ev.screenX, sy: ev.screenY, arming: false }
    try { ev.currentTarget.setPointerCapture(ev.pointerId) } catch { /* noop */ }
  }

  function onPointerMove(ev) {
    const p = press.current
    if (!p) return
    // 버튼을 뗀 뒤 들어온 이동 — 놓친 pointerup 에 대비한 안전장치.
    // 이게 없으면 드래그가 켜진 채 남아 마우스만 올려도 창이 따라온다.
    if (ev.buttons === 0) { endDrag(); return }

    const d = drag.current
    if (d) {
      pending.current = {
        x: Math.round(ev.screenX * d.dpr) - d.gx,
        y: Math.round(ev.screenY * d.dpr) - d.gy,
        w: d.w, h: d.h,
      }
      if (!raf.current) raf.current = requestAnimationFrame(flush)
      return
    }
    if (p.arming) return
    if (Math.abs(ev.screenX - p.sx) < TITLEBAR_DRAG_THRESHOLD &&
        Math.abs(ev.screenY - p.sy) < TITLEBAR_DRAG_THRESHOLD) return

    // 문턱을 넘었다 — 이제 시작한다(최대화 상태였다면 백엔드가 여기서 복원한다).
    // 모니터 배율이 섞인 환경에서 이동량이 어긋날 수 있는 한계는 리사이즈 핸들과 같다.
    p.arming = true
    const dpr = window.devicePixelRatio || 1
    Promise.resolve(window.pywebview.api.window_drag_begin(
      Math.round(ev.screenX * dpr), Math.round(ev.screenY * dpr)))
      .then(r => {
        // 응답을 기다리는 사이 손을 뗐으면 시작하지 않는다.
        // (이 확인이 없으면 클릭이 끝난 뒤 드래그가 켜져 창이 마우스를 따라다닌다)
        if (press.current !== p) return
        if (!r || r.ok === false) return
        if (r.restored) {
          // 캡션 버튼 아이콘·리사이즈 핸들이 복원 상태를 알아야 한다
          window.dispatchEvent(new CustomEvent('polaris:maximized', { detail: false }))
        }
        drag.current = { gx: r.grab_x, gy: r.grab_y, w: r.width, h: r.height, dpr }
      })
      .catch(() => {})
  }

  return {
    onPointerDown, onPointerMove,
    onPointerUp: endDrag,
    onPointerCancel: endDrag,
    onLostPointerCapture: endDrag,
    onDoubleClick: toggleMaximizeFromTitlebar,
    style: { touchAction: 'none' },
  }
}

// ── 클러스터 탭 단일 항목 ─────────────────────────────────────────────────────
function ClusterTab({ cluster, active, editing, editName, onSwitch, onRemove, onStartEdit, onEditChange, onEditCommit, onEditCancel }) {
  return (
    <div
      onClick={!active ? onSwitch : undefined}
      title={active ? undefined : cluster.display_name}
      style={{
        display: 'flex', alignItems: 'center', gap: 5,
        padding: '4px 8px 4px 9px',
        background: active ? 'var(--bg-3)' : 'var(--bg-2)',
        border: `1px solid ${active ? 'var(--nimbus)' : 'var(--border)'}`,
        borderRadius: 5, cursor: active ? 'default' : 'pointer',
        minWidth: 72, maxWidth: 170, flexShrink: 0,
        transition: 'border-color 0.15s',
        WebkitAppRegion: 'no-drag',
      }}
    >
      {/* 연결 상태 dot */}
      <div style={{
        width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
        background: cluster.connected ? 'var(--nimbus)' : 'var(--red)',
        boxShadow: cluster.connected && active ? '0 0 5px var(--nimbus)' : 'none',
      }} />

      {/* 이름 — 편집 중이면 input, 아니면 span */}
      {editing ? (
        <input
          autoFocus
          value={editName}
          onChange={e => onEditChange(e.target.value)}
          onKeyDown={e => {
            if (e.key === 'Enter')  onEditCommit()
            if (e.key === 'Escape') onEditCancel()
          }}
          onBlur={onEditCommit}
          style={{
            background: 'transparent', border: 'none', outline: 'none',
            color: 'var(--text-bright)', fontSize: 11, fontWeight: 600,
            width: 90, minWidth: 0,
          }}
        />
      ) : (
        <span
          onClick={active ? e => { e.stopPropagation(); onStartEdit() } : undefined}
          title={active ? '클릭하여 이름 수정' : undefined}
          style={{
            fontSize: 11, fontWeight: active ? 600 : 500,
            color: active ? 'var(--text-bright)' : 'var(--text-mid)',
            overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            cursor: active ? 'text' : 'pointer', flex: 1, minWidth: 0,
          }}
        >
          {cluster.display_name}
        </span>
      )}

      {/* k8s 버전 (활성 탭만, 편집 중 아닐 때) */}
      {active && !editing && cluster.version && (
        <span style={{
          fontSize: 8.5, color: 'var(--text-dim)', flexShrink: 0,
          fontFamily: 'var(--font-mono)',
        }}>
          {cluster.version}
        </span>
      )}

      {/* × 제거 버튼 */}
      <button
        onClick={e => { e.stopPropagation(); onRemove() }}
        title="클러스터 제거"
        style={{
          width: 14, height: 14, borderRadius: '50%', flexShrink: 0,
          background: 'transparent', border: 'none', padding: 0,
          color: 'var(--text-dim)', cursor: 'pointer',
          display: 'grid', placeItems: 'center', fontSize: 11, lineHeight: 1,
        }}
      >×</button>
    </div>
  )
}

// ── 클러스터 탭 스트립 ────────────────────────────────────────────────────────
function ClusterTabStrip() {
  const { clusters, activeClusterId, switchCluster, removeCluster, renameCluster, setShowConnect } = useApp()
  const [editingId, setEditingId]   = React.useState(null)
  const [editName,  setEditName]    = React.useState('')

  function startEdit(cluster) {
    setEditingId(cluster.id)
    setEditName(cluster.display_name)
  }

  async function commitEdit(id) {
    const name = editName.trim()
    setEditingId(null)
    if (!name) return
    const r = await renameCluster(id, name)
    // 보관함 이름 충돌 등 실패 시 안내 (vault 항목 이전이 거부됨 — 이름 유지)
    if (r && r.ok === false) {
      window.alert(r.error || '이름 변경에 실패했습니다.')
    }
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 4,
      overflow: 'hidden', WebkitAppRegion: 'no-drag',
    }}>
      {/* 탭 목록 */}
      {clusters.map(cluster => (
        <ClusterTab
          key={cluster.id}
          cluster={cluster}
          active={cluster.id === activeClusterId}
          editing={editingId === cluster.id}
          editName={editName}
          onSwitch={() => switchCluster(cluster.id)}
          onRemove={() => removeCluster(cluster.id)}
          onStartEdit={() => startEdit(cluster)}
          onEditChange={setEditName}
          onEditCommit={() => commitEdit(cluster.id)}
          onEditCancel={() => setEditingId(null)}
        />
      ))}

      {/* + 새 클러스터 연결 버튼 */}
      <button
        title="새 클러스터 연결"
        onClick={() => setShowConnect(true)}
        style={{
          width: 26, height: 26, flexShrink: 0,
          background: 'var(--bg-2)', border: '1px solid var(--border)',
          borderRadius: 5, color: 'var(--nimbus)',
          fontSize: 18, lineHeight: 1, cursor: 'pointer',
          display: 'grid', placeItems: 'center',
          WebkitAppRegion: 'no-drag',
        }}
      >+</button>
    </div>
  )
}

// ── 타이틀바 ──────────────────────────────────────────────────────────────────
function Titlebar({ onOpenPalette }) {
  const {
    appVersion, connected,
    setShowSettings,
    appMode, checkActivePage,
  } = useApp()
  const dragProps = useTitlebarDrag()

  return (
    <div style={{
      height: 'var(--titlebar-h)',
      background: 'linear-gradient(180deg, var(--bg-2), var(--bg-1))',
      borderBottom: '1px solid var(--border)',
      display: 'flex', alignItems: 'center',
      gap: 10, padding: '0 14px', flexShrink: 0,
      WebkitAppRegion: 'drag',
      userSelect: 'none',
    }}>
      {/* 로고 — Polaris 8각 별 + gradient text (창 드래그 영역) */}
      <div {...dragProps}
           style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0,
                    ...dragProps.style }}>
        <PolarisMark size={26} />
        <div>
          <div style={{
            fontSize: 13, fontWeight: 700, lineHeight: 1,
            background: 'linear-gradient(90deg, #ffe9b8, var(--nimbus) 55%, var(--blue))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            letterSpacing: '-0.01em',
          }}>POLARIS</div>
          <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 2, letterSpacing: '0.1em' }}>
            {appVersion ? `v${appVersion}` : ''}
          </div>
        </div>
      </div>

      {/* 글로벌 검색 트리거 — Ctrl+K 명령 팔레트 열기.
          **폭이 고정이다.** 예전엔 `flex: 1` 로 남는 자리를 채웠는데, 클러스터 탭
          스트립이 K8s 모드에서만 나타나므로 그 차이를 검색창이 흡수했다. 결과로
          모드를 오갈 때마다 바로 뒤의 상단 탭(K8S·CHECK)이 18px 씩
          좌우로 튀었다(사용자 신고, 1400px 미만 창에서 실측). 긴 안내문은 팔레트
          입력칸에 같은 문구가 있으므로 여기서는 「검색」 한 단어만 남긴다. */}
      <button
        type="button"
        onClick={onOpenPalette}
        title="검색 — 페이지 · 리소스 · 클러스터 (Ctrl+K)"
        style={{
          display: 'flex', alignItems: 'center', gap: 7, flexShrink: 0,
          background: 'var(--bg-1)', border: '1px solid var(--border-bright)',
          borderRadius: 6, padding: '5px 11px',
          marginLeft: 6, WebkitAppRegion: 'no-drag',
          cursor: 'pointer', textAlign: 'left',
          fontFamily: 'var(--font)',
          color: 'var(--text-dim)', fontSize: 12,
          transition: 'border-color 0.15s',
        }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--nimbus)' }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-bright)' }}
      >
        <span style={{ color: 'var(--nimbus)', fontSize: 14, lineHeight: 1, flexShrink: 0 }}>⌕</span>
        <span style={{ color: 'var(--text-mid)', whiteSpace: 'nowrap' }}>검색</span>
        <span style={{
          fontSize: 9.5, color: 'var(--text-mid)', fontFamily: 'var(--font-mono)',
          padding: '2px 6px', background: 'var(--bg-3)', borderRadius: 3, flexShrink: 0,
        }}>Ctrl+K</span>
      </button>

      {/* 상단 탭 — K8S · CHECK */}
      <ModeSwitcher />

      {/* 중앙 여백 — 창 드래그 영역 (빈 공간 더블클릭 시 최대화/복원) */}
      <div {...dragProps}
           style={{ flex: 1, alignSelf: 'stretch', ...dragProps.style }} />

      {/* 클러스터 탭 스트립 — K8s 모드, 그리고 CHECK 의 클러스터 화면(스캔·보고서) */}
      {(appMode === 'k8s' || (appMode === 'check' && checkPage(checkActivePage)?.cluster)) && <ClusterTabStrip />}

      {/* 네임스페이스 셀렉터는 리소스 화면(ResourceBrowser) 자체 셀렉터로 일원화 —
          타이틀바의 전역 셀렉터는 중복이라 제거(v1.2.48). */}

      {/* 새로고침(↻) 버튼은 v1.3.46 에서 뺐다 — 백엔드가 들고 있는 클러스터 목록만
          다시 받을 뿐 보고 있는 화면은 그대로여서, 누르면 "안 된다" 로 보였다.
          화면마다 자기 새로고침 버튼이 따로 있다. */}

      {/* 설정 (v3.7.11) */}
      <button
        title="설정"
        onClick={() => setShowSettings(true)}
        style={{
          width: 32, height: 32, background: 'var(--bg-3)',
          border: '1px solid var(--border-bright)', borderRadius: 6,
          color: 'var(--text-mid)', display: 'grid', placeItems: 'center',
          cursor: 'pointer', WebkitAppRegion: 'no-drag',
          flexShrink: 0,
        }}
        onMouseEnter={e => { e.currentTarget.style.color = 'var(--nimbus)' }}
        onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-mid)' }}
      >
        <Settings size={14} />
      </button>

      {/* 창 컨트롤 (frameless · pywebview 에서만) */}
      <WindowControls />
    </div>
  )
}

// ── 창 컨트롤 (최소화/최대화/닫기) — frameless 커스텀 타이틀바 ─────────────────
function WindowControls() {
  const [ready, setReady] = useState(() => !!window.pywebview?.api)
  const [maxed, setMaxed] = useState(false)
  useEffect(() => {
    if (ready) return undefined
    const t = setInterval(() => {
      if (window.pywebview?.api) { setReady(true); clearInterval(t) }
    }, 400)
    return () => clearInterval(t)
  }, [ready])
  // 타이틀바 더블클릭 등 다른 경로로 최대화 상태가 바뀌면 아이콘 동기화
  useEffect(() => {
    const onMax = (e) => { if (typeof e.detail === 'boolean') setMaxed(e.detail) }
    window.addEventListener('polaris:maximized', onMax)
    return () => window.removeEventListener('polaris:maximized', onMax)
  }, [])
  if (!ready) return null   // 브라우저(개발) 등 pywebview 아닐 때 숨김

  const min = () => { try { window.pywebview.api.window_minimize() } catch {} }
  const max = async () => {
    try {
      const r = await window.pywebview.api.window_toggle_maximize()
      if (r && typeof r.maximized === 'boolean') setMaxed(r.maximized)
      else setMaxed(v => !v)
    } catch { setMaxed(v => !v) }
  }
  const close = () => { try { window.pywebview.api.window_close() } catch {} }

  return (
    <div style={{
      display: 'flex', alignItems: 'center', alignSelf: 'stretch',
      marginLeft: 4, marginRight: -14, WebkitAppRegion: 'no-drag', flexShrink: 0,
    }}>
      <CapBtn onClick={min} title="최소화">
        <svg width="11" height="11" viewBox="0 0 11 11"><rect x="0" y="5" width="11" height="1" fill="currentColor" /></svg>
      </CapBtn>
      <CapBtn onClick={max} title={maxed ? '이전 크기로' : '최대화'}>
        {maxed
          ? <svg width="11" height="11" viewBox="0 0 11 11"><rect x="0.5" y="2.5" width="6.5" height="6.5" stroke="currentColor" fill="none" /><path d="M2.7 2.5 V0.5 H10.5 V8.3 H8.3" stroke="currentColor" fill="none" /></svg>
          : <svg width="10" height="10" viewBox="0 0 10 10"><rect x="0.5" y="0.5" width="9" height="9" stroke="currentColor" fill="none" /></svg>}
      </CapBtn>
      <CapBtn onClick={close} title="닫기" danger>
        <svg width="11" height="11" viewBox="0 0 11 11"><path d="M0.5 0.5 L10.5 10.5 M10.5 0.5 L0.5 10.5" stroke="currentColor" strokeWidth="1.1" /></svg>
      </CapBtn>
    </div>
  )
}

function CapBtn({ onClick, title, danger, children }) {
  const [h, setH] = useState(false)
  return (
    <button type="button" onClick={onClick} title={title}
      onMouseEnter={() => setH(true)} onMouseLeave={() => setH(false)}
      style={{
        width: 46, alignSelf: 'stretch', display: 'grid', placeItems: 'center',
        border: 'none', outline: 'none', cursor: 'pointer',
        WebkitAppRegion: 'no-drag', transition: 'background 0.12s, color 0.12s',
        background: h ? (danger ? '#c42b1c' : 'rgba(255,255,255,0.10)') : 'transparent',
        color: danger && h ? '#fff' : 'var(--text-mid)',
      }}>
      {children}
    </button>
  )
}

// ── 로딩 스피너 ──────────────────────────────────────────────────────────────
function PageLoading() {
  return (
    <div className="empty-state" style={{ height: '100%' }}>
      <div className="spinner" />
      <span>로딩 중...</span>
    </div>
  )
}

// ── 플레이스홀더 페이지 ───────────────────────────────────────────────────────
function PlaceholderPage({ icon: Icon, title, sub }) {
  return (
    <div className="empty-state" style={{ height: '100%' }}>
      <Icon size={36} opacity={0.25} />
      <p style={{ fontWeight: 600 }}>{title}</p>
      {sub && <p style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>{sub}</p>}
    </div>
  )
}

// ── K8s 모드 페이지 뷰 ───────────────────────────────────────────────────────
function K8sPageView() {
  const { activePage, connected } = useApp()

  switch (activePage) {
    case 'dashboard':  return <Dashboard />
    case 'resources':  return connected ? <ResourceBrowser /> : (
      <PlaceholderPage icon={AlertCircle} title="클러스터에 연결되지 않았습니다." />
    )
    case 'helm':       return <HelmPage />
    case 'argocd':     return connected ? <ArgoPage /> : (
      <PlaceholderPage icon={AlertCircle} title="클러스터에 연결되지 않았습니다." />
    )
    case 'terminal':   return <TerminalPage />
    case 'k9s':        return <K9sPage />
    case 'topology':   return <TopologyPage />
    case 'logs':       return <LogPage />
    case 'portforward': return <PortForwardPage />
    case 'events':     return connected ? <EventsPage /> : (
      <PlaceholderPage icon={AlertCircle} title="클러스터에 연결되지 않았습니다." />
    )
    case 'snapshots':  return <SnapshotPage />
    case 'multicluster': return <MultiClusterPage />
    case 'yamllab':    return connected ? <YamlLabPage /> : (
      <PlaceholderPage icon={AlertCircle} title="클러스터에 연결되지 않았습니다." />
    )
    default:           return <Dashboard />
  }
}

// ── CHECK 모드 페이지 뷰 — 클러스터 스캔 · 업그레이드 사전 점검 · 클러스터 보고서 ─────────
// K8s 모드와 같은 연결(제목표시줄의 클러스터 탭)을 쓴다.
function CheckPageView() {
  const { checkActivePage, setCheckActivePage, connected, clusterSwitchKey } = useApp()
  const page = resolveCheckPage(checkActivePage)
  useEffect(() => { if (page !== checkActivePage) setCheckActivePage(page) }, [page, checkActivePage, setCheckActivePage])
  if (!connected) {
    return <PlaceholderPage icon={AlertCircle} title="클러스터에 연결되지 않았습니다."
                            sub="위쪽 [+] 로 클러스터를 연결하거나 보관함에서 고르세요." />
  }
  switch (page) {
    case 'upgrade': return <UpgradeCheckPage key={clusterSwitchKey} />
    case 'report': return <ReportPage key={clusterSwitchKey} />
    default: return <HealthScanPage key={clusterSwitchKey} />
  }
}

// ── 에러 바운더리 — 한 페이지의 렌더 오류가 앱 전체를 까맣게 만드는 것 방지 ──────
// (v1.2.74) 이전엔 바운더리가 없어 어떤 페이지든 렌더 중 throw 하면 React 가 트리를
// 통째로 내려 화면이 까맣게 됐다. viewKey(모드:페이지)가 바뀌면 오류 상태를 자동 해제.
class ViewErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { err: null } }
  static getDerivedStateFromError(err) { return { err } }
  componentDidCatch(err, info) { try { console.error('[UI] 렌더 오류:', err, info) } catch { /* noop */ } }
  componentDidUpdate(prev) {
    if (prev.viewKey !== this.props.viewKey && this.state.err) this.setState({ err: null })
  }
  render() {
    if (this.state.err) {
      return (
        <div style={{ padding: 28, height: '100%', overflow: 'auto' }}>
          <h2 style={{ fontSize: 16, color: 'var(--red)', marginBottom: 8 }}>화면 표시 중 오류가 발생했습니다</h2>
          <p style={{ fontSize: 12.5, color: 'var(--text-dim)', marginBottom: 12 }}>
            다른 탭으로 이동했다 돌아오거나 [다시 시도]를 누르면 복구됩니다. 반복되면 아래 내용을 알려주세요.
          </p>
          <button className="btn btn-primary btn-sm" onClick={() => this.setState({ err: null })}>다시 시도</button>
          <pre style={{ marginTop: 14, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 11,
            color: 'var(--text-dim)', background: 'var(--bg-1)', border: '1px solid var(--border)',
            borderRadius: 6, padding: '10px 12px', maxHeight: 320, overflow: 'auto' }}>
            {String(this.state.err?.stack || this.state.err)}
          </pre>
        </div>
      )
    }
    return this.props.children
  }
}

// ── 메인 콘텐츠 — 모드에 따라 분기 ────────────────────────────────────────────
// K8s 모드: clusterSwitchKey 가 바뀌면 페이지 강제 재마운트
function MainContent() {
  const { appMode, clusterSwitchKey, activePage, checkActivePage } = useApp()
  const viewKey = `${appMode}:${appMode === 'check' ? checkActivePage : activePage}`
  return (
    <Suspense fallback={<PageLoading />}>
      <ViewErrorBoundary viewKey={viewKey}>
        {appMode === 'check'
          ? <CheckPageView />
          : <K8sPageView key={clusterSwitchKey} />}
      </ViewErrorBoundary>
    </Suspense>
  )
}

// ── 앱 레이아웃 ────────────────────────────────────────────────────────────────
// 옮긴 데이터 폴더(외장 · 네트워크 드라이브)를 못 찾아 기본 폴더로 열었을 때 — 예전엔 아무 말 없이
// 기본 폴더의 오래된 서버 목록 · 보관함으로 열려 두 곳이 어긋났다(v1.4.24)
function DataDirNotice() {
  const [info, setInfo] = useState(null)
  useEffect(() => {
    api.getDataDir().then(r => { if (r?.ok && r.fallback_from) setInfo(r) }).catch(() => {})
  }, [])
  if (!info) return null
  return (
    <div role="alert" style={{
      display: 'flex', alignItems: 'center', gap: 10, padding: '7px 14px', fontSize: 12, flexShrink: 0,
      background: 'rgba(250,204,21,0.14)', borderBottom: '1px solid rgba(250,204,21,0.4)', color: 'var(--text-bright)',
    }}>
      <AlertCircle size={14} color="var(--yellow)" style={{ flexShrink: 0 }} />
      <span style={{ flex: 1, lineHeight: 1.5 }}>
        데이터 폴더 <b style={{ fontFamily: 'var(--font-mono)' }}>{info.fallback_from}</b> 를 찾지 못해 기본 폴더
        <span style={{ fontFamily: 'var(--font-mono)' }}> {info.path}</span> 로 열었습니다. 지금 보이는 서버 목록 · 보안 보관함 · 설정은 기본 폴더의 것입니다 —
        드라이브가 연결됐는지 확인한 뒤 Polaris 를 다시 시작하세요.
      </span>
      <button className="btn btn-ghost btn-sm" onClick={() => setInfo(null)}>닫기</button>
    </div>
  )
}

function AppLayout() {
  const { showConnect, showSettings, appMode } = useApp()
  const [paletteOpen, setPaletteOpen] = useState(false)
  // Ctrl+K 글로벌 단축키 — 어디서든 명령 팔레트 토글
  useEffect(() => {
    function onKey(e) {
      const isMod = e.metaKey || e.ctrlKey
      if (isMod && (e.key === 'k' || e.key === 'K')) {
        e.preventDefault()
        setPaletteOpen(o => !o)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', overflow: 'hidden',
      background: 'var(--bg-0)',
    }}>
      {/* 타이틀바 */}
      <Titlebar onOpenPalette={() => setPaletteOpen(true)} />
      <DataDirNotice />

      {/* 사이드바 + 콘텐츠 — K8S / CHECK 에 따라 사이드바 교체 */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {appMode === 'check' ? <CheckSidebar /> : <Sidebar />}
        <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <MainContent />
        </main>
      </div>

      {/* 상태바 */}
      <StatusBar />


      {/* 연결 모달 */}
      {showConnect && <ConnectionModal />}

      {/* 설정 모달 (v3.7.11) */}
      {showSettings && <SettingsModal />}

      {/* 보안 보관함 패널 — 좌하단 박스 클릭 시 */}
      <VaultPanel />

      {/* 명령 팔레트 (Ctrl+K) */}
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />

    </div>
  )
}

// ── 창 가장자리/모서리 리사이즈 핸들 (frameless 창의 OS 리사이즈 대체) ───────────
// pywebview 가 frameless 라 OS 리사이즈 테두리가 없으므로, 얇은 투명 핸들 8개를 창
// 가장자리에 깔고 드래그 → 백엔드 window_set_bounds 로 절대 bounds 적용.
// 최대화 상태에서는 숨김(작업영역 고정). CSS px 델타를 devicePixelRatio 로 물리 px 변환.
const RESIZE_EDGES = [
  { e: 'n',  cur: 'ns-resize',   s: { top: 0, left: 8, right: 8, height: 5 } },
  { e: 's',  cur: 'ns-resize',   s: { bottom: 0, left: 8, right: 8, height: 5 } },
  { e: 'w',  cur: 'ew-resize',   s: { left: 0, top: 8, bottom: 8, width: 5 } },
  { e: 'e',  cur: 'ew-resize',   s: { right: 0, top: 8, bottom: 8, width: 5 } },
  { e: 'nw', cur: 'nwse-resize', s: { top: 0, left: 0, width: 12, height: 12 } },
  { e: 'ne', cur: 'nesw-resize', s: { top: 0, right: 0, width: 12, height: 12 } },
  { e: 'sw', cur: 'nesw-resize', s: { bottom: 0, left: 0, width: 12, height: 12 } },
  { e: 'se', cur: 'nwse-resize', s: { bottom: 0, right: 0, width: 12, height: 12 } },
]
const MIN_W = 960
const MIN_H = 640

function WindowResizeHandles() {
  const [ready, setReady] = useState(() => !!window.pywebview?.api)
  const [maximized, setMaximized] = useState(false)
  const drag = useRef(null)
  const raf = useRef(0)
  const pending = useRef(null)

  useEffect(() => {
    if (!ready) {
      const t = setInterval(() => { if (window.pywebview?.api) { setReady(true); clearInterval(t) } }, 400)
      return () => clearInterval(t)
    }
  }, [ready])
  useEffect(() => {
    const onMax = (e) => { if (typeof e.detail === 'boolean') setMaximized(e.detail) }
    window.addEventListener('polaris:maximized', onMax)
    return () => window.removeEventListener('polaris:maximized', onMax)
  }, [])

  if (!ready || maximized) return null

  const flush = () => {
    raf.current = 0
    const b = pending.current
    if (b) { pending.current = null; try { window.pywebview.api.window_set_bounds(b.x, b.y, b.w, b.h) } catch {} }
  }

  async function onDown(edge, ev) {
    ev.preventDefault()
    let r = null
    try { r = await window.pywebview.api.window_get_bounds() } catch {}
    if (!r || r.ok === false) return
    drag.current = {
      edge,
      sx: ev.screenX, sy: ev.screenY,
      x: r.x, y: r.y, w: r.width, h: r.height,
      right: r.x + r.width, bottom: r.y + r.height,
      dpr: window.devicePixelRatio || 1,
    }
    try { ev.target.setPointerCapture(ev.pointerId) } catch {}
  }
  function onMove(ev) {
    const d = drag.current
    if (!d) return
    const dx = (ev.screenX - d.sx) * d.dpr
    const dy = (ev.screenY - d.sy) * d.dpr
    let { x, y, w, h, right, bottom, edge } = d
    if (edge.includes('e')) w = Math.max(MIN_W, d.w + dx)
    if (edge.includes('s')) h = Math.max(MIN_H, d.h + dy)
    if (edge.includes('w')) { x = Math.min(d.x + dx, right - MIN_W); w = right - x }
    if (edge.includes('n')) { y = Math.min(d.y + dy, bottom - MIN_H); h = bottom - y }
    pending.current = { x: Math.round(x), y: Math.round(y), w: Math.round(w), h: Math.round(h) }
    if (!raf.current) raf.current = requestAnimationFrame(flush)
  }
  function onUp(ev) {
    if (!drag.current) return
    drag.current = null
    if (raf.current) { cancelAnimationFrame(raf.current); raf.current = 0 }
    flush()
    try { ev.target.releasePointerCapture(ev.pointerId) } catch {}
  }

  return (
    <>
      {RESIZE_EDGES.map(({ e, cur, s }) => (
        <div key={e}
          onPointerDown={(ev) => onDown(e, ev)}
          onPointerMove={onMove}
          onPointerUp={onUp}
          style={{ position: 'fixed', zIndex: 99999, cursor: cur,
                   WebkitAppRegion: 'no-drag', ...s }} />
      ))}
    </>
  )
}

// ── 루트 ──────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <AppProvider>
      <WindowResizeHandles />
      <VaultGate>
        <AppLayout />
      </VaultGate>
    </AppProvider>
  )
}
