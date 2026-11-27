/**
 * 토폴로지 — 앱 단위로 묶기 (v1.4.31). topologyApps.test.mjs 로 고정.
 *
 * 예전 화면은 클러스터 전체를 6개 열의 그래프 하나로 그렸다. 열마다 위에서부터 쌓아 관계와 상관없는 자리에 놓이니
 * 선이 화면을 가로질러 엉켰다(사용자: 「보기가 복잡해 잘 안 보게 된다」).
 * 이제 **서로 이어진 Ingress → Service → 워크로드를 앱 하나**로 묶어 카드로 보여 준다. 카드 안은 왼쪽에서 오른쪽으로
 * 「외부 진입 → 서비스 → 워크로드 → 쓰는 설정 · 저장소」 만 읽으면 된다.
 *
 * 묶는 기준은 Ingress ↔ Service ↔ 워크로드, CronJob ↔ Job 선만 — ConfigMap · Secret 은 여러 앱이 함께 쓰는 일이
 * 많아(레지스트리 Secret 하나에 앱 30개) 그걸로 묶으면 앱이 하나로 뭉친다. 설정 · 저장소는 쓰는 워크로드의 앱에 붙이고,
 * 여러 앱이 쓰면 「N개 앱이 함께 씀」 으로 알린다.
 */

const KIND_LABEL = {
  Deployment: 'Deployment', StatefulSet: 'StatefulSet', DaemonSet: 'DaemonSet', Job: 'Job', CronJob: 'CronJob',
}
export const USE_LABEL = { configmap: 'ConfigMap', secret: 'Secret', pvc: 'PVC', pv: 'PV' }

/** 워크로드 상태 → {level: 'ok'|'warn'|'bad'|'idle', text} */
export function workloadHealth(w) {
  if (!w) return { level: 'idle', text: '' }
  if (w.kind === 'Job') {
    if (w.status === 'Failed' || w.failed) return { level: 'bad', text: '실패' }
    if (w.status === 'Active' || w.active) return { level: 'ok', text: '실행 중' }
    if (w.status === 'Complete') return { level: 'ok', text: '완료' }
    return { level: 'idle', text: w.status || '대기' }
  }
  const reasons = w.waiting || []
  const total = w.total || 0
  // 준비 수(v1.4.31) — Running 이어도 준비가 안 됐으면 요청을 못 받는다. 예전 데이터엔 없어 running 으로
  const ready = w.ready ?? w.running ?? 0
  if (reasons.length) return { level: 'bad', text: `${reasons.join(' · ')} — ${ready}/${total} 준비` }
  if (!total) {
    if (w.replicas === 0) return { level: 'idle', text: '0개로 줄여 둠' }
    return { level: w.replicas > 0 ? 'bad' : 'idle', text: w.replicas > 0 ? `파드 없음(바라는 수 ${w.replicas})` : '파드 없음' }
  }
  if (ready < total) return { level: 'warn', text: `${ready}/${total} 준비` }
  return { level: 'ok', text: `${ready}/${total} 준비` + (w.restarts ? ` · 재시작 ${w.restarts}` : '') }
}

const RANK = { bad: 0, warn: 1, ok: 2, idle: 3 }

/** 앱 전체 상태 — 가장 나쁜 워크로드 기준 */
export function appHealth(app) {
  let worst = null
  for (const w of app.workloads) {
    const h = workloadHealth(w)
    if (!worst || RANK[h.level] < RANK[worst.level]) worst = h
  }
  if (!app.workloads.length && app.services.length) worst = { level: 'warn', text: '연결된 워크로드 없음' }
  return worst || { level: 'idle', text: '' }
}

/** get_topology_data 결과 → {apps, sharedUses, counts} */
export function buildApps(raw) {
  const d = raw || {}
  const byId = new Map()
  const put = (n, role) => { byId.set(n.id, { ...n, role }); return n.id }
  for (const x of d.ingresses || []) put(x, 'ingress')
  for (const x of d.services || []) put(x, 'service')
  for (const x of d.workloads || []) put(x, 'workload')
  for (const x of d.cronjobs || []) put(x, 'cronjob')
  for (const x of d.config_nodes || []) put(x, 'use')
  for (const x of d.pv_nodes || []) put(x, 'pv')

  // 묶기 — union-find. 설정 · 저장소 선은 묶는 데 쓰지 않는다
  const parent = new Map()
  const find = (a) => { while (parent.get(a) !== a) { parent.set(a, parent.get(parent.get(a))); a = parent.get(a) } return a }
  const union = (a, b) => { const ra = find(a), rb = find(b); if (ra !== rb) parent.set(rb, ra) }
  for (const [id, n] of byId) if (['ingress', 'service', 'workload', 'cronjob'].includes(n.role)) parent.set(id, id)
  const uses = new Map()       // 워크로드 id → [설정 id]
  const pvOf = new Map()       // pvc id → pv id
  for (const e of d.edges || []) {
    const a = byId.get(e.from), b = byId.get(e.to)
    if (!a || !b) continue
    if (parent.has(e.from) && parent.has(e.to)) union(e.from, e.to)
    else if (a.role === 'workload' && b.role === 'use') { if (!uses.has(a.id)) uses.set(a.id, []); uses.get(a.id).push(b.id) }
    else if (a.role === 'use' && b.role === 'pv') pvOf.set(a.id, b.id)
  }

  const groups = new Map()
  for (const id of parent.keys()) {
    const r = find(id)
    if (!groups.has(r)) groups.set(r, [])
    groups.get(r).push(byId.get(id))
  }

  const useApps = new Map()    // 설정 id → Set(앱 id)
  const apps = []
  for (const [root, members] of groups) {
    const pick = (role) => members.filter(m => m.role === role).sort((a, b) => a.name.localeCompare(b.name))
    const workloads = pick('workload')
    const app = {
      id: root, ns: members[0].ns || '',
      ingresses: pick('ingress'), services: pick('service'), cronjobs: pick('cronjob'),
      // CronJob 이 만든 Job 은 최근 것부터 몇 개만 — 수십 개가 쌓여 카드가 길어진다
      workloads: workloads.filter(w => w.kind !== 'Job' || !members.some(m => m.role === 'cronjob')),
      jobs: workloads.filter(w => w.kind === 'Job' && members.some(m => m.role === 'cronjob'))
        .sort((a, b) => b.name.localeCompare(a.name)),
      uses: [],
    }
    const useIds = new Set()
    for (const w of workloads) for (const u of uses.get(w.id) || []) useIds.add(u)
    app.uses = [...useIds].map(id => ({ ...byId.get(id), pv: pvOf.has(id) ? byId.get(pvOf.get(id)) : null }))
      .sort((a, b) => (a.type + a.name).localeCompare(b.type + b.name))
    for (const id of useIds) { if (!useApps.has(id)) useApps.set(id, new Set()); useApps.get(id).add(root) }
    // 이름 — 밖에서 부르는 이름(Ingress) 보다 실제로 도는 것(워크로드)이 알아보기 쉽다
    const head = app.workloads[0] || app.cronjobs[0] || app.services[0] || app.ingresses[0]
    app.name = head?.name || root
    app.kind = app.cronjobs.length ? 'batch' : app.ingresses.length ? 'exposed' : app.services.length ? 'internal' : 'background'
    app.health = appHealth({ ...app, workloads: [...app.workloads, ...app.jobs.slice(0, 1)] })
    app.hosts = [...new Set(app.ingresses.flatMap(i => (i.rules || []).map(r => r.host).filter(Boolean)))]
    apps.push(app)
  }
  for (const app of apps) {
    for (const u of app.uses) u.sharedBy = useApps.get(u.id)?.size || 1
  }
  apps.sort((a, b) => RANK[a.health.level] - RANK[b.health.level] || a.ns.localeCompare(b.ns) || a.name.localeCompare(b.name))
  const counts = { all: apps.length, problem: 0, exposed: 0, batch: 0 }
  for (const a of apps) {
    if (a.health.level === 'bad' || a.health.level === 'warn') counts.problem++
    if (a.kind === 'exposed') counts.exposed++
    if (a.kind === 'batch') counts.batch++
  }
  return { apps, counts }
}

export const FILTERS = [
  { id: 'all', label: '전체' }, { id: 'problem', label: '문제 있는 것' },
  { id: 'exposed', label: '외부 노출(Ingress)' }, { id: 'batch', label: '배치 작업(CronJob)' },
]

/** 거르기 + 찾기 — 이름 · 호스트 · 리소스 이름 어디든 */
export function filterApps(apps, filter = 'all', q = '') {
  const s = String(q || '').trim().toLowerCase()
  return apps.filter(a => {
    if (filter === 'problem' && !['bad', 'warn'].includes(a.health.level)) return false
    if (filter === 'exposed' && a.kind !== 'exposed') return false
    if (filter === 'batch' && a.kind !== 'batch') return false
    if (!s) return true
    const names = [a.name, a.ns, ...a.hosts, ...a.ingresses.map(x => x.name), ...a.services.map(x => x.name),
                   ...a.workloads.map(x => x.name), ...a.cronjobs.map(x => x.name), ...a.uses.map(x => x.name)]
    return names.some(n => String(n || '').toLowerCase().includes(s))
  })
}

export function kindLabel(w) { return KIND_LABEL[w.kind] || w.kind || '' }
