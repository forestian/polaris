import React, { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import {
  Activity, Cable, ExternalLink, Play, RefreshCw, Server, Square, X,
} from 'lucide-react'
import {
  buildPortForwardStartArgs,
  canStartPortForward,
  normalizePort,
} from '../portForwardTargets.js'

function StatusPill({ status }) {
  const palette = {
    running: ['var(--nimbus)', 'rgba(52,211,153,0.12)'],
    starting: ['var(--yellow)', 'rgba(251,191,36,0.12)'],
    error: ['var(--red)', 'var(--red-bg)'],
    stopped: ['var(--text-dim)', 'var(--bg-3)'],
  }
  const [color, background] = palette[status] || ['var(--text-mid)', 'var(--bg-3)']
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', gap: 5,
      color, background, border: `1px solid ${color}55`,
      borderRadius: 4, padding: '2px 7px', fontSize: 10.5,
      fontFamily: 'var(--font-mono)', textTransform: 'uppercase',
    }}>
      <span style={{ width: 5, height: 5, borderRadius: '50%', background: color }} />
      {status || 'unknown'}
    </span>
  )
}

function Select({ value, onChange, children, style, disabled = false }) {
  return (
    <select
      className="select"
      value={value}
      onChange={e => onChange(e.target.value)}
      disabled={disabled}
      style={{ minWidth: 0, ...style }}
    >
      {children}
    </select>
  )
}

function TargetKindButton({ active, icon: Icon, children, onClick }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="btn btn-sm"
      style={{
        background: active ? 'var(--nimbus)' : 'transparent',
        color: active ? '#051a0e' : 'var(--text-mid)',
        border: `1px solid ${active ? 'var(--nimbus)' : 'var(--border-bright)'}`,
        borderRadius: 5,
      }}
    >
      <Icon size={12} />
      {children}
    </button>
  )
}

export default function PortForwardPage() {
  const { connected, namespaces, namespace: globalNs, windowVisible } = useApp()
  const namespaceOptions = useMemo(
    () => namespaces.filter(n => n && n !== 'All Namespaces'),
    [namespaces],
  )

  const [ns, setNs] = useState(() => globalNs && globalNs !== 'All Namespaces' ? globalNs : '')
  const [kind, setKind] = useState('service')
  const [targets, setTargets] = useState({ services: [], pods: [] })
  const [targetName, setTargetName] = useState('')
  const [remotePort, setRemotePort] = useState('')
  const [localPort, setLocalPort] = useState('')
  const [sessions, setSessions] = useState([])
  const [loadingTargets, setLoadingTargets] = useState(false)
  const [starting, setStarting] = useState(false)
  const [message, setMessage] = useState('')

  useEffect(() => {
    if (!connected) return
    setNs(prev => {
      if (prev && namespaceOptions.includes(prev)) return prev
      if (globalNs && globalNs !== 'All Namespaces' && namespaceOptions.includes(globalNs)) return globalNs
      return namespaceOptions[0] || ''
    })
  }, [connected, globalNs, namespaceOptions])

  const refreshSessions = useCallback(async () => {
    const res = await api.getPortForwards()
    if (res?.ok) setSessions(res.sessions || [])
  }, [])

  const refreshTargets = useCallback(async () => {
    if (!connected || !ns) {
      setTargets({ services: [], pods: [] })
      setTargetName('')
      return
    }
    setLoadingTargets(true)
    const res = await api.getPortForwardTargets(ns)
    setLoadingTargets(false)
    if (!res?.ok) {
      setTargets({ services: [], pods: [] })
      setTargetName('')
      setMessage(res?.error || '대상 조회 실패')
      return
    }
    setMessage('')
    setTargets({ services: res.services || [], pods: res.pods || [] })
  }, [connected, ns])

  useEffect(() => { refreshTargets() }, [refreshTargets])
  useEffect(() => { refreshSessions() }, [refreshSessions])
  useEffect(() => {
    if (!windowVisible) return
    const id = setInterval(refreshSessions, 2000)
    return () => clearInterval(id)
  }, [refreshSessions, windowVisible])

  const targetList = kind === 'service' ? targets.services : targets.pods
  const selectedTarget = targetList.find(t => t.name === targetName) || null
  const portOptions = selectedTarget?.ports || []

  useEffect(() => {
    setTargetName(prev => {
      if (prev && targetList.some(t => t.name === prev)) return prev
      return targetList[0]?.name || ''
    })
  }, [targetList])

  useEffect(() => {
    if (!portOptions.length) return
    const current = normalizePort(remotePort)
    if (portOptions.some(p => Number(p.port) === current)) return
    setRemotePort(String(portOptions[0].port))
  }, [portOptions, remotePort])

  async function startForward() {
    const target = {
      kind,
      namespace: ns,
      name: targetName,
      localPort,
      remotePort,
    }
    if (!canStartPortForward({ connected, namespace: ns, name: targetName, localPort: localPort || remotePort, remotePort })) return
    setStarting(true)
    setMessage('')
    const res = await api.startPortForward(...buildPortForwardStartArgs(target))
    setStarting(false)
    if (!res?.ok) {
      setMessage(res?.error || '포트포워딩 시작 실패')
      return
    }
    setLocalPort('')
    await refreshSessions()
  }

  async function stopForward(id) {
    await api.stopPortForward(id)
    await refreshSessions()
  }

  if (!connected) {
    return (
      <div className="empty-state" style={{ height: '100%' }}>
        <Cable size={40} opacity={0.3} />
        <p>클러스터에 연결되어 있지 않습니다</p>
      </div>
    )
  }

  const canStart = canStartPortForward({
    connected,
    namespace: ns,
    name: targetName,
    localPort: localPort || remotePort,
    remotePort,
  })

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', background: 'var(--bg-0)' }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '8px 14px', borderBottom: '1px solid var(--border)',
        background: 'var(--bg-1)', flexShrink: 0,
      }}>
        <Cable size={14} color="var(--nimbus)" />
        <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)' }}>포트포워딩</span>
        <span style={{ flex: 1 }} />
        <button className="btn btn-ghost btn-sm" onClick={() => { refreshTargets(); refreshSessions() }} title="새로고침">
          <RefreshCw size={12} />
        </button>
      </div>

      <div style={{
        display: 'grid',
        gridTemplateColumns: 'minmax(130px, 0.8fr) auto minmax(180px, 1.3fr) minmax(110px, 0.7fr) minmax(110px, 0.7fr) auto',
        gap: 8, alignItems: 'center',
        padding: '10px 14px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-2)',
        flexShrink: 0,
      }}>
        <Select value={ns} onChange={setNs} disabled={!namespaceOptions.length}>
          {namespaceOptions.map(n => <option key={n} value={n}>{n}</option>)}
        </Select>

        <div style={{ display: 'flex', gap: 4 }}>
          <TargetKindButton active={kind === 'service'} icon={Server} onClick={() => setKind('service')}>Service</TargetKindButton>
          <TargetKindButton active={kind === 'pod'} icon={Activity} onClick={() => setKind('pod')}>Pod</TargetKindButton>
        </div>

        <Select value={targetName} onChange={setTargetName} disabled={loadingTargets || targetList.length === 0}>
          {targetList.length === 0 ? (
            <option value="">{loadingTargets ? '조회 중...' : '대상 없음'}</option>
          ) : targetList.map(t => (
            <option key={t.name} value={t.name}>{t.name}</option>
          ))}
        </Select>

        {portOptions.length > 0 ? (
          <Select value={remotePort} onChange={setRemotePort}>
            {portOptions.map(p => <option key={`${p.name}-${p.port}`} value={p.port}>{p.label || p.port}</option>)}
          </Select>
        ) : (
          <input
            className="input"
            value={remotePort}
            onChange={e => setRemotePort(e.target.value)}
            placeholder="remote"
            inputMode="numeric"
          />
        )}

        <input
          className="input"
          value={localPort}
          onChange={e => setLocalPort(e.target.value)}
          placeholder={remotePort ? `local ${remotePort}` : 'local'}
          inputMode="numeric"
        />

        <button className="btn btn-primary btn-sm" onClick={startForward} disabled={!canStart || starting}>
          <Play size={12} />
          시작
        </button>
      </div>

      {message && (
        <div style={{
          padding: '7px 14px', color: 'var(--red)', background: 'var(--red-bg)',
          borderBottom: '1px solid var(--border)', fontSize: 12, flexShrink: 0,
        }}>
          {message}
        </div>
      )}

      <div style={{ flex: 1, overflow: 'auto', padding: 14 }}>
        {sessions.length === 0 ? (
          <div className="empty-state" style={{ height: '100%' }}>
            <Cable size={36} opacity={0.25} />
            <p>실행 중인 포트포워딩이 없습니다</p>
          </div>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {sessions.map(session => (
              <div
                key={session.id}
                style={{
                  display: 'grid',
                  gridTemplateColumns: '120px minmax(220px, 1fr) 120px 120px auto',
                  gap: 10,
                  alignItems: 'center',
                  background: 'var(--bg-2)',
                  border: '1px solid var(--border)',
                  borderRadius: 7,
                  padding: '10px 12px',
                }}
              >
                <StatusPill status={session.status} />
                <div style={{ minWidth: 0 }}>
                  <div style={{
                    fontFamily: 'var(--font-mono)', fontSize: 12,
                    color: 'var(--text-bright)', overflow: 'hidden',
                    textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {session.flow}
                  </div>
                  <div style={{
                    marginTop: 4, fontSize: 11, color: session.error ? 'var(--red)' : 'var(--text-dim)',
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                  }}>
                    {session.error || session.last_event || `${session.namespace}/${session.name}`}
                  </div>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                  <div>{session.namespace}</div>
                  <div style={{ fontFamily: 'var(--font-mono)' }}>pid {session.pid || '-'}</div>
                </div>
                <div style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                  <div>연결 {session.connections || 0}</div>
                  <div style={{ fontFamily: 'var(--font-mono)' }}>{session.cluster_name || '-'}</div>
                </div>
                <div style={{ display: 'flex', gap: 4, justifyContent: 'flex-end' }}>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => window.open(`http://localhost:${session.local_port}`, '_blank')}
                    title="브라우저에서 열기"
                  >
                    <ExternalLink size={12} />
                  </button>
                  <button
                    className="btn btn-ghost btn-sm"
                    onClick={() => stopForward(session.id)}
                    title="종료"
                    style={{ color: 'var(--red)' }}
                  >
                    {session.status === 'running' || session.status === 'starting' ? <Square size={12} /> : <X size={12} />}
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
