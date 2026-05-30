import React, { Suspense, lazy, useState, useEffect } from 'react'
import { AppProvider, useApp } from './store.jsx'
import Sidebar from './components/Sidebar.jsx'
import StatusBar from './components/StatusBar.jsx'
import ConnectionModal from './components/ConnectionModal.jsx'
import CommandPalette from './components/CommandPalette.jsx'
import SettingsModal  from './components/SettingsModal.jsx'
import VaultGate      from './components/VaultGate.jsx'
import VaultPanel     from './components/VaultPanel.jsx'
import { AlertCircle, Settings } from 'lucide-react'
import PolarisMark from './components/PolarisMark.jsx'
import { isFeatureEnabled } from './featureGate.js'

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

// ── catalog 플러그인 조건부 로드 (v1.2.2~) ────────────────────────────────────
// infra 와 동일 패턴: 파일이 있으면 glob 이 로더를 반환, 무료빌드처럼 삭제되면
// 빈 객체 → CatalogPage=null 로 자동 제외(정적 import 였다면 빌드가 깨짐).
const _catalogGlob = import.meta.glob('./pages/CatalogPage.jsx', { eager: false })
const _catalogLoader = _catalogGlob['./pages/CatalogPage.jsx']
const CATALOG_BUNDLED = !!_catalogLoader
const CatalogPage = _catalogLoader ? lazy(_catalogLoader) : null

// ── infra 플러그인 조건부 로드 ────────────────────────────────────────────────
// ui/src/infra/ 폴더가 빌드 시점에 존재하면 자동 등록. 무료빌드처럼 폴더
// 삭제된 상태로 빌드하면 Vite 가 chunk 자체를 만들지 않음 (용량 증가 0).
// 런타임 게이팅은 useApp().enabledFeatures.includes('infra') 로 추가 확인.
const _infraGlob = import.meta.glob('./infra/index.jsx', { eager: false })
const _infraLoader = _infraGlob['./infra/index.jsx']
const INFRA_BUNDLED = !!_infraLoader

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
    if (name) await renameCluster(id, name)
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
function Titlebar({ onOpenPalette, infraComponents }) {
  const {
    appVersion, connected,
    namespace, setNamespace, namespaces, refreshStatus,
    setShowSettings,
    appMode, enabledFeatures,
  } = useApp()
  const infraEnabled = isFeatureEnabled('infra', enabledFeatures, INFRA_BUNDLED)

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
      {/* 로고 — Polaris 8각 별 + gradient text */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
        <PolarisMark size={26} />
        <div>
          <div style={{
            fontSize: 13, fontWeight: 700, lineHeight: 1,
            background: 'linear-gradient(90deg, #ffe9b8, var(--nimbus) 55%, var(--blue))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            letterSpacing: '-0.01em',
          }}>POLARIS</div>
          <div style={{ fontSize: 9, color: 'var(--text-dim)', marginTop: 2, letterSpacing: '0.1em' }}>
            {/* 변형(무료 -f/-e) 빌드에서는 조직 브랜딩 숨김 */}
            {appVersion ? `v${appVersion}` : ''}
            {appVersion && !/-[ef]\d/.test(appVersion) ? ' · NIMBUS NETWORKS' : ''}
          </div>
        </div>
      </div>

      {/* 글로벌 검색 트리거 — ⌘K 명령 팔레트 열기 */}
      <button
        type="button"
        onClick={onOpenPalette}
        title="명령 팔레트 열기 (Ctrl+K)"
        style={{
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'var(--bg-1)', border: '1px solid var(--border-bright)',
          borderRadius: 6, padding: '5px 12px', flex: 1, maxWidth: 380,
          marginLeft: 6, WebkitAppRegion: 'no-drag',
          cursor: 'pointer', textAlign: 'left',
          fontFamily: 'var(--font)',
          color: 'var(--text-dim)', fontSize: 12,
          transition: 'border-color 0.15s',
        }}
        onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--nimbus)' }}
        onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border-bright)' }}
      >
        <span style={{ color: 'var(--nimbus)', fontSize: 14, lineHeight: 1 }}>⌕</span>
        <span style={{ flex: 1 }}>페이지 · 리소스 · 클러스터 · 명령어 검색...</span>
        <span style={{
          fontSize: 9.5, color: 'var(--text-mid)', fontFamily: 'var(--font-mono)',
          padding: '2px 6px', background: 'var(--bg-3)', borderRadius: 3, flexShrink: 0,
        }}>Ctrl+K</span>
      </button>

      {/* 모드 스위처 (v1.1.0) — infra 플러그인 활성 시에만 표시 */}
      {infraEnabled && infraComponents?.ModeSwitcher && <infraComponents.ModeSwitcher />}

      <div style={{ flex: 1 }} />

      {/* 클러스터 탭 스트립 — K8s 모드에서만 */}
      {appMode === 'k8s' && <ClusterTabStrip />}

      {/* 네임스페이스 셀렉터 — K8s 모드에서만 */}
      {appMode === 'k8s' && connected && namespaces.length > 0 && (
        <select
          className="select"
          value={namespace}
          onChange={e => setNamespace(e.target.value)}
          style={{ minWidth: 150, WebkitAppRegion: 'no-drag' }}
        >
          {namespaces.map(n => <option key={n}>{n}</option>)}
        </select>
      )}

      {/* 새로고침 */}
      <button
        title="새로고침"
        onClick={refreshStatus}
        style={{
          width: 32, height: 32, background: 'var(--bg-3)',
          border: '1px solid var(--border-bright)', borderRadius: 6,
          color: 'var(--text-mid)', display: 'grid', placeItems: 'center',
          cursor: 'pointer', fontSize: 16, WebkitAppRegion: 'no-drag',
          flexShrink: 0,
        }}
      >↻</button>

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
    </div>
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
    case 'report':     return <ReportPage />
    case 'events':     return connected ? <EventsPage /> : (
      <PlaceholderPage icon={AlertCircle} title="클러스터에 연결되지 않았습니다." />
    )
    case 'catalog':    return CatalogPage
      ? <CatalogPage />
      : <PlaceholderPage icon={AlertCircle} title="앱 카탈로그는 이 빌드에 포함되지 않았습니다." />
    case 'crds':       return connected ? <CrdPage /> : (
      <PlaceholderPage icon={AlertCircle} title="클러스터에 연결되지 않았습니다." />
    )
    case 'rbac':       return connected ? <RbacPage /> : (
      <PlaceholderPage icon={AlertCircle} title="클러스터에 연결되지 않았습니다." />
    )
    case 'snapshots':  return <SnapshotPage />
    default:           return <Dashboard />
  }
}

// ── SSH 모드 페이지 뷰 (v1.1.0) — infra 컴포넌트 동적 로드 ────────────────────
function SSHPageView({ infraComponents }) {
  const { sshActivePage } = useApp()
  if (!infraComponents) return <PageLoading />
  const { ServersPage, InstallPage, SSHTerminalPage } = infraComponents
  switch (sshActivePage) {
    case 'servers':  return <ServersPage />
    case 'install':  return <InstallPage />
    case 'terminal': return <SSHTerminalPage />
    default:         return <ServersPage />
  }
}

// ── 메인 콘텐츠 — 모드에 따라 분기 ────────────────────────────────────────────
// K8s 모드: clusterSwitchKey 가 바뀌면 페이지 강제 재마운트
function MainContent({ infraComponents }) {
  const { appMode, clusterSwitchKey, enabledFeatures } = useApp()
  const infraEnabled = isFeatureEnabled('infra', enabledFeatures, INFRA_BUNDLED)
  return (
    <Suspense fallback={<PageLoading />}>
      {appMode === 'ssh' && infraEnabled
        ? <SSHPageView infraComponents={infraComponents} />
        : <K8sPageView key={clusterSwitchKey} />}
    </Suspense>
  )
}

// ── 앱 레이아웃 ────────────────────────────────────────────────────────────────
function AppLayout() {
  const { showConnect, showSettings, appMode, enabledFeatures } = useApp()
  const [paletteOpen, setPaletteOpen] = useState(false)
  const [infraComponents, setInfraComponents] = useState(null)

  // infra 모듈 비동기 로드 — 폴더 있을 때만
  useEffect(() => {
    if (!INFRA_BUNDLED) return
    _infraLoader().then(setInfraComponents).catch(() => setInfraComponents(null))
  }, [])

  // ⌘K / Ctrl+K 글로벌 단축키 — 어디서든 명령 팔레트 토글
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

  const infraEnabled = isFeatureEnabled('infra', enabledFeatures, INFRA_BUNDLED)

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: '100vh', overflow: 'hidden',
      background: 'var(--bg-0)',
    }}>
      {/* 타이틀바 */}
      <Titlebar onOpenPalette={() => setPaletteOpen(true)}
                infraComponents={infraComponents} />

      {/* 사이드바 + 콘텐츠 — 모드에 따라 사이드바 교체 */}
      <div style={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
        {appMode === 'ssh' && infraEnabled && infraComponents?.SSHSidebar
          ? <infraComponents.SSHSidebar />
          : <Sidebar />}
        <main style={{ flex: 1, overflow: 'hidden', display: 'flex', flexDirection: 'column' }}>
          <MainContent infraComponents={infraComponents} />
        </main>
      </div>

      {/* 상태바 */}
      <StatusBar />

      {/* 연결 모달 */}
      {showConnect && <ConnectionModal />}

      {/* 설정 모달 (v3.7.11) */}
      {showSettings && <SettingsModal />}

      {/* 보안 보관함 패널 (v1.2.1) — 좌하단 박스 클릭 시, K8s/SSH 공통 */}
      <VaultPanel />

      {/* 명령 팔레트 (⌘K) */}
      <CommandPalette open={paletteOpen} onClose={() => setPaletteOpen(false)} />
    </div>
  )
}

// ── 루트 ──────────────────────────────────────────────────────────────────────
export default function App() {
  return (
    <AppProvider>
      <VaultGate>
        <AppLayout />
      </VaultGate>
    </AppProvider>
  )
}
