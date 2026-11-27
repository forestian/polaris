import React, { useState } from 'react'
import { useApp } from '../store.jsx'
import {
  LayoutDashboard, Network, Box, Layers, Globe, Database,
  Package, GitBranch, Terminal, Monitor, ChevronDown, ChevronRight,
  Server, Cpu, HardDrive, Shield, FileText, ScrollText, Activity,
  AppWindow, Cable, Boxes, KeyRound, Camera, Lock, Unlock, ChevronUp, Archive, ArrowRightLeft,
  HeartPulse, Wrench, FlaskConical,
} from 'lucide-react'

const TREE = [
  {
    id: 'cluster', label: '클러스터', icon: Server,
    items: [
      { id: 'nodes',      label: '노드' },
      { id: 'namespaces', label: '네임스페이스' },
    ],
  },
  {
    id: 'workloads', label: '워크로드', icon: Box,
    items: [
      { id: 'pods',         label: '파드' },
      { id: 'deployments',  label: '디플로이먼트' },
      { id: 'statefulsets', label: '스테이트풀셋' },
      { id: 'daemonsets',   label: '데몬셋' },
      { id: 'replicasets',  label: '레플리카셋' },
      { id: 'jobs',         label: '잡' },
      { id: 'cronjobs',     label: '크론잡' },
    ],
  },
  {
    id: 'networking', label: '네트워킹', icon: Network,
    items: [
      { id: 'services',  label: '서비스' },
      { id: 'ingresses', label: '인그레스' },
    ],
  },
  {
    id: 'config', label: '설정', icon: Shield,
    items: [
      { id: 'configmaps', label: '컨피그맵' },
      { id: 'secrets',    label: '시크릿' },
    ],
  },
  {
    id: 'storage', label: '스토리지', icon: HardDrive,
    items: [
      { id: 'pvcs', label: 'PVC' },
      { id: 'pvs',  label: 'PV' },
    ],
  },
  {
    id: 'access', label: '접근 제어', icon: KeyRound,
    items: [
      { id: 'rbac', label: 'RBAC 분석' },
    ],
  },
  {
    id: 'crd', label: 'CRD', icon: Boxes,
    items: [
      { id: 'crds', label: '커스텀 리소스' },
    ],
  },
  {
    id: 'helm', label: 'HELM', icon: Package,
    items: [
      { id: 'helm_releases', label: 'Helm 현황' },
    ],
  },
  {
    id: 'argocd', label: '배포', icon: GitBranch,
    items: [
      { id: 'argocd_apps', label: '앱 목록' },
    ],
  },
]

// 상단 고정 — 매 세션 항상 보이는 핵심 진입점만. 나머지는 아래 TOOL_PAGES(접이식 '도구' 그룹)로.
const TOP_PAGES = [
  { id: 'dashboard', label: '대시보드', icon: LayoutDashboard },
]

// 도구 모음 — 자주 쓰지 않는 기능들. 리소스 트리 공간을 지키기 위해 기본 접힘 상태의
// 단일 그룹으로 묶는다(v1.2.111). 페이지가 늘어나도 여기에 추가하면 트리 공간은 그대로.
const TOOL_PAGES = [
  { id: 'multicluster', label: '멀티클러스터', icon: Layers },
  { id: 'topology',  label: '토폴로지',      icon: Globe },
  { id: 'events',    label: '이벤트',        icon: Activity },
  { id: 'snapshots', label: '스냅샷',        icon: Camera },
  { id: 'yamllab',   label: 'YAML 실험실',   icon: FlaskConical },
  { id: 'logs',      label: '로그뷰어',      icon: ScrollText },
  { id: 'portforward', label: '포트포워딩', icon: Cable },
  { id: 'k9s',       label: 'k9s',          icon: Monitor },
  { id: 'terminal',  label: 'kubectl 터미널', icon: Terminal },
]

export default function Sidebar() {
  const { activePage, activeResource, navigate, connected, clusterName, kubeVersion,
          vaultStatus, setShowVaultPanel } = useApp()
  // '도구' 그룹은 기본 접힘 — 리소스 트리가 스크롤 없이 바로 보이도록.
  const [collapsed, setCollapsed] = useState(() => ({ tools: true }))

  const toolPages = TOOL_PAGES

  function toggle(id) {
    setCollapsed(p => ({ ...p, [id]: !p[id] }))
  }

  function handleItem(item) {
    if (!connected && item !== 'dashboard') return
    if (item === 'kubectl_terminal') navigate('terminal')
    else if (item === 'k9s_launcher') navigate('k9s')
    else if (item === 'log_viewer')   navigate('logs')
    else if (item === 'helm_releases') navigate('helm')
    else if (item === 'argocd_apps')   navigate('argocd')
    else if (item === 'crds')          navigate('crds')
    else if (item === 'rbac')          navigate('rbac')
    else navigate('resources', item)
  }

  function isActive(item) {
    if (item === activePage) return true
    if (activePage === 'resources' && activeResource === item) return true
    if (activePage === 'crds' && item === 'crds') return true
    if (activePage === 'rbac' && item === 'rbac') return true
    if (activePage === 'helm' && item === 'helm_releases') return true
    if (activePage === 'argocd' && item === 'argocd_apps') return true
    if (activePage === 'terminal' && item === 'kubectl_terminal') return true
    if (activePage === 'k9s' && item === 'k9s_launcher') return true
    if (activePage === 'logs' && item === 'log_viewer') return true
    return false
  }

  const activeItemStyle = {
    color: 'var(--text-bright)',
    background: 'linear-gradient(90deg, rgba(52,211,153,0.15), rgba(96,165,250,0.04))',
    borderLeft: '2px solid var(--nimbus)',
    fontWeight: 600,
  }

  const inactiveItemStyle = {
    color: 'var(--text)',
    background: 'transparent',
    borderLeft: '2px solid transparent',
    fontWeight: 400,
  }

  return (
    <aside style={{
      width: 'var(--sidebar-w)',
      background: 'var(--bg-2)',
      borderRight: '1px solid var(--border)',
      display: 'flex',
      flexDirection: 'column',
      overflow: 'hidden',
      flexShrink: 0,
    }}>
      {/* 상단 고정 페이지 */}
      <div style={{ padding: '8px 0 4px' }}>
        {TOP_PAGES.map(p => {
          const Icon = p.icon
          const active = activePage === p.id
          return (
            <button key={p.id} onClick={() => navigate(p.id)}
              style={{
                width: '100%', display: 'flex', alignItems: 'center', gap: 10,
                padding: '8px 12px', margin: '1px 0',
                border: 'none', cursor: 'pointer', fontSize: 12.5,
                fontFamily: 'var(--font)', transition: 'all 0.12s',
                ...(active ? activeItemStyle : inactiveItemStyle),
              }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.03)' }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
            >
              <Icon size={14} color={active ? 'var(--nimbus)' : 'var(--text-dim)'} />
              {p.label}
            </button>
          )
        })}
      </div>

      <div style={{ borderTop: '1px solid var(--border)', margin: '4px 0' }} />

      {/* 트리 탐색기 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
        {/* 도구 모음 — 자주 안 쓰는 기능들을 접이식 그룹 하나로. 리소스 그룹과 같은 헤더 스타일,
            하위 항목은 기존 아이콘을 유지(다양한 기능이라 아이콘으로 빠르게 스캔 가능하게). */}
        <div>
          <button onClick={() => toggle('tools')}
            style={{
              width: '100%', display: 'flex', alignItems: 'center', gap: 8,
              padding: '6px 14px', border: 'none', cursor: 'pointer',
              background: 'transparent', color: 'var(--text-dim)',
              fontSize: 10.5, fontFamily: 'var(--font)',
              fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
            }}
          >
            {!collapsed.tools ? <ChevronDown size={9} /> : <ChevronRight size={9} />}
            <Wrench size={11} />
            <span style={{ flex: 1, textAlign: 'left', color: 'var(--text-mid)' }}>도구</span>
          </button>

          {!collapsed.tools && toolPages.map(p => {
            const Icon = p.icon
            const active = activePage === p.id
            return (
              <button key={p.id} onClick={() => navigate(p.id)}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                  padding: '5px 12px 5px 30px', border: 'none',
                  cursor: 'pointer', fontSize: 12, fontFamily: 'var(--font)',
                  transition: 'all 0.12s', borderRadius: '0 4px 4px 0', marginLeft: 6,
                  ...(active ? activeItemStyle : inactiveItemStyle),
                }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.03)' }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
              >
                <Icon size={13} color={active ? 'var(--nimbus)' : 'var(--text-dim)'} />
                {p.label}
              </button>
            )
          })}
        </div>

        {TREE.map(cat => {
          const isOpen = !collapsed[cat.id]
          const CatIcon = cat.icon
          return (
            <div key={cat.id}>
              <button onClick={() => toggle(cat.id)}
                style={{
                  width: '100%', display: 'flex', alignItems: 'center', gap: 8,
                  padding: '6px 14px', border: 'none', cursor: 'pointer',
                  background: 'transparent', color: 'var(--text-dim)',
                  fontSize: 10.5, fontFamily: 'var(--font)',
                  fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.06em',
                }}
              >
                {isOpen ? <ChevronDown size={9} /> : <ChevronRight size={9} />}
                <CatIcon size={11} />
                <span style={{ flex: 1, textAlign: 'left', color: 'var(--text-mid)' }}>{cat.label}</span>
              </button>

              {isOpen && cat.items.map(item => {
                const active = isActive(item.id)
                const disabled = !connected
                return (
                  <button key={item.id}
                    onClick={() => handleItem(item.id)}
                    disabled={disabled}
                    style={{
                      width: '100%', display: 'block', textAlign: 'left',
                      padding: '5px 12px 5px 36px', border: 'none',
                      cursor: disabled ? 'default' : 'pointer',
                      fontSize: 12, fontFamily: 'var(--font)',
                      opacity: disabled ? 0.4 : 1,
                      transition: 'all 0.12s',
                      borderRadius: '0 4px 4px 0', marginLeft: 6,
                      ...(active ? activeItemStyle : inactiveItemStyle),
                    }}
                    onMouseEnter={e => { if (!active && !disabled) e.currentTarget.style.background = 'rgba(255,255,255,0.03)' }}
                    onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent' }}
                  >
                    {item.label}
                  </button>
                )
              })}
            </div>
          )
        })}
      </div>

      {/* 클러스터 / 보안 보관함 위젯 — 클릭 시 보안 보관함 패널 열기 (v1.2.1) */}
      <ClusterVaultBox
        connected={connected}
        clusterName={clusterName}
        kubeVersion={kubeVersion}
        vaultStatus={vaultStatus}
        onOpen={() => setShowVaultPanel(true)}
      />
    </aside>
  )
}

// ── 좌하단 클러스터 / 보안 보관함 박스 ──────────────────
export function ClusterVaultBox({ connected, clusterName, kubeVersion, vaultStatus, onOpen }) {
  const unlocked = vaultStatus?.unlocked
  return (
    <button
      onClick={onOpen}
      title="보안 보관함 열기"
      style={{
        margin: '10px 10px 12px', padding: '10px 12px',
        borderRadius: 8, background: 'var(--bg-3)',
        border: '1px solid var(--border)', cursor: 'pointer',
        textAlign: 'left', width: 'calc(100% - 20px)',
        transition: 'border-color 0.12s, background 0.12s',
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--nimbus)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)' }}
    >
      {connected ? (
        <>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
            <span style={{ fontSize: 10, color: 'var(--text-dim)', fontWeight: 700, letterSpacing: '0.06em', textTransform: 'uppercase', flex: 1 }}>
              클러스터
            </span>
            {unlocked ? <Unlock size={11} color="var(--nimbus)" /> : <Lock size={11} color="var(--text-mid)" />}
          </div>
          <div style={{ fontSize: 12.5, fontWeight: 600, color: 'var(--text-bright)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', marginTop: 4 }}>
            {clusterName || '연결됨'}
          </div>
          {kubeVersion && (
            <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 3, fontFamily: 'var(--font-mono)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {kubeVersion}
            </div>
          )}
          <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginTop: 8, fontSize: 10, color: 'var(--text-dim)' }}>
            <KeyRound size={10} color="var(--nimbus)" /> 보안 보관함 열기
            <span style={{ flex: 1 }} />
            <ChevronUp size={11} />
          </div>
        </>
      ) : (
        <div style={{ display: 'flex', alignItems: 'center', gap: 9 }}>
          <div style={{
            width: 30, height: 30, borderRadius: 7, flexShrink: 0,
            background: 'var(--bg-2)', display: 'grid', placeItems: 'center',
          }}>
            <KeyRound size={15} color="var(--nimbus)" />
          </div>
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--text-bright)' }}>
              보안 보관함
            </div>
            <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 1, display: 'flex', alignItems: 'center', gap: 4, minWidth: 0 }}>
              {unlocked ? <Unlock size={9} color="var(--nimbus)" style={{ flexShrink: 0 }} /> : <Lock size={9} style={{ flexShrink: 0 }} />}
              <span style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', minWidth: 0 }}>
                kubeconfig·접속정보·스냅샷
              </span>
            </div>
          </div>
          <ChevronUp size={12} color="var(--text-dim)" />
        </div>
      )}
    </button>
  )
}
