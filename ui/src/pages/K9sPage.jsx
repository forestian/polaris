import React, { useState, useEffect } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { Monitor } from 'lucide-react'

export default function K9sPage() {
  const { connected } = useApp()
  const [status, setStatus] = useState(null)   // null | {ok, msg}
  const [launched, setLaunched] = useState(false)

  // 페이지 진입 시 자동 실행
  useEffect(() => {
    if (connected && !launched) {
      launch()
    }
  }, [connected])

  async function launch() {
    setStatus(null)
    try {
      const res = await api.launchK9s()
      if (res?.ok) {
        setLaunched(true)
        const term = res.terminal || '터미널'
        setStatus({ ok: true, msg: `k9s가 ${term}에서 실행되었습니다.` })
      } else {
        setStatus({ ok: false, msg: res?.error || 'k9s 실행 실패' })
      }
    } catch (e) {
      setStatus({ ok: false, msg: String(e) })
    }
  }

  if (!connected) return (
    <div className="empty-state" style={{ height: '100%' }}>
      <Monitor size={40} opacity={0.3} />
      <p>클러스터에 연결되지 않았습니다.</p>
    </div>
  )

  return (
    <div className="empty-state" style={{ height: '100%' }}>
      <Monitor size={44} color="var(--nimbus)" opacity={0.7} />

      <p style={{ fontWeight: 700, fontSize: 15, color: 'var(--text-bright)' }}>k9s</p>

      {status ? (
        <div style={{
          background: status.ok ? 'var(--bg-3)' : 'var(--red-bg)',
          color: status.ok ? 'var(--green)' : 'var(--red)',
          border: `1px solid ${status.ok ? 'var(--border-bright)' : '#7f1d1d'}`,
          borderRadius: 6, padding: '10px 20px',
          fontSize: 12, maxWidth: 380, textAlign: 'center',
          whiteSpace: 'pre-wrap',
        }}>
          {status.msg}
        </div>
      ) : (
        <div className="spinner" />
      )}

      <button className="btn btn-default" onClick={launch} style={{ marginTop: 8 }}>
        <Monitor size={13} />
        다시 실행
      </button>

      <p style={{ fontSize: 11, color: 'var(--text-dim)', maxWidth: 320, textAlign: 'center', marginTop: 4 }}>
        k9s가 설치되어 있지 않다면 <code style={{ color: 'var(--nimbus)' }}>~/.kube/k9s.exe</code> 에 배치하거나
        PATH에 추가하세요.
      </p>
    </div>
  )
}
