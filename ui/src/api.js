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
  // 앱 버전 / 활성 플러그인
  getAppVersion:        ()              => call('get_app_version'),
  getEnabledFeatures:   ()              => callSafe('get_enabled_features'),

  // 멀티클러스터 관리 (v3.7.0)
  getClusters:            ()                   => call('get_clusters'),
  addCluster:             (path, context=null) => call('add_cluster', path, context),
  addClusterFromVault:    (kcName, context=null) => callSafe('add_cluster_from_vault', kcName, context),
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

  // 데이터 디렉터리 위치 (v1.2.2)
  getDataDir:        ()              => callSafe('get_data_dir'),
  browseFolder:      (start=null)    => callSafe('browse_folder', start),
  changeDataDir:     (newPath)       => callSafe('change_data_dir', newPath),

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

  // 리소스 쓰기 (YAML apply / scale / rollout restart)
  applyResourceYaml: (yamlText, kind='') => callSafe('apply_resource_yaml', yamlText, kind),
  scaleResource:     (kind, ns, name, replicas) => callSafe('scale_resource', kind, ns, name, replicas),
  rolloutRestart:    (kind, ns, name) => callSafe('rollout_restart', kind, ns, name),

  // CRD 자동 발견
  getCrds:           ()                => callSafe('get_crds'),
  getCrdObjects:     (group, version, plural, namespaced, ns='', printerColumns=[]) =>
                       callSafe('get_crd_objects', group, version, plural, namespaced, ns, printerColumns),

  // RBAC 분석
  getRbac:           (includeSystem=false) => callSafe('get_rbac', includeSystem),

  // 스냅샷 / Diff (운영 점검)
  takeSnapshot:      (label='')      => callSafe('take_snapshot', label),
  listSnapshots:     ()              => callSafe('list_snapshots'),
  deleteSnapshot:    (sid)           => callSafe('delete_snapshot', sid),
  diffSnapshots:     (idA, idB)      => callSafe('diff_snapshots', idA, idB),

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
  installK9s:        ()              => call('install_k9s'),

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

  // 앱 카탈로그 (v3.7.13-r1)
  getCatalog:              ()                                        => callSafe('get_catalog'),
  detectClusterProfile:    ()                                        => callSafe('detect_cluster_profile'),
  getCatalogAppValues:     (appId, preset)                           => callSafe('get_catalog_app_values', appId, preset),
  catalogPreflight:        (appId)                                   => callSafe('catalog_preflight', appId),
  startCatalogInstall:     (appId, ns, releaseName, valuesYaml)      => callSafe('start_catalog_install', appId, ns, releaseName, valuesYaml),
  getCatalogInstallStatus: (jobId)                                   => callSafe('get_catalog_install_status', jobId),
  uninstallCatalogApp:     (releaseName, ns)                         => callSafe('uninstall_catalog_app', releaseName, ns),
  getInstalledCatalogApps: ()                                        => callSafe('get_installed_catalog_apps'),
  installHelm:             ()                                        => callSafe('install_helm'),

  // 스택 묶음 설치 (v3.7.13-r7)
  startStackInstall:       (stackId, preset, appConfigs)            => callSafe('start_stack_install', stackId, preset, appConfigs),
  getStackInstallStatus:   (jobId)                                  => callSafe('get_stack_install_status', jobId),

  // ── Vault (v1.2.1 — 코어 보안, K8s/SSH 공통) ────────────────────────────
  vaultStatus:           ()                          => callSafe('vault_status'),
  vaultInit:             (masterPw, autoUnlock=false) => callSafe('vault_init', masterPw, autoUnlock),
  vaultUnlock:           (masterPw)                  => callSafe('vault_unlock', masterPw),
  vaultUnlockDpapi:      ()                          => callSafe('vault_unlock_dpapi'),
  vaultSetAutoUnlock:    (enable)                    => callSafe('vault_set_auto_unlock', enable),
  vaultLock:             ()                          => callSafe('vault_lock'),
  vaultChangePassword:   (oldPw, newPw)              => callSafe('vault_change_password', oldPw, newPw),
  vaultEntries:          ()                          => callSafe('vault_entries'),

  // kubeconfig vault 보관 (v1.2.1)
  storeKubeconfig:       (name, content)             => callSafe('store_kubeconfig', name, content),
  listKubeconfigs:       ()                          => callSafe('list_kubeconfigs'),
  getKubeconfig:         (name)                      => callSafe('get_kubeconfig', name),
  deleteKubeconfig:      (name)                      => callSafe('delete_kubeconfig', name),

  // ── infra 플러그인 (v1.1.0) ─────────────────────────────────────────────

  // 서버 인벤토리
  listServers:           ()                          => callSafe('list_servers'),
  getServer:             (id)                        => callSafe('get_server', id),
  addServer:             (payload)                   => callSafe('add_server', payload),
  updateServer:          (id, patch)                 => callSafe('update_server', id, patch),
  deleteServer:          (id)                        => callSafe('delete_server', id),

  // 서버 비밀
  setServerSecret:       (id, kind, value)           => callSafe('set_server_secret', id, kind, value),
  setServerSecretFromFile:(id, kind, path)           => callSafe('set_server_secret_from_file', id, kind, path),
  clearServerSecret:     (id, kind)                  => callSafe('clear_server_secret', id, kind),
  browsePkey:            ()                          => callSafe('browse_pkey'),

  // 연결 테스트
  testServer:            (id)                        => callSafe('test_server', id),
  validateServer:        (payload, secrets)          => callSafe('validate_server', payload, secrets),

  // 레시피 (RKE2 등)
  listRecipes:           ()                          => callSafe('list_recipes'),
  runRecipe:             (recipe, serverId, options, sudoPw) =>
                                                        callSafe('run_recipe', recipe, serverId, options, sudoPw),
  getRecipeJob:          (jobId)                     => callSafe('get_recipe_job', jobId),
  listRecipeJobs:        ()                          => callSafe('list_recipe_jobs'),
  cancelRecipeJob:       (jobId)                     => callSafe('cancel_recipe_job', jobId),
  clearRecipeJob:        (jobId)                     => callSafe('clear_recipe_job', jobId),

  // SSH 터미널 (PTY) 세션
  startSshSession:       (serverId, cols=80, rows=24) => callSafe('start_ssh_session', serverId, cols, rows),
  recvSshSession:        (sessionId)                 => callSafe('recv_ssh_session', sessionId),
  getSshSessionSnapshot: (sessionId)                 => callSafe('get_ssh_session_snapshot', sessionId),
  sendSshSession:        (sessionId, data)           => callSafe('send_ssh_session', sessionId, data),
  resizeSshSession:      (sessionId, cols, rows)     => callSafe('resize_ssh_session', sessionId, cols, rows),
  closeSshSession:       (sessionId)                 => callSafe('close_ssh_session', sessionId),
  listSshSessions:       ()                          => callSafe('list_ssh_sessions'),
}
