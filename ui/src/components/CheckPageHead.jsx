/**
 * CHECK 화면 공통 머리 (v1.5.60, 사용자 결정 「넣기」).
 *
 * 화면마다 제각각이던 두세 줄 설명을 한 모양으로 맞춘다 — 제목 · 대상 · 결과물 · 「조회만」 표시와
 * 무엇을 하는 화면인지 한 줄. 글은 checkPages.js 의 line · target · output 을 그대로 쓰므로
 * 메뉴와 화면 머리가 어긋나지 않는다. 화면별 주의 사항(배포판 차이 · 계정 권한 등)은 children 으로
 * 넘기면 「자세히」 아래에 접어 둔다.
 */
import React, { useState } from 'react'
import { ChevronDown, ChevronRight } from 'lucide-react'
import { checkPage } from '../checkPages.js'

const tag = {
  fontSize: 10.5, padding: '1px 7px', borderRadius: 10, border: '1px solid var(--border)',
  color: 'var(--text-mid)', whiteSpace: 'nowrap', lineHeight: 1.6,
}

const dim = { color: 'var(--text-dim)', marginRight: 2 }

export default function CheckPageHead({ page, icon: Icon, actions, children, style }) {
  const meta = checkPage(page) || {}
  const [open, setOpen] = useState(false)
  return (
    <div style={{ display: 'flex', alignItems: 'flex-start', gap: 10, marginBottom: 12, ...style }}>
      {Icon && <Icon size={20} color="var(--nimbus)" style={{ marginTop: 2, flexShrink: 0 }} />}
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap' }}>
          <h1 style={{ fontSize: 15, fontWeight: 700, color: 'var(--text-bright)', margin: '0 4px 0 0' }}>{meta.label}</h1>
          {meta.target && <span style={tag}><span style={dim}>대상</span> {meta.target}</span>}
          {meta.output && <span style={tag}><span style={dim}>결과</span> {meta.output}</span>}
          <span style={{ ...tag, color: 'var(--green)', borderColor: 'var(--green)' }}
                title="대상의 설정 · 데이터를 바꾸지 않고 조회 명령만 실행합니다">조회만</span>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-mid)', marginTop: 4, lineHeight: 1.55 }}>
          {meta.line}
          {children && (
            <button type="button" onClick={() => setOpen(o => !o)}
                    style={{ marginLeft: 6, background: 'none', border: 'none', padding: 0, cursor: 'pointer',
                             color: 'var(--nimbus)', fontSize: 11.5, display: 'inline-flex', alignItems: 'center', gap: 2 }}>
              {open ? <ChevronDown size={11} /> : <ChevronRight size={11} />} 자세히
            </button>
          )}
        </div>
        {open && children && (
          <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 6, lineHeight: 1.6 }}>{children}</div>
        )}
      </div>
      {actions}
    </div>
  )
}
