const KIND_ALIASES = {
  pod: 'pod',
  pods: 'pod',
  service: 'service',
  services: 'service',
  svc: 'service',
}

export function normalizePortForwardKind(kind) {
  return KIND_ALIASES[String(kind || 'service').trim().toLowerCase()] || 'service'
}

export function normalizePort(value) {
  const port = Number.parseInt(String(value ?? '').trim(), 10)
  return Number.isFinite(port) ? port : 0
}

export function normalizePortForwardTarget({
  kind = 'service',
  namespace = '',
  name = '',
  localPort = '',
  remotePort = '',
} = {}) {
  const remote = normalizePort(remotePort)
  const local = String(localPort ?? '').trim() === '' ? remote : normalizePort(localPort)
  return {
    kind: normalizePortForwardKind(kind),
    namespace: String(namespace || '').trim(),
    name: String(name || '').trim(),
    remotePort: remote,
    localPort: local,
  }
}

export function buildPortForwardStartArgs(target) {
  const normalized = normalizePortForwardTarget(target)
  return [
    normalized.kind,
    normalized.namespace,
    normalized.name,
    normalized.localPort,
    normalized.remotePort,
  ]
}

export function isValidPort(port) {
  return Number.isInteger(port) && port >= 1 && port <= 65535
}

export function canStartPortForward({
  connected,
  namespace,
  name,
  localPort,
  remotePort,
} = {}) {
  const ns = String(namespace || '').trim()
  if (!connected) return false
  if (!ns || ns.toLowerCase() === 'all namespaces' || ns.toLowerCase() === 'all') return false
  if (!String(name || '').trim()) return false
  return isValidPort(normalizePort(localPort)) && isValidPort(normalizePort(remotePort))
}
