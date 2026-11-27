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

  // 창 컨트롤 (frameless 커스텀 타이틀바)
  windowMinimize:       ()              => callSafe('window_minimize'),
  windowToggleMaximize: ()              => callSafe('window_toggle_maximize'),
  windowClose:          ()              => callSafe('window_close'),
  windowGetBounds:      ()              => callSafe('window_get_bounds'),
  windowSetBounds:      (x, y, w, h)    => callSafe('window_set_bounds', x, y, w, h),
  // 제목표시줄 드래그 시작 — 최대화 상태면 복원하고 잡은 지점을 돌려준다 (v1.2.151)
  windowDragBegin:      (sx, sy)        => callSafe('window_drag_begin', sx, sy),
  // 보고서 기본 파일명 (클러스터 별명 포함) — v1.2.154
  defaultReportFilename: ()             => callSafe('default_report_filename'),

  // 멀티클러스터 관리 (v3.7.0)
  getClusters:            ()                   => call('get_clusters'),
  getMulticlusterSummary: ()                   => callSafe('get_multicluster_summary'),
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
  testWebhook:       (url)           => callSafe('test_webhook', url),

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
  // 리소스 실시간 갱신 (watch API) — v1: pods 만 지원
  resourceWatchKinds:  ()                       => callSafe('resource_watch_kinds'),
  startResourceWatch:  (kind, ns='')            => callSafe('start_resource_watch', kind, ns),
  recvResourceWatch:   (watchId)                => callSafe('recv_resource_watch', watchId),
  stopResourceWatch:   (watchId)                => callSafe('stop_resource_watch', watchId),
  deleteResource:    (kind, ns, name)=> call('delete_resource', kind, ns, name),

  // 리소스 쓰기 (YAML apply / scale / rollout restart)
  applyResourceYaml: (yamlText, kind='') => callSafe('apply_resource_yaml', yamlText, kind),
  validateResourceYaml: (yamlText) => callSafe('validate_resource_yaml', yamlText),
  patchResource:     (kind, ns, name, patch) => callSafe('patch_resource', kind, ns, name, patch),
  scaleResource:     (kind, ns, name, replicas) => callSafe('scale_resource', kind, ns, name, replicas),
  rolloutRestart:    (kind, ns, name) => callSafe('rollout_restart', kind, ns, name),
  getRolloutRevisions: (kind, ns, name)          => callSafe('get_rollout_revisions', kind, ns, name),
  rolloutUndo:         (kind, ns, name, revision) => callSafe('rollout_undo', kind, ns, name, revision),

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
  getHelmReleases:     ()                  => call('get_helm_releases'),

  // kubectl 터미널
  runKubectl:        (cmd)           => call('run_kubectl', cmd),
  openPodShell:      (ns, name, ctr) => call('open_pod_shell', ns, name, ctr),
  // 내장 파드 exec 셸 (WebSocket 스트림, xterm.js)
  startPodExec:      (ns, name, ctr='', shell='', cols=80, rows=24) =>
                       callSafe('start_pod_exec', ns, name, ctr, shell, cols, rows),
  recvPodExec:       (sessionId)     => callSafe('recv_pod_exec', sessionId),
  getPodExecSnapshot:(sessionId)     => callSafe('get_pod_exec_snapshot', sessionId),
  sendPodExec:       (sessionId, data) => callSafe('send_pod_exec', sessionId, data),
  resizePodExec:     (sessionId, cols, rows) => callSafe('resize_pod_exec', sessionId, cols, rows),
  closePodExec:      (sessionId)     => callSafe('close_pod_exec', sessionId),
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
  // 규칙 기반 클러스터 스캔 (온디맨드) + 선택적 LLM 설명 + 선택적 네트워크 스캐닝.
  // positional 호출이므로 새 인자는 반드시 **맨 뒤에** 추가해야 한다(중간 삽입 시 오결합).
  healthScan:        (explain=false, llmUrl='', llmModel='local-model', netscan=false) =>
                       callSafe('health_scan', explain, llmUrl, llmModel, netscan),

  // CHECK 탭 업그레이드 사전 점검 (v1.4.1)
  upgradeCheckVersions: ()                 => callSafe('upgrade_check_versions'),
  upgradeCheck:         (target)           => callSafe('upgrade_check', target),
  upgradeCheckSave:     (path)             => callSafe('upgrade_check_save', path),
  upgradeCheckFilename: ()                 => callSafe('upgrade_check_filename'),

  // YAML 실험실 — 매니페스트 저장/버전/적용/파급관찰/반출.
  // GitLab 연동은 의도적으로 없다(클러스터마다 저장소가 달라 대상이 하나로 안 정해짐).
  labList:           (query='')                  => callSafe('lab_list', query),
  labGet:            (mid)                       => callSafe('lab_get', mid),
  labSave:           (mid, name, content, tags='', notes='') =>
                       callSafe('lab_save', mid, name, content, tags, notes),
  labDelete:         (mid)                       => callSafe('lab_delete', mid),
  labVersionDiff:    (va, vb)                    => callSafe('lab_version_diff', va, vb),
  labPreview:        (content)                   => callSafe('lab_preview', content),
  labApply:          (mid, content, watchS=40)   => callSafe('lab_apply', mid, content, watchS),
  labApplyStatus:    (jobId)                     => callSafe('lab_apply_status', jobId),
  labApplyCancel:    (jobId)                     => callSafe('lab_apply_cancel', jobId),
  labTeardown:       (mid, content='')           => callSafe('lab_teardown', mid, content),
  labExportText:     (ids)                       => callSafe('lab_export_text', ids),
  labExportFolder:   (ids, byCluster=true)       => callSafe('lab_export_folder', ids, byCluster),

  // AIOps — LLM 진단 (이벤트/로그). source: 'events' | 'logs'
  aiDiagnose:        (source, payload, llmUrl, llmModel, question = '') =>
                       callSafe('ai_diagnose', source, payload, llmUrl, llmModel, question),
  // AIOps — 멀티턴 후속 질문 / 자유 대화. messages: [{role,content}, ...]
  // system 생략 시 K8s 진단 후속용.
  aiChat:            (messages, llmUrl, llmModel, system = '') =>
                       callSafe('ai_chat', messages, llmUrl, llmModel, system),
  // 로컬 모델 UX — LLM 서버 도달성 확인 + 모델 목록(/v1/models)
  testLlmConnection: (llmUrl)        => callSafe('test_llm_connection', llmUrl),

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

  // ── Vault (v1.2.1 — 코어 보안) ────────────────────────────────────
  vaultStatus:           ()                          => callSafe('vault_status'),
  vaultInit:             (masterPw, autoUnlock=false) => callSafe('vault_init', masterPw, autoUnlock),
  vaultUnlock:           (masterPw)                  => callSafe('vault_unlock', masterPw),
  vaultUnlockDpapi:      ()                          => callSafe('vault_unlock_dpapi'),

  // Windows Hello (v1.2.167)
  helloStatus:           ()                          => callSafe('hello_status'),
  vaultUnlockHello:      ()                          => callSafe('vault_unlock_hello'),
  vaultSetRequireHello:  (enable)                    => callSafe('vault_set_require_hello', !!enable),
  vaultSetAutoUnlock:    (enable)                    => callSafe('vault_set_auto_unlock', enable),
  vaultLock:             ()                          => callSafe('vault_lock'),
  vaultChangePassword:   (oldPw, newPw)              => callSafe('vault_change_password', oldPw, newPw),
  // MCP 액세스 토큰 (v1.2.119) — 발급 응답의 token 은 1회성, 저장하지 말 것
  vaultIssueMcpToken:    (label, scope, days)        => callSafe('vault_issue_mcp_token', label, scope, days),
  vaultListMcpTokens:    ()                          => callSafe('vault_list_mcp_tokens'),
  vaultRevokeMcpToken:   (tokenId)                   => callSafe('vault_revoke_mcp_token', tokenId),
  vaultEntries:          ()                          => callSafe('vault_entries'),

  // kubeconfig vault 보관 (v1.2.1)
  storeKubeconfig:       (name, content)             => callSafe('store_kubeconfig', name, content),
  listKubeconfigs:       ()                          => callSafe('list_kubeconfigs'),
  getKubeconfig:         (name)                      => callSafe('get_kubeconfig', name),
  deleteKubeconfig:      (name)                      => callSafe('delete_kubeconfig', name),
  renameKubeconfig:      (oldName, newName)          => call('rename_kubeconfig', oldName, newName),

  openThirdPartyNotices: ()                          => callSafe('open_third_party_notices'),   // 오픈소스 고지 (v1.4.19)

}
