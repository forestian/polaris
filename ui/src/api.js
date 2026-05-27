/**
 * pywebview API 브릿지
 * window.pywebview.api.xxx() 호출 래퍼
 * 개발 중에는 mock 데이터로 폴백
 */

function getApi() {
  return window.pywebview?.api ?? null
}

/** pywebview API 메서드 호출. 연결 안 된 경우 에러 throw. */
export async function call(method, ...args) {
  const api = getApi()
  if (!api) throw new Error('pywebview not ready')
  return api[method](...args)
}

/** 안전 호출 — 에러 시 { ok: false, error } 반환 */
export async function callSafe(method, ...args) {
  try {
    const result = await call(method, ...args)
    return result
  } catch (e) {
    return { ok: false, error: String(e) }
  }
}

/** Python → JS 이벤트 구독 */
export function onBusEvent(event, handler) {
  const listener = (e) => handler(e.detail)
  window.addEventListener('polaris:' + event, listener)
  return () => window.removeEventListener('polaris:' + event, listener)
}

// ── 편의 함수 ────────────────────────────────────────────────────────────────

export const api = {
  // 앱 버전
  getAppVersion:     ()              => call('get_app_version'),

  // 멀티클러스터 관리 (v3.7.0)
  getClusters:            ()                   => call('get_clusters'),
  addCluster:             (path, context=null) => call('add_cluster', path, context),
  listKubeconfigContexts: (path)               => callSafe('list_kubeconfig_contexts', path),
  removeCluster:     (id)            => call('remove_cluster', id),
  switchCluster:     (id)            => call('switch_cluster', id),
  renameCluster:     (id, name)      => call('rename_cluster', id, name),

  // 세션 영속화 (v3.7.3)
  getSession:        ()              => callSafe('get_session'),
  saveSession:       (state)         => callSafe('save_session', state),
  clearSession:      ()              => callSafe('clear_session'),

  // 앱 설정 (v3.7.11) — closeBehavior, autoRestore
  getSettings:       ()              => callSafe('get_settings'),
  saveSettings:      (state)         => callSafe('save_settings', state),

  // 명령 팔레트 검색 인덱스 (v3.7.3)
  getSearchIndex:    (force = false) => callSafe('get_search_index', force),

  // 이벤트 타임라인 (v3.7.5)
  getClusterEvents:  (ns = '', limit = 500, types = null) =>
                       callSafe('get_cluster_events', ns, limit, types),

  // CronJob 수동 실행 (v3.7.5)
  triggerCronjob:    (ns, name) => callSafe('trigger_cronjob', ns, name),

  // 연결 (하위 호환)
  browseKubeconfig:  ()              => call('browse_kubeconfig'),
  connect:           (path)          => call('connect', path),
  disconnect:        ()              => call('disconnect'),
  getStatus:         ()              => call('get_status'),

  // 네임스페이스
  getNamespaces:     ()              => call('get_namespaces_list'),

  // 리소스 브라우저
  getResource:       (type, ns)      => call('get_resource', type, ns),
  deleteResource:    (kind, ns, name)=> call('delete_resource', kind, ns, name),

  // 대시보드
  getDashboard:      ()              => call('get_dashboard'),

  // ArgoCD
  getArgoApps:       ()              => call('get_argocd_apps'),
  syncArgoApp:       (ns, name)      => call('sync_argocd_app', ns, name),
  rollbackArgoApp:   (ns, name, id)  => call('rollback_argocd_app', ns, name, id),
  createArgoApp:     (data)          => call('create_argocd_app_json', data),
  updateArgoApp:     (data)          => call('update_argocd_app_json', data),
  deleteArgoApp:     (ns, name)      => call('delete_argocd_app', ns, name),

  // Helm
  getHelmReleases:   ()              => call('get_helm_releases'),

  // kubectl 터미널
  runKubectl:        (cmd)           => call('run_kubectl', cmd),
  openPodShell:      (ns, name, ctr) => call('open_pod_shell', ns, name, ctr),
  getPortForwardTargets: (ns)        => callSafe('get_port_forward_targets', ns),
  startPortForward:  (kind, ns, name, localPort, remotePort) =>
                       callSafe('start_port_forward', kind, ns, name, localPort, remotePort),
  getPortForwards:   ()              => callSafe('get_port_forwards'),
  stopPortForward:   (id)            => callSafe('stop_port_forward', id),
  stopAllPortForwards: ()            => callSafe('stop_all_port_forwards'),

  // k9s 런처
  launchK9s:         ()              => call('launch_k9s'),

  // 보고서
  openSaveDialog:    (name)          => call('open_save_dialog', name),
  saveTextFile:      (content, filename) => callSafe('save_text_file', content, filename),
  generateReport:    (cfg)           => call('generate_report', cfg),
  startReport:       (cfg)           => call('start_report', cfg),
  getJobStatus:      (id)            => call('get_job_status', id),

  // 리소스 상세 패널
  getPodDetail:      (ns, name)             => call('get_pod_detail', ns, name),
  getPodMetrics:     (ns, name)             => callSafe('get_pod_metrics', ns, name),
  getResourceEvents: (kind, ns, name)       => call('get_resource_events', kind, ns, name),
  getResourceLogs:   (ns, name, ctr, tail)  => call('get_resource_logs', ns, name, ctr, tail),
  getResourceYaml:   (kind, ns, name)       => call('get_resource_yaml', kind, ns, name),
  getResourceDescribe:(kind, ns, name)      => call('get_resource_describe', kind, ns, name),

  // 로그 스트리밍 (LogPage 전용)
  startLogStream:  (ns, name, ctr, tail, follow, sourceType = 'pod') => call('start_log_stream', ns, name, ctr, tail, follow, sourceType),
  getLogChunk:     (jobId)                        => call('get_log_chunk', jobId),
  stopLogStream:   (jobId)                        => call('stop_log_stream', jobId),

  // 토폴로지 그래프
  getTopologyData: (ns)                           => call('get_topology_data', ns),

  // (free 빌드 v1.0.10-e1) 앱 카탈로그 plugin 제거됨
}
