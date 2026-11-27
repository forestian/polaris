import React, { useState, useMemo, useRef, useEffect, useDeferredValue, useCallback, memo } from 'react'
import { ChevronUp, ChevronDown, Search } from 'lucide-react'
import { visibleWindow, rowKeys } from '../tableWindow.js'

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

// 행 하나 — 같은 행·같은 선택 상태면 다시 그리지 않는다 (v1.3.42, 성능 P9)
// v1.3.75(성능 13): 그런데 memo 가 거의 안 먹었다 — 실시간 보기(1초)가 **모든 행을 새 객체로**
// 주고, 부르는 쪽이 columns·onSelect 를 렌더마다 새로 만들어서다. 이제 「보이는 칸의 값」 과
// 칸 구성(colsKey)을 비교하고, 누르면 그때의 최신 행을 키로 찾아 넘긴다(옛 객체를 넘기지 않게).
function sameCells(a, b, columns) {
  if (a === b) return true
  if (!a || !b) return false
  for (const c of columns) if (a[c.key] !== b[c.key]) return false
  return true
}

const Row = memo(function Row({ row, rowKey, columns, isSelected, onPick, clickable }) {
  return (
    <tr data-row="1"
      className={isSelected ? 'selected' : ''}
      onClick={() => onPick(rowKey)}
      style={{ cursor: clickable ? 'pointer' : 'default' }}
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
  )
}, (p, n) => p.rowKey === n.rowKey && p.isSelected === n.isSelected && p.colsKey === n.colsKey
  && p.clickable === n.clickable && p.onPick === n.onPick && sameCells(p.row, n.row, n.columns))

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
  // 입력은 바로 보이고, 걸러 내기는 한 박자 뒤에 — 파드 수천 개에서 타이핑이 밀리지 않게
  const deferredSearch = useDeferredValue(search)

  // ── 보이는 행만 그리기 (v1.3.42, 성능 P9) ─────────────────────────────────
  // 파드 5000개면 칸이 4만 개였고, 실시간 보기(1초)·행 클릭마다 전부 다시 그렸다.
  // 행은 한 줄 고정 높이(nowrap)라 스크롤 위치로 보이는 구간을 계산할 수 있다.
  const scrollRef = useRef(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [viewH, setViewH] = useState(600)
  const [rowH, setRowH] = useState(31)
  useEffect(() => {
    const el = scrollRef.current
    if (!el) return
    const ro = new ResizeObserver(() => setViewH(el.clientHeight || 600))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  // 스크롤 이벤트는 Chromium 이 이미 프레임당 한 번만 보낸다 — rAF 로 한 번 더 미루면
  // 창이 가려진 동안 rAF 가 멈춰 빈 표가 보일 수 있다(미리보기에서 실측)
  function onScroll(e) {
    const top = e.currentTarget.scrollTop
    // 창 안에서 행 몇 개만큼 움직였을 때만 다시 그린다
    setScrollTop(prev => (Math.abs(prev - top) < rowH ? prev : top))
  }

  function handleSort(col) {
    if (sortCol === col) setSortAsc(a => !a)
    else { setSortCol(col); setSortAsc(true) }
  }

  const filtered = useMemo(() => {
    let data = rows || []
    if (deferredSearch.trim()) {
      const q = deferredSearch.toLowerCase()
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
  }, [rows, deferredSearch, sortCol, sortAsc])

  const keys = useMemo(() => rowKeys(filtered), [filtered])
  // 칸 구성이 같으면 같은 문자열 — 부르는 쪽이 columns 배열을 렌더마다 새로 만들어도 줄은 그대로
  const colsKey = columns.map(c => `${c.key}\u0001${c.label}\u0001${c.width || ''}`).join('\u0002')
  const byKeyRef = useRef(new Map())
  byKeyRef.current = new Map(keys.map((k, i) => [k, filtered[i]]))
  const onSelectRef = useRef(onSelect)
  onSelectRef.current = onSelect
  const pick = useCallback((k) => {
    const row = byKeyRef.current.get(k)
    if (row !== undefined) onSelectRef.current?.(row)
  }, [])
  // 목록 길이가 바뀌면(필터·실시간 갱신) 브라우저가 스크롤 위치를 당겨 놓을 수 있다 —
  // 그 값으로 맞춘다. 안 그러면 옛 위치 기준 구간을 그려 빈 표가 잠깐 보인다.
  useEffect(() => {
    const el = scrollRef.current
    if (el && Math.abs(el.scrollTop - scrollTop) >= rowH) setScrollTop(el.scrollTop)
  }, [filtered.length])  // eslint-disable-line react-hooks/exhaustive-deps
  const win = visibleWindow(filtered.length, scrollTop, viewH, rowH)
  // 실제 행 높이를 한 번 재서 맞춘다(글꼴·테마에 따라 1~2px 다를 수 있다)
  useEffect(() => {
    const tr = scrollRef.current?.querySelector('tr[data-row]')
    const h = tr?.getBoundingClientRect().height
    if (h && Math.abs(h - rowH) > 0.5) setRowH(h)
  })

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
      <div ref={scrollRef} onScroll={onScroll} style={{ flex: 1, overflow: 'auto' }}>
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
              {win.top > 0 && <tr aria-hidden="true" style={{ height: win.top }} />}
              {filtered.slice(win.start, win.end).map((row, i) => (
                <Row key={keys[win.start + i]} rowKey={keys[win.start + i]} row={row}
                  columns={columns} colsKey={colsKey} clickable={!!onSelect}
                  isSelected={selected === row} onPick={pick} />
              ))}
              {win.bottom > 0 && <tr aria-hidden="true" style={{ height: win.bottom }} />}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
