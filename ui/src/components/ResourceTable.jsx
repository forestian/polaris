import React, { useState, useMemo } from 'react'
import { ChevronUp, ChevronDown, Search } from 'lucide-react'

const STATUS_CHIP = {
  Running: 'chip-green', Ready: 'chip-green', Active: 'chip-green',
  Synced: 'chip-green', Healthy: 'chip-green', Succeeded: 'chip-green',
  Bound: 'chip-green', Available: 'chip-green',
  Pending: 'chip-yellow', OutOfSync: 'chip-yellow', Progressing: 'chip-yellow',
  Suspended: 'chip-yellow', Unknown: 'chip-dim',
  Failed: 'chip-red', CrashLoopBackOff: 'chip-red', Error: 'chip-red',
  OOMKilled: 'chip-red', NotReady: 'chip-red', Degraded: 'chip-red',
  Lost: 'chip-red', Terminating: 'chip-yellow',
}

function StatusChip({ value }) {
  if (!value) return <span style={{ color: 'var(--text-dim)' }}>—</span>
  const chip = STATUS_CHIP[value] || 'chip-dim'
  const clean = value.replace(/^● /, '')
  return <span className={`chip ${chip}`}>{clean}</span>
}

function isStatusCol(key) {
  return ['status', 'sync', 'health', 'phase', 'state'].includes(key.toLowerCase())
}

export default function ResourceTable({
  columns,  // [{ key, label, width? }]
  rows,
  loading,
  onSelect,
  selected,
  toolbar,
  emptyMsg = '데이터가 없습니다.',
}) {
  const [search, setSearch] = useState('')
  const [sortCol, setSortCol] = useState('')
  const [sortAsc, setSortAsc] = useState(true)

  function handleSort(col) {
    if (sortCol === col) setSortAsc(a => !a)
    else { setSortCol(col); setSortAsc(true) }
  }

  const filtered = useMemo(() => {
    let data = rows || []
    if (search.trim()) {
      const q = search.toLowerCase()
      data = data.filter(r =>
        Object.values(r).some(v => String(v).toLowerCase().includes(q))
      )
    }
    if (sortCol) {
      data = [...data].sort((a, b) => {
        const av = String(a[sortCol] ?? '').toLowerCase()
        const bv = String(b[sortCol] ?? '').toLowerCase()
        return sortAsc ? av.localeCompare(bv) : bv.localeCompare(av)
      })
    }
    return data
  }, [rows, search, sortCol, sortAsc])

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* 툴바 */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '8px 12px', background: 'var(--bg-2)',
        borderBottom: '1px solid var(--border)', flexShrink: 0,
      }}>
        <div style={{ position: 'relative', flex: '0 0 220px' }}>
          <Search size={12} style={{
            position: 'absolute', left: 8, top: '50%', transform: 'translateY(-50%)',
            color: 'var(--text-dim)',
          }} />
          <input className="input" value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="검색..."
            style={{ paddingLeft: 26, fontSize: 12 }}
          />
        </div>
        {toolbar}
        <span style={{ flex: 1 }} />
        <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
          {loading ? '로딩 중...' : `${filtered.length}개`}
        </span>
      </div>

      {/* 테이블 */}
      <div style={{ flex: 1, overflow: 'auto' }}>
        {loading ? (
          <div className="empty-state">
            <div className="spinner" />
            <span>데이터를 불러오는 중...</span>
          </div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <span>{emptyMsg}</span>
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                {columns.map(col => (
                  <th key={col.key}
                    onClick={() => handleSort(col.key)}
                    style={{ width: col.width }}
                  >
                    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4 }}>
                      {col.label}
                      {sortCol === col.key
                        ? (sortAsc ? <ChevronUp size={10} /> : <ChevronDown size={10} />)
                        : null}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, i) => (
                <tr key={row._uid || i}
                  className={selected === row ? 'selected' : ''}
                  onClick={() => onSelect?.(row)}
                  style={{ cursor: onSelect ? 'pointer' : 'default' }}
                >
                  {columns.map(col => (
                    <td key={col.key} style={{ maxWidth: col.width || 300 }}>
                      {isStatusCol(col.key)
                        ? <StatusChip value={String(row[col.key] ?? '')} />
                        : <span className="truncate" style={{ display: 'block' }}>
                            {row[col.key] ?? '—'}
                          </span>
                      }
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
