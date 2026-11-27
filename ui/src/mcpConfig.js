/**
 * MCP 클라이언트(Claude Desktop) 설정 만들기 (v1.5.55) — mcpConfig.test.mjs 가 고정.
 *
 * 새 PC 에서 연결이 자주 실패했다(사용자 신고): 안내 문서의 예시 경로가 실제 설치 위치와 달랐고,
 * JSON 안 역슬래시를 두 번 써야 하는 것 · 다른 MCP 서버가 이미 있을 때 쉼표를 맞추는 것도 손으로 하면 틀린다.
 * 그래서 토큰을 발급할 때 **이 PC 의 실제 실행 경로**와 토큰을 넣은 설정을 통째로 만들어 복사하게 한다.
 * JSON.stringify 가 역슬래시를 알아서 두 번 쓴다.
 */

/** claude_desktop_config.json 전체 — 파일이 비어 있거나 없을 때 그대로 붙여 넣는다 */
export function claudeConfig(launch, token) {
  return JSON.stringify({ mcpServers: { 'polaris-free': serverEntry(launch, token) } }, null, 2)
}

/** 이미 다른 MCP 서버가 있을 때 mcpServers 안에 넣을 한 항목("polaris-free": {...}) */
export function claudeEntry(launch, token) {
  const body = JSON.stringify(serverEntry(launch, token), null, 2).split('\n').map((l, i) => (i ? '  ' + l : l)).join('\n')
  return `  "polaris-free": ${body}`
}

function serverEntry(launch, token) {
  const cmd = String(launch?.command || '')
  const args = Array.isArray(launch?.args) && launch.args.length ? launch.args : ['--mcp']
  return { command: cmd, args, env: { POLARIS_MCP_TOKEN: String(token || '') } }
}

/** 설정 파일 자리 · 하는 순서(화면 안내와 문서가 같은 글) */
export const CLAUDE_STEPS = [
  'Claude Desktop → 설정 → 개발자 → 「구성 편집」(Edit Config) 을 누르면 claude_desktop_config.json 이 있는 폴더가 열립니다(직접 찾을 때는 %APPDATA%\\Claude).',
  '파일이 비어 있거나 없으면 「설정 전체 복사」 를 붙여 넣고, 다른 MCP 서버가 이미 있으면 mcpServers 안에 「항목만 복사」 를 붙여 넣습니다(앞 항목 끝에 쉼표).',
  'Claude Desktop 을 완전히 종료합니다 — 창만 닫으면 트레이에 남아 있으니 트레이 아이콘에서 「종료」 — 그다음 다시 실행합니다.',
]

/** 화면 안내를 글로 복사(v1.5.56) — 동료에게 보내거나 메모에 붙여 넣는 용도라 **토큰은 넣지 않는다** */
export function claudeGuide(launch) {
  const lines = ['[Polaris Free MCP — Claude Desktop 연결 순서]', '']
  lines.push('0. Polaris → 설정 → 보안 잠금 → MCP 액세스 토큰에서 토큰을 발급하고 「설정 전체 복사」 를 누릅니다(토큰은 PC 마다 따로 발급).')
  CLAUDE_STEPS.forEach((t, i) => lines.push(`${i + 1}. ${t}`))
  lines.push('')
  if (launch?.command) lines.push(`실행 경로(이 PC): ${launch.command}`)
  lines.push('설정 파일에는 토큰이 평문으로 들어가므로 캡처·공유에 주의하세요.')
  return lines.join('\n')
}
