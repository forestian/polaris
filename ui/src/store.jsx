import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { api } from './api.js'
import { applyTheme, normalizeThemeId } from './themeRegistry.js'

const AppContext = createContext(null)

export function AppProvider({ children }) {
  // ── 멀티클러스터 상태 ──────────────────────────────────────────────────────
  // clusters 배열: 백엔드 필드 + 프론트엔드 전용 필드(lastPage, lastNamespace)
  // 식별자는 항상 id (display_name 변경에 영향 없음)
  const [clusters, setClusters]               = useState([])
  const [activeClusterId, setActiveClusterId] = useState(null)

  // 탭 전환 시 현재 페이지를 강제 재마운트하기 위한 카운터
  const [clusterSwitchKey, setClusterSwitchKey] = useState(0)

  // 활성 클러스터 파생 상태 (기존 코드 호환)
  const activeCluster = clusters.find(c => c.id === activeClusterId) ?? null
  const connected     = activeCluster?.connected  ?? false
  const clusterName   = activeCluster?.display_name ?? ''
  const kubeVersion   = activeCluster?.version    ?? ''

  // ── 기존 상태 ────────────────────────────────────────────────────────────
  const [appVersion, setAppVersion]   = useState('')
  const [namespace,  _setNamespace]   = useState('All Namespaces')
  const [namespaces, setNamespaces]   = useState([])
  const [activePage, setActivePage]   = useState('dashboard')
  const [activeResource, setActiveResource] = useState(null)
  const [showConnect, setShowConnect] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [logTarget,  setLogTarget]    = useState(null)
  const [terminalCommand, setTerminalCommand] = useState('')

  // ── 윈도우 가시성 (v3.7.11) ──────────────────────────────────────────────
  // 트레이로 hide되면 false → 모든 polling 일시정지
  const [windowVisible, setWindowVisible] = useState(true)

  // ── 앱 설정 (v3.7.11) ────────────────────────────────────────────────────
  const [settings, setSettingsState] = useState({
    closeBehavior: 'tray',  // 'tray' | 'exit'
    autoRestore:   true,
    themeId:       'polaris',
  })

  // ── 세션 영속화 (v3.7.3) ─────────────────────────────────────────────────
  // 초기 복원이 끝나기 전에는 save를 트리거하지 않는다 (race 방지)
  const restoredRef = useRef(false)
  const saveTimerRef = useRef(null)

  // ── 앱 버전 로드 ─────────────────────────────────────────────────────────
  useEffect(() => {
    function loadVersion() {
      api.getAppVersion()
        .then(r => setAppVersion(r?.version || ''))
        .catch(() => {})
    }
    if (window.pywebview?.api) {
      loadVersion()
    } else {
      window.addEventListener('pywebviewready', loadVersion, { once: true })
      return () => window.removeEventListener('pywebviewready', loadVersion)
    }
  }, [])

  // ── 윈도우 가시성 이벤트 리스너 (v3.7.11) ───────────────────────────────
  // 백엔드 _notify_visibility가 발행하는 'polaris:visibility' 커스텀 이벤트 구독
  useEffect(() => {
    function syncNativeVisibility() {
      setWindowVisible(document.visibilityState !== 'hidden')
    }
    function onVis(e) {
      setWindowVisible(e.detail === 'visible')
    }
    document.addEventListener('visibilitychange', syncNativeVisibility)
    window.addEventListener('focus', syncNativeVisibility)
    window.addEventListener('blur', syncNativeVisibility)
    window.addEventListener('polaris:visibility', onVis)
    syncNativeVisibility()
    return () => {
      document.removeEventListener('visibilitychange', syncNativeVisibility)
      window.removeEventListener('focus', syncNativeVisibility)
      window.removeEventListener('blur', syncNativeVisibility)
      window.removeEventListener('polaris:visibility', onVis)
    }
  }, [])

  // ── 설정 저장 함수 (v3.7.11) ─────────────────────────────────────────────
  const saveSettings = useCallback(async (next) => {
    const merged = {
      ...settings,
      ...next,
      themeId: normalizeThemeId(next?.themeId ?? settings.themeId),
    }
    setSettingsState(merged)
    try {
      await api.saveSettings(merged)
    } catch {}
    return merged
  }, [settings])

  useEffect(() => {
    applyTheme(settings.themeId)
  }, [settings.themeId])

  // ── 클러스터 목록 갱신 ────────────────────────────────────────────────────
  // 백엔드에서 가져온 목록과 프론트엔드 전용 필드(lastPage, lastNamespace)를 병합
  const refreshClusters = useCallback(async () => {
    try {
      const list = await api.getClusters()
      const arr  = list || []
      setClusters(prev => arr.map(c => {
        const existing = prev.find(p => p.id === c.id)
        return {
          ...c,
          lastPage:      existing?.lastPage      ?? 'dashboard',
          lastNamespace: existing?.lastNamespace ?? 'All Namespaces',
          lastResource:  existing?.lastResource  ?? null,
        }
      }))
      const active = arr.find(c => c.active)
      if (active) setActiveClusterId(active.id)
      else if (arr.length === 0) setActiveClusterId(null)
    } catch {}
  }, [])

  // ── 활성 클러스터 변경 시 네임스페이스 목록 갱신 ──────────────────────────
  useEffect(() => {
    if (!connected) {
      setNamespaces([])
      _setNamespace('All Namespaces')
      return
    }
    api.getNamespaces()
      .then(ns => setNamespaces(['All Namespaces', ...(ns || [])]))
      .catch(() => {})
  }, [activeClusterId, connected])

  // ── refreshStatus (기존 호환) ─────────────────────────────────────────────
  const refreshStatus = useCallback(async () => {
    await refreshClusters()
  }, [refreshClusters])

  // ── 네임스페이스 변경 — 현재 클러스터에 lastNamespace 저장 ────────────────
  const setNamespace = useCallback((ns) => {
    _setNamespace(ns)
    setActiveClusterId(id => {
      if (id) {
        setClusters(prev => prev.map(c =>
          c.id === id ? { ...c, lastNamespace: ns } : c
        ))
      }
      return id  // setActiveClusterId는 값을 바꾸지 않음, 현재 id 반환
    })
  }, [])

  // ── 페이지 이동 — 현재 클러스터에 lastPage + lastResource 저장 ────────────
  const navigate = useCallback((page, resource = null) => {
    setActivePage(page)
    setActiveResource(resource)
    setActiveClusterId(id => {
      if (id) {
        setClusters(prev => prev.map(c =>
          c.id === id ? { ...c, lastPage: page, lastResource: resource } : c
        ))
      }
      return id
    })
  }, [])

  // ── 클러스터 추가 ─────────────────────────────────────────────────────────
  const addCluster = useCallback(async (path, context = null) => {
    const result = await api.addCluster(path, context)
    if (result?.ok) {
      await refreshClusters()
      // 새 클러스터는 대시보드에서 시작
      setActivePage('dashboard')
      _setNamespace('All Namespaces')
      setClusterSwitchKey(k => k + 1)
    }
    return result
  }, [refreshClusters])

  // ── 클러스터 제거 ─────────────────────────────────────────────────────────
  const removeCluster = useCallback(async (id) => {
    const result = await api.removeCluster(id)
    if (result?.ok) {
      await refreshClusters()
    }
    return result
  }, [refreshClusters])

  // ── 클러스터 전환 — lastPage / lastNamespace 복원 + 페이지 강제 재마운트 ──
  const switchCluster = useCallback(async (id) => {
    if (id === activeClusterId) return
    const result = await api.switchCluster(id)
    if (result?.ok) {
      // 전환 전에 현재 클러스터 lastPage 저장 (혹시 navigate 없이 바뀌었을 경우 대비)
      setActiveClusterId(id)

      // 대상 클러스터의 마지막 페이지/네임스페이스/리소스 종류 복원
      setClusters(prev => {
        const target = prev.find(c => c.id === id)
        const restoredPage     = target?.lastPage      ?? 'dashboard'
        const restoredNs       = target?.lastNamespace ?? 'All Namespaces'
        const restoredResource = target?.lastResource  ?? null
        setActivePage(restoredPage)
        _setNamespace(restoredNs)
        setActiveResource(restoredResource)
        return prev  // clusters 배열 자체는 변경 없음
      })

      // 카운터 증가 → PageView 강제 재마운트 (같은 페이지여도 데이터 새로고침)
      setClusterSwitchKey(k => k + 1)

      await refreshClusters()
    }
  }, [activeClusterId, refreshClusters])

  // ── 클러스터 이름 변경 — id 기반이므로 lastPage 등 다른 필드 영향 없음 ─────
  const renameCluster = useCallback(async (id, name) => {
    const result = await api.renameCluster(id, name)
    if (result?.ok) {
      // display_name만 업데이트, lastPage/lastNamespace 보존
      setClusters(prev => prev.map(c =>
        c.id === id ? { ...c, display_name: name } : c
      ))
    }
    return result
  }, [])

  // ── 세션 자동 저장 (debounced 500ms) ─────────────────────────────────────
  // clusters · activeClusterId · activePage · namespace 변경 시 자동 호출
  useEffect(() => {
    if (!restoredRef.current) return  // 복원 끝나기 전에는 저장하지 않음
    if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    saveTimerRef.current = setTimeout(() => {
      const activeCl = clusters.find(c => c.id === activeClusterId)
      const state = {
        version: 1,
        clusters: clusters.map(c => ({
          path:          c.path,
          context:       c.context       ?? null,
          display_name:  c.display_name,
          lastPage:      c.lastPage      ?? 'dashboard',
          lastNamespace: c.lastNamespace ?? 'All Namespaces',
          lastResource:  c.lastResource  ?? null,
        })),
        activePath:    activeCl?.path    ?? null,
        activeContext: activeCl?.context ?? null,
      }
      api.saveSession(state).catch(() => {})
    }, 500)
    return () => {
      if (saveTimerRef.current) clearTimeout(saveTimerRef.current)
    }
  }, [clusters, activeClusterId, activePage, activeResource, namespace])

  // ── 세션 자동 복원 + 설정 로드 (앱 시작 시 1회) ───────────────────────────
  useEffect(() => {
    async function loadSettingsThenRestore() {
      // 1) 설정 먼저 로드 — autoRestore 결정에 필요
      let activeSettings = { closeBehavior: 'tray', autoRestore: true, themeId: 'polaris' }
      try {
        const s = await api.getSettings()
        if (s && s.ok !== false && typeof s === 'object') {
          activeSettings = {
            closeBehavior: s.closeBehavior === 'exit' ? 'exit' : 'tray',
            autoRestore:   s.autoRestore !== false,
            themeId:       normalizeThemeId(s.themeId),
          }
          setSettingsState(activeSettings)
        }
      } catch {}

      // 2) autoRestore=false면 세션 복원 스킵
      if (!activeSettings.autoRestore) {
        restoredRef.current = true
        return
      }
      // 3) 기존 복원 로직 실행
      await restoreSession()
    }

    async function restoreSession() {
      try {
        const saved = await api.getSession()
        // 세션 없음, 빈 세션, 또는 에러 → 초기화 완료 처리만
        if (!saved || saved.ok === false || !Array.isArray(saved.clusters) || saved.clusters.length === 0) {
          return
        }
        // 저장된 path+context를 순차적으로 재연결 (실패는 조용히 skip)
        // 동일 파일의 여러 context를 구분하기 위해 복합 키 사용
        const cidByKey = {}
        for (const sc of saved.clusters) {
          if (!sc.path) continue
          try {
            const r = await api.addCluster(sc.path, sc.context ?? null)
            if (r?.ok && r.cluster_id) {
              const key = sc.path + '::' + (sc.context || '')
              cidByKey[key] = r.cluster_id
            }
          } catch {}
        }
        // 백엔드 목록 동기화
        const list = await api.getClusters()
        if (!Array.isArray(list) || list.length === 0) return
        // 저장 metadata 병합
        const merged = list.map(c => {
          const sc = saved.clusters.find(s => {
            const key = s.path + '::' + (s.context || '')
            return cidByKey[key] === c.id
          })
          return {
            ...c,
            lastPage:      sc?.lastPage      ?? 'dashboard',
            lastNamespace: sc?.lastNamespace ?? 'All Namespaces',
            lastResource:  sc?.lastResource  ?? null,
          }
        })
        setClusters(merged)
        // 사용자 지정 이름이 있던 클러스터는 백엔드에 rename 호출
        for (const c of merged) {
          const sc = saved.clusters.find(s => {
            const key = s.path + '::' + (s.context || '')
            return cidByKey[key] === c.id
          })
          if (sc?.display_name && sc.display_name !== c.display_name) {
            try { await api.renameCluster(c.id, sc.display_name) } catch {}
          }
        }
        // 활성 클러스터 결정 (저장된 activePath + activeContext → 첫 클러스터)
        const activeMatch =
          merged.find(c => {
            const sc = saved.clusters.find(s => {
              const key = s.path + '::' + (s.context || '')
              return cidByKey[key] === c.id
            })
            return sc
              && saved.activePath
              && sc.path === saved.activePath
              && (sc.context || '') === (saved.activeContext || '')
          }) || merged[0]
        if (activeMatch) {
          try { await api.switchCluster(activeMatch.id) } catch {}
          setActiveClusterId(activeMatch.id)
          setActivePage(activeMatch.lastPage || 'dashboard')
          _setNamespace(activeMatch.lastNamespace || 'All Namespaces')
          setActiveResource(activeMatch.lastResource || null)
          setClusterSwitchKey(k => k + 1)
        }
        // display_name 갱신 반영을 위해 한번 더 refresh
        await refreshClusters()
      } catch {
        // 복원 실패는 빈 상태로 fallback
      } finally {
        restoredRef.current = true
      }
    }
    if (window.pywebview?.api) {
      loadSettingsThenRestore()
    } else {
      const handler = () => loadSettingsThenRestore()
      window.addEventListener('pywebviewready', handler, { once: true })
      return () => window.removeEventListener('pywebviewready', handler)
    }
  }, [refreshClusters])

  return (
    <AppContext.Provider value={{
      // 멀티클러스터
      clusters, activeClusterId, clusterSwitchKey,
      addCluster, removeCluster, switchCluster, renameCluster,
      refreshClusters,

      // 기존 호환 파생 상태
      connected, kubeVersion, clusterName,

      // 기존 상태
      appVersion,
      namespace, setNamespace,
      namespaces, setNamespaces,
      activePage, activeResource,
      navigate,
      showConnect, setShowConnect,
      showSettings, setShowSettings,
      logTarget, setLogTarget,
      terminalCommand, setTerminalCommand,
      refreshStatus,

      // 가시성 & 설정 (v3.7.11)
      windowVisible,
      settings, saveSettings,
    }}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be inside AppProvider')
  return ctx
}
