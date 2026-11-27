import React, { useState, useEffect } from 'react'
import { api } from '../api.js'
import { Loader2 } from 'lucide-react'

/**
 * LLM 연결 테스트 버튼 — AI 진단/AI 어시스턴트/보고서/건강 스캔 등 LLM URL 설정이 있는
 * 모든 곳에서 공용으로 쓴다. /v1/models 로 도달성 확인 + 모델 목록을 받아 onModels 로
 * 부모에 전달(부모가 datalist 를 채우는 데 사용).
 */
export default function LlmConnectionTest({ url, onModels, compact }) {
  const [test, setTest] = useState(null)   // null | {loading} | {ok, count, models, warning, error}

  // URL 이 바뀌면 이전 서버에 대한 테스트 결과는 무의미 — 초기화(오해 방지)
  useEffect(() => { setTest(null) }, [url])

  async function run() {
    setTest({ loading: true })
    let r
    try { r = await api.testLlmConnection(url) }
    catch (e) { r = { ok: false, error: String(e) } }
    setTest(r || { ok: false, error: '연결 테스트 실패' })
    if (r?.ok && onModels) onModels(r.models || [])
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 4, alignItems: 'flex-start' }}>
      <button type="button" className={compact ? 'btn btn-ghost btn-sm' : 'btn btn-default btn-sm'}
        onClick={run} disabled={test?.loading} style={{ gap: 5, whiteSpace: 'nowrap', flexShrink: 0 }}>
        {test?.loading ? <Loader2 size={12} className="spin" /> : null}
        {test?.loading ? '테스트 중…' : '연결 테스트'}
      </button>
      {test && !test.loading && (
        <div style={{ fontSize: 10.5, lineHeight: 1.5, color: test.ok ? 'var(--nimbus)' : '#f87171' }}>
          {test.ok
            ? (test.count
                ? `✓ 연결됨 · 모델 ${test.count}개 (아래에서 선택)`
                : `✓ 연결됨 · ${test.warning || '모델 목록 없음 — 모델명을 직접 입력하세요.'}`)
            : `✗ ${test.error || '연결 실패'}`}
        </div>
      )}
    </div>
  )
}
