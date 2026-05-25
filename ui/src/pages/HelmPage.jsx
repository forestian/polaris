import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import ResourceTable from '../components/ResourceTable.jsx'
import { RefreshCw, Package } from 'lucide-react'

const COLUMNS = [
  { key: 'name',        label: '이름',          width: 200 },
  { key: 'namespace',   label: '네임스페이스',  width: 120 },
  { key: 'chart',       label: '차트',           width: 200 },
  { key: 'app_version', label: 'App Version',    width: 110 },
  { key: 'revision',    label: 'Revision',       width: 80  },
  { key: 'status',      label: '상태',           width: 90  },
  { key: 'updated',     label: '업데이트',       width: 160 },
]

export default function HelmPage() {
  const { connected } = useApp()
  const [rows, setRows]       = useState([])
  const [loading, setLoading] = useState(false)

  async function load() {
    if (!connected) return
    setLoading(true)
    try {
      const data = await api.getHelmReleases()
      setRows(Array.isArray(data) ? data : [])
    } catch {
      setRows([])
    }
    setLoading(false)
  }

  useEffect(() => { load() }, [connected])

  if (!connected) return (
    <div className="empty-state" style={{ height: '100%' }}>
      <Package size={40} opacity={0.3} />
      <p>클러스터에 연결되지 않았습니다.</p>
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 헤더 */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        padding: '10px 16px',
        borderBottom: '1px solid var(--border)',
        background: 'var(--bg-1)', flexShrink: 0,
      }}>
        <Package size={15} color="var(--nimbus)" />
        <h1 style={{ fontSize: 14, fontWeight: 700, color: 'var(--text-bright)', margin: 0 }}>
          Helm 릴리스
        </h1>
        <span style={{ flex: 1 }} />
        <button className="btn btn-default btn-sm" onClick={load} disabled={loading}>
          <RefreshCw size={12} className={loading ? 'spinner' : ''} />
          새로고침
        </button>
      </div>

      {/* 테이블 */}
      <div style={{ flex: 1, overflow: 'hidden' }}>
        <ResourceTable
          columns={COLUMNS}
          rows={rows}
          loading={loading}
          emptyMsg="Helm 릴리스가 없습니다."
        />
      </div>
    </div>
  )
}
