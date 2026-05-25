export function buildPodLogTarget({ namespace, name, container = '', tail = 200 }) {
  return {
    namespace: namespace || '',
    pod: name || '',
    container: container || '',
    tail: Number(tail) || 200,
    autoStart: true,
  }
}

export function buildPodExecCommand({ namespace, name, container = '' }) {
  const base = ['exec', '-it', '-n', namespace || '', name || '']
  if (container) base.push('-c', container)
  base.push('--', 'sh')
  return base.join(' ').trim()
}
