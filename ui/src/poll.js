/**
 * 겹치지 않는 폴링 (v1.3.41, 성능 P8).
 *
 * 예전 폴러들은 `setInterval(async () => { await api.x() }, ms)` 모양이었다. 응답이
 * ms 보다 늦으면 **다음 호출이 앞 호출을 기다리지 않고** 떴다. pywebview 는 호출마다
 * 스레드를 새로 띄워 동시에 돌리므로, 「읽으면 비워지는」(drain) 엔드포인트에서는
 * 늦게 도착한 앞 응답이 뒤 응답 뒤에 붙어 **로그 순서가 뒤집히거나** 빠졌다.
 *
 * startPoll 은 앞 호출이 끝난 뒤에야 다음을 예약한다(setTimeout 사슬). 그리고 창이
 * 트레이로 숨겨진 동안은 부르지 않는다 — 백엔드 작업은 그대로 돌고, 다시 보이면
 * 쌓인 것을 받아 간다.
 */

let _polarisVisible = true
if (typeof window !== 'undefined' && window.addEventListener) {
  // 백엔드(_notify_visibility)가 트레이 숨김/복원 때 쏘는 신호 — store 와 같은 것
  window.addEventListener('polaris:visibility', e => { _polarisVisible = e?.detail !== 'hidden' })
}

/** 지금 창이 보이는가 (훅 밖에서도 쓸 수 있게 모듈에 둔다). */
export function windowVisibleNow() {
  const docHidden = typeof document !== 'undefined' && document.visibilityState === 'hidden'
  return _polarisVisible && !docHidden
}

/**
 * `fn` 을 `ms` 간격으로 부른다. 앞 호출이 끝나야 다음을 예약한다.
 *  - fn 이 `false` 를 돌려주면 멈춘다(작업 끝).
 *  - fn 이 던지면 무시하고 다음 차례에 다시 부른다(일시 오류).
 *  - pauseHidden(기본 true): 창이 숨겨진 동안 fn 을 부르지 않는다.
 *  - immediate: 첫 호출을 기다리지 않고 바로.
 * 반환: stop() — 여러 번 불러도 된다. useEffect 의 정리 함수로 그대로 쓸 수 있다.
 */
export function startPoll(fn, ms, { pauseHidden = true, immediate = false,
                                    isVisible = windowVisibleNow } = {}) {
  let stopped = false
  let timer = null
  const loop = async () => {
    timer = null
    if (stopped) return
    if (pauseHidden && !isVisible()) {
      timer = setTimeout(loop, Math.max(ms, 500))
      return
    }
    let more = true
    try { more = (await fn()) !== false } catch { more = true }
    if (!stopped && more) timer = setTimeout(loop, ms)
  }
  timer = setTimeout(loop, immediate ? 0 : ms)
  return () => {
    stopped = true
    if (timer) { clearTimeout(timer); timer = null }
  }
}

/** 누적 배열에 붙이고 뒤쪽 `cap` 개만 남긴다 — 끝없이 자라는 로그 버퍼 방지. */
export function appendCapped(prev, add, cap) {
  if (!add || add.length === 0) return prev
  const a = (prev || []).concat(add)
  return a.length > cap ? a.slice(a.length - cap) : a
}
