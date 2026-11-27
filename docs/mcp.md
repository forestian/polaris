# Polaris MCP 서버 — AI에게 크리덴셜을 주지 않고 클러스터를 보여 주는 방법

*stdio 트랜스포트 · MCP 액세스 토큰 인증 · 쿠버네티스 조회 전용*

## 이게 무엇인가

MCP(Model Context Protocol)는 AI가 외부 도구를 호출하는 표준 규약입니다. Polaris를 MCP
서버로 띄우면 **Claude 같은 AI가 Polaris를 도구처럼 불러서** 클러스터를 조회할 수 있습니다.
이 판의 MCP 는 **조회 전용**입니다 — 클러스터를 바꾸는 툴은 들어 있지 않습니다.

핵심은 **크리덴셜이 AI에게 넘어가지 않는다**는 점입니다.

```
   AI (MCP 클라이언트)                Polaris (MCP 서버)              클러스터
   ───────────────────                ──────────────────              ────────
   "default 네임스페이스        →     토큰 검증 → vault 열기 →       →   조회
    파드 목록 보여줘"                  Polaris가 직접 조회
                                ←     결과(JSON)만 반환               ←
```

AI는 "무엇을 보여 달라"는 tool call만 보냅니다. kubeconfig 본문 · 토큰은 Polaris 내부(vault)에만
있고 **응답으로도 감사 로그로도 나가지 않습니다.**

---

## 인증 — MCP 액세스 토큰

MCP 서버는 GUI 없는 헤드리스 프로세스라 마스터 비밀번호를 물어볼 창이 없습니다. 그래서
Polaris에서 **MCP 전용 액세스 토큰**을 발급해 클라이언트 설정에 붙여넣는 방식으로
인증합니다.

> Polaris 실행 → 설정(톱니바퀴) → **보안 잠금** → **「MCP 액세스 토큰」** → **발급**
>
> 이름(예: `Claude Desktop`)과 유효기간을 고르면 `plrs_mcp_…` 형태의 문자열이 **딱 한 번**
> 표시됩니다. 복사해서 클라이언트 설정에 넣으세요. 창을 닫으면 다시 볼 수 없습니다(분실 시
> 폐기하고 재발급).

토큰이 없거나 틀리면 **모든 툴이 거부**됩니다.

```
MCP 액세스 토큰이 없습니다. Polaris → 설정 → 보안 잠금 → "MCP 액세스 토큰" 에서
토큰을 발급한 뒤, MCP 클라이언트 설정의 env 에 POLARIS_MCP_TOKEN 으로 넣고
클라이언트를 재시작하세요.
```

### DPAPI 자동 잠금 해제는 MCP에 관여하지 않는다

「자동 잠금 해제 (이 PC)」는 **Polaris GUI 전용** 기능입니다. 이 설정이 켜져 있어도
MCP 연결은 토큰 없이는 열리지 않습니다. AI 클라이언트가 사용자 계정 권한만으로 vault를
여는 경로를 원천 차단하기 위한 설계입니다.

| | Polaris GUI | MCP |
|---|---|---|
| 마스터 비밀번호 | ✅ | ❌ (물어볼 창이 없음) |
| DPAPI 자동 해제 | ✅ | ❌ **의도적으로 미사용** |
| MCP 액세스 토큰 | ❌ | ✅ **유일한 경로** |

### 토큰의 성질

- **저장 형태** — 토큰 원문은 어디에도 저장되지 않습니다. vault의 데이터 키(DEK)를
  토큰에서 유도한 키(HKDF-SHA256)로 감싼 봉투만 남습니다. 서버는 제시된 토큰으로
  봉투를 풀어보고, 풀리면 인증 성공으로 봅니다.
- **권한** — 조회 전용입니다.
- **유효기간** — 발급 시 지정(기본 90일). 만료되면 자동 거부됩니다.
- **폐기** — 설정 화면의 토큰 목록에서 언제든 개별 폐기. 폐기 즉시 그 토큰으로는
  vault가 열리지 않습니다(다른 토큰·GUI는 영향 없음).
- **감사 추적** — 어느 토큰이 호출했는지가 감사 로그에 토큰 ID로 남습니다.

---

## 실행

```bash
polaris.exe --mcp
```

개발 환경에서는:

```bash
python polaris.py --mcp
```

stdout은 JSON-RPC 채널이므로 아무것도 출력하지 않습니다. 정상 동작 신호는 감사 로그에
남습니다.

---

## MCP 클라이언트 연결 (Claude Desktop)

### 가장 쉬운 길 — Polaris 가 설정을 만들어 준다

토큰을 발급하면 그 자리에 **「설정 전체 복사」 · 「항목만 복사」** 버튼이 나옵니다. **이 PC 의 실제 설치 경로**와
방금 발급한 토큰이 들어간 설정이 복사되므로 경로 · 역슬래시 · 쉼표를 손으로 맞출 일이 없습니다.

1. Claude Desktop → **설정 → 개발자 → 「구성 편집」(Edit Config)** → `claude_desktop_config.json` 이 있는 폴더가 열립니다
   (직접 찾을 때는 탐색기 주소창에 `%APPDATA%\Claude`).
2. 파일이 비어 있거나 없으면 **설정 전체 복사**를 붙여 넣습니다. 다른 MCP 서버가 이미 있으면 `mcpServers` 안에
   **항목만 복사**를 붙여 넣습니다(앞 항목 끝에 쉼표).
3. Claude Desktop 을 **완전히 종료**합니다 — 창만 닫으면 트레이에 남아 설정을 다시 읽지 않습니다. 트레이 아이콘에서
   「종료」 한 뒤 다시 실행합니다.
4. 대화창에서 「Polaris 에 등록된 클러스터 목록 보여줘」 라고 물어 확인합니다.

### 직접 쓸 때

설치 프로그램의 기본 위치는 **`%LOCALAPPDATA%\Programs\Polaris Free\polaris.exe`** 입니다(사용자마다 다름 —
`C:\Users\<사용자>\AppData\Local\Programs\Polaris Free\polaris.exe`). 설치할 때 위치를 바꿨다면 그 경로를 씁니다.
설정 파일 안에서는 `%LOCALAPPDATA%` 같은 환경 변수가 풀리지 않으므로 **전체 경로**를 적습니다.

```json
{
  "mcpServers": {
    "polaris-free": {
      "command": "C:\\Users\\<사용자>\\AppData\\Local\\Programs\\Polaris Free\\polaris.exe",
      "args": ["--mcp"],
      "env": {
        "POLARIS_MCP_TOKEN": "plrs_mcp_1a2b3c4d_여기에_발급받은_토큰"
      }
    }
  }
}
```

`POLARIS_MCP_TOKEN` 은 **필수**입니다. 없으면 툴이 전부 거부됩니다.

설정 후 클라이언트를 완전히 재시작하면 툴 6종이 잡힙니다.

### 새 PC 에서 연결할 때

- **토큰은 PC 마다 따로입니다.** 토큰은 그 PC 의 보안 보관함에 묶여 있어 다른 PC 에서 발급한 토큰으로는
  열리지 않습니다(「토큰이 올바르지 않거나 만료/폐기」 오류). 새 PC 의 Polaris 에서 새로 발급하세요.
- **새 PC 의 Polaris 에 클러스터가 있어야 합니다.** MCP 는 그 PC 의 Polaris 에 등록된 것만 봅니다 —
  새 PC 의 Polaris 에서 kubeconfig 를 다시 등록하세요.
- 예전 PC 의 `claude_desktop_config.json` 을 그대로 복사하면 경로(사용자 이름)와 토큰이 둘 다 맞지 않습니다 —
  새 PC 에서 「설정 전체 복사」 로 다시 만드세요.

> **토큰은 평문으로 설정 파일에 들어갑니다.** 이 파일은 사용자 홈 디렉터리에 있고
> 다른 사람과 공유하지 마세요. 노출이 의심되면 Polaris에서 해당 토큰을 폐기하고
> 재발급하면 됩니다.

---

## 제공 툴 — 툴 6종 (모두 조회)

| 툴 | 하는 일 | 필수 인자 |
|---|---|---|
| `polaris_list_clusters` | 보관된 클러스터(kubeconfig) 이름 목록 | — |
| `polaris_use_cluster` | 이후 호출의 기본 대상 클러스터 지정 | `cluster` |
| `polaris_list_resources` | 특정 kind 리소스 목록 — CRD 포함 모든 종류(CRD 는 이름 · 네임스페이스 · 만든 시각만) · 클러스터에 없는 종류는 오류 | `kind` |
| `polaris_get_resource` | 단일 리소스 상세 (describe / yaml / events) — Secret 값은 가림 | `kind`, `name` |
| `polaris_get_logs` | 파드 로그 (tail) | `namespace`, `pod` |
| `polaris_get_events` | 클러스터 이벤트 | — |

---

## 안전장치

**1. 토큰 없이는 아무것도 안 된다**
조회 툴 하나까지 토큰을 요구합니다. DPAPI 자동 잠금 해제가 켜져 있어도 MCP 경로로는
vault가 열리지 않습니다. 즉 **AI 클라이언트를 붙인 것만으로는 클러스터 정보를 볼 수
없고**, 사용자가 Polaris에서 명시적으로 토큰을 발급해 건네준 경우에만 동작합니다.

**2. 조회 전용**
클러스터를 바꾸는 툴(apply · scale · 재시작 · 삭제)은 이 판에 들어 있지 않습니다.

**3. 크리덴셜 미반출**
kubeconfig 본문 · 토큰은 응답에도 로그에도 직렬화하지 않습니다. 조회 결과에는 백엔드
Secret 마스킹이 그대로 적용됩니다.

**4. 감사 로그**
모든 호출이 다음 위치에 JSON Lines 로 남습니다.

```
%USERPROFILE%\.polaris-free\logs\mcp-audit.log
```

한 줄 예시 — 인자 중 크리덴셜류 키는 `***` 로 세탁됩니다. `token`(토큰 ID)이 함께 남아
**어느 토큰이 무엇을 했는지** 추적할 수 있습니다. 토큰 원문(secret)은 로그에 남지 않습니다.

```json
{"ts":"2026-07-28T05:12:33+00:00","id":"9f2a1c04","tool":"polaris_list_resources",
 "args":{"kind":"pods","namespace":"default"},
 "token":"1a2b3c4d","scope":"read","status":"ok","ms":212}
```

**5. 신뢰 경계**
로컬 stdio 전용입니다 — 네트워크 포트를 열지 않습니다. 같은 PC·같은 사용자 계정 안에서만
동작합니다.

---

## 문제 해결

| 증상 | 원인 / 조치 |
|---|---|
| 툴이 전부 "MCP 액세스 토큰이 없습니다" | 클라이언트 설정 `env` 에 `POLARIS_MCP_TOKEN` 이 없음 → 발급 후 넣고 **클라이언트 재시작** |
| "토큰이 올바르지 않거나 만료/폐기되었습니다" | 오타·복사 누락, 만료, 또는 이미 폐기된 토큰 → 재발급 |
| "vault 가 없습니다" | Polaris GUI를 한 번 실행해 마스터 비밀번호를 먼저 설정 |
| DPAPI를 켰는데도 안 열림 | 정상입니다. MCP는 토큰만 받습니다 (위 *인증* 참고) |
| 클라이언트가 서버를 못 잡음 · 툴이 안 보임 | ① `polaris.exe` 경로가 실제 설치 위치인지(기본 `%LOCALAPPDATA%\Programs\Polaris Free` — `Program Files` 아님) ② JSON 안 역슬래시는 `\\` ③ 다른 MCP 서버와 사이에 쉼표 ④ Claude Desktop 을 트레이에서 **완전히 종료** 후 재실행 — ①~③ 은 Polaris 의 「설정 전체 복사」 로 피할 수 있음 |
| 새 PC 에서 「토큰이 올바르지 않거나 만료/폐기」 | 다른 PC 에서 발급한 토큰 — 토큰은 PC 마다 그 PC 의 보관함에 묶임 → 새 PC 의 Polaris 에서 발급 |
| 연결은 되는데 클러스터가 하나도 없음 | 새 PC 의 Polaris 에 아직 등록되지 않음 → kubeconfig 를 등록 |
| Claude 쪽 오류 내용 보기 | Claude Desktop 로그 `%APPDATA%\Claude\logs\mcp-server-polaris-free.log` (설정 → 개발자에도 오류가 표시됨) |
| 동작 확인 | `%USERPROFILE%\.polaris-free\logs\mcp-audit.log` 에 `mcp_server_start` 가 찍혔는지 확인 |
