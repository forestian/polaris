/**
 * MCP 클라이언트 설정 만들기 (v1.5.55) — 새 PC 에서 연결이 실패하던 것(예시 경로 · 역슬래시 · 쉼표).
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'
import { claudeConfig, claudeEntry, CLAUDE_STEPS } from './mcpConfig.js'

const L = { command: 'C:\\Users\\kim\\AppData\\Local\\Programs\\Polaris Free\\polaris.exe', args: ['--mcp'] }

test('설정 전체 — 실제 경로 · 역슬래시 두 번 · 토큰', () => {
  const s = claudeConfig(L, 'plrs_mcp_abcd_x')
  assert.ok(s.includes('"C:\\\\Users\\\\kim\\\\AppData\\\\Local\\\\Programs\\\\Polaris Free\\\\polaris.exe"'), '파일 안에서는 \\\\ 로')
  const d = JSON.parse(s)
  assert.equal(d.mcpServers['polaris-free'].command, L.command, '읽으면 원래 경로')
  assert.deepEqual(d.mcpServers['polaris-free'].args, ['--mcp'])
  assert.equal(d.mcpServers['polaris-free'].env.POLARIS_MCP_TOKEN, 'plrs_mcp_abcd_x')
})

test('항목만 — 다른 MCP 서버가 있는 파일에 쉼표로 이어 붙여도 올바른 JSON', () => {
  const e = claudeEntry(L, 't')
  const merged = '{\n  "mcpServers": {\n    "other": { "command": "x" },\n' + e + '\n  }\n}'
  const d = JSON.parse(merged)
  assert.equal(d.mcpServers['polaris-free'].command, L.command)
  assert.equal(d.mcpServers.other.command, 'x')
})

test('개발 실행(python polaris.py --mcp)도 그대로', () => {
  const d = JSON.parse(claudeConfig({ command: 'C:\\Python\\python.exe', args: ['C:\\src\\polaris.py', '--mcp'] }, 't'))
  assert.deepEqual(d.mcpServers['polaris-free'].args, ['C:\\src\\polaris.py', '--mcp'])
  assert.deepEqual(JSON.parse(claudeConfig({ command: 'x' }, 't')).mcpServers['polaris-free'].args, ['--mcp'], 'args 가 없으면 --mcp')
})

test('안내 — 구성 편집 · 트레이에서 종료 · 화면 배선', () => {
  const steps = CLAUDE_STEPS.join(' ')
  assert.match(steps, /구성 편집/)
  assert.match(steps, /트레이/)
  const ui = readFileSync(new URL('./components/SettingsModal.jsx', import.meta.url), 'utf8')
  assert.match(ui, /setLaunch\(r\.launch \|\| null\)/)
  assert.match(ui, /copyIssued\('config'\)/)
  assert.match(ui, /다른 PC 에서는 열리지 않습니다/)
})

test('안내 복사 — 순서 · 실행 경로는 들어가고 토큰은 빠진다(v1.5.56)', async () => {
  const { claudeGuide } = await import('./mcpConfig.js')
  const g = claudeGuide(L)
  for (const t of CLAUDE_STEPS) assert.ok(g.includes(t))
  assert.ok(g.includes(L.command))
  assert.ok(!/plrs_mcp_/.test(g), '토큰 없음')
  assert.ok(claudeGuide(null).includes('1. '), '경로를 몰라도 순서는 나온다')
  const ui = readFileSync(new URL('./components/SettingsModal.jsx', import.meta.url), 'utf8')
  assert.match(ui, /copyIssued\('guide'\)/)
})
