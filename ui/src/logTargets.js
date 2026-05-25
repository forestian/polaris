export const LOG_SOURCE_OPTIONS = [
  { id: 'pod', label: 'Pod', resource: 'pods' },
  { id: 'deployment', label: 'Deployment', resource: 'deployments' },
  { id: 'statefulset', label: 'StatefulSet', resource: 'statefulsets' },
  { id: 'daemonset', label: 'DaemonSet', resource: 'daemonsets' },
  { id: 'replicaset', label: 'ReplicaSet', resource: 'replicasets' },
  { id: 'job', label: 'Job', resource: 'jobs' },
  { id: 'ingress', label: 'Ingress 통합', resource: null },
]

export function resourceTypeForLogSource(sourceType) {
  return LOG_SOURCE_OPTIONS.find(opt => opt.id === sourceType)?.resource ?? null
}

export function isIngressLogSource(sourceType) {
  return sourceType === 'ingress'
}

export function isPodLogSource(sourceType) {
  return sourceType === 'pod'
}

export function buildLogStreamArgs({ sourceType, namespace, target, container = '', tail = 200, follow = false }) {
  if (isIngressLogSource(sourceType)) {
    return ['', '', '', Number(tail) || 200, Boolean(follow), 'ingress']
  }
  return [
    namespace || '',
    target || '',
    isPodLogSource(sourceType) ? (container || '') : '',
    Number(tail) || 200,
    Boolean(follow),
    sourceType || 'pod',
  ]
}

export function canStartLogStream({ connected, sourceType, namespace, target }) {
  if (!connected) return false
  if (isIngressLogSource(sourceType)) return true
  return Boolean(namespace && target)
}
