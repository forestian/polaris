import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { installThemeStyles } from './themeRegistry.js'

installThemeStyles()

// 창에 끌어다 놓은 파일·링크로 **페이지가 넘어가지 않게** 한다 (v1.3.39).
// 기본 동작은 그 파일을 여는 것이고, 새 페이지도 js_api 를 통째로 받는다.
// 받는 곳은 자기 핸들러에서 먼저 preventDefault 하므로
// 여기서는 **아무도 받지 않은 드래그만** 「놓을 수 없음」으로 바꾼다.
// 창 쪽 검사기(src/navguard.py)가 마지막 방어선이고, 이것은 그 앞의 첫 줄이다.
//
// 글 입력칸·편집기(YAML)는 건드리지 않는다 — 거기선 글을 끌어 옮기는 것이 정상 동작이다.
const _editable = el => !!(el && el.closest &&
  el.closest('input, textarea, [contenteditable=""], [contenteditable="true"]'))
const _hasFiles = e => Array.from(e.dataTransfer?.types || []).includes('Files')
window.addEventListener('dragover', e => {
  if (e.defaultPrevented || _editable(e.target)) return
  e.preventDefault()
  if (e.dataTransfer) e.dataTransfer.dropEffect = 'none'
})
window.addEventListener('drop', e => {
  // 입력칸에 글을 떨어뜨리는 것은 그대로 둔다(그건 페이지를 넘기지 않는다)
  if (_editable(e.target) && !_hasFiles(e)) return
  e.preventDefault()
})

// pywebview 이벤트 버스 설정 (Python → JS 이벤트 수신)
window.__polarisBus = (event, data) => {
  window.dispatchEvent(new CustomEvent('polaris:' + event, { detail: data }))
}

// 맨 바깥 오류 경계 — 페이지 안의 오류는 App 의 ViewErrorBoundary 가 받지만, 사이드바 · 모달에서 난
// 렌더 오류는 받을 곳이 없어 창 전체가 하얗게 비었다.
class RootErrorBoundary extends React.Component {
  constructor(props) { super(props); this.state = { err: null } }
  static getDerivedStateFromError(err) { return { err } }
  componentDidCatch(err, info) { try { console.error('[UI] 렌더 오류(최상위):', err, info) } catch { /* noop */ } }
  render() {
    if (!this.state.err) return this.props.children
    return (
      <div style={{ padding: 24, color: 'var(--text, #ddd)', background: 'var(--bg-0, #0b0f1a)', height: '100vh', overflow: 'auto', boxSizing: 'border-box' }}>
        <h2 style={{ fontSize: 15, color: 'var(--red, #f87171)', marginBottom: 8 }}>화면을 그리는 중 오류가 발생했습니다</h2>
        <p style={{ fontSize: 12.5, opacity: 0.8, marginBottom: 12 }}>[다시 시도] 로 이어서 쓰거나, 안 되면 [새로 고침] 하세요. 연결 · 작업은 그대로 남아 있습니다.</p>
        <button className="btn btn-primary btn-sm" onClick={() => this.setState({ err: null })}>다시 시도</button>{' '}
        <button className="btn btn-ghost btn-sm" onClick={() => window.location.reload()}>새로 고침</button>
        <pre style={{ marginTop: 14, whiteSpace: 'pre-wrap', wordBreak: 'break-word', fontSize: 11, opacity: 0.75 }}>
          {String(this.state.err?.stack || this.state.err)}
        </pre>
      </div>
    )
  }
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <RootErrorBoundary>
      <App />
    </RootErrorBoundary>
  </React.StrictMode>,
)
