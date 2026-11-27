import React, { useState, useRef, useEffect } from 'react'
import { useApp } from '../store.jsx'
import { api } from '../api.js'
import { helloButtonReady } from '../vaultGate.js'
import PolarisMark from './PolarisMark.jsx'
import { Lock, KeyRound, ShieldCheck, AlertCircle, Loader2, Check, FolderCog , ScanFace} from 'lucide-react'

/**
 * VaultGate — 시작 잠금 화면 (v1.2.1).
 *
 * 프로그램을 열면 메인 UI 전에 이 게이트가 먼저 뜬다 (로그인 방식).
 *   • vault 미생성(첫 실행)  → 마스터 비밀번호 생성 (2회 입력)
 *   • vault 존재 + 잠김       → 마스터 비밀번호로 잠금 해제 (로그인)
 *   • vault 잠금 해제됨        → children(메인 앱) 렌더
 *   • cryptography 미사용(available:false) → 게이트 우회 (평문 동작)
 *
 * vault 가 잠금 해제돼야 kubeconfig / 스냅샷 복호화가 가능하므로, 이 게이트가
 * 통과되기 전에는 세션 복원(store)도 보류된다.
 */
export default function VaultGate({ children }) {
  const {
    vaultStatus, vaultChecked, vaultUnlocked,
    vaultInit, vaultUnlock, vaultUnlockHello, appVersion, vaultLockedByUser,
  } = useApp()

  // Windows Hello (v1.2.167) — 쓸 수 있고 자동 해제가 켜져 있을 때만 버튼을 띄운다.
  // Hello 는 확인만 하고 복호화는 DPAPI 가 하므로 둘 다 있어야 의미가 있다.
  const [hello, setHello] = useState(null)
  useEffect(() => {
    if (vaultUnlocked || !vaultChecked) return
    let alive = true
    api.helloStatus().then(r => { if (alive) setHello(r?.ok ? r : null) }).catch(() => {})
    return () => { alive = false }
  }, [vaultChecked, vaultUnlocked])
  const helloReady = helloButtonReady(hello)

  async function unlockWithHello() {
    setError(''); setBusy(true)
    const r = await vaultUnlockHello()
    setBusy(false)
    if (!r?.ok) setError(r?.error || 'Windows Hello 확인 실패')
  }

  const [pw1, setPw1] = useState('')
  const [pw2, setPw2] = useState('')
  const [autoUnlock, setAutoUnlock] = useState(false)   // 첫 실행 잠금 방식 선택
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const inputRef = useRef(null)
  // 수동 잠금 시 자물쇠 화면을 먼저 보여주고, 클릭하면 해제 폼으로 (revealed=true)
  const [revealed, setRevealed] = useState(false)

  const creating = !vaultStatus.exists   // 첫 실행 = 생성 모드

  // 모드 진입 시 첫 입력에 포커스 (자물쇠 화면에서 폼으로 넘어온 직후 포함)
  useEffect(() => {
    if (vaultChecked && !vaultUnlocked) {
      const t = setTimeout(() => inputRef.current?.focus(), 80)
      return () => clearTimeout(t)
    }
  }, [vaultChecked, vaultUnlocked, creating, revealed])

  // 잠금 해제되면: 자물쇠 화면 상태 초기화 + 입력했던 마스터 비밀번호를 state 에서 즉시 폐기.
  // (게이트 컴포넌트는 unmount 되지 않고 children 을 렌더하므로, 비우지 않으면 다음에 잠갔을 때
  //  비밀번호 입력칸이 채워진 채로 남아 누구나 클릭만으로 잠금 해제되는 보안 문제가 있었음.)
  useEffect(() => {
    if (vaultUnlocked) { setRevealed(false); setPw1(''); setPw2(''); setError('') }
  }, [vaultUnlocked])

  // ── 잠금 해제됨 / vault 비활성 → 메인 앱 통과 ─────────────────────────────
  if (vaultUnlocked) return children

  // ── 최초 상태 조회 전 → 로딩 ──────────────────────────────────────────────
  if (!vaultChecked) {
    return (
      <GateShell>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14, color: 'var(--text-dim)' }}>
          <Loader2 size={26} className="spin" color="var(--nimbus)" />
          <span style={{ fontSize: 12 }}>보안 보관함 확인 중...</span>
        </div>
      </GateShell>
    )
  }

  // ── 사용자가 직접 '잠그기'를 누른 경우 → 까만 잠금화면(자물쇠). 클릭 시 해제 폼. ──
  // 시작 시 로그인(자동 잠금 아님)은 기존대로 바로 폼을 보여준다.
  if (!creating && vaultLockedByUser && !revealed) {
    return <LockScreen onUnlock={() => setRevealed(true)} />
  }

  async function submit() {
    setError('')
    if (creating) {
      if (pw1.length < 4) { setError('비밀번호는 4자 이상이어야 합니다 (8자 이상 권장).'); return }
      if (pw1 !== pw2)    { setError('두 비밀번호가 일치하지 않습니다.'); return }
      setBusy(true)
      const r = await vaultInit(pw1, autoUnlock)
      if (r?.ok) {
        const u = await vaultUnlock(pw1)   // 생성 직후 바로 잠금 해제
        setBusy(false)
        if (!u?.ok) setError(u?.error || '잠금 해제 실패')
      } else {
        setBusy(false)
        setError(r?.error || 'Vault 생성 실패')
      }
    } else {
      if (!pw1) { setError('비밀번호를 입력하세요.'); return }
      setBusy(true)
      const r = await vaultUnlock(pw1)
      setBusy(false)
      if (!r?.ok) {
        setError(r?.error || '잠금 해제 실패')
        setPw1('')
        inputRef.current?.focus()
      }
    }
  }

  function onKeyDown(e) {
    if (e.key === 'Enter' && !busy) submit()
  }

  const Icon = creating ? ShieldCheck : Lock

  return (
    <GateShell>
      <div
        onClick={e => e.stopPropagation()}
        style={{
          width: 380, padding: '30px 32px 26px',
          background: 'var(--bg-2)',
          border: '1px solid var(--border-bright)',
          borderRadius: 14,
          boxShadow: '0 24px 70px rgba(0,0,0,0.55)',
          WebkitAppRegion: 'no-drag',
        }}
      >
        {/* 로고 */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 10, marginBottom: 22 }}>
          <PolarisMark size={42} />
          <div style={{ textAlign: 'center' }}>
            <div style={{
              fontSize: 17, fontWeight: 800, letterSpacing: '-0.01em',
              background: 'linear-gradient(90deg, #ffe9b8, var(--nimbus) 55%, var(--blue))',
              WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            }}>POLARIS</div>
            <div style={{ fontSize: 9.5, color: 'var(--text-dim)', marginTop: 3, letterSpacing: '0.12em' }}>
              {appVersion ? `v${appVersion} · ` : ''}보안 보관함
            </div>
          </div>
        </div>

        {/* 타이틀 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
          <Icon size={16} color="var(--nimbus)" />
          <h1 style={{ fontSize: 14, fontWeight: 700, margin: 0, color: 'var(--text-bright)' }}>
            {creating ? '마스터 비밀번호 설정' : '잠금 해제'}
          </h1>
        </div>
        <p style={{ fontSize: 11.5, color: 'var(--text-dim)', lineHeight: 1.6, margin: '0 0 18px' }}>
          {creating
            ? '이 비밀번호로 kubeconfig, 클러스터 스냅샷이 암호화됩니다. 한 번만 설정하며, 분실 시 복구할 수 없습니다.'
            : '저장된 kubeconfig, 클러스터 스냅샷을 열려면 마스터 비밀번호를 입력하세요.'}
        </p>

        {/* Windows Hello (v1.2.167) — 잠금 해제 화면에서만 */}
        {!creating && helloReady && (
          <div style={{ marginBottom: 12 }}>
            <button onClick={unlockWithHello} disabled={busy} style={{
              width: '100%', padding: '9px 12px', fontSize: 12.5, fontWeight: 600,
              background: 'var(--bg-3)', color: 'var(--text-bright)',
              border: '1px solid var(--nimbus)', borderRadius: 6,
              cursor: busy ? 'wait' : 'pointer',
              display: 'inline-flex', alignItems: 'center', justifyContent: 'center', gap: 7,
            }}>
              <ScanFace size={14} color="var(--nimbus)" /> Windows Hello 로 잠금 해제
            </button>
            <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 5,
                          textAlign: 'center' }}>
              얼굴·지문·PIN 으로 본인 확인 후 이 PC 의 저장된 키로 엽니다
            </div>
          </div>
        )}

        {/* 입력 */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          <input
            ref={inputRef}
            type="password"
            value={pw1}
            disabled={busy}
            onChange={e => setPw1(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder={creating ? '마스터 비밀번호 (4자 이상)' : '마스터 비밀번호'}
            style={inputStyle}
            autoComplete="off"
          />
          {creating && (
            <input
              type="password"
              value={pw2}
              disabled={busy}
              onChange={e => setPw2(e.target.value)}
              onKeyDown={onKeyDown}
              placeholder="비밀번호 확인"
              style={inputStyle}
              autoComplete="off"
            />
          )}
        </div>

        {/* 첫 실행 — 잠금 방식 선택 */}
        {creating && (
          <div style={{ marginTop: 14 }}>
            <div style={{ fontSize: 10.5, color: 'var(--text-dim)', fontWeight: 700,
                          letterSpacing: '0.05em', marginBottom: 7 }}>
              잠금 방식
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 7 }}>
              <ModeOption
                active={!autoUnlock} disabled={busy}
                onClick={() => setAutoUnlock(false)}
                title="매번 비밀번호 입력"
                desc="가장 안전 · 실행할 때마다 비밀번호로 로그인"
              />
              <ModeOption
                active={autoUnlock} disabled={busy}
                onClick={() => setAutoUnlock(true)}
                title="자동 잠금 해제 (이 PC)"
                desc="비밀번호 생략 · Windows 계정(DPAPI)으로 자동 해제. 설정에서 변경 가능"
              />
            </div>
            <div style={{
              marginTop: 10, fontSize: 10, color: 'var(--text-dim)', lineHeight: 1.6,
              display: 'flex', gap: 6, alignItems: 'flex-start',
            }}>
              <FolderCog size={12} style={{ flexShrink: 0, marginTop: 1 }} />
              <span>
                데이터(보관함·스냅샷 등)는 사용자 폴더의 <code>.polaris-free</code> 에 저장됩니다.
                저장 위치는 나중에 <strong>설정 → 데이터 폴더</strong>에서 바꿀 수 있어요.
              </span>
            </div>
          </div>
        )}

        {/* 에러 */}
        {error && (
          <div style={{
            marginTop: 12, padding: '8px 11px', borderRadius: 6,
            display: 'flex', alignItems: 'center', gap: 8,
            background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.4)',
            fontSize: 11.5, color: 'var(--text)',
          }}>
            <AlertCircle size={13} color="var(--red)" style={{ flexShrink: 0 }} />
            {error}
          </div>
        )}

        {/* 버튼 */}
        <button
          onClick={submit}
          disabled={busy}
          style={{
            width: '100%', marginTop: 16, padding: '10px 0',
            fontSize: 13, fontWeight: 700,
            background: busy ? 'var(--bg-3)' : 'var(--nimbus)',
            color: busy ? 'var(--text-dim)' : 'var(--accent-ink, #04121a)',
            border: 'none', borderRadius: 7, cursor: busy ? 'default' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 7,
            transition: 'background 0.12s',
          }}
        >
          {busy
            ? <><Loader2 size={14} className="spin" /> 처리 중...</>
            : creating
              ? <><ShieldCheck size={14} /> 생성하고 시작</>
              : <><KeyRound size={14} /> 잠금 해제</>}
        </button>
      </div>
    </GateShell>
  )
}

// ── 잠금 방식 선택 카드 (첫 실행) ────────────────────────────────────────────
function ModeOption({ active, disabled, onClick, title, desc }) {
  return (
    <button
      type="button" onClick={onClick} disabled={disabled} aria-pressed={active}
      style={{
        textAlign: 'left', padding: '9px 11px', borderRadius: 8, cursor: disabled ? 'default' : 'pointer',
        background: active ? 'var(--nimbus-dim, rgba(52,211,153,0.12))' : 'var(--bg-1)',
        border: `1px solid ${active ? 'var(--nimbus)' : 'var(--border-bright)'}`,
        display: 'flex', alignItems: 'flex-start', gap: 9, width: '100%',
        WebkitAppRegion: 'no-drag',
      }}
    >
      <div style={{
        width: 15, height: 15, borderRadius: '50%', flexShrink: 0, marginTop: 1,
        border: `2px solid ${active ? 'var(--nimbus)' : 'var(--border-bright)'}`,
        background: active ? 'var(--nimbus)' : 'transparent',
        display: 'grid', placeItems: 'center',
      }}>
        {active && <Check size={9} color="var(--accent-ink)" strokeWidth={3} />}
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontSize: 12, fontWeight: 700, color: active ? 'var(--text-bright)' : 'var(--text)' }}>
          {title}
        </div>
        <div style={{ fontSize: 10.5, color: 'var(--text-dim)', lineHeight: 1.5, marginTop: 2 }}>
          {desc}
        </div>
      </div>
    </button>
  )
}

// ── 수동 잠금 화면 (Windows+L 식) — 까만 배경 + 중앙 자물쇠. 클릭 시 해제 폼으로. ──
function LockScreen({ onUnlock }) {
  const [hover, setHover] = useState(false)
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999, background: '#000',
      userSelect: 'none', overflow: 'hidden',
    }}>
      {/* 드래그 레이어 — 검은 배경을 끌어 창 이동 (pywebview 는 easy_drag=False 라
          pywebview-drag-region 클래스로만 드래그 인식; WebkitAppRegion 은 보조 힌트) */}
      <div className="pywebview-drag-region" style={{
        position: 'absolute', inset: 0, WebkitAppRegion: 'drag',
      }} />
      {/* 클릭 레이어 — 자물쇠만 클릭 가능, 나머지 영역은 클릭이 드래그 레이어로 통과 */}
      <div style={{
        position: 'absolute', inset: 0, display: 'grid', placeItems: 'center',
        pointerEvents: 'none',
      }}>
      <div
        onClick={onUnlock}
        onMouseEnter={() => setHover(true)}
        onMouseLeave={() => setHover(false)}
        title="클릭하여 잠금 해제"
        style={{
          WebkitAppRegion: 'no-drag', cursor: 'pointer', pointerEvents: 'auto',
          display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 22,
        }}
      >
        <div style={{
          width: 108, height: 108, borderRadius: '50%', display: 'grid', placeItems: 'center',
          background: hover ? 'rgba(52,211,153,0.12)' : 'rgba(255,255,255,0.045)',
          border: `1px solid ${hover ? 'var(--nimbus)' : 'rgba(255,255,255,0.14)'}`,
          boxShadow: hover ? '0 0 46px rgba(52,211,153,0.28)' : 'none',
          transition: 'all 0.18s ease',
        }}>
          <Lock size={48} color={hover ? 'var(--nimbus)' : 'var(--text-mid)'}
            style={{ transition: 'color 0.18s ease' }} />
        </div>
        <div style={{ textAlign: 'center' }}>
          <div style={{
            fontSize: 17, fontWeight: 800, letterSpacing: '-0.01em',
            background: 'linear-gradient(90deg, #ffe9b8, var(--nimbus) 55%, var(--blue))',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>POLARIS</div>
          <div style={{
            fontSize: 12, marginTop: 9, transition: 'color 0.18s ease',
            color: hover ? 'var(--text-mid)' : 'var(--text-dim)',
          }}>
            잠겨 있음 · 자물쇠를 클릭하여 잠금 해제
          </div>
        </div>
      </div>
      </div>
      <GateWindowControls />
    </div>
  )
}

// ── 게이트용 창 컨트롤 (최소화/닫기) — 게이트가 타이틀바를 덮으므로 직접 제공 ──────
function GateWindowControls() {
  const [ready, setReady] = useState(() => !!window.pywebview?.api)
  const [hM, setHM] = useState(false)
  const [hC, setHC] = useState(false)
  useEffect(() => {
    if (ready) return undefined
    const t = setInterval(() => { if (window.pywebview?.api) { setReady(true); clearInterval(t) } }, 400)
    return () => clearInterval(t)
  }, [ready])
  if (!ready) return null
  const min = () => { try { window.pywebview.api.window_minimize() } catch { /* noop */ } }
  const close = () => { try { window.pywebview.api.window_close() } catch { /* noop */ } }
  const base = {
    width: 46, height: 32, display: 'grid', placeItems: 'center', border: 'none',
    cursor: 'pointer', WebkitAppRegion: 'no-drag', transition: 'background 0.12s, color 0.12s',
  }
  return (
    <div style={{
      position: 'absolute', top: 0, right: 0, zIndex: 20, display: 'flex',
      pointerEvents: 'auto', WebkitAppRegion: 'no-drag',
    }}>
      <button type="button" title="최소화" onClick={min}
        onMouseEnter={() => setHM(true)} onMouseLeave={() => setHM(false)}
        style={{ ...base, background: hM ? 'rgba(255,255,255,0.10)' : 'transparent', color: 'var(--text-mid)' }}>
        <svg width="11" height="11" viewBox="0 0 11 11"><rect x="0" y="5" width="11" height="1" fill="currentColor" /></svg>
      </button>
      <button type="button" title="닫기" onClick={close}
        onMouseEnter={() => setHC(true)} onMouseLeave={() => setHC(false)}
        style={{ ...base, background: hC ? '#c42b1c' : 'transparent', color: hC ? '#fff' : 'var(--text-mid)' }}>
        <svg width="11" height="11" viewBox="0 0 11 11"><path d="M0.5 0.5 L10.5 10.5 M10.5 0.5 L0.5 10.5" stroke="currentColor" strokeWidth="1.1" /></svg>
      </button>
    </div>
  )
}

// ── 게이트 배경 (드래그 가능, 메인 창 이동용) ────────────────────────────────
function GateShell({ children }) {
  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 9999, overflow: 'hidden',
      background: 'radial-gradient(1200px 600px at 50% -10%, rgba(52,211,153,0.10), transparent 60%), var(--bg-0)',
      userSelect: 'none',
    }}>
      {/* 드래그 레이어 — 배경을 끌어 창 이동 (pywebview-drag-region 클래스로만 인식) */}
      <div className="pywebview-drag-region" style={{
        position: 'absolute', inset: 0, WebkitAppRegion: 'drag',
      }} />
      {/* 콘텐츠 레이어 — 카드만 상호작용, 주변 여백은 드래그 레이어로 통과 */}
      <div style={{
        position: 'absolute', inset: 0, display: 'grid', placeItems: 'center',
        pointerEvents: 'none',
      }}>
        <div style={{ pointerEvents: 'auto' }}>{children}</div>
      </div>
      <GateWindowControls />
    </div>
  )
}

const inputStyle = {
  width: '100%', padding: '9px 12px',
  background: 'var(--bg-1)', border: '1px solid var(--border-bright)',
  borderRadius: 7, color: 'var(--text-bright)',
  fontSize: 13, fontFamily: 'var(--font)', outline: 'none',
  boxSizing: 'border-box',
}
