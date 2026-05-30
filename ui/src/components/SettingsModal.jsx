import React, { useEffect, useState } from 'react'
import { useApp } from '../store.jsx'
import { api } from '../api.js'
import { applyTheme, normalizeThemeId, THEME_IDS, THEMES } from '../themeRegistry.js'
import {
  Check,
  LogOut,
  MinusSquare,
  Palette,
  RotateCw,
  Settings as SettingsIcon,
  KeyRound,
  Lock,
  Unlock,
  AlertCircle,
  FolderCog,
  FolderOpen,
  X,
} from 'lucide-react'

const TABS = [
  { id: 'exit', label: '종료 옵션', icon: SettingsIcon },
  { id: 'security', label: '보안 잠금', icon: KeyRound },
  { id: 'data', label: '데이터 폴더', icon: FolderCog },
  { id: 'theme', label: '배경 테마', icon: Palette },
]

export default function SettingsModal() {
  const { setShowSettings, settings, saveSettings,
          vaultStatus, vaultSetAutoUnlock } = useApp()
  const [draft, setDraft] = useState(() => normalizeSettings(settings))
  const [activeTab, setActiveTab] = useState('exit')
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setDraft(normalizeSettings(settings))
  }, [settings])

  useEffect(() => {
    applyTheme(draft.themeId)
  }, [draft.themeId])

  function closeWithoutSave() {
    applyTheme(settings.themeId)
    setShowSettings(false)
  }

  async function applyAndClose() {
    setSaving(true)
    await saveSettings(draft)
    setSaving(false)
    setSaved(true)
    setTimeout(() => setShowSettings(false), 400)
  }

  function update(key, value) {
    setDraft(d => ({ ...d, [key]: value }))
  }

  return (
    <div
      className="modal-overlay"
      onClick={e => e.target === e.currentTarget && closeWithoutSave()}
    >
      <div className="modal" style={{ width: 560 }}>
        <div className="modal-header">
          <h2 style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <SettingsIcon size={16} color="var(--nimbus)" />
            설정
          </h2>
          <button className="btn btn-ghost btn-sm" onClick={closeWithoutSave}>
            <X size={14} />
          </button>
        </div>

        <div style={{
          display: 'flex', gap: 6, padding: '10px 14px 0',
          borderBottom: '1px solid var(--border)',
        }}>
          {TABS.map(tab => {
            const Icon = tab.icon
            const active = activeTab === tab.id
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: 'inline-flex', alignItems: 'center', gap: 6,
                  padding: '8px 12px',
                  border: '1px solid var(--border)',
                  borderBottomColor: active ? 'var(--bg-2)' : 'var(--border)',
                  borderRadius: '6px 6px 0 0',
                  background: active ? 'var(--bg-2)' : 'var(--bg-3)',
                  color: active ? 'var(--text-bright)' : 'var(--text-mid)',
                  fontSize: 12, fontWeight: 700,
                  cursor: 'pointer',
                  transform: active ? 'translateY(1px)' : 'none',
                }}
              >
                <Icon size={13} color={active ? 'var(--nimbus)' : 'var(--text-dim)'} />
                {tab.label}
              </button>
            )
          })}
        </div>

        <div className="modal-body" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
          {activeTab === 'exit' && <ExitOptionsTab draft={draft} update={update} />}
          {activeTab === 'security' && (
            <SecurityTab vaultStatus={vaultStatus} vaultSetAutoUnlock={vaultSetAutoUnlock} />
          )}
          {activeTab === 'data' && <DataFolderTab />}
          {activeTab === 'theme' && (
            <ThemeTab selected={draft.themeId} onSelect={themeId => update('themeId', themeId)} />
          )}
        </div>

        <div className="modal-footer">
          <button className="btn btn-default" onClick={closeWithoutSave}>
            취소
          </button>
          <button
            className="btn btn-primary"
            onClick={applyAndClose}
            disabled={saving}
            style={{ gap: 5 }}
          >
            {saved && <Check size={13} />}
            {saving ? '저장 중...' : saved ? '저장됨' : '저장'}
          </button>
        </div>
      </div>
    </div>
  )
}

function normalizeSettings(settings) {
  return {
    closeBehavior: settings?.closeBehavior === 'exit' ? 'exit' : 'tray',
    autoRestore: settings?.autoRestore !== false,
    themeId: normalizeThemeId(settings?.themeId),
  }
}

function ExitOptionsTab({ draft, update }) {
  return (
    <>
      <section>
        <h3 style={sectionTitleStyle}>창 닫기 동작</h3>
        <p style={descStyle}>
          <kbd style={kbdStyle}>X</kbd> 버튼 또는 <kbd style={kbdStyle}>Alt+F4</kbd>를 눌렀을 때의 동작입니다.
        </p>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
          <RadioCard
            icon={MinusSquare}
            selected={draft.closeBehavior === 'tray'}
            onClick={() => update('closeBehavior', 'tray')}
            title="시스템 트레이로 최소화"
            desc="창만 숨기고 현재 클러스터 탭과 연결 상태를 유지합니다."
            color="var(--nimbus)"
          />
          <RadioCard
            icon={LogOut}
            selected={draft.closeBehavior === 'exit'}
            onClick={() => update('closeBehavior', 'exit')}
            title="즉시 완전 종료"
            desc="모든 클러스터 연결을 해제하고 저장된 세션을 삭제합니다."
            color="var(--red)"
          />
        </div>
      </section>

      <section>
        <h3 style={sectionTitleStyle}>다음 실행 시 자동 복원</h3>
        <p style={descStyle}>
          트레이로 숨긴 상태가 아닌 정상 종료 후에도 마지막 탭 구성을 복원할지 선택합니다.
        </p>
        <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
          <ToggleButton
            active={draft.autoRestore === true}
            onClick={() => update('autoRestore', true)}
            label="자동 복원"
            color="var(--nimbus)"
          />
          <ToggleButton
            active={draft.autoRestore === false}
            onClick={() => update('autoRestore', false)}
            label="복원 안 함"
            color="var(--red)"
          />
        </div>
        {draft.autoRestore === false && (
          <div style={{
            marginTop: 10, padding: '8px 12px',
            background: 'rgba(251,191,36,0.08)',
            border: '1px solid rgba(251,191,36,0.25)',
            borderRadius: 5, fontSize: 11, color: 'var(--text-mid)',
            display: 'flex', alignItems: 'center', gap: 8,
          }}>
            <RotateCw size={12} color="var(--yellow)" />
            저장된 세션은 유지하되, 재시작 시 빈 상태로 시작합니다.
          </div>
        )}
      </section>
    </>
  )
}

function SecurityTab({ vaultStatus, vaultSetAutoUnlock }) {
  const [busy, setBusy] = React.useState(false)
  const [msg, setMsg] = React.useState(null)   // {kind, text}

  if (vaultStatus?.available === false) {
    return (
      <section>
        <h3 style={sectionTitleStyle}>잠금 해제 방식</h3>
        <p style={descStyle}>이 빌드는 보안 보관함(암호화)을 사용하지 않습니다.</p>
      </section>
    )
  }

  const auto = vaultStatus?.has_dpapi === true

  async function choose(enable) {
    if (busy || enable === auto) return
    setBusy(true); setMsg(null)
    const r = await vaultSetAutoUnlock(enable)
    setBusy(false)
    setMsg(r?.ok
      ? { kind: 'ok', text: enable ? '자동 잠금 해제로 변경됨' : '매번 비밀번호 입력으로 변경됨' }
      : { kind: 'error', text: r?.error || '변경 실패' })
  }

  return (
    <section>
      <h3 style={sectionTitleStyle}>잠금 해제 방식</h3>
      <p style={descStyle}>
        프로그램을 열 때 보안 보관함(kubeconfig·SSH 접속정보·스냅샷)을 어떻게 해제할지 선택합니다.
        지금 바로 적용됩니다.
      </p>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
        <RadioCard
          icon={Lock}
          selected={!auto}
          onClick={() => choose(false)}
          title="매번 비밀번호 입력 (권장)"
          desc="가장 안전 · 실행할 때마다 마스터 비밀번호로 로그인합니다."
          color="var(--nimbus)"
        />
        <RadioCard
          icon={Unlock}
          selected={auto}
          onClick={() => choose(true)}
          title="자동 잠금 해제 (이 PC)"
          desc="비밀번호 생략 · 현재 Windows 계정(DPAPI)에서만 자동 해제됩니다. 다른 PC/계정에서는 비밀번호가 필요합니다."
          color="var(--blue)"
        />
      </div>
      {msg && (
        <div style={{
          marginTop: 10, padding: '8px 12px', borderRadius: 5, fontSize: 11.5,
          display: 'flex', alignItems: 'center', gap: 8,
          background: msg.kind === 'ok' ? 'rgba(52,211,153,0.1)' : 'rgba(239,68,68,0.1)',
          border: `1px solid ${msg.kind === 'ok' ? 'rgba(52,211,153,0.3)' : 'rgba(239,68,68,0.3)'}`,
          color: 'var(--text-mid)',
        }}>
          {msg.kind === 'ok'
            ? <Check size={12} color="var(--nimbus)" />
            : <AlertCircle size={12} color="var(--red)" />}
          {msg.text}
        </div>
      )}
      <p style={{ ...descStyle, marginTop: 12 }}>
        ※ 마스터 비밀번호 변경은 좌하단 <strong>보안 보관함</strong> 박스에서 할 수 있습니다.
      </p>
    </section>
  )
}

function DataFolderTab() {
  const [cur, setCur] = useState(null)        // {path, is_default, default}
  const [picked, setPicked] = useState('')    // 사용자가 고른 새 경로
  const [busy, setBusy] = useState(false)
  const [result, setResult] = useState(null)  // 변경 성공 결과 {old_dir, new_dir}
  const [err, setErr] = useState('')

  useEffect(() => {
    api.getDataDir().then(r => { if (r?.ok) setCur(r) }).catch(() => {})
  }, [])

  async function pickFolder() {
    setErr('')
    const p = await api.browseFolder(cur?.path || null)
    if (p) setPicked(p)
  }

  async function apply() {
    if (!picked) { setErr('새 폴더를 선택하세요.'); return }
    setBusy(true); setErr(''); setResult(null)
    const r = await api.changeDataDir(picked)
    setBusy(false)
    if (r?.ok) { setResult(r); setPicked('') }
    else setErr(r?.error || '변경 실패')
  }

  return (
    <section>
      <h3 style={sectionTitleStyle}>데이터 폴더 위치</h3>
      <p style={descStyle}>
        vault·kubeconfig·스냅샷·세션·로그 등 모든 데이터가 저장되는 폴더입니다.
        위치를 바꾸면 현재 파일을 새 폴더로 <strong>복사</strong>합니다.
      </p>

      <div style={{
        marginTop: 10, padding: '9px 12px', borderRadius: 6,
        background: 'var(--bg-3)', border: '1px solid var(--border)',
        fontSize: 11.5, fontFamily: 'var(--font-mono)', color: 'var(--text)',
        wordBreak: 'break-all',
      }}>
        {cur ? cur.path : '...'}
        {cur?.is_default && <span style={{ color: 'var(--text-dim)', fontFamily: 'var(--font)' }}> (기본값)</span>}
      </div>

      <div style={{ display: 'flex', gap: 8, marginTop: 10, alignItems: 'center' }}>
        <input
          value={picked}
          onChange={e => setPicked(e.target.value)}
          placeholder="새 폴더 경로 (또는 찾아보기)"
          disabled={busy}
          style={{
            flex: 1, padding: '7px 10px', boxSizing: 'border-box',
            background: 'var(--bg-3)', border: '1px solid var(--border)',
            borderRadius: 5, color: 'var(--text-bright)', fontSize: 11.5,
          }}
        />
        <button className="btn btn-default" onClick={pickFolder} disabled={busy} style={{ gap: 5, flexShrink: 0 }}>
          <FolderOpen size={13} /> 찾아보기
        </button>
        <button className="btn btn-primary" onClick={apply} disabled={busy || !picked} style={{ flexShrink: 0 }}>
          {busy ? '복사 중...' : '변경'}
        </button>
      </div>

      {err && (
        <div style={{
          marginTop: 10, padding: '8px 12px', borderRadius: 5, fontSize: 11.5,
          display: 'flex', alignItems: 'center', gap: 8,
          background: 'rgba(239,68,68,0.1)', border: '1px solid rgba(239,68,68,0.3)', color: 'var(--text-mid)',
        }}>
          <AlertCircle size={12} color="var(--red)" /> {err}
        </div>
      )}

      {result && (
        <div style={{
          marginTop: 10, padding: '11px 13px', borderRadius: 6, fontSize: 11.5, lineHeight: 1.7,
          background: 'rgba(251,191,36,0.08)', border: '1px solid rgba(251,191,36,0.3)', color: 'var(--text)',
        }}>
          <div style={{ fontWeight: 700, marginBottom: 4 }}>복사 완료 — 재시작 후 적용됩니다</div>
          <div>새 위치: <code>{result.new_dir}</code></div>
          <div style={{ marginTop: 6, color: 'var(--text-mid)' }}>
            기존 폴더는 자동 삭제되지 않습니다. 정상 동작을 확인한 뒤 아래 폴더를 직접 삭제하세요:
          </div>
          <div><code>{result.old_dir}</code></div>
        </div>
      )}
    </section>
  )
}

function ThemeTab({ selected, onSelect }) {
  return (
    <section>
      <h3 style={sectionTitleStyle}>테마 선택</h3>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(2, minmax(0, 1fr))',
        gap: 9,
      }}>
        {THEME_IDS.map(themeId => (
          <ThemeCard
            key={themeId}
            themeId={themeId}
            theme={THEMES[themeId]}
            selected={selected === themeId}
            onClick={() => onSelect(themeId)}
          />
        ))}
      </div>
    </section>
  )
}

function ThemeCard({ themeId, theme, selected, onClick }) {
  const tokens = theme.tokens
  const swatches = [
    tokens['--bg-1'],
    tokens['--bg-3'],
    tokens['--text'],
    tokens['--nimbus'],
    tokens['--blue'],
  ]
  return (
    <button
      onClick={onClick}
      aria-pressed={selected}
      style={{
        textAlign: 'left',
        padding: 12,
        minHeight: 104,
        background: selected ? 'var(--nimbus-dim)' : 'var(--bg-3)',
        border: `1px solid ${selected ? 'var(--nimbus)' : 'var(--border)'}`,
        borderRadius: 7,
        cursor: 'pointer',
        display: 'flex',
        flexDirection: 'column',
        gap: 10,
        transition: 'border-color 0.12s, background 0.12s',
      }}
    >
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8 }}>
        <div>
          <div style={{
            fontSize: 12.5,
            fontWeight: 800,
            color: selected ? 'var(--text-bright)' : 'var(--text)',
            marginBottom: 3,
          }}>
            {theme.label}
          </div>
          <div style={{ fontSize: 10.5, color: 'var(--text-dim)', lineHeight: 1.45 }}>
            {theme.tone}
          </div>
        </div>
        <div style={{
          width: 17, height: 17, borderRadius: '50%',
          border: `2px solid ${selected ? 'var(--nimbus)' : 'var(--border-bright)'}`,
          background: selected ? 'var(--nimbus)' : 'transparent',
          display: 'grid', placeItems: 'center',
          flexShrink: 0,
        }}>
          {selected && <Check size={10} color="var(--accent-ink)" strokeWidth={3} />}
        </div>
      </div>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(5, 1fr)',
        gap: 4,
        height: 24,
      }}>
        {swatches.map((color, i) => (
          <span
            key={`${themeId}-${color}-${i}`}
            style={{
              background: color,
              border: '1px solid rgba(255,255,255,0.12)',
              borderRadius: 4,
            }}
          />
        ))}
      </div>
    </button>
  )
}

function RadioCard({ icon: Icon, selected, onClick, title, desc, color }) {
  return (
    <button
      onClick={onClick}
      style={{
        textAlign: 'left',
        padding: '12px 14px',
        background: selected ? 'var(--nimbus-dim)' : 'var(--bg-3)',
        border: `1px solid ${selected ? color : 'var(--border)'}`,
        borderRadius: 7,
        cursor: 'pointer',
        display: 'flex', gap: 12, alignItems: 'flex-start',
        transition: 'all 0.12s',
        position: 'relative',
      }}
    >
      <div style={{
        width: 28, height: 28, borderRadius: 6,
        background: selected ? color : 'var(--bg-2)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0,
      }}>
        <Icon size={15} color={selected ? 'var(--accent-ink)' : 'var(--text-dim)'} />
      </div>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          fontSize: 12.5, fontWeight: 700,
          color: selected ? 'var(--text-bright)' : 'var(--text)',
          marginBottom: 3,
        }}>
          {title}
        </div>
        <div style={{ fontSize: 11, color: 'var(--text-dim)', lineHeight: 1.6 }}>
          {desc}
        </div>
      </div>
      <div style={{
        width: 16, height: 16, borderRadius: '50%',
        border: `2px solid ${selected ? color : 'var(--border-bright)'}`,
        background: selected ? color : 'transparent',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0, marginTop: 4,
      }}>
        {selected && <Check size={9} color="var(--accent-ink)" strokeWidth={3} />}
      </div>
    </button>
  )
}

function ToggleButton({ active, onClick, label, color }) {
  return (
    <button
      onClick={onClick}
      style={{
        padding: '7px 16px',
        background: active ? color : 'transparent',
        color: active ? 'var(--accent-ink)' : 'var(--text-dim)',
        border: `1px solid ${active ? color : 'var(--border)'}`,
        borderRadius: 5, cursor: 'pointer',
        fontSize: 12, fontWeight: 600,
        transition: 'all 0.1s',
      }}
    >
      {label}
    </button>
  )
}

const sectionTitleStyle = {
  fontSize: 11,
  fontWeight: 700,
  textTransform: 'uppercase',
  letterSpacing: '0.07em',
  color: 'var(--text-dim)',
  marginBottom: 5,
  marginTop: 0,
}

const descStyle = {
  fontSize: 11.5,
  color: 'var(--text-mid)',
  lineHeight: 1.6,
  margin: 0,
}

const kbdStyle = {
  display: 'inline-block',
  padding: '0 5px',
  background: 'var(--bg-3)',
  border: '1px solid var(--border)',
  borderRadius: 3,
  color: 'var(--text)',
  fontFamily: 'var(--font-mono)',
  fontSize: 10,
}
