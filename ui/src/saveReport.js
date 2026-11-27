import { api } from './api.js'

/**
 * CHECK 보고서(DOCX) 저장 — 기본 파일 이름을 받아 저장 대화상자를 띄우고, 고른 경로로 백엔드가 만든다.
 * 돌려주는 값: null(취소) 또는 {ok, text}
 */
export async function saveReport({ filename, save, fallback, done }) {
  const name = await filename()
  const path = await api.openSaveDialog(typeof name === 'string' && name ? name : fallback)
  if (!path) return null
  const r = await save(path)
  return r?.ok ? { ok: true, text: done ? done(r) : `저장했습니다 — ${r.path}` } : { ok: false, text: r?.error || '저장하지 못했습니다' }
}
