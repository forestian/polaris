import React, { createContext, useContext, useState, useCallback, useEffect, useRef } from 'react'
import { api } from './api.js'
import { shouldSilentUnlock } from './vaultGate.js'
import { applyTheme, normalizeThemeId, installThemeStyles } from './themeRegistry.js'
import { normalizeCustom } from './customTheme.js'
import { normalizeEnabledFeaturesResponse } from './featureGate.js'

const AppContext = createContext(null)

// Provider value 는 (수정 전) 매 렌더 새 객체(60+ 필드)라, useApp() 을 쓰는 ~40개 소비자 전체가
// 자신과 무관한 상태 변화(예: 다른 탭에서 진행 중인 설치 job 의 1~2초 폴링)에도 함께 리렌더됐다.
// 필드가 많아 손으로 useMemo dependency 배열을 나열하면 하나만 빠뜨려도 그 필드가 stale 값에
// 갇히는 버그가 생기므로, 대신 얕은 비교로 실제 값이 하나라도 바뀐 필드가 있을 때만 새 참조를
// 반환한다(전부 그대로면 이전 객체 참조를 그대로 재사용 → React 가 리렌더 스킵).
function useStableProviderValue(obj) {
  const ref = useRef(obj)
  const prev = ref.current
  const keys = Object.keys(obj)
  const changed = keys.length !== Object.keys(prev).length || keys.some(k => obj[k] !== prev[k])
  if (changed) ref.current = obj
  return ref.current
}

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
  const [settingsTab, setSettingsTab] = useState(null)   // 설정을 특정 탭으로 열 때 (v1.3.50)
  const [logTarget,  setLogTarget]    = useState(null)
  const [terminalCommand, setTerminalCommand] = useState('')

  // ── 앱 모드 — 'k8s' | 'check' ──────────────────────────────────────────
  // 모드 전환 시 사이드바 / 상단 탭 / 페이지 라우팅 모두 교체됨.
  const [appMode, _setAppMode] = useState('k8s')
  // CHECK 모드 — 클러스터 스캔 · 업그레이드 사전 점검 · 클러스터 보고서. 목록은 checkPages.js
  const [checkActivePage, setCheckActivePage] = useState('health')

  // ── Vault (v1.2.1 — 코어 보안) ────────────────────────────────────────────
  // available: cryptography 사용 가능 여부 (false 면 게이트 우회 = 평문 동작)
  // exists/unlocked: vault 파일 존재 / 현재 잠금 해제 상태
  const [vaultStatus, setVaultStatus] = useState({ exists: false, unlocked: false, available: true, has_dpapi: false })
  const [vaultChecked, setVaultChecked] = useState(false)   // 최초 부팅 시퀀스(자동해제 포함) 완료 여부
  const [showVaultPanel, setShowVaultPanel] = useState(false) // 좌하단 박스 클릭 시 보안 보관함 패널
  // 사용자가 직접 '잠그기'를 눌렀는지 (Win+L 식 잠금화면 표시 트리거). 시작 시 로그인과 구분.
  const [vaultLockedByUser, setVaultLockedByUser] = useState(false)

  // vault 잠금 해제 간주 조건: 실제 unlock 됐거나 vault 가 비활성(평문 빌드)일 때
  const vaultUnlocked = vaultStatus.unlocked === true || vaultStatus.available === false

  // 상태만 갱신(부팅 완료 플래그는 건드리지 않음). 갱신된 상태 객체를 반환.
  const refreshVaultStatus = useCallback(async () => {
    let next
    try {
      const s = await api.vaultStatus()
      if (s && s.error === undefined && typeof s.exists === 'boolean') {
        next = {
          exists:    !!s.exists,
          unlocked:  !!s.unlocked,
          available: s.available !== false,
          has_dpapi: !!s.has_dpapi,
        }
      } else {
        // 백엔드 미준비 / cryptography 없음 → 게이트 우회 (평문 동작)
        next = { exists: false, unlocked: false, available: false, has_dpapi: false }
      }
    } catch {
      next = { exists: false, unlocked: false, available: false, has_dpapi: false }
    }
    setVaultStatus(next)
    return next
  }, [])

  // ── Vault 액션 (init / unlock / lock / 비번 변경 / 자동해제 토글) ─────────
  const vaultInit = useCallback(async (pw, autoUnlock = false) => {
    const r = await api.vaultInit(pw, autoUnlock)
    await refreshVaultStatus()
    return r
  }, [refreshVaultStatus])

  const vaultUnlock = useCallback(async (pw) => {
    const r = await api.vaultUnlock(pw)
    if (r?.ok) setVaultLockedByUser(false)
    await refreshVaultStatus()
    return r
  }, [refreshVaultStatus])

  const vaultUnlockDpapi = useCallback(async () => {
    const r = await api.vaultUnlockDpapi()
    if (r?.ok) setVaultLockedByUser(false)
    await refreshVaultStatus()
    return r
  }, [refreshVaultStatus])

  const vaultUnlockHello = useCallback(async () => {
    const r = await api.vaultUnlockHello()
    if (r?.ok) setVaultLockedByUser(false)
    await refreshVaultStatus()
    return r
  }, [refreshVaultStatus])

  const vaultLock = useCallback(async () => {
    setVaultLockedByUser(true)   // 수동 잠금 → 잠금화면(자물쇠) 표시
    const r = await api.vaultLock()
    await refreshVaultStatus()
    return r
  }, [refreshVaultStatus])

  const vaultChangePassword = useCallback(async (oldPw, newPw) => {
    const r = await api.vaultChangePassword(oldPw, newPw)
    return r
  }, [])

  const vaultSetAutoUnlock = useCallback(async (enable) => {
    const r = await api.vaultSetAutoUnlock(enable)
    await refreshVaultStatus()
    return r
  }, [refreshVaultStatus])

  const setAppMode = useCallback((mode) => {
    if (!['k8s', 'check'].includes(mode)) return
    _setAppMode(mode)
  }, [])

  // ── 윈도우 가시성 (v3.7.11) ──────────────────────────────────────────────
  // 트레이로 hide되면 false → 모든 polling 일시정지
  const [windowVisible, setWindowVisible] = useState(true)

  // ── 앱 설정 (v3.7.11) ────────────────────────────────────────────────────
  const [settings, setSettingsState] = useState({
    closeBehavior: 'tray',  // 'tray' | 'exit'
    autoRestore:   true,
    themeId:       'polaris',
    customTheme:   {},      // 커스텀 테마 색 (themeId==='custom' 일 때 쓰임)
    notifications: {},      // 이벤트→트레이/웹훅 알림
  })

  // ── 세션 영속화 (v3.7.3) ─────────────────────────────────────────────────
  // 초기 복원이 끝나기 전에는 save를 트리거하지 않는다 (race 방지)
  const restoredRef = useRef(false)
  const saveTimerRef = useRef(null)

  // 활성 옵셔널 플러그인 목록 (v1.1.0) — UI 게이팅용
  const [enabledFeatures, setEnabledFeatures] = useState(null)

  // 설정에서 기능을 켜고 끈 직후 상단 탭이 바로 바뀌게 — 재시작 없이. (v1.3.16)
  const refreshEnabledFeatures = useCallback(async () => {
    const r = await api.getEnabledFeatures()
    const features = normalizeEnabledFeaturesResponse(r)
    if (features !== null) setEnabledFeatures(features)
  }, [])

  // ── 앱 버전 + features 로드 ─────────────────────────────────────────────
  useEffect(() => {
    let cancelled = false
    let retryTimer = null

    function loadFeatures(attempt = 0) {
      api.getEnabledFeatures()
        .then(r => {
          if (cancelled) return
          const features = normalizeEnabledFeaturesResponse(r)
          if (features !== null) {
            setEnabledFeatures(features)
            return
          }
          if (attempt < 20) {
            retryTimer = window.setTimeout(() => loadFeatures(attempt + 1), 250)
          }
        })
        .catch(() => {
          if (!cancelled && attempt < 20) {
            retryTimer = window.setTimeout(() => loadFeatures(attempt + 1), 250)
          }
        })
    }

    function loadVersion() {
      api.getAppVersion()
        .then(r => setAppVersion(r?.version || ''))
        .catch(() => {})
      loadFeatures()
    }
    if (window.pywebview?.api) {
      loadVersion()
    } else {
      window.addEventListener('pywebviewready', loadVersion, { once: true })
    }

    return () => {
      cancelled = true
      if (retryTimer) window.clearTimeout(retryTimer)
      window.removeEventListener('pywebviewready', loadVersion)
    }
  }, [])

  // ── Vault 부팅 시퀀스 (v1.2.1~) ──────────────────────────────────────────
  // pywebview 준비 후 vault_status 조회 → DPAPI 자동해제 모드면 비밀번호 없이
  // 먼저 해제 시도 → 결과 확정 후 vaultChecked=true (게이트 깜빡임 방지).
  // dev 브라우저(pywebview 없음)는 2초 후 우회.
  useEffect(() => {
    let cancelled = false
    let fallback = null
    async function boot() {
      if (cancelled) return
      const s = await refreshVaultStatus()
      // 자동 잠금 해제(DPAPI) 모드 + 아직 잠김 → 비밀번호 없이 해제 시도.
      // 단, Windows Hello 요구(v1.2.167)가 켜져 있으면 **조용히 열지 않는다** —
      // 사람 확인을 세우려고 켠 설정인데 부팅 때 그냥 열리면 의미가 없다.
      // 판단은 shouldSilentUnlock() 에 모아 뒀다 (vaultGate.test.mjs 로 고정).
      const dpapiCandidate = s.available && s.exists && s.has_dpapi && !s.unlocked
      let hello = null
      if (!cancelled && dpapiCandidate) {
        try { hello = await api.helloStatus() } catch { hello = null }
      }
      if (!cancelled && shouldSilentUnlock(s, hello)) {
        try {
          const r = await api.vaultUnlockDpapi()
          if (!cancelled && r?.ok) await refreshVaultStatus()
        } catch {}
      }
      if (!cancelled) setVaultChecked(true)
    }
    if (window.pywebview?.api) {
      boot()
    } else {
      window.addEventListener('pywebviewready', boot, { once: true })
      // dev 폴백: pywebview 가 끝내 안 뜨면 게이트 통과 (평문)
      fallback = window.setTimeout(() => {
        if (!cancelled && !window.pywebview?.api) {
          setVaultStatus({ exists: false, unlocked: false, available: false, has_dpapi: false })
          setVaultChecked(true)
        }
      }, 2000)
    }
    return () => {
      cancelled = true
      if (fallback) window.clearTimeout(fallback)
      window.removeEventListener('pywebviewready', boot)
    }
  }, [refreshVaultStatus])

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

  // 커스텀 색이 바뀌면 <style> 블록을 다시 심고 나서 테마를 적용한다.
  // 순서가 반대면 방금 고른 색이 **한 박자 늦게** 반영된다.
  useEffect(() => {
    installThemeStyles(undefined, normalizeCustom(settings.customTheme))
    applyTheme(settings.themeId)
  }, [settings.themeId, settings.customTheme])

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

  // 네임스페이스 목록 재조회 — 클러스터 변경 외에도 리소스 화면 진입 시 호출.
  const refreshNamespaces = useCallback(() => {
    if (!connected) return
    api.getNamespaces()
      .then(ns => setNamespaces(['All Namespaces', ...(ns || [])]))
      .catch(() => {})
  }, [connected])

  // ── 활성 클러스터 변경 시 네임스페이스 목록 갱신 ──────────────────────────
  useEffect(() => {
    if (!connected) {
      setNamespaces([])
      _setNamespace('All Namespaces')
      return
    }
    refreshNamespaces()
  }, [activeClusterId, connected, refreshNamespaces])

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

  // ── vault 보관 kubeconfig 로 연결 (보안 보관함 패널에서, v1.2.1) ───────────
  const connectFromVault = useCallback(async (kcName, context = null) => {
    const result = await api.addClusterFromVault(kcName, context)
    if (result?.ok) {
      _setAppMode('k8s')
      await refreshClusters()
      if (result.cluster_id) setActiveClusterId(result.cluster_id)
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
      // display_name 업데이트 + vault 보관 키(kc_name) 동기화 (백엔드가 vault 항목도 이전)
      // → 같은 보관본을 가리키던 다른 탭들의 kc_name 도 함께 갱신(세션 복원 댕글링 방지)
      const oldKc = clusters.find(c => c.id === id)?.kc_name
      const newKc = result.kc_name
      setClusters(prev => prev.map(c => {
        if (c.id === id) return { ...c, display_name: name, kc_name: newKc ?? c.kc_name }
        if (newKc && oldKc && c.kc_name === oldKc) return { ...c, kc_name: newKc }
        return c
      }))
    }
    return result
  }, [clusters])

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
          kc_name:       c.kc_name       ?? null,   // vault 보관 키 (v1.2.1)
          display_name:  c.display_name,
          lastPage:      c.lastPage      ?? 'dashboard',
          lastNamespace: c.lastNamespace ?? 'All Namespaces',
          lastResource:  c.lastResource  ?? null,
        })),
        activePath:    activeCl?.path    ?? null,
        activeContext: activeCl?.context ?? null,
        activeKcName:  activeCl?.kc_name ?? null,
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
            customTheme:   normalizeCustom(s.customTheme),
            // 빠뜨리면 재시작 뒤 테마 · 글꼴만 바꿔 저장해도 웹훅 주소 · 알림 켜기가 지워졌다(v1.4.24) —
            // 저장은 이 객체를 통째로 보내고 백엔드는 없는 키를 기본값으로 채운다
            notifications: (s.notifications && typeof s.notifications === 'object') ? s.notifications : {},
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
        // 저장된 클러스터를 순차적으로 재연결 (실패는 조용히 skip).
        // v1.2.1: kc_name 이 있으면 vault 내용으로 우선 복원(파일 불필요),
        // 실패하거나 kc_name 이 없으면 원본 파일 경로로 fallback.
        // 동일 파일/키의 여러 context 를 구분하기 위해 복합 키 사용.
        const ckey = (s) => (s.kc_name ? 'kc:' + s.kc_name : 'path:' + (s.path || '')) + '::' + (s.context || '')
        const cidByKey = {}
        for (const sc of saved.clusters) {
          const hasVault = !!sc.kc_name
          if (!hasVault && !sc.path) continue
          try {
            let r = null
            if (hasVault) {
              r = await api.addClusterFromVault(sc.kc_name, sc.context ?? null)
            }
            if ((!r || !r.ok) && sc.path) {
              r = await api.addCluster(sc.path, sc.context ?? null)
            }
            if (r?.ok && r.cluster_id) {
              cidByKey[ckey(sc)] = r.cluster_id
            }
          } catch {}
        }
        // 백엔드 목록 동기화
        const list = await api.getClusters()
        if (!Array.isArray(list) || list.length === 0) return
        // 저장 metadata 병합
        const merged = list.map(c => {
          const sc = saved.clusters.find(s => cidByKey[ckey(s)] === c.id)
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
          const sc = saved.clusters.find(s => cidByKey[ckey(s)] === c.id)
          if (sc?.display_name && sc.display_name !== c.display_name) {
            try { await api.renameCluster(c.id, sc.display_name) } catch {}
          }
        }
        // 활성 클러스터 결정 (저장된 active 키 → 첫 클러스터)
        const activeMatch =
          merged.find(c => {
            const sc = saved.clusters.find(s => cidByKey[ckey(s)] === c.id)
            if (!sc) return false
            if (saved.activeKcName) return sc.kc_name === saved.activeKcName
            if (saved.activePath)   return sc.path === saved.activePath
                                          && (sc.context || '') === (saved.activeContext || '')
            return false
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
    // v1.2.1: vault 잠금 해제 전에는 복원을 미룬다 (kubeconfig 가 vault 에 있을 수
    // 있으므로). vaultUnlocked 가 true 가 되는 순간 1회만 실행 (restoredRef 가드).
    if (!vaultUnlocked) return
    if (restoredRef.current) return
    if (window.pywebview?.api) {
      loadSettingsThenRestore()
    } else {
      const handler = () => loadSettingsThenRestore()
      window.addEventListener('pywebviewready', handler, { once: true })
      return () => window.removeEventListener('pywebviewready', handler)
    }
  }, [refreshClusters, vaultUnlocked])

  const value = useStableProviderValue({
    // 멀티클러스터
    clusters, activeClusterId, clusterSwitchKey,
    addCluster, connectFromVault, removeCluster, switchCluster, renameCluster,
    refreshClusters,

    // 기존 호환 파생 상태
    connected, kubeVersion, clusterName,

    // 기존 상태
    appVersion,
    namespace, setNamespace,
    namespaces, setNamespaces, refreshNamespaces,
    activePage, activeResource,
    navigate,
    showConnect, setShowConnect,
    showSettings, setShowSettings,
    settingsTab, setSettingsTab,
    logTarget, setLogTarget,
    terminalCommand, setTerminalCommand,

    // 가시성 & 설정 (v3.7.11)
    windowVisible,
    settings, saveSettings,

    // 앱 모드 (v1.1.0)
    appMode, setAppMode,
    checkActivePage, setCheckActivePage,
    enabledFeatures, refreshEnabledFeatures,

    // Vault (v1.2.1~)
    vaultStatus, vaultChecked, vaultUnlocked, refreshVaultStatus,
    vaultInit, vaultUnlock, vaultUnlockDpapi, vaultUnlockHello, vaultLock,
    vaultChangePassword, vaultSetAutoUnlock,
    showVaultPanel, setShowVaultPanel,
    vaultLockedByUser,
  })

  return (
    <AppContext.Provider value={value}>
      {children}
    </AppContext.Provider>
  )
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be inside AppProvider')
  return ctx
}


