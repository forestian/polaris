import CheckPageHead from '../components/CheckPageHead.jsx'
import React, { useState, useEffect } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { ArrowUpCircle, Play, Loader2, AlertTriangle, CheckCircle2, Info, Copy, ChevronDown, ChevronRight, ListChecks, XCircle, Save } from 'lucide-react'
import { saveReport } from '../saveReport.js'
import { verdictText, SEV_STYLE, CATEGORY_KO, resultText } from '../upgradeModel.js'

/**
 * CHECK → 업그레이드 사전 점검 (v1.4.1).
 *
 * 목표 버전으로 올리기 전에 막히거나 서비스가 끊길 곳을 찾는다 — 사라지는 API · 버전 차이 ·
 * 노드 비우기 방해 · 지금 상태 · 애드온. 클러스터는 바꾸지 않는다. 판정은 백엔드(src/upgradecheck.py).
 */

// 탭을 오가도 결과를 유지한다 — 클러스터가 바뀌면(switchKey) 버린다
const _cache = { key: null, versions: null, target: '', result: null }

export default function UpgradeCheckPage() {
  const { clusterSwitchKey } = useApp()
  const fresh = _cache.key === clusterSwitchKey
  const [versions, setVersions] = useState(fresh ? _cache.versions : null)
  const [target, setTarget] = useState(fresh ? _cache.target : '')
  const [result, setResult] = useState(fresh ? _cache.result : null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState('')
  const [saving, setSaving] = useState(false)
  const [msg, setMsg] = useState(null)

  useEffect(() => { Object.assign(_cache, { key: clusterSwitchKey, versions, target, result }) },
            [clusterSwitchKey, versions, target, result])

  useEffect(() => {
    if (versions) return
    api.upgradeCheckVersions().then(r => {
      if (!r?.ok) { setErr(r?.error || '버전을 읽지 못했습니다'); return }
      setVersions(r)
      setTarget(t => t || r.targets?.[0]?.value || '')
    })
  }, [versions])

  async function run() {
    setBusy(true); setErr('')
    const r = await api.upgradeCheck(target)
    setBusy(false)
    if (!r?.ok) { setErr(r?.error || '점검하지 못했습니다'); return }
    setResult(r); setMsg(null)
  }

  async function save() {
    setMsg(null); setSaving(true)
    try {
      setMsg(await saveReport({ filename: api.upgradeCheckFilename, save: api.upgradeCheckSave, fallback: 'Polaris-upgrade-check.docx' }))
    } finally { setSaving(false) }
  }

  return (
    <div style={{ height: '100%', overflow: 'auto', padding: '16px 20px' }}>
      <CheckPageHead page="upgrade" icon={ArrowUpCircle}>
        버전 차이와 지금 클러스터 상태도 함께 봅니다. 결과는 글로 복사해 작업 문서에 붙여 넣을 수 있습니다.
      </CheckPageHead>

      <div style={{ ...card, display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
        <span style={{ fontSize: 12, color: 'var(--text-mid)' }}>지금 버전</span>
        <b style={{ fontFamily: 'var(--font-mono)', fontSize: 12.5 }}>{versions?.version || '…'}</b>
        {versions?.rke2 && <span style={tag}>RKE2</span>}
        <span style={{ fontSize: 12, color: 'var(--text-mid)', marginLeft: 8 }}>목표 버전</span>
        <select value={target} onChange={e => setTarget(e.target.value)} style={sel} disabled={!versions}>
          {(versions?.targets || []).map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
        </select>
        <div style={{ flex: 1 }} />
        <button className="btn btn-primary btn-sm" onClick={run} disabled={!target || busy}>
          {busy ? <Loader2 size={12} className="spin" /> : <Play size={12} />} {busy ? '점검 중…' : '점검 실행'}
        </button>
        {result && (
          <button className="btn btn-sm" onClick={save} disabled={saving || busy} title="이 점검 결과를 DOCX 보고서로 저장합니다">
            {saving ? <Loader2 size={12} className="spin" /> : <Save size={12} />} DOCX 저장</button>)}
      </div>
      {err && <div style={errBox}>{err}</div>}
      {msg && <div style={msg.ok ? okBox : errBox}>{msg.text}</div>}

      {result && <Result r={result} />}
      {!result && !busy && !err && (
        <div style={{ ...card, marginTop: 12, textAlign: 'center', padding: 30, color: 'var(--text-dim)', fontSize: 12.5 }}>
          목표 버전을 고르고 [점검 실행]을 누르세요. 큰 클러스터는 수십 초 걸릴 수 있습니다.
        </div>
      )}
    </div>
  )
}

function Result({ r }) {
  const v = verdictText(r)
  const Icon = r.verdict === 'blocked' ? XCircle : r.verdict === 'caution' ? AlertTriangle : CheckCircle2
  return (
    <>
      <div style={{ ...card, marginTop: 12, borderColor: v.color, background: `color-mix(in srgb, ${v.color} 8%, var(--bg-2))`,
                    display: 'flex', alignItems: 'center', gap: 10 }}>
        <Icon size={22} color={v.color} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 14, fontWeight: 700, color: ink(v.color) }}>{v.title}</div>
          <div style={{ fontSize: 12, color: 'var(--text-mid)', marginTop: 2 }}>{v.sub}</div>
        </div>
        <button className="btn btn-sm" title="결과를 글로 복사 — 작업 문서에 붙여 넣을 수 있습니다"
                onClick={() => navigator.clipboard?.writeText(resultText(r)).catch(() => {})}><Copy size={12} /> 결과 복사</button>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.6fr) minmax(280px, 1fr)', gap: 10, marginTop: 10, alignItems: 'start' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0 }}>
          {r.findings.length === 0 && <div style={{ ...card, fontSize: 12.5, color: 'var(--text-mid)' }}>확인할 항목이 없습니다.</div>}
          {r.findings.map((f, i) => <Finding key={i} f={f} />)}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0 }}>
          {r.passed.length > 0 && (
            <div style={card}>
              <div style={h3}><CheckCircle2 size={13} color="var(--nimbus)" /> 확인 완료 ({r.passed.length})</div>
              {r.passed.map((t, i) => <div key={i} style={{ fontSize: 11.5, color: 'var(--text)', padding: '2px 0', lineHeight: 1.5 }}>· {t}</div>)}
            </div>
          )}
          <div style={card}>
            <div style={h3}><ListChecks size={13} color="var(--nimbus)" /> 업그레이드 순서</div>
            <ol style={{ margin: '2px 0 0 18px', padding: 0 }}>
              {r.checklist.map((t, i) => <li key={i} style={{ fontSize: 11.5, padding: '2px 0', lineHeight: 1.5 }}>{t}</li>)}
            </ol>
          </div>
        </div>
      </div>
    </>
  )
}

function Finding({ f }) {
  const s = SEV_STYLE[f.severity] || SEV_STYLE.info
  const [open, setOpen] = useState(f.severity !== 'info')
  const [all, setAll] = useState(false)
  const items = all ? f.items : f.items.slice(0, 8)
  return (
    <div style={{ ...card, borderLeft: `3px solid ${s.color}` }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: 8, cursor: f.items.length ? 'pointer' : 'default' }}
           onClick={() => f.items.length && setOpen(o => !o)}>
        <span style={badge(s.color)}>{s.label}</span>
        <span style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 2 }}>{CATEGORY_KO[f.category] || f.category}</span>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontSize: 12.5, fontWeight: 700, color: 'var(--text-bright)' }}>{f.title}</div>
          {f.detail && <div style={{ fontSize: 11.5, color: 'var(--text-mid)', marginTop: 3, lineHeight: 1.6 }}>{f.detail}</div>}
          {f.action && <div style={{ fontSize: 11.5, marginTop: 4, lineHeight: 1.6 }}><Info size={11} style={{ verticalAlign: -1 }} /> {f.action}</div>}
        </div>
        {f.items.length > 0 && (open ? <ChevronDown size={13} /> : <ChevronRight size={13} />)}
      </div>
      {open && f.items.length > 0 && (
        <div style={{ marginTop: 6, padding: '6px 8px', background: 'var(--bg-1)', borderRadius: 6, border: '1px solid var(--border)' }}>
          {items.map((t, i) => <div key={i} style={{ fontSize: 11, fontFamily: 'var(--font-mono)', padding: '1px 0', wordBreak: 'break-all' }}>{t}</div>)}
          {(f.items.length > 8 || f.more > 0) && (
            <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
              {f.items.length > 8 && <button className="btn btn-ghost btn-sm" onClick={() => setAll(a => !a)}>
                {all ? '접기' : `모두 보기 (${f.items.length}건)`}</button>}
              {f.more > 0 && <span style={{ fontSize: 11, color: 'var(--text-dim)', alignSelf: 'center' }}>그 밖에 {f.more}건</span>}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

const ink = (c) => `color-mix(in srgb, ${c} 62%, var(--text-bright))`
const card = { background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8, padding: '10px 12px' }
const h3 = { display: 'flex', alignItems: 'center', gap: 5, fontSize: 12, fontWeight: 700, marginBottom: 5 }
const sel = { background: 'var(--bg-1)', border: '1px solid var(--border)', borderRadius: 5, padding: '4px 8px',
              fontSize: 12, color: 'var(--text)', fontFamily: 'var(--font)' }
const tag = { fontSize: 10.5, padding: '1px 7px', borderRadius: 10, border: '1px solid var(--border)', color: 'var(--text-mid)' }
const badge = (c) => ({ display: 'inline-block', fontSize: 10.5, padding: '1px 7px', borderRadius: 10, whiteSpace: 'nowrap', flexShrink: 0,
                        border: `1px solid ${c}`, color: ink(c), background: `color-mix(in srgb, ${c} 12%, transparent)` })
const okBox = { padding: '8px 12px', borderRadius: 6, fontSize: 12, background: 'rgba(52,211,153,0.10)',
                border: '1px solid rgba(52,211,153,0.3)', color: 'var(--text)', marginTop: 8, wordBreak: 'break-all' }
const errBox = { padding: '8px 12px', borderRadius: 6, fontSize: 12, background: 'rgba(239,68,68,0.12)',
                 border: '1px solid rgba(239,68,68,0.3)', color: 'var(--red)', marginTop: 8 }
