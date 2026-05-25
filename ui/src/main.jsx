import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'
import './index.css'
import { installThemeStyles } from './themeRegistry.js'

installThemeStyles()

// pywebview 이벤트 버스 설정 (Python → JS 이벤트 수신)
window.__polarisBus = (event, data) => {
  window.dispatchEvent(new CustomEvent('polaris:' + event, { detail: data }))
}

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
