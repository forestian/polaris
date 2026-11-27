/**
 * 보관함 잠금 게이트 판단 (v1.2.167).
 *
 * 부팅 때 "비밀번호 없이 열어도 되는가" 와 "Hello 버튼을 띄울까" 는 한 줄짜리 boolean
 * 이지만 틀리면 기능이 조용히 무력화된다 — 화면에는 아무 표시도 나지 않는다.
 * 그래서 JSX 밖 순수 함수로 두고 테스트로 고정한다.
 */

/**
 * 사용자 확인 없이 DPAPI 로 열어도 되는가.
 *
 * 판단 근거: Hello 요구가 켜져 있으면 **장치가 지금 쓸 수 있든 없든** 조용히 열지
 * 않는다. 장치 고장 시 열어주는 쪽(fail-open)이 편해 보이지만, 그러면 사용자가 막으려던
 * 상황("이 PC 에 앉은 사람이 그냥 열어봄")이 아무 알림 없이 되돌아온다. 반대로 막아도
 * **마스터 비밀번호로 들어가는 길은 항상 열려 있으므로** 잠기는 사람은 없다.
 *
 * @param status vault_status 결과 {available, exists, has_dpapi, unlocked}
 * @param hello  hello_status 결과 {ok, required, available} · null 이면 조회 실패
 */
export function shouldSilentUnlock(status, hello) {
  const s = status || {}
  if (!(s.available && s.exists && s.has_dpapi && !s.unlocked)) return false
  // 조회 실패(null)도 막는다 — 설정이 켜져 있는지 모르는 채로 여는 것보다 안전하다.
  // (백엔드 IPC 가 죽은 상황이면 vault_status 도 못 받으므로 위에서 이미 걸린다.)
  if (!hello || hello.ok !== true) return false
  return !hello.required
}

/**
 * 잠금화면에 "Windows Hello 로 잠금 해제" 버튼을 띄울까.
 *
 * Hello 는 확인만 하고 복호화는 DPAPI 가 한다 — 둘 다 있어야 실제로 열린다.
 * 자동 해제가 설정돼 있지 않은데 버튼을 띄우면, 얼굴을 확인해 준 뒤에 "열 수 없다" 는
 * 말을 듣게 된다.
 */
export function helloButtonReady(hello) {
  return !!(hello && hello.ok !== false && hello.available && hello.has_dpapi)
}

/**
 * Hello 요구 설정을 켤 수 있는 상태인가 (설정 화면 체크박스 활성화 조건).
 * 켜는 것은 조건이 필요하지만 끄는 것은 완화이므로 언제나 가능하다.
 */
export function canRequireHello(hello) {
  return helloButtonReady(hello)
}
