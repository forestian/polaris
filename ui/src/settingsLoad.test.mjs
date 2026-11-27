/**
 * 앱 시작 때 설정을 다시 만들 때 백엔드가 저장하는 키를 빠뜨리지 않는다 (v1.4.24).
 *
 * 저장(saveSettings)은 이 객체를 통째로 보내고 백엔드는 없는 키를 기본값으로 채운다 — 그래서 여기서 빠진 키는
 * 다른 설정을 저장하는 순간 조용히 지워진다(재시작 뒤 테마만 바꿨는데 웹훅 주소 · 알림 켜기가 사라졌다).
 */
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync } from 'node:fs'

const store = readFileSync(new URL('./store.jsx', import.meta.url), 'utf8')
const base = readFileSync(new URL('../../src/api/base.py', import.meta.url), 'utf8')

test('백엔드가 저장하는 설정 키를 시작할 때 모두 되살린다', () => {
  const norm = base.slice(base.indexOf('def _normalize_settings'), base.indexOf('def _dropped_settings_keys'))
  const keys = [...norm.matchAll(/^\s+'(\w+)':/gm)].map(m => m[1])
  assert.ok(keys.includes('notifications'))
  const from = store.indexOf('async function loadSettingsThenRestore')
  const load = store.slice(from, store.indexOf('setSettingsState(activeSettings)', from))
  // security 는 백엔드가 지금 값을 그대로 지킨다(save_settings 가 덮지 않는다) — 화면이 들고 있을 필요가 없다
  for (const k of keys.filter(k => k !== 'security')) {
    assert.match(load, new RegExp(`\\b${k}:`), `${k} 를 시작할 때 되살리지 않으면 다음 저장 때 지워진다`)
  }
})
