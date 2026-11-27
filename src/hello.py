"""Windows Hello 사용자 확인 (v1.2.167).

DPAPI 자동 잠금 해제는 **사용자 확인 없이** 보관함을 연다 — 잠기지 않은 Windows 세션에
접근할 수 있는 사람은 누구나 Polaris 를 열어 접속정보를 볼 수 있다. 그 앞에 Windows Hello
(얼굴·지문·PIN) 확인을 세워 "이 사람이 지금 여기 있는지" 를 묻는다.

구현 판단
─────────────────────────────────────────────────────────────────────────
· **WinRT 파이썬 바인딩(winsdk/winrt)을 새로 넣지 않는다.** frozen 빌드에서 네이티브
  모듈이 빠지면 조용히 죽는다(v1.2.114 에서 plugin 누락으로 겪었다). 대신 Windows 에
  항상 있는 PowerShell 로 `UserConsentVerifier` 를 호출한다 — 새 의존성이 0 이고
  PyInstaller 가 번들할 것도 없다.
· Hello 는 **키를 주지 않는다.** 확인(Verified)만 돌려주므로 복호화는 종전대로 DPAPI 가
  한다. 즉 이 기능은 "DPAPI 를 쓰기 전에 사람 확인" 이지, 새 암호 계층이 아니다.
  그렇게만 설명해야 사용자가 보호 수준을 오해하지 않는다.
· 실패는 전부 '잠긴 상태 유지' 로 수렴한다. 확인이 안 되면 아무것도 열지 않는다.
"""
import subprocess

from .tools import _NO_WINDOW

# UserConsentVerifierAvailability / UserConsentVerificationResult 값
AVAIL_OK = 'Available'
VERIFIED = 'Verified'

# PowerShell 은 IAsyncOperation 을 직접 await 하지 못해 AsTask 확장 메서드를 찾아 쓴다.
# 콘솔 창이 뜨지 않게 _NO_WINDOW 로 띄운다(앱 안에서 부르므로).
_PS_PREAMBLE = r'''
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
$asTask = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
  $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
  $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1' })
function Await($op, $type) {
  $t = $asTask.MakeGenericMethod($type).Invoke($null, @($op))
  if (-not $t.Wait(%TIMEOUT_MS%)) { return 'Timeout' }
  return [string]$t.Result
}
'''

_PS_AVAIL = _PS_PREAMBLE + r'''
$v = [Windows.Security.Credentials.UI.UserConsentVerifier,Windows.Security.Credentials.UI,ContentType=WindowsRuntime]
$type = [Windows.Security.Credentials.UI.UserConsentVerifierAvailability,Windows.Security.Credentials.UI,ContentType=WindowsRuntime]
Write-Output (Await $v::CheckAvailabilityAsync() $type)
'''

_PS_VERIFY = _PS_PREAMBLE + r'''
$v = [Windows.Security.Credentials.UI.UserConsentVerifier,Windows.Security.Credentials.UI,ContentType=WindowsRuntime]
$type = [Windows.Security.Credentials.UI.UserConsentVerificationResult,Windows.Security.Credentials.UI,ContentType=WindowsRuntime]
Write-Output (Await ($v::RequestVerificationAsync(%MESSAGE%)) $type)
'''


def _run_ps(script: str, timeout: float) -> tuple[str, str | None]:
    """PowerShell 한 줄 결과를 돌려준다. (값, 오류)"""
    try:
        p = subprocess.run(
            ['powershell', '-NoProfile', '-NonInteractive', '-Command', script],
            capture_output=True, text=True, timeout=timeout,
            creationflags=_NO_WINDOW, encoding='utf-8', errors='replace')
    except FileNotFoundError:
        return '', 'PowerShell 을 찾을 수 없습니다.'
    except subprocess.TimeoutExpired:
        return '', 'Timeout'
    except Exception as e:
        return '', f'{type(e).__name__}: {e}'
    out = (p.stdout or '').strip().splitlines()
    val = out[-1].strip() if out else ''
    if not val:
        return '', (p.stderr or '').strip()[:300] or '결과가 비어 있습니다.'
    return val, None


def availability(timeout: float = 15.0) -> dict:
    """Hello 를 쓸 수 있는 상태인지. {available, state, error}

    state 예: Available · DeviceNotPresent · NotConfiguredForUser · DisabledByPolicy
    """
    script = _PS_AVAIL.replace('%TIMEOUT_MS%', str(int(timeout * 1000)))
    val, err = _run_ps(script, timeout + 5)
    if err and not val:
        return {'available': False, 'state': 'error', 'error': err}
    return {'available': val == AVAIL_OK, 'state': val, 'error': None}


def verify(message: str = 'Polaris 보안 보관함 잠금 해제',
           timeout: float = 90.0) -> dict:
    """Hello 확인창을 띄운다. {verified, state, error}

    사용자가 얼굴/지문/PIN 을 입력할 시간이 필요해 기본 90초를 준다. 취소·시간초과는
    모두 verified=False — 실패는 '잠긴 상태 유지' 하나로 수렴한다.
    """
    # 메시지는 PowerShell 작은따옴표 문자열로 넣는다 — 그 안에서는 변수 · 식이 펼쳐지지 않고, ' 는 '' 로 겹쳐 쓴다.
    # 예전엔 json.dumps(ASCII 만)라 한글이 \uXXXX 그대로 확인 창에 보였다(PowerShell 은 \u 를 풀지 않는다, v1.4.24)
    msg = str(message or '')[:120].replace('\r', ' ').replace('\n', ' ')
    safe = "'" + msg.replace("'", "''") + "'"
    script = (_PS_VERIFY
              .replace('%TIMEOUT_MS%', str(int(timeout * 1000)))
              .replace('%MESSAGE%', safe))
    val, err = _run_ps(script, timeout + 10)
    if err and not val:
        return {'verified': False, 'state': 'error', 'error': err}
    return {'verified': val == VERIFIED, 'state': val, 'error': None}
