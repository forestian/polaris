export const TOPOLOGY_COLUMNS = [
  { id: 'ingress', label: 'Ingress', x: 32 },
  { id: 'service', label: 'Service', x: 300 },
  { id: 'schedule', label: 'Schedule', x: 568 },
  { id: 'workload', label: 'Workload', x: 836 },
  { id: 'config', label: 'Config / Storage', x: 1104 },
  { id: 'pv', label: 'PV', x: 1372 },
]

export const TOPOLOGY_LAYOUT = {
  nodeWidth: 190,
  nodeHeight: 50,
  gapY: 20,
  startY: 50,
  minColumnGap: 72,
  svgWidth: TOPOLOGY_COLUMNS[TOPOLOGY_COLUMNS.length - 1].x + 190 + 32,
}

export const TYPE_STYLE = {
  ingress:     { color: '#60a5fa', bg: '#1e3a5f', badge: 'ING'  },
  service:     { color: '#34d399', bg: '#064e3b', badge: 'SVC'  },
  cronjob:     { color: '#facc15', bg: '#422006', badge: 'CJ'   },
  job:         { color: '#fbbf24', bg: '#451a03', badge: 'JOB'  },
  deployment:  { color: '#a78bfa', bg: '#2e1065', badge: 'D'    },
  statefulset: { color: '#c084fc', bg: '#3b0764', badge: 'SS'   },
  daemonset:   { color: '#e879f9', bg: '#4a044e', badge: 'DS'   },
  configmap:   { color: '#94a3b8', bg: '#1e293b', badge: 'CM'   },
  secret:      { color: '#fb923c', bg: '#431407', badge: 'SEC'  },
  pvc:         { color: '#2dd4bf', bg: '#134e4a', badge: 'PVC'  },
  pv:          { color: '#22d3ee', bg: '#083344', badge: 'PV'   },
}

const COLUMN_INDEX = Object.fromEntries(TOPOLOGY_COLUMNS.map((col, index) => [col.id, index]))

export function typeKey(node) {
  return (node.kind?.toLowerCase() ?? node.type ?? 'unknown')
}

export function styleOf(node) {
  return TYPE_STYLE[typeKey(node)] ?? { color: '#64748b', bg: '#1e293b', badge: '?' }
}

function columnForNode(node, fallback) {
  const tk = typeKey(node)
  if (tk === 'cronjob') return COLUMN_INDEX.schedule
  if (tk === 'pv') return COLUMN_INDEX.pv
  if (tk === 'configmap' || tk === 'secret' || tk === 'pvc') return COLUMN_INDEX.config
  if (tk === 'ingress') return COLUMN_INDEX.ingress
  if (tk === 'service') return COLUMN_INDEX.service
  return fallback ?? COLUMN_INDEX.workload
}

export function buildTopologyGraph(data) {
  const nodes = []
  const nodeMap = new Map()

  function addNode(raw, fallbackCol) {
    if (!nodeMap.has(raw.id)) {
      const col = columnForNode(raw, fallbackCol)
      const n = { ...raw, col }
      nodes.push(n)
      nodeMap.set(raw.id, n)
    }
    return nodeMap.get(raw.id)
  }

  for (const ing of data.ingresses ?? []) addNode(ing, COLUMN_INDEX.ingress)
  for (const svc of data.services ?? []) addNode(svc, COLUMN_INDEX.service)
  for (const cj of data.cronjobs ?? []) addNode(cj, COLUMN_INDEX.schedule)
  for (const wl of data.workloads ?? []) addNode(wl, COLUMN_INDEX.workload)
  for (const cfg of data.config_nodes ?? []) addNode(cfg, COLUMN_INDEX.config)
  for (const pv of data.pv_nodes ?? []) addNode(pv, COLUMN_INDEX.pv)

  const colCnt = Array(TOPOLOGY_COLUMNS.length).fill(0)
  for (const n of nodes) {
    const col = n.col ?? 0
    n.x = TOPOLOGY_COLUMNS[col]?.x ?? 0
    n.y = TOPOLOGY_LAYOUT.startY + colCnt[col] * (TOPOLOGY_LAYOUT.nodeHeight + TOPOLOGY_LAYOUT.gapY)
    n.rx = n.x + TOPOLOGY_LAYOUT.nodeWidth
    n.cy = n.y + TOPOLOGY_LAYOUT.nodeHeight / 2
    colCnt[col]++
  }

  const edges = []
  for (const e of data.edges ?? []) {
    const src = nodeMap.get(e.from)
    const tgt = nodeMap.get(e.to)
    if (!src || !tgt) continue
    const sx = src.rx
    const sy = src.cy
    const tx = tgt.x
    const ty = tgt.cy
    const dx = Math.max((tx - sx) * 0.5, 32)
    edges.push({
      id: `${e.from}→${e.to}`,
      from: e.from,
      to: e.to,
      d: `M ${sx} ${sy} C ${sx + dx} ${sy} ${tx - dx} ${ty} ${tx} ${ty}`,
      srcColor: styleOf(src).color,
    })
  }

  const maxRows = Math.max(...colCnt, 1)
  const svgH = TOPOLOGY_LAYOUT.startY + maxRows * (TOPOLOGY_LAYOUT.nodeHeight + TOPOLOGY_LAYOUT.gapY) + 34

  return { nodes, edges, svgH, nodeMap }
}
