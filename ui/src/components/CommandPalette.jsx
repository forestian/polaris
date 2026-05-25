/**
 * CommandPalette — ⌘K 명령 팔레트 (v3.7.3)
 *
 * 검색 가능한 빠른 네비게이션 / 명령 실행 UI.
 * 키보드: Ctrl/Cmd+K로 열기, Esc로 닫기, ↑↓ 이동, Enter 실행.
 *
 * 검색 대상:
 *   1) 페이지 / 도구 (정적)
 *   2) 클러스터 전환 (현재 비활성 탭)
 *   3) 명령 (새 클러스터 연결, 새로고침)
 *   4) 실제 K8s 리소스 — 파드, 디플로이먼트, 서비스, 컨피그맵 등
 *      (활성 클러스터에서 가져온 인덱스 기반, 30s 캐시)
 */
import React, { useState, useEffect, useRef, useMemo } from 'react'
import { useApp } from '../store.jsx'
import { api } from '../api.js'
import {
  LayoutDashboard, Globe, FileText,
  Server, Boxes, Layers, ChevronsUp, ChevronsDown, Briefcase, Clock,
  Network, Lock, Key, HardDrive, Package, GitBranch,
  Terminal, Activity, Monitor, RefreshCw, Plus, Box, Cable,
} from 'lucide-react'

// ── 리소스 kind → 아이콘 / rtype ─────────────────────────────────────────────
const KIND_META = {
  Node:        { icon: Server,        rtype: 'nodes' },
  Namespace:   { icon: Layers,        rtype: 'namespaces' },
  Pod:         { icon: Box,           rtype: 'pods' },
  Deployment:  { icon: Boxes,         rtype: 'deployments' },
  StatefulSet: { icon: ChevronsUp,    rtype: 'statefulsets' },
  DaemonSet:   { icon: ChevronsDown,  rtype: 'daemonsets' },
  ReplicaSet:  { icon: Boxes,         rtype: 'replicasets' },
  Job:         { icon: Briefcase,     rtype: 'jobs' },
  CronJob:     { icon: Clock,         rtype: 'cronjobs' },
  Service:     { icon: Network,       rtype: 'services' },
  Ingress:     { icon: Network,       rtype: 'ingresses' },
  ConfigMap:   { icon: Lock,          rtype: 'configmaps' },
  Secret:      { icon: Key,           rtype: 'secrets' },
  PVC:         { icon: HardDrive,     rtype: 'pvcs' },
  PV:          { icon: HardDrive,     rtype: 'pvs' },
}

// ── 네비게이션 항목 ──────────────────────────────────────────────────────────
const NAV_PAGES = [
  { id: 'dashboard', label: '대시보드',      icon: LayoutDashboard, kind: 'page', page: 'dashboard' },
  { id: 'topology',  label: '토폴로지',      icon: Globe,           kind: 'page', page: 'topology', requiresConn: true },
  { id: 'events',    label: '이벤트 타임라인', icon: Activity,       kind: 'page', page: 'events',   requiresConn: true },
  { id: 'report',    label: '보고서',        icon: FileText,        kind: 'page', page: 'report',   requiresConn: true },
  { id: 'logs',      label: '로그뷰어',      icon: Activity,        kind: 'page', page: 'logs',     requiresConn: true },
  { id: 'portforward', label: '포트포워딩', icon: Cable,           kind: 'page', page: 'portforward', requiresConn: true },
  { id: 'k9s',       label: 'k9s',          icon: Monitor,         kind: 'page', page: 'k9s',      requiresConn: true },
  { id: 'terminal',  label: 'kubectl 터미널', icon: Terminal,        kind: 'page', page: 'terminal', requiresConn: true },
]

const NAV_RESOURCES = [
  { id: 'nodes',        label: '노드',         icon: Server,    resource: 'nodes' },
  { id: 'namespaces',   label: '네임스페이스', icon: Layers,    resource: 'namespaces' },
  { id: 'pods',         label: '파드',         icon: Box,       resource: 'pods' },
  { id: 'deployments',  label: '디플로이먼트', icon: Boxes,     resource: 'deployments' },
  { id: 'statefulsets', label: '스테이트풀셋', icon: ChevronsUp, resource: 'statefulsets' },
  { id: 'daemonsets',   label: '데몬셋',       icon: ChevronsDown, resource: 'daemonsets' },
  { id: 'replicasets',  label: '레플리카셋',   icon: Boxes,     resource: 'replicasets' },
  { id: 'jobs',         label: '잡',           icon: Briefcase, resource: 'jobs' },
  { id: 'cronjobs',     label: '크론잡',       icon: Clock,     resource: 'cronjobs' },
  { id: 'services',     label: '서비스',       icon: Network,   resource: 'services' },
  { id: 'ingresses',    label: '인그레스',     icon: Network,   resource: 'ingresses' },
  { id: 'configmaps',   label: '컨피그맵',     icon: Lock,      resource: 'configmaps' },
  { id: 'secrets',      label: '시크릿',       icon: Key,       resource: 'secrets' },
  { id: 'pvcs',         label: 'PVC',         icon: HardDrive, resource: 'pvcs' },
  { id: 'pvs',          label: 'PV',          icon: HardDrive, resource: 'pvs' },
]

const NAV_TOOLS = [
  { id: 'helm',   label: 'Helm',   icon: Package,   kind: 'page', page: 'helm',   requiresConn: true },
  { id: 'argocd', label: 'ArgoCD', icon: GitBranch, kind: 'page', page: 'argocd', requiresConn: true },
]

// ── 명령어 ───────────────────────────────────────────────────────────────────
const COMMANDS = [
  { id: 'cmd:connect', label: '새 클러스터 연결', icon: Plus,      kind: 'command', action: 'connect' },
  { id: 'cmd:refresh', label: '새로고침',          icon: RefreshCw, kind: 'command', action: 'refresh' },
]

// ── 메인 컴포넌트 ────────────────────────────────────────────────────────────
export default function CommandPalette({ open, onClose }) {
  const {
    connected, clusters, activeClusterId,
    navigate, switchCluster, setShowConnect, refreshStatus,
    setNamespace,
  } = useApp()

  const [query, setQuery]       = useState('')
  const [selected, setSelected] = useState(0)
  const [resourceIdx, setResourceIdx] = useState([])
  const [idxLoading, setIdxLoading]   = useState(false)
  const [idxError, setIdxError]       = useState(null)
  const inputRef = useRef(null)
  const listRef  = useRef(null)

  // 열릴 때 input 포커스 + 초기화
  useEffect(() => {
    if (open) {
      setQuery('')
      setSelected(0)
      // pywebview/안드로이드 keyboard 이슈 대응 위해 timeout
      setTimeout(() => inputRef.current?.focus(), 20)
    }
  }, [open])

  // 팔레트 열릴 때 리소스 인덱스 로드 (활성 클러스터별, 백엔드에서 30s 캐시)
  useEffect(() => {
    if (!open || !connected) {
      setResourceIdx([])
      return
    }
    let cancelled = false
    setIdxLoading(true)
    setIdxError(null)
    api.getSearchIndex(false)
      .then(res => {
        if (cancelled) return
        if (Array.isArray(res)) {
          setResourceIdx(res)
        } else {
          // callSafe 에러 형태 {ok:false, error}
          setResourceIdx([])
          if (res?.error) setIdxError(String(res.error))
        }
      })
      .catch(e => {
        if (!cancelled) {
          setResourceIdx([])
          setIdxError(String(e))
        }
      })
      .finally(() => { if (!cancelled) setIdxLoading(false) })
    return () => { cancelled = true }
  }, [open, connected, activeClusterId])

  // 항목 목록 빌드
  const items = useMemo(() => {
    const q = query.trim().toLowerCase()

    // 1) 리소스 매칭 — 쿼리 있을 때만, 최상단 노출
    const resourceMatches = []
    if (q && connected && resourceIdx.length > 0) {
      for (const r of resourceIdx) {
        const hay = (r.name + ' ' + (r.namespace || '')).toLowerCase()
        if (!hay.includes(q)) continue
        const meta = KIND_META[r.kind] || { icon: Box, rtype: r.rtype }
        resourceMatches.push({
          id:        `res:${r.kind}/${r.namespace}/${r.name}`,
          label:     r.name,
          sub:       r.namespace || '(cluster-scoped)',
          icon:      meta.icon,
          kind:      'k8s-resource',
          k8sKind:   r.kind,
          k8sRtype:  meta.rtype || r.rtype,
          k8sName:   r.name,
          k8sNs:     r.namespace,
          group:     r.kind,
        })
        if (resourceMatches.length >= 60) break
      }
    }

    // 2) 정적 항목 빌드
    const staticItems = []

    // 페이지
    for (const it of NAV_PAGES) {
      if (it.requiresConn && !connected) continue
      staticItems.push({ ...it, group: '페이지' })
    }

    // 리소스 종류 바로가기 (연결 시에만)
    if (connected) {
      for (const it of NAV_RESOURCES) {
        staticItems.push({ ...it, kind: 'resource', group: '리소스 종류' })
      }
    }

    // 도구
    for (const it of NAV_TOOLS) {
      if (it.requiresConn && !connected) continue
      staticItems.push({ ...it, group: '도구' })
    }

    // 클러스터 전환 (현재 활성 제외)
    for (const c of clusters) {
      if (c.id === activeClusterId) continue
      staticItems.push({
        id:         'cluster:' + c.id,
        label:      c.display_name,
        sub:        c.context || '',
        icon:       Server,
        kind:       'cluster',
        clusterId:  c.id,
        group:      '클러스터 전환',
      })
    }

    // 명령
    for (const cmd of COMMANDS) {
      staticItems.push({ ...cmd, group: '명령' })
    }

    // 3) 쿼리 필터
    let filteredStatic = staticItems
    if (q) {
      filteredStatic = staticItems.filter(it => {
        const hay = (it.label + ' ' + (it.sub || '') + ' ' + (it.id || '')).toLowerCase()
        return hay.includes(q)
      })
    }

    // 리소스 결과를 상단에 (쿼리가 있을 때만 표시)
    return q ? [...resourceMatches, ...filteredStatic] : staticItems
  }, [query, connected, clusters, activeClusterId, resourceIdx])

  // selected가 items 범위를 벗어나면 보정
  useEffect(() => {
    if (selected >= items.length) setSelected(Math.max(0, items.length - 1))
  }, [items, selected])

  // 선택 항목 스크롤 인투 뷰
  useEffect(() => {
    if (!open || !listRef.current) return
    const el = listRef.current.querySelector('[data-selected="true"]')
    el?.scrollIntoView({ block: 'nearest' })
  }, [selected, open])

  // 키보드 핸들러
  useEffect(() => {
    if (!open) return
    function onKey(e) {
      if (e.key === 'Escape') {
        e.preventDefault()
        onClose()
      } else if (e.key === 'ArrowDown') {
        e.preventDefault()
        setSelected(s => Math.min(s + 1, Math.max(0, items.length - 1)))
      } else if (e.key === 'ArrowUp') {
        e.preventDefault()
        setSelected(s => Math.max(s - 1, 0))
      } else if (e.key === 'Enter') {
        e.preventDefault()
        const item = items[selected]
        if (item) execute(item)
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, items, selected])

  function execute(item) {
    switch (item.kind) {
      case 'page':
        navigate(item.page)
        break
      case 'resource':
        // 사이드바 리소스 종류 클릭과 동일 동작
        navigate('resources', item.resource)
        break
      case 'k8s-resource':
        // 실제 리소스 — 네임스페이스 자동 전환 후 해당 종류 브라우저로 이동
        if (item.k8sNs) setNamespace(item.k8sNs)
        navigate('resources', item.k8sRtype)
        break
      case 'cluster':
        switchCluster(item.clusterId)
        break
      case 'command':
        if (item.action === 'connect') setShowConnect(true)
        else if (item.action === 'refresh') refreshStatus()
        break
      default:
        break
    }
    onClose()
  }

  if (!open) return null

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0,
        background: 'rgba(0,0,0,0.55)',
        backdropFilter: 'blur(2px)',
        zIndex: 1000,
        display: 'flex', alignItems: 'flex-start', justifyContent: 'center',
        paddingTop: 110,
      }}
    >
      <div
        onClick={e => e.stopPropagation()}
        style={{
          background: 'var(--bg-2)',
          border: '1px solid var(--border-bright)',
          borderRadius: 10,
          width: 580, maxWidth: 'calc(100vw - 40px)',
          maxHeight: 'calc(100vh - 180px)',
          display: 'flex', flexDirection: 'column',
          boxShadow: '0 18px 70px rgba(0,0,0,0.7)',
          overflow: 'hidden',
        }}
      >
        {/* 검색 input */}
        <div style={{
          padding: '14px 18px',
          borderBottom: '1px solid var(--border)',
          display: 'flex', alignItems: 'center', gap: 10,
        }}>
          <span style={{ color: 'var(--nimbus)', fontSize: 18, lineHeight: 1 }}>⌕</span>
          <input
            ref={inputRef}
            value={query}
            onChange={e => { setQuery(e.target.value); setSelected(0) }}
            placeholder="페이지, 리소스, 클러스터, 명령어 검색..."
            style={{
              flex: 1,
              background: 'transparent', border: 'none', outline: 'none',
              color: 'var(--text-bright)', fontSize: 14,
              fontFamily: 'var(--font)',
            }}
          />
        </div>

        {/* 결과 */}
        <div ref={listRef} style={{ flex: 1, overflowY: 'auto', padding: '4px 0' }}>
          {items.length === 0 ? (
            <div style={{
              padding: '28px 18px', color: 'var(--text-dim)',
              fontSize: 13, textAlign: 'center',
            }}>
              일치하는 결과가 없습니다.
            </div>
          ) : items.map((item, idx) => {
            const isSel = idx === selected
            const Icon  = item.icon
            return (
              <div
                key={item.id}
                data-selected={isSel}
                onClick={() => execute(item)}
                onMouseEnter={() => setSelected(idx)}
                style={{
                  display: 'flex', alignItems: 'center', gap: 11,
                  padding: '8px 18px',
                  cursor: 'pointer',
                  background: isSel ? 'rgba(52,211,153,0.10)' : 'transparent',
                  borderLeft: `2px solid ${isSel ? 'var(--nimbus)' : 'transparent'}`,
                  fontSize: 13,
                  color: isSel ? 'var(--text-bright)' : 'var(--text)',
                  transition: 'background 0.08s',
                }}
              >
                {Icon && (
                  <Icon
                    size={14}
                    color={isSel ? 'var(--nimbus)' : 'var(--text-dim)'}
                    style={{ flexShrink: 0 }}
                  />
                )}
                <div style={{
                  flex: 1, overflow: 'hidden',
                  textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                }}>
                  {item.label}
                  {item.sub && (
                    <span style={{
                      marginLeft: 8, fontSize: 10.5, color: 'var(--text-dim)',
                      fontFamily: 'var(--font-mono)',
                    }}>
                      {item.sub}
                    </span>
                  )}
                </div>
                <span style={{
                  fontSize: 10, color: 'var(--text-dim)',
                  letterSpacing: '0.04em', flexShrink: 0,
                }}>
                  {item.group}
                </span>
              </div>
            )
          })}
        </div>

        {/* footer hint */}
        <div style={{
          padding: '8px 18px',
          borderTop: '1px solid var(--border)',
          fontSize: 10, color: 'var(--text-dim)',
          display: 'flex', gap: 16, alignItems: 'center',
          letterSpacing: '0.04em',
        }}>
          <span><kbd style={kbdStyle}>↑↓</kbd> 이동</span>
          <span><kbd style={kbdStyle}>Enter</kbd> 선택</span>
          <span><kbd style={kbdStyle}>Esc</kbd> 닫기</span>
          <span style={{ flex: 1 }} />
          {idxLoading && (
            <span style={{ color: 'var(--nimbus)' }}>리소스 인덱싱 중...</span>
          )}
          {!idxLoading && idxError && (
            <span style={{ color: 'var(--red)' }} title={idxError}>인덱스 실패</span>
          )}
          {!idxLoading && !idxError && connected && resourceIdx.length > 0 && (
            <span style={{ color: 'var(--text-mid)' }}>리소스 {resourceIdx.length}건</span>
          )}
          <span style={{ color: 'var(--text-mid)', marginLeft: 8 }}>{items.length}건 표시</span>
        </div>
      </div>
    </div>
  )
}

const kbdStyle = {
  display: 'inline-block',
  padding: '1px 5px',
  background: 'var(--bg-3)',
  border: '1px solid var(--border)',
  borderRadius: 3,
  color: 'var(--text-mid)',
  fontFamily: 'var(--font-mono)',
  fontSize: 9.5,
  marginRight: 3,
}
