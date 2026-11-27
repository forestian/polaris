/**
 * CommandPalette — Ctrl+K 명령 팔레트 (v3.7.3, v1.2.99 전 페이지+즐겨찾기/최근)
 *
 * 검색 가능한 빠른 네비게이션 / 명령 실행 UI.
 * 키보드: Ctrl/Cmd+K로 열기, Esc로 닫기, ↑↓ 이동, Enter 실행.
 *
 * 검색 대상:
 *   1) 페이지 / 도구 (정적 — 사이드바 전 메뉴 노출: 스냅샷 · RBAC · CRD 포함)
 *   2) 클러스터 전환 (현재 비활성 탭)
 *   3) 명령 (새 클러스터 연결)
 *   4) 실제 K8s 리소스 — 파드, 디플로이먼트, 서비스, 컨피그맵 등 (30s 캐시)
 *   5) CHECK 화면(클러스터 스캔 · 업그레이드 사전 점검 · 클러스터 보고서)
 *
 * 고르면 **그 항목의 탭으로 옮겨 간다**(K8S · CHECK).
 *
 * 즐겨찾기(★)/최근(clock): 정적 항목(페이지·리소스 종류·도구)에 한해 localStorage 로 보관,
 * 검색어가 비어 있을 때 상단에 표시. (실제 K8s 리소스/클러스터/명령은 대상 아님)
 */
import React, { useState, useEffect, useRef, useMemo, useCallback } from 'react'
import { useApp } from '../store.jsx'
import { api } from '../api.js'
import { checkPageItems } from '../checkPages.js'
import {
  LayoutDashboard, Globe, FileText,
  Server, Boxes, Layers, ChevronsUp, ChevronsDown, Briefcase, Clock,
  Network, Lock, Key, HardDrive, Package, GitBranch,
  Terminal, Activity, Monitor, Plus, Box, Cable,
  Camera, Archive, ArrowRightLeft, AppWindow, Shield, KeyRound, Star, HeartPulse,
  FlaskConical,
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
  { id: 'multicluster', label: '멀티클러스터', icon: Layers,         kind: 'page', page: 'multicluster' },
  { id: 'topology',  label: '토폴로지',      icon: Globe,           kind: 'page', page: 'topology', requiresConn: true },
  { id: 'events',    label: '이벤트 타임라인', icon: Activity,       kind: 'page', page: 'events',   requiresConn: true },
  { id: 'snapshots', label: '스냅샷',        icon: Camera,          kind: 'page', page: 'snapshots', requiresConn: true },
  { id: 'yamllab',   label: 'YAML 실험실',   icon: FlaskConical,    kind: 'page', page: 'yamllab',  requiresConn: true, sub: '매니페스트 · 적용 · 내보내기' },
  // sub 는 검색 해이스택(label+sub+id)에 들어간다 — 「헬스 체크」 로도 찾히게 남겨둠
  // 클러스터 스캔 · 업그레이드 사전 점검 · 보고서는 CHECK 탭 — 아래 checkPageItems 가 띄운다
  { id: 'logs',      label: '로그뷰어',      icon: Activity,        kind: 'page', page: 'logs',     requiresConn: true },
  { id: 'portforward', label: '포트포워딩', icon: Cable,           kind: 'page', page: 'portforward', requiresConn: true },
  { id: 'rbac',      label: 'RBAC 분석',     icon: Shield,          kind: 'page', page: 'rbac',     requiresConn: true },
  { id: 'crds',      label: 'CRD 커스텀 리소스', icon: KeyRound,    kind: 'page', page: 'crds',     requiresConn: true },
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
  // 「새로고침」 명령은 타이틀바 ↻ 와 같은 동작이라 함께 뺐다(v1.3.46)
]

// ── 정적 항목 레지스트리 (즐겨찾기/최근 id → 재구성용) ─────────────────────────
// 페이지/리소스종류/도구만 즐겨찾기·최근 대상. 명령·클러스터·실 리소스는 제외.
const STATIC_REGISTRY = {}
for (const it of NAV_PAGES) STATIC_REGISTRY[it.id] = { ...it, kind: 'page', group: '페이지' }
for (const it of NAV_TOOLS) STATIC_REGISTRY[it.id] = { ...it, kind: 'page', group: '도구' }
for (const it of NAV_RESOURCES) STATIC_REGISTRY[it.id] = { ...it, kind: 'resource', group: '리소스 종류', requiresConn: true }

function _isFavoritable(item) {
  return !!(item && STATIC_REGISTRY[item.id] &&
            (item.kind === 'page' || item.kind === 'resource'))
}

function _visible(it, ctx) {
  if (it.requiresConn && !ctx.connected) return false
  return true
}

// ── localStorage (즐겨찾기/최근) ──────────────────────────────────────────────
const FAV_KEY    = 'polaris.palette.favorites'
const RECENT_KEY = 'polaris.palette.recent'
const RECENT_MAX = 8

function _loadIds(key) {
  try {
    const a = JSON.parse(localStorage.getItem(key) || '[]')
    return Array.isArray(a) ? a.filter(x => typeof x === 'string') : []
  } catch { return [] }
}
function _saveIds(key, ids) {
  try { localStorage.setItem(key, JSON.stringify(ids.slice(0, 40))) } catch { /* quota/무시 */ }
}

/** 이 항목을 고르면 어느 탭으로 가야 하는가 (다른 탭에서 골라도 화면이 바뀌게) */
function modeFor(item) {
  if (!item) return null
  if (item.kind === 'check-page') return 'check'
  if (['page', 'resource', 'k8s-resource', 'cluster'].includes(item.kind)) return 'k8s'
  return null   // 명령(새 클러스터 연결)은 창만 띄운다 — 탭은 그대로
}

// ── 메인 컴포넌트 ────────────────────────────────────────────────────────────
export default function CommandPalette({ open, onClose }) {
  const {
    connected, clusters, activeClusterId,
    navigate, switchCluster, setShowConnect,
    setNamespace,
    appMode, setAppMode,
    setCheckActivePage,
  } = useApp()
  const gateCtx = useMemo(() => ({ connected }), [connected])

  const [query, setQuery]       = useState('')
  const [selected, setSelected] = useState(0)
  const [resourceIdx, setResourceIdx] = useState([])
  const [idxLoading, setIdxLoading]   = useState(false)
  const [idxError, setIdxError]       = useState(null)
  const [favorites, setFavorites]     = useState(() => _loadIds(FAV_KEY))
  const [recent, setRecent]           = useState(() => _loadIds(RECENT_KEY))
  const inputRef = useRef(null)
  const listRef  = useRef(null)

  const toggleFavorite = useCallback((id) => {
    setFavorites(prev => {
      const next = prev.includes(id) ? prev.filter(x => x !== id) : [id, ...prev]
      _saveIds(FAV_KEY, next)
      return next
    })
  }, [])

  const pushRecent = useCallback((id) => {
    setRecent(prev => {
      const next = [id, ...prev.filter(x => x !== id)].slice(0, RECENT_MAX)
      _saveIds(RECENT_KEY, next)
      return next
    })
  }, [])

  // 열릴 때 input 포커스 + 초기화
  useEffect(() => {
    if (open) {
      setQuery('')
      setSelected(0)
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

    // 2) 정적 항목 빌드 (게이팅 적용)
    const staticItems = []
    for (const it of NAV_PAGES) {
      if (_visible(it, gateCtx)) staticItems.push({ ...it, group: '페이지' })
    }
    if (connected) {
      for (const it of NAV_RESOURCES) {
        staticItems.push({ ...it, kind: 'resource', group: '리소스 종류' })
      }
    }
    for (const it of NAV_TOOLS) {
      if (_visible(it, gateCtx)) staticItems.push({ ...it, group: '도구' })
    }
    for (const c of clusters) {
      if (c.id === activeClusterId) continue
      staticItems.push({
        id: 'cluster:' + c.id, label: c.display_name, sub: c.context || '',
        icon: Server, kind: 'cluster', clusterId: c.id, group: '클러스터 전환',
      })
    }
    for (const cmd of COMMANDS) {
      staticItems.push({ ...cmd, group: '명령' })
    }

    // 3) 쿼리 있으면 필터 (리소스 결과 상단)
    if (q) {
      const filtered = staticItems.filter(it => {
        const hay = (it.label + ' ' + (it.sub || '') + ' ' + (it.id || '')).toLowerCase()
        return hay.includes(q)
      })
      return [...resourceMatches, ...filtered, ...checkPageItems(q)]
    }

    // 4) 쿼리 없으면 즐겨찾기 / 최근 을 상단에 (정적 항목만, 게이팅·중복 정리)
    const favItems = favorites
      .map(id => STATIC_REGISTRY[id]).filter(Boolean)
      .filter(it => _visible(it, gateCtx))
      .map(it => ({ ...it, group: '즐겨찾기' }))
    const favSet = new Set(favorites)
    const recentItems = recent
      .filter(id => !favSet.has(id))
      .map(id => STATIC_REGISTRY[id]).filter(Boolean)
      .filter(it => _visible(it, gateCtx))
      .map(it => ({ ...it, group: '최근' }))

    return [...favItems, ...recentItems, ...staticItems, ...checkPageItems('')]
  }, [query, connected, clusters, activeClusterId, resourceIdx, favorites, recent, gateCtx])

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
    if (_isFavoritable(item)) pushRecent(item.id)   // 정적 네비 항목만 최근에 기록
    // 항목의 탭으로 먼저 옮긴다 — 안 하면 다른 탭에서 골랐을 때 화면이 그대로다
    const mode = modeFor(item)
    if (mode && mode !== appMode) setAppMode(mode)
    switch (item.kind) {
      case 'check-page':
        setCheckActivePage(item.checkPage)
        break
      case 'page':
        navigate(item.page)
        break
      case 'resource':
        navigate('resources', item.resource)
        break
      case 'k8s-resource':
        if (item.k8sNs) setNamespace(item.k8sNs)
        navigate('resources', item.k8sRtype)
        break
      case 'cluster':
        switchCluster(item.clusterId)
        break
      case 'command':
        if (item.action === 'connect') setShowConnect(true)
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
            const fav   = _isFavoritable(item) && favorites.includes(item.id)
            const canFav = _isFavoritable(item)
            return (
              <div
                key={(item.group || '') + ':' + item.id}
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
                {canFav && (isSel || fav) && (
                  <button
                    onClick={e => { e.stopPropagation(); toggleFavorite(item.id) }}
                    title={fav ? '즐겨찾기 해제' : '즐겨찾기 추가'}
                    style={{
                      background: 'transparent', border: 'none', cursor: 'pointer',
                      padding: 2, display: 'grid', placeItems: 'center', flexShrink: 0,
                    }}
                  >
                    <Star size={13}
                      color={fav ? 'var(--nimbus)' : 'var(--text-dim)'}
                      fill={fav ? 'var(--nimbus)' : 'none'} />
                  </button>
                )}
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
          <span><kbd style={kbdStyle}>★</kbd> 즐겨찾기</span>
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
