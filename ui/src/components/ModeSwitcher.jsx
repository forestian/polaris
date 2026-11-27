import React from 'react'
import { useApp } from '../store.jsx'
import { Cloud, ClipboardCheck } from 'lucide-react'

/**
 * 좌상단 탭 — K8S(클러스터 관리) · CHECK(클러스터 점검 · 보고서).
 * 탭마다 사이드바와 화면이 통째로 바뀐다.
 */
export default function ModeSwitcher() {
  const { appMode, setAppMode } = useApp()

  const baseBtn = {
    display: 'flex', alignItems: 'center', gap: 5,
    padding: '4px 10px', border: 'none', cursor: 'pointer',
    fontSize: 11, fontWeight: 600, fontFamily: 'var(--font)',
    transition: 'all 0.15s',
    WebkitAppRegion: 'no-drag',
  }
  const active = {
    background: 'var(--bg-3)', color: 'var(--text-bright)',
    // 선택된 탭을 포인트 컬러 테두리로 확실히 표시 (컨테이너 overflow:hidden 이라 inset 사용)
    boxShadow: 'inset 0 0 0 1.5px var(--nimbus)',
  }
  const inactive = {
    background: 'transparent', color: 'var(--text-dim)',
    boxShadow: 'none',
  }

  return (
    <div style={{
      display: 'flex', alignItems: 'center',
      background: 'var(--bg-1)', border: '1px solid var(--border-bright)',
      borderRadius: 6, overflow: 'hidden',
      WebkitAppRegion: 'no-drag', flexShrink: 0,
    }}>
      <button onClick={() => setAppMode('k8s')}
        title="Kubernetes 모드"
        style={{ ...baseBtn, ...(appMode === 'k8s' ? active : inactive) }}>
        <Cloud size={12} />
        <span>K8S</span>
      </button>
      <button onClick={() => setAppMode('check')}
        title="CHECK 모드 (클러스터 점검과 보고서)"
        style={{ ...baseBtn, ...(appMode === 'check' ? active : inactive) }}>
        <ClipboardCheck size={12} />
        <span>CHECK</span>
      </button>
    </div>
  )
}
