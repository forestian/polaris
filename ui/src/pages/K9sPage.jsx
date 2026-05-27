import React, { useState, useEffect } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { Monitor, Download } from 'lucide-react'

export default function K9sPage() {
  const { connected } = useApp()
  const [status, setStatus]       = useState(null)   // null | {ok, msg, notFound}
  const [launched, setLaunched]   = useState(false)
  const [installing, setInstalling] = useState(false)

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
        setStatus({ ok: false, notFound: !!res?.not_found, msg: res?.error || 'k9s 실행 실패' })
      }
    } catch (e) {
      setStatus({ ok: false, msg: String(e) })
    }
  }

  async function installK9s() {
    setInstalling(true)
    setStatus({ ok: null, msg: 'GitHub에서 k9s 최신 버전을 다운로드 중...' })
    try {
      const res = await api.installK9s()
      if (res?.ok) {
        setStatus({ ok: true, msg: `k9s ${res.version} 설치 완료. 실행 중...` })
        setInstalling(false)
        setTimeout(launch, 800)
      } else {
        setStatus({ ok: false, notFound: true, msg: `설치 실패: ${res?.error || '알 수 없는 오류'}` })
        setInstalling(false)
      }
    } catch (e) {
      setStatus({ ok: false, notFound: true, msg: `설치 실패: ${String(e)}` })
      setInstalling(false)
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
          background: status.ok === true  ? 'var(--bg-3)'
                    : status.ok === false ? 'var(--red-bg)'
                    : 'var(--bg-2)',
          color:      status.ok === true  ? 'var(--green)'
                    : status.ok === false ? 'var(--red)'
                    : 'var(--text-dim)',
          border: `1px solid ${status.ok === true ? 'var(--border-bright)' : status.ok === false ? '#7f1d1d' : 'var(--border)'}`,
          borderRadius: 6, padding: '10px 20px',
          fontSize: 12, maxWidth: 380, textAlign: 'center',
          whiteSpace: 'pre-wrap',
        }}>
          {status.msg}
        </div>
      ) : (
        <div className="spinner" />
      )}

      <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
        <button className="btn btn-default" onClick={launch} disabled={installing}>
          <Monitor size={13} />
          {launched ? '다시 실행' : '실행'}
        </button>

        {status?.notFound && !installing && (
          <button className="btn btn-primary" onClick={installK9s}>
            <Download size={13} />
            k9s 설치
          </button>
        )}

        {installing && (
          <div className="spinner" style={{ width: 16, height: 16, alignSelf: 'center' }} />
        )}
      </div>

      <p style={{ fontSize: 11, color: 'var(--text-dim)', maxWidth: 320, textAlign: 'center', marginTop: 4 }}>
        설치 버튼은 GitHub에서 최신 버전을 받아 <code style={{ color: 'var(--nimbus)' }}>~/.kube/k9s.exe</code> 에 저장합니다.
      </p>
    </div>
  )
}
