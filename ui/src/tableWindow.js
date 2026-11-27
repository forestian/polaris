/**
 * 긴 표에서 **보이는 행만** 그리기 위한 계산 (v1.3.42, 성능 P9).
 *
 * 행 높이가 일정한 표(한 줄 고정)에서만 쓴다. 적은 목록은 그대로 전부 그린다 —
 * 창 방식은 이득이 없고, 브라우저의 페이지 내 찾기(Ctrl+F) 같은 동작이 달라진다.
 */
export const WINDOW_MIN_ROWS = 300   // 이보다 적으면 전부 그린다
export const OVERSCAN = 20           // 화면 위아래로 더 그려 둘 행 — 빠른 스크롤에서 빈칸 방지

/** → { start, end, top, bottom } — 그릴 구간 [start, end) 과 위아래 빈 공간 높이(px). */
export function visibleWindow(total, scrollTop, viewH, rowH) {
  if (total <= WINDOW_MIN_ROWS || !(rowH > 0)) return { start: 0, end: total, top: 0, bottom: 0 }
  // 목록이 줄었는데(필터 등) 스크롤은 아래에 남아 있을 수 있다 — 끝을 넘지 않게
  const first = Math.min(total, Math.floor(Math.max(0, scrollTop) / rowH))
  const start = Math.max(0, first - OVERSCAN)
  const end = Math.min(total, first + Math.ceil(Math.max(viewH, 0) / rowH) + OVERSCAN)
  return { start, end, top: start * rowH, bottom: (total - end) * rowH }
}

/**
 * 행의 React key. 예전에는 `row._uid || i` 였는데 백엔드는 `_uid` 를 주지 않아
 * **늘 순번**이었다 — 정렬·필터·실시간 갱신 때 모든 행이 다른 행으로 다시 만들어졌다.
 */
export function rowKey(row, i) {
  if (row && row._uid) return row._uid
  if (row && row.name != null) return `${row._kind || ''}|${row.namespace ?? row._ns ?? ''}|${row.name}`
  return `i${i}`
}

/** 목록 전체의 key — 이름이 겹치면(이벤트 등) 뒤의 것에 번호를 붙여 **절대 겹치지 않게**. */
export function rowKeys(rows) {
  const seen = new Map()
  return (rows || []).map((r, i) => {
    const k = rowKey(r, i)
    const n = seen.get(k) || 0
    seen.set(k, n + 1)
    return n ? `${k}#${n}` : k
  })
}
