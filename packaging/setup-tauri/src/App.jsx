import React, { useState, useEffect, useRef } from 'react'
import PolarisInstallStar from './PolarisStar.jsx'
import { STR } from './strings.js'

/* Polaris 설치 마법사 (Tauri) — 5페이지 위저드.
   1 설치 언어 / 2 설치 위치 / 3 추가 작업 / 4 설치(로그) / 5 완료 */

const ACCENT = '#f3c969'
const PRODUCT = 'Polaris Free'
const VERSION = 'v1.5.74-f1'
const TOTAL = 5

const isTauri = () => !!(window.__TAURI__ || window.__TAURI_INTERNALS__)
async function tInvoke(cmd, args) {
  const { invoke } = await import('@tauri-apps/api/core')
  return invoke(cmd, args)
}
async function winAction(a) {
  try {
    if (!isTauri()) return
    const { getCurrentWindow } = await import('@tauri-apps/api/window')
    const w = getCurrentWindow()
    if (a === 'min') await w.minimize()
    else if (a === 'max') await w.toggleMaximize()
    else await w.close()
  } catch {}
}

const S = {
  window: { width: '100vw', height: '100vh', background: 'var(--panel)', display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' },
  titlebar: { height: 40, flexShrink: 0, display: 'flex', alignItems: 'center', paddingLeft: 14, background: 'linear-gradient(180deg, #0e1422 0%, #0b0f1a 100%)', borderBottom: '1px solid #1a1f2e', position: 'relative', zIndex: 5 },
  titleLabel: { fontSize: 12.5, fontWeight: 600, color: '#cfd6e6', letterSpacing: '0.01em', whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 9 },
  capGroup: { marginLeft: 'auto', display: 'flex', height: '100%' },
  capBtn: { width: 46, height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#aab3c5', cursor: 'pointer', transition: 'background 0.12s, color 0.12s', border: 'none', background: 'transparent' },
  body: { flex: 1, display: 'flex', minHeight: 0 },
  brand: { width: 286, flexShrink: 0, position: 'relative', overflow: 'hidden', background: 'radial-gradient(ellipse at 50% 32%, rgba(125,211,252,0.08) 0%, transparent 60%),linear-gradient(165deg, #0a0e1f 0%, #11143200 40%, #14163d 70%, #1a1648 100%)', borderRight: '1px solid #1c2133', display: 'flex', flexDirection: 'column', padding: '24px 24px 20px' },
  starWrap: { display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 2, marginBottom: 2 },
  wordmark: { fontFamily: "'Fraunces', serif", fontStyle: 'italic', fontWeight: 600, fontSize: 36, lineHeight: 1, letterSpacing: '-0.03em', color: 'var(--gold)', textAlign: 'center', marginTop: 2 },
  tagline: { fontFamily: "'Pretendard', sans-serif", fontSize: 11.5, letterSpacing: '0.01em', color: 'var(--cyan)', textAlign: 'center', marginTop: 10, opacity: 0.9, lineHeight: 1.4, padding: '0 4px' },
  steps: { marginTop: 22, display: 'flex', flexDirection: 'column', gap: 2 },
  brandFooter: { marginTop: 'auto', paddingTop: 16, borderTop: '1px solid rgba(255,255,255,0.06)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' },
  content: { flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', background: 'var(--panel)' },
  inner: { flex: 1, padding: '26px 34px 6px', minHeight: 0, overflowX: 'hidden', overflowY: 'auto', display: 'flex', flexDirection: 'column' },
  eyebrow: { fontFamily: "'JetBrains Mono', monospace", fontSize: 11, letterSpacing: '0.18em', color: 'var(--cyan)', marginBottom: 12 },
  h1: { margin: 0, fontSize: 24, fontWeight: 700, color: 'var(--text)', letterSpacing: '-0.01em' },
  sub: { margin: '8px 0 0', fontSize: 13.5, color: 'var(--text-mid)', lineHeight: 1.6 },
  rule: { height: 1, background: 'linear-gradient(90deg, var(--border) 0%, transparent 100%)', margin: '18px 0 14px' },
  groupLabel: { fontSize: 12, fontWeight: 600, color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.12em', marginBottom: 10 },
  list: { display: 'flex', flexDirection: 'column', gap: 9 },
  listTight: { display: 'flex', flexDirection: 'column', gap: 5 },
  footer: { flexShrink: 0, height: 66, borderTop: '1px solid #1a1f2e', background: 'linear-gradient(180deg, #0e121d 0%, #0b0e18 100%)', display: 'flex', alignItems: 'center', padding: '0 24px 0 34px', gap: 12 },
  input: { flex: 1, height: 38, padding: '0 12px', background: 'var(--navy-900)', border: '1px solid var(--border-hi)', borderRadius: 8, color: 'var(--text)', fontSize: 13, fontFamily: "'JetBrains Mono', monospace" },
  logBox: { flex: 1, minHeight: 0, overflow: 'auto', background: '#070b13', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 12px', fontFamily: "'JetBrains Mono', monospace", fontSize: 11.5, lineHeight: 1.6, color: '#b7c0d4', whiteSpace: 'pre-wrap', wordBreak: 'break-all' },
}

function CaptionButtons() {
  const [h, setH] = useState(null)
  const b = S.capBtn
  return (
    <div style={S.capGroup}>
      <button style={{ ...b, background: h === 'min' ? 'rgba(255,255,255,0.08)' : 'transparent' }} onMouseEnter={() => setH('min')} onMouseLeave={() => setH(null)} onClick={() => winAction('min')}>
        <svg width="11" height="11" viewBox="0 0 11 11"><rect x="0" y="5" width="11" height="1" fill="currentColor"/></svg>
      </button>
      <button style={{ ...b, background: h === 'max' ? 'rgba(255,255,255,0.08)' : 'transparent' }} onMouseEnter={() => setH('max')} onMouseLeave={() => setH(null)} onClick={() => winAction('max')}>
        <svg width="10" height="10" viewBox="0 0 10 10"><rect x="0.5" y="0.5" width="9" height="9" stroke="currentColor" fill="none"/></svg>
      </button>
      <button style={{ ...b, background: h === 'close' ? '#c42b1c' : 'transparent', color: h === 'close' ? '#fff' : b.color }} onMouseEnter={() => setH('close')} onMouseLeave={() => setH(null)} onClick={() => winAction('close')}>
        <svg width="11" height="11" viewBox="0 0 11 11"><path d="M0.5 0.5 L10.5 10.5 M10.5 0.5 L0.5 10.5" stroke="currentColor" strokeWidth="1"/></svg>
      </button>
    </div>
  )
}

function StepItem({ label, n, active, done }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 11, padding: '6px 8px', borderRadius: 8, background: active ? 'rgba(243,201,105,0.10)' : 'transparent', border: active ? '1px solid rgba(243,201,105,0.22)' : '1px solid transparent' }}>
      <div style={{ width: 22, height: 22, borderRadius: '50%', flexShrink: 0, display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 11, fontWeight: 700, fontFamily: "'JetBrains Mono', monospace", background: active ? ACCENT : (done ? 'rgba(125,211,252,0.14)' : 'rgba(255,255,255,0.05)'), color: active ? '#1a1408' : (done ? 'var(--cyan)' : 'var(--text-dim)'), border: done && !active ? '1px solid rgba(125,211,252,0.3)' : 'none' }}>
        {done && !active ? <svg width="11" height="11" viewBox="0 0 12 12"><path d="M2 6.2 L4.8 9 L10 3" stroke="currentColor" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg> : n}
      </div>
      <span style={{ fontSize: 13, fontWeight: active ? 600 : 500, whiteSpace: 'nowrap', color: active ? 'var(--text)' : (done ? 'var(--text-mid)' : 'var(--text-dim)') }}>{label}</span>
    </div>
  )
}

function SelectCard({ checked, onClick, radio, title, desc, recommended, badge, t, compact }) {
  const [hover, setHover] = useState(false)
  return (
    <div onClick={onClick} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}
      style={{ display: 'flex', gap: 13, padding: compact ? '8px 14px' : '12px 15px', borderRadius: 10, cursor: 'pointer', alignItems: 'flex-start',
        background: checked ? 'rgba(243,201,105,0.06)' : (hover ? 'rgba(255,255,255,0.025)' : 'transparent'),
        border: '1px solid ' + (checked ? 'rgba(243,201,105,0.28)' : (hover ? 'var(--border-hi)' : 'var(--border)')), transition: 'background 0.12s, border-color 0.12s' }}>
      <div style={{ width: 20, height: 20, borderRadius: radio ? '50%' : 6, flexShrink: 0, marginTop: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', background: checked && !radio ? ACCENT : 'transparent', border: '1.5px solid ' + (checked ? ACCENT : 'var(--border-hi)') }}>
        {checked && (radio ? <div style={{ width: 10, height: 10, borderRadius: '50%', background: ACCENT }} /> : <svg width="12" height="12" viewBox="0 0 12 12"><path d="M2 6.2 L4.8 9 L10 3" stroke="#1a1408" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>)}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{title}</span>
          {recommended && <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.04em', whiteSpace: 'nowrap', color: 'var(--cyan)', background: 'rgba(125,211,252,0.12)', padding: '2px 7px', borderRadius: 999 }}>{t.recommended}</span>}
          {badge && <span style={{ fontSize: 10, fontWeight: 600, letterSpacing: '0.04em', whiteSpace: 'nowrap', color: ACCENT, background: 'rgba(243,201,105,0.12)', padding: '2px 7px', borderRadius: 999 }}>{badge}</span>}
        </div>
        {desc && <div style={{ fontSize: compact ? 12 : 12.5, color: 'var(--text-mid)', marginTop: compact ? 1 : 3, lineHeight: 1.45 }}>{desc}</div>}
      </div>
    </div>
  )
}

function FooterBtn({ children, variant, onClick, disabled }) {
  const [hover, setHover] = useState(false)
  let style = { height: 38, padding: '0 20px', borderRadius: 8, fontSize: 13.5, fontWeight: 600, cursor: disabled ? 'default' : 'pointer', fontFamily: 'inherit', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7, transition: 'background 0.12s, border-color 0.12s, transform 0.08s', border: '1px solid transparent', whiteSpace: 'nowrap', flexShrink: 0, opacity: disabled ? 0.5 : 1 }
  if (variant === 'primary') style = { ...style, background: hover && !disabled ? 'var(--gold-soft)' : ACCENT, color: '#1a1408', boxShadow: '0 4px 16px -4px rgba(243,201,105,0.5)', transform: hover && !disabled ? 'translateY(-1px)' : 'none' }
  else if (variant === 'ghost') style = { ...style, background: hover && !disabled ? 'rgba(255,255,255,0.05)' : 'transparent', color: 'var(--text-mid)', border: '1px solid var(--border-hi)' }
  else style = { ...style, background: 'transparent', color: hover ? 'var(--text-mid)' : 'var(--text-dim)' }
  return <button style={style} disabled={disabled} onClick={onClick} onMouseEnter={() => setHover(true)} onMouseLeave={() => setHover(false)}>{children}</button>
}

export default function App() {
  const [lang, setLang] = useState('ko')
  const [page, setPage] = useState(0)
  const [installDir, setInstallDir] = useState('')
  const [tasks, setTasks] = useState({ desktop: true, startmenu: true, autostart: false })
  const [logs, setLogs] = useState([])
  const [installing, setInstalling] = useState(false)
  const [installDone, setInstallDone] = useState(false)
  const [installErr, setInstallErr] = useState(null)
  const [runAfter, setRunAfter] = useState(true)
  const [copied, setCopied] = useState(false)
  const startedRef = useRef(false)
  const logRef = useRef(null)
  const t = STR[lang]

  useEffect(() => {
    (async () => {
      if (isTauri()) { try { setInstallDir(await tInvoke('default_install_dir')) } catch {} }
      else setInstallDir('C:\\Users\\me\\AppData\\Local\\Programs\\Polaris Free')
    })()
  }, [])

  useEffect(() => {
    if (logRef.current) logRef.current.scrollTop = logRef.current.scrollHeight
  }, [logs])

  async function startInstall() {
    setInstalling(true); setInstallErr(null); setLogs([])
    if (isTauri()) {
      let un = () => {}
      try {
        const { listen } = await import('@tauri-apps/api/event')
        un = await listen('install-log', (e) => setLogs((l) => [...l, String(e.payload)]))
        await tInvoke('do_install', { dir: installDir, desktop: tasks.desktop, startmenu: tasks.startmenu, autostart: tasks.autostart })
        setInstallDone(true)
      } catch (err) {
        setInstallErr(String(err)); setLogs((l) => [...l, 'ERROR: ' + String(err)])
      } finally { try { un() } catch {}; setInstalling(false) }
    } else {
      const sim = lang === 'en'
        ? ['Preparing install folder...', 'Extracting application files (1/2)...', 'Extracting application files (2/2)...', 'Creating shortcuts...', 'Registering uninstall entry...', 'Installation complete.']
        : ['설치 폴더 준비...', '애플리케이션 파일 압축 해제 (1/2)...', '애플리케이션 파일 압축 해제 (2/2)...', '바로 가기 생성...', '추가/제거 항목 등록...', '설치 완료.']
      for (const line of sim) { await new Promise((r) => setTimeout(r, 430)); setLogs((l) => [...l, line]) }
      setInstalling(false); setInstallDone(true)
    }
  }

  useEffect(() => {
    if (page === 3 && !startedRef.current) { startedRef.current = true; startInstall() }
  }, [page])

  async function pickDir() {
    if (!isTauri()) return
    try { const d = await tInvoke('pick_install_dir', { current: installDir }); if (d) setInstallDir(d) } catch {}
  }
  function copyLog() {
    try { navigator.clipboard.writeText(logs.join('\n')); setCopied(true); setTimeout(() => setCopied(false), 1500) } catch {}
  }
  async function finish() {
    if (runAfter && isTauri()) { try { await tInvoke('launch_polaris', { dir: installDir }) } catch {} }
    winAction('close')
  }
  function retry() { startedRef.current = false; setInstallDone(false); setPage(3); startedRef.current = true; startInstall() }

  // ── 페이지 본문 ──
  function Page() {
    if (page === 0) return (
      <>
        <h1 style={S.h1}>{t.p0_h}</h1><p style={S.sub}>{t.p0_sub}</p>
        <div style={S.rule}></div>
        <div style={S.list}>
          <SelectCard radio checked={lang === 'ko'} onClick={() => setLang('ko')} title={t.lang_ko} desc={STR.ko.lang_ko_d} t={t} />
          <SelectCard radio checked={lang === 'en'} onClick={() => setLang('en')} title={t.lang_en} desc={STR.en.lang_en_d} t={t} />
        </div>
      </>
    )
    if (page === 1) return (
      <>
        <h1 style={S.h1}>{t.p1_h}</h1><p style={S.sub}>{t.p1_sub}</p>
        <div style={S.rule}></div>
        <div style={S.groupLabel}>{t.p1_label}</div>
        <div style={{ display: 'flex', gap: 8 }}>
          <input style={S.input} value={installDir} readOnly />
          <FooterBtn variant="ghost" onClick={pickDir}>{t.browse}</FooterBtn>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 14, lineHeight: 1.6 }}>{t.p1_note}</div>
      </>
    )
    if (page === 2) return (
      <>
        <h1 style={S.h1}>{t.p2_h}</h1><p style={S.sub}>{t.p2_sub}</p>
        <div style={S.rule}></div>
        {/* 창 높이가 고정(612)이라 카드를 촘촘히(compact) — v1.4.2 전에는 「자동 실행」 이 아래로 잘려 안 보였다 */}
        <div style={S.groupLabel}>{t.g_shortcut}</div>
        <div style={S.listTight}>
          <SelectCard compact checked={tasks.desktop} onClick={() => setTasks((s) => ({ ...s, desktop: !s.desktop }))} recommended title={t.t_desktop} desc={t.t_desktop_d} t={t} />
          <SelectCard compact checked={tasks.startmenu} onClick={() => setTasks((s) => ({ ...s, startmenu: !s.startmenu }))} title={t.t_start} desc={t.t_start_d} t={t} />
          <SelectCard compact checked={tasks.autostart} onClick={() => setTasks((s) => ({ ...s, autostart: !s.autostart }))} title={t.t_auto} desc={t.t_auto_d} t={t} />
        </div>
      </>
    )
    if (page === 3) return (
      <>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <h1 style={{ ...S.h1, flex: 1 }}>{installErr ? t.p3_h : (installDone ? t.p3_done : t.p3_h)}</h1>
          <FooterBtn variant="ghost" onClick={copyLog} disabled={logs.length === 0}>{copied ? t.copied : t.copyLog}</FooterBtn>
        </div>
        <p style={S.sub}>{t.p3_sub}</p>
        {/* 진행 막대 */}
        <div style={{ height: 4, borderRadius: 4, background: 'rgba(255,255,255,0.08)', overflow: 'hidden', margin: '14px 0 12px' }}>
          <div style={{ height: '100%', width: installDone ? '100%' : '60%', background: installErr ? 'var(--red, #ef4444)' : ACCENT, transition: 'width 0.3s', animation: installing ? 'none' : 'none' }} />
        </div>
        <div ref={logRef} style={S.logBox}>{logs.map((l, i) => <div key={i}>{l}</div>)}</div>
      </>
    )
    return (
      <>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
          <div style={{ width: 30, height: 30, borderRadius: '50%', background: 'rgba(125,211,252,0.14)', border: '1px solid rgba(125,211,252,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <svg width="15" height="15" viewBox="0 0 12 12"><path d="M2 6.2 L4.8 9 L10 3" stroke="var(--cyan)" strokeWidth="1.8" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
          </div>
          <h1 style={S.h1}>{t.p4_h}</h1>
        </div>
        <p style={S.sub}>{t.p4_sub}</p>
        <div style={S.rule}></div>
        <SelectCard checked={runAfter} onClick={() => setRunAfter((v) => !v)} title={t.runAfter} t={t} />
      </>
    )
  }

  // ── 푸터 버튼 ──
  function Footer() {
    const showBack = page === 1 || page === 2
    const showCancel = page < 3
    let primary
    if (page === 0 || page === 1) primary = <FooterBtn variant="primary" onClick={() => setPage(page + 1)}>{t.next}<Arrow /></FooterBtn>
    else if (page === 2) primary = <FooterBtn variant="primary" onClick={() => setPage(3)}>{t.install}<Arrow /></FooterBtn>
    else if (page === 3) {
      if (installErr) primary = <FooterBtn variant="primary" onClick={retry}>{t.retry}</FooterBtn>
      else if (installDone) primary = <FooterBtn variant="primary" onClick={() => setPage(4)}>{t.next}<Arrow /></FooterBtn>
      else primary = <FooterBtn variant="primary" disabled>{t.installing}</FooterBtn>
    } else primary = <FooterBtn variant="primary" onClick={finish}>{t.finish}</FooterBtn>
    return (
      <div style={S.footer}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7, marginRight: 'auto' }}>
          {Array.from({ length: TOTAL }).map((_, i) => (
            <span key={i} style={{ width: i === page ? 22 : 7, height: 7, borderRadius: 999, background: i === page ? ACCENT : (i < page ? 'rgba(125,211,252,0.4)' : 'rgba(255,255,255,0.12)'), transition: 'all 0.2s' }}></span>
          ))}
        </div>
        {showBack && <FooterBtn variant="ghost" onClick={() => setPage(page - 1)}>{t.back}</FooterBtn>}
        {primary}
        {showCancel && <FooterBtn variant="text" onClick={() => winAction('close')}>{t.cancel}</FooterBtn>}
      </div>
    )
  }

  return (
    <div style={S.window}>
      <div style={S.titlebar} data-tauri-drag-region>
        <div style={S.titleLabel} data-tauri-drag-region>
          <svg width="17" height="17" viewBox="0 0 40 40" style={{ display: 'block' }}>
            <polygon points="20,3 23.5,16.5 37,20 23.5,23.5 20,37 16.5,23.5 3,20 16.5,16.5" fill={ACCENT}/>
            <polygon points="20,11 21.4,18.6 29,20 21.4,21.4 20,29 18.6,21.4 11,20 18.6,18.6" fill="#fff5d6"/>
          </svg>
          <span>{t.title}</span>
          <span style={{ color: 'var(--text-dim)', fontWeight: 500, fontSize: 12 }}>— {VERSION}</span>
        </div>
        <CaptionButtons />
      </div>

      <div style={S.body}>
        <div style={S.brand}>
          <div style={S.starWrap}><PolarisInstallStar size={132} intensity={0.78} /></div>
          <div style={S.wordmark}>{PRODUCT}</div>
          <div style={S.tagline}>{t.tagline}</div>
          <div style={S.steps}>
            {t.steps.map((label, i) => <StepItem key={i} label={label} n={i + 1} active={i === page} done={i < page} />)}
          </div>
          <div style={S.brandFooter}>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, letterSpacing: '0.14em', color: 'var(--text-dim)' }}>POLARIS FREE</span>
            <span style={{ fontFamily: "'JetBrains Mono', monospace", fontSize: 10, color: 'var(--text-dim)', opacity: 0.7 }}>{VERSION}</span>
          </div>
        </div>

        <div style={S.content}>
          <div style={S.inner}>
            <div style={S.eyebrow}>{t.stepN(page + 1, TOTAL)}</div>
            <Page />
          </div>
          <Footer />
        </div>
      </div>
    </div>
  )
}

function Arrow() {
  return <svg width="14" height="14" viewBox="0 0 14 14"><path d="M3 7 H11 M7.5 3.5 L11 7 L7.5 10.5" stroke="#1a1408" strokeWidth="1.6" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
}
