import React, { useEffect, useState, useRef } from 'react'
import { useApp } from '../store.jsx'
import { api } from '../api.js'
import { canRequireHello } from '../vaultGate.js'
import { claudeConfig, claudeEntry, claudeGuide, CLAUDE_STEPS } from '../mcpConfig.js'
import { applyTheme, normalizeThemeId, installThemeStyles, THEME_IDS, THEMES, CUSTOM_THEME_ID } from '../themeRegistry.js'
import { normalizeCustom, makeCustomTokens } from '../customTheme.js'
import CustomThemeEditor from './CustomThemeEditor.jsx'
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
  Share2,
  Download,
  Upload,
  X,
  BellRing,
  Loader2,
  AlertTriangle,
  LayoutGrid,
  NotebookText,
  Send,
  Boxes,
  TerminalSquare,
  Cloud, ClipboardCheck, Sparkles,
} from 'lucide-react'

const TABS = [
  { id: 'exit', label: '종료 · 복원', icon: SettingsIcon },
  { id: 'security', label: '보안 잠금', icon: KeyRound },
  { id: 'data', label: '데이터 폴더', icon: FolderCog },
  { id: 'theme', label: '배경 테마', icon: Palette },
  { id: 'notifications', label: '알림', icon: BellRing },
]

export default function SettingsModal() {
  const { setShowSettings, settings, saveSettings,
          vaultStatus, vaultSetAutoUnlock, settingsTab, setSettingsTab } = useApp()
  const [draft, setDraft] = useState(() => normalizeSettings(settings))
  // 특정 탭으로 열라는 요청이 있으면 그 탭으로 (한 번만)
  const [activeTab, setActiveTab] = useState(() =>
    TABS.some(t => t.id === settingsTab) ? settingsTab : 'exit')
  useEffect(() => { if (settingsTab) setSettingsTab(null) }, [])  // eslint-disable-line react-hooks/exhaustive-deps
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setDraft(normalizeSettings(settings))
  }, [settings])

  useEffect(() => {
    // 커스텀 색을 먼저 심고 테마를 적용해야 고른 즉시 보인다
    installThemeStyles(undefined, normalizeCustom(draft.customTheme))
    applyTheme(draft.themeId)
  }, [draft.themeId, draft.customTheme])

  function closeWithoutSave() {
    installThemeStyles(undefined, normalizeCustom(settings.customTheme))
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
      {/* 탭이 6개라 560px 에서는 글자가 한 글자씩 쪼개져 내려갔다(v1.2.171).
          창을 넓히고, 아래 탭 버튼에 nowrap+flexShrink:0 을 줘서 탭이 늘어도
          다시는 글자가 갈라지지 않게 했다.
          v1.3.52: 탭이 늘자 680px 에서 마지막 탭이 가로 스크롤 뒤로
          숨었다(사용자 신고) — 800px 로 넓히고, 창이 그보다 좁으면 스크롤 대신 줄을 바꾼다. */}
      <div className="modal" style={{ width: 800, maxWidth: '94vw' }}>
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
          flexShrink: 0,   // .modal 이 flex 컬럼 — 탭 줄이 눌리지 않게 고정
          // 넘치면 가로 스크롤(옛 방식) 대신 **다음 줄로** — 스크롤 뒤에 숨은 탭은
          // 있는 줄도 모른다(v1.3.52). 글자는 탭 안에서 갈라지지 않는다(nowrap).
          flexWrap: 'wrap', rowGap: 4,
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
                  padding: '8px 11px',
                  whiteSpace: 'nowrap', flexShrink: 0,   // 글자가 갈라지지 않게
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
            <ThemeTab selected={draft.themeId} onSelect={themeId => update('themeId', themeId)}
              custom={draft.customTheme} onCustom={v => update('customTheme', v)} />
          )}
          {activeTab === 'notifications' && (
            <NotificationsTab value={draft.notifications} onChange={v => update('notifications', v)} />
          )}
        </div>

        <div className="modal-footer">
          {/* 오픈소스 고지 — 설치 폴더의 THIRD_PARTY_NOTICES.txt 를 연다 */}
          <button className="btn btn-ghost btn-sm" style={{ marginRight: 'auto' }}
            onClick={() => api.openThirdPartyNotices()}>
            오픈소스 고지
          </button>
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
    customTheme: normalizeCustom(settings?.customTheme),
    notifications: {
      enabled: !!settings?.notifications?.enabled,
      tray: settings?.notifications?.tray !== false,
      webhookUrl: settings?.notifications?.webhookUrl || '',
    },
  }
}

// ── 알림 탭 — 이벤트(Warning) → 트레이 풍선알림 / 웹훅 ──────────────────────────
function NotificationsTab({ value, onChange }) {
  const n = value || { enabled: false, tray: true, webhookUrl: '' }
  const [testResult, setTestResult] = useState(null)
  const [testing, setTesting] = useState(false)

  function set(key, v) {
    onChange({ ...n, [key]: v })
  }

  async function runTest() {
    setTesting(true); setTestResult(null)
    try {
      const r = await api.testWebhook(n.webhookUrl)
      setTestResult(r)
    } catch (e) {
      setTestResult({ ok: false, error: String(e) })
    }
    setTesting(false)
  }

  return (
    <div>
      <label style={{ display: 'flex', alignItems: 'flex-start', gap: 10, cursor: 'pointer' }}>
        <input type="checkbox" checked={n.enabled} onChange={e => set('enabled', e.target.checked)}
          style={{ marginTop: 2 }} />
        <div>
          <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)' }}>알림 사용</div>
          <div style={{ fontSize: 11.5, color: 'var(--text-dim)', marginTop: 2, lineHeight: 1.5 }}>
            활성 클러스터에 새로운 Warning 이벤트가 나타나면 알려줍니다(약 15초 주기 점검).
            같은 이슈가 반복(횟수만 증가)되면 다시 알리지 않습니다.
          </div>
        </div>
      </label>

      {n.enabled && (
        <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--border)',
          display: 'flex', flexDirection: 'column', gap: 12 }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
            <input type="checkbox" checked={n.tray} onChange={e => set('tray', e.target.checked)} />
            <span style={{ fontSize: 12.5 }}>트레이 풍선 알림 (Windows)</span>
          </label>

          <div>
            <div style={{ fontSize: 11, color: 'var(--text-dim)', marginBottom: 4 }}>
              웹훅 URL (선택 — Slack/Discord/Teams 등 incoming webhook 호환)
            </div>
            <div style={{ display: 'flex', gap: 6 }}>
              <input className="input" value={n.webhookUrl}
                onChange={e => { set('webhookUrl', e.target.value); setTestResult(null) }}
                placeholder="https://hooks.slack.com/services/..."
                style={{ flex: 1, minWidth: 0, fontSize: 12, fontFamily: 'var(--font-mono)' }} />
              <button className="btn btn-default btn-sm" onClick={runTest}
                disabled={!n.webhookUrl?.trim() || testing} style={{ flexShrink: 0, gap: 4, whiteSpace: 'nowrap' }}>
                {testing ? <Loader2 size={12} className="spin" /> : null}
                {testing ? '전송 중…' : '테스트 전송'}
              </button>
            </div>
            {testResult && (
              <div style={{ fontSize: 10.5, marginTop: 5,
                color: testResult.ok ? 'var(--nimbus)' : '#f87171' }}>
                {testResult.ok ? '✓ 전송 성공 — 대상 채널을 확인하세요.' : `✗ ${testResult.error || '전송 실패'}`}
              </div>
            )}
            <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 6, lineHeight: 1.5 }}>
              ⚠️ 외부 URL 로 설정하면 이벤트 요약(네임스페이스/이름/사유/메시지)이 해당 서버로
              전송됩니다. 신뢰하는 대상만 사용하세요.
            </div>
          </div>
        </div>
      )}
    </div>
  )
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

  // Windows Hello 요구 (v1.2.167) — 자동 해제를 켠 경우에만 의미가 있다.
  // Hello 는 확인만 하고 복호화는 DPAPI 가 하므로, 자동 해제가 꺼져 있으면 걸 곳이 없다.
  const [hello, setHello] = useState(null)
  const refreshHello = React.useCallback(() => {
    api.helloStatus().then(r => setHello(r?.ok ? r : null)).catch(() => setHello(null))
  }, [])
  useEffect(() => { refreshHello() }, [refreshHello, auto])

  async function toggleHello(enable) {
    setBusy(true); setMsg(null)
    const r = await api.vaultSetRequireHello(enable)
    setBusy(false)
    setMsg(r?.ok
      ? { kind: 'ok', text: enable
          ? 'Windows Hello 확인을 요구합니다 (다음 실행부터)'
          : 'Windows Hello 요구를 해제했습니다' }
      : { kind: 'error', text: r?.error || '변경 실패' })
    refreshHello()
  }

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
        프로그램을 열 때 보안 보관함(kubeconfig·스냅샷)을 어떻게 해제할지 선택합니다.
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
      {/* Windows Hello 요구 (v1.2.167) */}
      {auto && (
        <div style={{ marginTop: 10, padding: '9px 11px', borderRadius: 6,
                      background: 'var(--bg-2)', border: '1px solid var(--border)' }}>
          <label style={{ display: 'flex', alignItems: 'center', gap: 7, fontSize: 12,
                           cursor: canRequireHello(hello) ? 'pointer' : 'not-allowed' }}>
            <input type="checkbox" checked={!!hello?.required} disabled={busy || !canRequireHello(hello)}
              onChange={e => toggleHello(e.target.checked)}
              style={{ accentColor: 'var(--nimbus)' }} />
            <span style={{ color: 'var(--text-bright)' }}>
              자동 해제 전에 Windows Hello 확인
            </span>
          </label>
          <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 4, marginLeft: 21,
                        lineHeight: 1.5 }}>
            {hello?.available
              ? '켜면 프로그램을 열 때 얼굴·지문·PIN 확인을 먼저 받습니다. 자동 해제만 켜두면 이 PC 에 앉은 사람은 누구나 접속정보를 볼 수 있습니다. (확인만 Hello 가 하고 복호화는 종전대로 이 PC 의 키로 합니다 — 별도 암호 계층이 아닙니다.)'
              : `이 PC 에서는 Windows Hello 를 쓸 수 없습니다 (${hello?.state || '확인 실패'}).`}
          </div>
        </div>
      )}

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

      <McpTokenSection vaultStatus={vaultStatus} />
    </section>
  )
}

// ── MCP 액세스 토큰 (v1.2.119) ───────────────────────────────────────────────
// 위 "자동 잠금 해제"(DPAPI)는 Polaris 앱 전용이다. 외부 AI 가 MCP 로 붙을 때는
// DPAPI 를 쓰지 않고 여기서 발급한 토큰을 제시해야만 보관함이 열린다.
export function McpTokenSection({ vaultStatus }) {
  const [tokens, setTokens] = useState([])
  const [issued, setIssued] = useState('')      // 방금 발급된 전체 토큰 (1회 표시)
  const [launch, setLaunch] = useState(null)    // 이 PC 의 실제 실행 경로(v1.5.55) — Claude Desktop 설정을 통째로 만든다
  const [copied, setCopied] = useState(false)
  const [label, setLabel] = useState('')
  const scope = 'read'   // 이 판의 MCP 는 조회 전용
  const [days, setDays] = useState(90)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')

  const unlocked = vaultStatus?.unlocked === true

  const reload = React.useCallback(() => {
    api.vaultListMcpTokens()
      .then(r => setTokens(r?.tokens || []))
      .catch(() => setTokens([]))
  }, [])

  useEffect(() => { reload() }, [reload])

  async function issue() {
    setBusy(true); setErr(''); setCopied(false)
    try {
      const r = await api.vaultIssueMcpToken(label, scope, Number(days) || 0)
      if (r?.ok) {
        setIssued(r.token)
        setLaunch(r.launch || null)
        setTokens(r.tokens || [])
        setLabel('')
      } else {
        setErr(r?.error || '발급 실패')
      }
    } catch (e) { setErr(String(e)) }
    setBusy(false)
  }

  async function revoke(id) {
    if (!window.confirm(`토큰 ${id} 을(를) 폐기할까요?\n이 토큰을 쓰던 AI 연결은 즉시 끊깁니다.`)) return
    const r = await api.vaultRevokeMcpToken(id)
    if (r?.ok) setTokens(r.tokens || [])
    else setErr(r?.error || '폐기 실패')
  }

  function copyIssued(what = 'token') {
    const text = what === 'config' ? claudeConfig(launch, issued) : what === 'entry' ? claudeEntry(launch, issued)
      : what === 'guide' ? claudeGuide(launch) : issued
    navigator.clipboard?.writeText(text)
      .then(() => setCopied(what))
      .catch(() => setCopied(false))
  }

  return (
    <div style={{ marginTop: 22, paddingTop: 16, borderTop: '1px solid var(--border)' }}>
      <h3 style={sectionTitleStyle}>MCP 액세스 토큰</h3>
      <p style={descStyle}>
        Claude 등 외부 AI가 <strong>MCP</strong>로 Polaris에 붙을 때 쓰는 인증 수단입니다.
        위의 자동 잠금 해제와 무관하게, <strong>MCP는 이 토큰이 있어야만</strong> 보관함을 엽니다.
        토큰은 발급 직후 한 번만 보이며 개별 폐기할 수 있습니다.
      </p>

      {!unlocked && (
        <div style={{ ...noteBoxStyle, borderColor: 'rgba(251,191,36,0.35)',
                      background: 'rgba(251,191,36,0.08)' }}>
          <AlertCircle size={12} color="var(--amber, #fbbf24)" />
          보안 보관함이 잠겨 있어 발급할 수 없습니다. 먼저 잠금을 해제하세요.
        </div>
      )}

      {/* 발급 폼 */}
      <div style={{ display: 'flex', gap: 6, alignItems: 'center', marginTop: 10, flexWrap: 'wrap' }}>
        <input className="input" value={label} onChange={e => setLabel(e.target.value)}
          placeholder="용도 메모 (예: claude-desktop)" maxLength={60}
          style={{ flex: 1, minWidth: 170, fontSize: 12 }} />
        <span style={{ fontSize: 11.5, color: 'var(--text-dim)', whiteSpace: 'nowrap' }}>조회 전용</span>
        <select className="input" value={days} onChange={e => setDays(e.target.value)}
          style={{ fontSize: 12, width: 110 }}>
          <option value={30}>30일</option>
          <option value={90}>90일</option>
          <option value={365}>1년</option>
          <option value={0}>만료 없음</option>
        </select>
        <button className="btn btn-primary btn-sm" onClick={issue} disabled={busy || !unlocked}
          style={{ gap: 4, whiteSpace: 'nowrap' }}>
          {busy ? <Loader2 size={12} className="spin" /> : <KeyRound size={12} />} 토큰 발급
        </button>
      </div>

      {/* 방금 발급된 토큰 — 1회 표시 */}
      {issued && (
        <div style={{
          marginTop: 10, padding: '10px 12px', borderRadius: 6,
          background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.35)',
        }}>
          <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--nimbus)', marginBottom: 6 }}>
            발급되었습니다 — 이 화면을 닫으면 다시 볼 수 없습니다. 지금 복사하세요.
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center' }}>
            <code style={{
              flex: 1, minWidth: 0, fontSize: 11, fontFamily: 'var(--font-mono)',
              background: 'var(--bg-3)', padding: '6px 8px', borderRadius: 4,
              wordBreak: 'break-all', color: 'var(--text-bright)',
            }}>{issued}</code>
            <button className="btn btn-default btn-sm" onClick={() => copyIssued('token')}
              style={{ flexShrink: 0, gap: 4 }}>
              {copied === 'token' ? <Check size={12} /> : <Share2 size={12} />}{copied === 'token' ? '복사됨' : '토큰만 복사'}
            </button>
          </div>
          {launch?.command && (
            <div style={{ marginTop: 10 }}>
              <div style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--text-bright)', marginBottom: 4 }}>
                Claude Desktop 에 연결 — 이 PC 의 실제 설치 경로와 토큰이 들어간 설정을 복사합니다
              </div>
              <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                <button className="btn btn-primary btn-sm" onClick={() => copyIssued('config')} style={{ gap: 4 }}>
                  {copied === 'config' ? <Check size={12} /> : <Share2 size={12} />}{copied === 'config' ? '복사됨' : '설정 전체 복사'}
                </button>
                <button className="btn btn-default btn-sm" onClick={() => copyIssued('entry')} style={{ gap: 4 }}>
                  {copied === 'entry' ? <Check size={12} /> : <Share2 size={12} />}{copied === 'entry' ? '복사됨' : '항목만 복사(다른 MCP 서버가 있을 때)'}
                </button>
                <button className="btn btn-ghost btn-sm" onClick={() => copyIssued('guide')} style={{ gap: 4 }}
                  title="아래 연결 순서를 글로 복사합니다(토큰은 빠집니다)">
                  {copied === 'guide' ? <Check size={12} /> : <Share2 size={12} />}{copied === 'guide' ? '복사됨' : '안내 복사'}
                </button>
              </div>
              <ol style={{ margin: '6px 0 0', paddingLeft: 18, fontSize: 10.5, color: 'var(--text-mid)', lineHeight: 1.6 }}>
                {CLAUDE_STEPS.map((t, i) => <li key={i}>{t}</li>)}
              </ol>
              <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 4, fontFamily: 'var(--font-mono)', wordBreak: 'break-all' }}>
                실행 경로: {launch.command}
              </div>
            </div>
          )}
          <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 6, lineHeight: 1.5 }}>
            토큰은 <b>이 PC 의 보안 보관함</b>에 묶여 있어 다른 PC 에서는 열리지 않습니다 — PC 마다 그 PC 의 Polaris 에서 발급하세요.
            설정 파일에는 토큰이 평문으로 들어가므로 캡처·공유에 주의하세요.
          </div>
          <button className="btn btn-ghost btn-sm" onClick={() => { setIssued(''); setCopied(false) }}
            style={{ marginTop: 6 }}>확인했습니다</button>
        </div>
      )}

      {err && (
        <div style={{ ...noteBoxStyle, borderColor: 'rgba(239,68,68,0.3)',
                      background: 'rgba(239,68,68,0.08)' }}>
          <AlertCircle size={12} color="var(--red)" /> {err}
        </div>
      )}

      {/* 발급된 토큰 목록 */}
      <div style={{ marginTop: 12 }}>
        {tokens.length === 0 ? (
          <div style={{ fontSize: 11.5, color: 'var(--text-dim)' }}>발급된 토큰이 없습니다.</div>
        ) : tokens.map(t => (
          <div key={t.id} style={{
            display: 'flex', alignItems: 'center', gap: 10, padding: '7px 10px',
            borderBottom: '1px solid var(--border)', fontSize: 11.5,
          }}>
            <code style={{ fontFamily: 'var(--font-mono)', color: 'var(--text-mid)' }}>{t.id}</code>
            <span style={{ flex: 1, minWidth: 0, overflow: 'hidden', textOverflow: 'ellipsis',
                           whiteSpace: 'nowrap', color: 'var(--text)' }}>
              {t.label || '(메모 없음)'}
            </span>
            <span style={{
              fontSize: 10, padding: '1px 6px', borderRadius: 3, flexShrink: 0,
              background: t.scope === 'write' ? 'rgba(239,68,68,0.15)' : 'rgba(96,165,250,0.15)',
              color: t.scope === 'write' ? '#fca5a5' : '#93c5fd',
            }}>{t.scope === 'write' ? '변경 가능' : '조회 전용'}</span>
            {t.expired && (
              <span style={{ fontSize: 10, color: 'var(--red)', flexShrink: 0 }}>만료됨</span>
            )}
            <span style={{ fontSize: 10, color: 'var(--text-dim)', flexShrink: 0 }}>
              {t.last_used_at ? `최근 사용 ${t.last_used_at.slice(0, 10)}` : '미사용'}
            </span>
            <button className="btn btn-ghost btn-sm" onClick={() => revoke(t.id)}
              title="이 토큰 폐기" style={{ flexShrink: 0, padding: '2px 6px' }}>
              <X size={12} />
            </button>
          </div>
        ))}
      </div>
    </div>
  )
}

const noteBoxStyle = {
  marginTop: 10, padding: '8px 12px', borderRadius: 5, fontSize: 11.5,
  display: 'flex', alignItems: 'center', gap: 8,
  border: '1px solid', color: 'var(--text-mid)', lineHeight: 1.5,
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

function ThemeTab({ selected, onSelect, custom, onCustom }) {
  const liveCustom = makeCustomTokens(normalizeCustom(custom))
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
            theme={themeId === CUSTOM_THEME_ID
              ? { ...THEMES[themeId], tokens: liveCustom }
              : THEMES[themeId]}
            selected={selected === themeId}
            onClick={() => onSelect(themeId)}
          />
        ))}
      </div>
      {selected === CUSTOM_THEME_ID && (
        <CustomThemeEditor value={custom} onChange={onCustom} />
      )}
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
