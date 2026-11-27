import React, { useState } from 'react'
import {
  CUSTOM_PRESETS, TOKEN_LABELS, TOKEN_ORDER,
  contrast, customWarnings, isLightColor, makeCustomTokens, normalizeCustom,
} from '../customTheme.js'

/**
 * 커스텀 테마 편집기 (v1.3.34).
 *
 * ## 왜 세 색만 먼저 묻는가
 *
 * 토큰이 25개인데 다 물어보면 고르다 지치고, 무엇보다 **읽을 수 없는 조합**이
 * 쉽게 나온다. 그래서 배경·글자·강조 셋만 받고 나머지는 관계로 만든다.
 * 끝까지 만지고 싶으면 아래 「하나씩 직접 고르기」를 펼치면 된다.
 *
 * ## 대비를 계산해서 알려 준다
 *
 * 밝은 배경을 처음 써 보면 「글자가 잘 안 보인다」가 거의 반드시 한 번은 나온다.
 * 막지는 않되(취향이니까) **수치로 알려는 준다** — WCAG 본문 기준 4.5:1.
 */
export default function CustomThemeEditor({ value, onChange }) {
  const cfg = normalizeCustom(value)
  const [advanced, setAdvanced] = useState(false)
  const tokens = makeCustomTokens(cfg)
  const warnings = customWarnings(cfg)
  const ratio = contrast(cfg.bg, cfg.text)

  const set = (patch) => onChange({ ...cfg, ...patch })
  const setOverride = (token, hex) => {
    const next = { ...cfg.overrides }
    if (hex) next[token] = hex
    else delete next[token]
    onChange({ ...cfg, overrides: next })
  }

  return (
    <div style={{ marginTop: 14 }}>
      <div style={{ ...rowLabel, marginBottom: 7 }}>빠른 시작</div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 14 }}>
        {CUSTOM_PRESETS.map(p => {
          const on = p.bg === cfg.bg && p.text === cfg.text && p.accent === cfg.accent
          return (
            <button key={p.id} type="button"
              onClick={() => onChange({ bg: p.bg, text: p.text, accent: p.accent, overrides: {} })}
              title={`${p.bg} · ${p.text} · ${p.accent}`}
              style={{
                display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer',
                padding: '5px 9px', borderRadius: 6, fontSize: 11.5,
                fontFamily: 'var(--font)',
                background: on ? 'var(--nimbus-dim)' : 'var(--bg-3)',
                color: 'var(--text)',
                border: `1px solid ${on ? 'var(--nimbus)' : 'var(--border)'}`,
              }}>
              <span style={{
                width: 13, height: 13, borderRadius: 3, flexShrink: 0,
                background: p.bg, border: '1px solid rgba(0,0,0,0.35)',
              }} />
              {p.label}
            </button>
          )
        })}
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, minmax(0,1fr))', gap: 10 }}>
        <ColorField label="배경" hint="바탕이 되는 면" value={cfg.bg}
          onChange={v => set({ bg: v })} />
        <ColorField label="글자" hint="본문 글자색" value={cfg.text}
          onChange={v => set({ text: v })} />
        <ColorField label="강조" hint="버튼 · 선택 표시" value={cfg.accent}
          onChange={v => set({ accent: v })} />
      </div>

      <div style={{
        marginTop: 10, fontSize: 10.5, lineHeight: 1.6,
        color: ratio < 4.5 ? 'var(--yellow)' : 'var(--text-dim)',
      }}>
        글자 대비 <b>{ratio.toFixed(1)}:1</b>
        {ratio >= 7 ? ' — 아주 좋습니다.'
          : ratio >= 4.5 ? ' — 본문으로 쓰기 충분합니다.'
            : ' — 권장(4.5:1)보다 낮습니다.'}
        {' '}지금은 <b>{isLightColor(cfg.bg) ? '밝은' : '어두운'}</b> 테마로 계산됩니다.
      </div>
      {warnings.map((w, i) => (
        <div key={i} style={{ marginTop: 5, fontSize: 10.5, color: 'var(--yellow)' }}>· {w}</div>
      ))}

      <Preview tokens={tokens} />

      <button type="button" onClick={() => setAdvanced(a => !a)} style={{
        marginTop: 12, padding: '5px 10px', fontSize: 11, cursor: 'pointer',
        borderRadius: 5, background: 'var(--bg-3)', color: 'var(--text)',
        border: '1px solid var(--border)', fontFamily: 'var(--font)',
      }}>
        {advanced ? '▾' : '▸'} 하나씩 직접 고르기 ({TOKEN_ORDER.length}개)
      </button>

      {advanced && (
        <div style={{ marginTop: 10 }}>
          <div style={{ fontSize: 10.5, color: 'var(--text-dim)', lineHeight: 1.6, marginBottom: 8 }}>
            비워 두면 위의 세 색에서 <b>자동으로 만든 값</b>을 씁니다. 여기서 고른 색만
            그 위에 덮어씁니다.
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, minmax(0,1fr))', gap: 6 }}>
            {TOKEN_ORDER.map(tk => (
              <TokenRow key={tk} token={tk} label={TOKEN_LABELS[tk]}
                derived={tokens[tk]} override={cfg.overrides[tk] || ''}
                onChange={hex => setOverride(tk, hex)} />
            ))}
          </div>
          {Object.keys(cfg.overrides).length > 0 && (
            <button type="button" onClick={() => onChange({ ...cfg, overrides: {} })}
              style={{
                marginTop: 9, padding: '4px 9px', fontSize: 10.5, cursor: 'pointer',
                borderRadius: 5, background: 'var(--bg-3)', color: 'var(--text-mid)',
                border: '1px solid var(--border)', fontFamily: 'var(--font)',
              }}>
              직접 고른 {Object.keys(cfg.overrides).length}개 되돌리기
            </button>
          )}
        </div>
      )}
    </div>
  )
}

function ColorField({ label, hint, value, onChange }) {
  return (
    <label style={{ display: 'block' }}>
      <div style={rowLabel}>{label}</div>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 6, marginTop: 4,
        background: 'var(--bg-3)', border: '1px solid var(--border)',
        borderRadius: 6, padding: 4,
      }}>
        <input type="color" value={value} onChange={e => onChange(e.target.value)}
          style={{
            width: 28, height: 24, padding: 0, border: 'none', borderRadius: 4,
            background: 'transparent', cursor: 'pointer', flexShrink: 0,
          }} />
        <input type="text" value={value} onChange={e => onChange(e.target.value)}
          spellCheck={false}
          style={{
            flex: 1, minWidth: 0, border: 'none', background: 'transparent',
            color: 'var(--text)', fontFamily: 'var(--font-mono)', fontSize: 11,
            outline: 'none',
          }} />
      </div>
      <div style={{ fontSize: 10, color: 'var(--text-dim)', marginTop: 3 }}>{hint}</div>
    </label>
  )
}

function TokenRow({ token, label, derived, override, onChange }) {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6,
      padding: '3px 5px', borderRadius: 5,
      background: override ? 'var(--nimbus-dim)' : 'transparent',
    }}>
      <input type="color" value={override || derived}
        onChange={e => onChange(e.target.value)}
        title={token}
        style={{
          width: 22, height: 20, padding: 0, border: 'none', borderRadius: 3,
          background: 'transparent', cursor: 'pointer', flexShrink: 0,
        }} />
      <span style={{
        flex: 1, minWidth: 0, fontSize: 10.5, color: 'var(--text)',
        overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
      }} title={token}>{label}</span>
      {override && (
        <button type="button" onClick={() => onChange('')} title="자동값으로 되돌리기"
          style={{
            border: 'none', background: 'transparent', color: 'var(--text-dim)',
            cursor: 'pointer', fontSize: 12, lineHeight: 1, padding: '0 2px',
          }}>×</button>
      )}
    </div>
  )
}

/** 실제 화면 조각을 그대로 흉내 낸 미리보기 — 색만 봐서는 감이 안 온다. */
function Preview({ tokens }) {
  const v = k => tokens[k]
  return (
    <div style={{
      marginTop: 12, borderRadius: 8, overflow: 'hidden',
      border: `1px solid ${v('--border')}`, background: v('--bg-0'),
    }}>
      <div style={{
        display: 'flex', alignItems: 'center', gap: 7, padding: '7px 10px',
        background: v('--bg-2'), borderBottom: `1px solid ${v('--border')}`,
      }}>
        <span style={{ width: 9, height: 9, borderRadius: '50%', background: v('--nimbus') }} />
        <span style={{ fontSize: 11.5, fontWeight: 700, color: v('--text-bright') }}>미리보기</span>
        <span style={{ marginLeft: 'auto', fontSize: 10, color: v('--text-dim') }}>사이드바 · 본문 · 버튼</span>
      </div>
      <div style={{ display: 'flex', minHeight: 92 }}>
        <div style={{
          width: 96, padding: 8, background: v('--bg-1'),
          borderRight: `1px solid ${v('--border')}`,
        }}>
          <div style={{
            fontSize: 10.5, color: v('--text-bright'), background: v('--bg-3'),
            borderRadius: 4, padding: '4px 6px', marginBottom: 4,
          }}>대시보드</div>
          <div style={{ fontSize: 10.5, color: v('--text-dim'), padding: '4px 6px' }}>토폴로지</div>
          <div style={{ fontSize: 10.5, color: v('--text-dim'), padding: '4px 6px' }}>이벤트</div>
        </div>
        <div style={{ flex: 1, padding: 10, background: v('--bg-1') }}>
          <div style={{ fontSize: 12, color: v('--text'), marginBottom: 3 }}>
            본문 글자입니다.
          </div>
          <div style={{ fontSize: 10.5, color: v('--text-dim'), marginBottom: 8 }}>
            설명은 이 정도 밝기로 보입니다.
          </div>
          <div style={{ display: 'flex', gap: 6, alignItems: 'center', flexWrap: 'wrap' }}>
            <span style={{
              padding: '3px 9px', borderRadius: 5, fontSize: 11, fontWeight: 700,
              background: v('--nimbus'), color: v('--accent-ink'),
            }}>연결</span>
            <span style={{
              padding: '3px 9px', borderRadius: 5, fontSize: 11,
              background: v('--bg-3'), color: v('--text'),
              border: `1px solid ${v('--border-bright')}`,
            }}>취소</span>
            <span style={{ fontSize: 10.5, color: v('--green') }}>● 실행 중</span>
            <span style={{ fontSize: 10.5, color: v('--yellow') }}>● 경고</span>
            <span style={{ fontSize: 10.5, color: v('--red') }}>● 오류</span>
          </div>
        </div>
      </div>
    </div>
  )
}

const rowLabel = {
  fontSize: 11, fontWeight: 700, color: 'var(--text-mid)',
}
