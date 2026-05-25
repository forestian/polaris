import React from 'react'
import { useApp } from '../store.jsx'

export default function StatusBar() {
  const { connected, kubeVersion, appVersion, clusterName, setShowConnect } = useApp()

  return (
    <div style={{
      height: 'var(--statusbar-h)',
      background: 'var(--bg-2)',
      borderTop: '1px solid var(--border)',
      display: 'flex', alignItems: 'center',
      padding: '0 14px', flexShrink: 0,
      fontSize: 10.5,
    }}>
      {/* 연결 상태 */}
      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: connected ? 'var(--nimbus)' : 'var(--red)',
          boxShadow: connected ? '0 0 5px var(--nimbus)' : 'none',
          display: 'inline-block', flexShrink: 0,
        }} />
        <span style={{ color: connected ? 'var(--text)' : 'var(--red)', fontWeight: connected ? 400 : 600 }}>
          {connected ? `연결됨${clusterName ? ` · ${clusterName}` : ''}` : '연결 안 됨'}
        </span>
      </span>

      {connected && kubeVersion && (
        <span style={{ color: 'var(--text-dim)', marginLeft: 12 }}>k8s {kubeVersion}</span>
      )}

      <span style={{ flex: 1 }} />

      {!connected && (
        <button className="btn btn-primary btn-sm"
          style={{ marginRight: 12 }}
          onClick={() => setShowConnect(true)}>
          kubeconfig 연결
        </button>
      )}

      <span style={{ color: 'var(--text-dim)' }}>F5 새로고침 · ⌘K 검색</span>
      <span style={{ marginLeft: 14, color: 'var(--text-mid)', fontWeight: 500 }}>
        {appVersion ? `Polaris v${appVersion}` : 'Polaris'}
      </span>
    </div>
  )
}
