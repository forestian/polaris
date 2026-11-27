import React from 'react'
import { useApp } from '../store.jsx'

/**
 * 하단 상태 표시줄 — 클러스터 연결 상태와 판.
 */
export default function StatusBar() {
  const { connected, kubeVersion, appVersion, clusterName } = useApp()

  const dot = connected ? 'var(--nimbus)' : 'var(--red)'
  const text = connected ? `연결됨${clusterName ? ` · ${clusterName}` : ''}` : '연결 안 됨'
  const color = connected ? 'var(--text)' : 'var(--red)'
  const strong = !connected
  const extra = connected && kubeVersion ? `k8s ${kubeVersion}` : null

  return (
    <div style={{
      height: 'var(--statusbar-h)',
      background: 'var(--bg-2)',
      borderTop: '1px solid var(--border)',
      display: 'flex', alignItems: 'center',
      padding: '0 14px', flexShrink: 0,
      fontSize: 10.5,
    }}>
      <span style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
        <span style={{
          width: 6, height: 6, borderRadius: '50%',
          background: dot,
          boxShadow: dot === 'var(--nimbus)' ? '0 0 5px var(--nimbus)' : 'none',
          display: 'inline-block', flexShrink: 0,
        }} />
        <span style={{ color, fontWeight: strong ? 600 : 400 }}>{text}</span>
      </span>

      {extra && <span style={{ color: 'var(--text-dim)', marginLeft: 12 }}>{extra}</span>}

      <span style={{ flex: 1 }} />

      <span style={{ color: 'var(--text-dim)' }}>Ctrl+K 검색</span>
      <span style={{ marginLeft: 14, color: 'var(--text-mid)', fontWeight: 500 }}>
        {appVersion ? `Polaris Free v${appVersion}` : 'Polaris Free'}
      </span>
    </div>
  )
}
