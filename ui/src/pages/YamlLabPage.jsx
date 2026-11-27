import React, { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'
import { startPoll, appendCapped } from '../poll.js'
import { useApp } from '../store.jsx'
import {
  FlaskConical, Save, Play, Eye, Trash2, Copy, FolderDown, Loader2,
  AlertCircle, AlertTriangle, CheckCircle2, Search, FilePlus2, History, Square,
} from 'lucide-react'

// 탭을 떠났다 돌아와도 **붙여넣던 YAML 이 날아가지 않도록** 모듈 스코프에 유지한다
// (K8sPageView 가 activePage 별 switch 렌더 → 탭 전환 시 언마운트). 편집 중 내용을
// 잃는 건 이 페이지에서 가장 치명적인 UX 사고라 캐시는 선택이 아니라 필수.
// 클러스터를 바꾸면 다른 클러스터 기준이므로 폐기한다.
let _labCache = null   // { switchKey, editor, selectedId, query }

const EMPTY = { id: null, name: '', tags: '', notes: '', content: '' }

// 편집기는 CodeMirror 가 아니라 textarea 다. 문법 오류는 「미리보기」의 서버 dry-run 이
// 줄 번호까지 정확히 짚어주므로 하이라이팅보다 확실하고, 이 페이지는 '붙여넣고 돌린다'가
// 주 용도라 무거운 편집기를 얹을 이유가 없다.
export default function YamlLabPage() {
  const { connected, clusterSwitchKey } = useApp()
  const seed = (_labCache && _labCache.switchKey === clusterSwitchKey) ? _labCache : null

  const [items, setItems] = useState([])
  const [query, setQuery] = useState(seed?.query ?? '')
  const [selected, setSelected] = useState(() => new Set())
  const [editor, setEditor] = useState(seed?.editor ?? EMPTY)
  const [detail, setDetail] = useState(null)      // 버전/적용 이력
  const [preview, setPreview] = useState(null)
  const [job, setJob] = useState(null)            // {id, status, logs[], diff, warnings, ...}
  const [busy, setBusy] = useState('')            // '' | 'save' | 'preview' | 'apply' | 'export' | 'teardown'
  const [msg, setMsg] = useState(null)            // {kind:'ok'|'err', text}
  const pollRef = useRef(null)

  useEffect(() => {
    _labCache = { switchKey: clusterSwitchKey, editor, selectedId: editor.id, query }
  }, [clusterSwitchKey, editor, query])

  useEffect(() => { refresh() }, [])              // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => () => { if (pollRef.current) pollRef.current() }, [])   // startPoll 의 stop

  async function refresh(q = query) {
    const r = await api.labList(q)
    if (r?.ok) setItems(r.items || [])
  }

  async function openItem(mid) {
    const r = await api.labGet(mid)
    if (!r?.ok) { setMsg({ kind: 'err', text: r?.error || '불러오기 실패' }); return }
    const it = r.item
    setEditor({ id: it.id, name: it.name, tags: it.tags || '', notes: it.notes || '',
                content: it.content || '' })
    setDetail(it)
    setPreview(null); setJob(null); setMsg(null)
  }

  function newItem() {
    setEditor(EMPTY); setDetail(null); setPreview(null); setJob(null); setMsg(null)
  }

  async function save() {
    if (!editor.content.trim()) { setMsg({ kind: 'err', text: '저장할 YAML 이 비어 있습니다.' }); return }
    setBusy('save')
    const r = await api.labSave(editor.id, editor.name || '이름없음', editor.content,
                                editor.tags, editor.notes)
    setBusy('')
    if (!r?.ok) { setMsg({ kind: 'err', text: r?.error || '저장 실패' }); return }
    setEditor(e => ({ ...e, id: r.id }))
    setMsg({ kind: 'ok', text: r.new_version ? '새 버전으로 저장했습니다.' : '저장했습니다 (내용 동일 — 새 버전 없음).' })
    await refresh()
    await openItem(r.id)
  }

  async function runPreview() {
    if (!editor.content.trim()) return
    setBusy('preview'); setPreview(null); setMsg(null)
    const r = await api.labPreview(editor.content)
    setBusy('')
    if (!r?.ok) { setMsg({ kind: 'err', text: r?.error || '미리보기 실패' }); return }
    setPreview(r)
  }

  async function runApply() {
    if (!editor.content.trim()) return
    setBusy('apply'); setJob(null); setMsg(null)
    const r = await api.labApply(editor.id, editor.content, 40)
    if (!r?.ok) { setBusy(''); setMsg({ kind: 'err', text: r?.error || '적용 실패' }); return }
    const jobId = r.job_id
    setJob({ id: jobId, status: 'running', logs: [], diff: null, warnings: [] })
    if (pollRef.current) { pollRef.current(); pollRef.current = null }
    // 겹치지 않는 폴러(v1.3.41) — drain 엔드포인트라 겹치면 로그 순서가 뒤집힌다
    pollRef.current = startPoll(async () => {
      const s = await api.labApplyStatus(jobId)
      setJob(prev => ({
        ...(prev || {}), id: jobId, ...s,
        logs: appendCapped((prev && prev.logs) || [], (s && s.logs) || [], 3000),
      }))
      if (!s || s.status === 'done' || s.status === 'error' || s.status === 'unknown') {
        pollRef.current = null
        setBusy('')
        if (editor.id) { refresh(); }
        return false
      }
    }, 1200)
  }

  async function cancelWatch() {
    if (job?.id) await api.labApplyCancel(job.id)
  }

  async function teardown() {
    setBusy('teardown'); setMsg(null)
    const r = await api.labTeardown(editor.id, editor.content)
    setBusy('')
    setMsg(r?.ok ? { kind: 'ok', text: `정리 완료: ${(r.output || '').slice(0, 200)}` }
                 : { kind: 'err', text: r?.error || '정리 실패' })
  }

  async function removeItem(mid) {
    const r = await api.labDelete(mid)
    if (r?.ok) {
      if (editor.id === mid) newItem()
      setSelected(s => { const n = new Set(s); n.delete(mid); return n })
      refresh()
    }
  }

  function toggle(mid) {
    setSelected(s => { const n = new Set(s); n.has(mid) ? n.delete(mid) : n.add(mid); return n })
  }

  async function copySelected() {
    const ids = [...selected]
    if (!ids.length) return
    setBusy('export')
    const r = await api.labExportText(ids)
    setBusy('')
    if (!r?.ok) { setMsg({ kind: 'err', text: r?.error || '복사 실패' }); return }
    try {
      await navigator.clipboard.writeText(r.text)
      setMsg({ kind: 'ok', text: `${r.count}건을 클립보드에 복사했습니다.` })
    } catch {
      setMsg({ kind: 'err', text: '클립보드 접근이 거부되었습니다 — 폴더로 내보내기를 사용하세요.' })
    }
  }

  async function exportFolder() {
    const ids = [...selected]
    if (!ids.length) return
    setBusy('export')
    const r = await api.labExportFolder(ids, true)
    setBusy('')
    if (r?.cancelled) return
    setMsg(r?.ok ? { kind: 'ok', text: `${r.count}개 파일을 내보냈습니다 → ${r.path}` }
                 : { kind: 'err', text: r?.error || '내보내기 실패' })
  }

  if (!connected) {
    return <div style={{ padding: 40, color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: 8 }}>
      <AlertCircle size={16} /> 클러스터에 연결되지 않았습니다.
    </div>
  }

  const warnings = preview?.warnings || detail?.warnings || []

  return (
    <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
      {/* 헤더 */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, padding: '14px 20px 12px',
        borderBottom: '1px solid var(--border)' }}>
        <FlaskConical size={20} style={{ color: 'var(--nimbus)' }} />
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 17, fontWeight: 700, color: 'var(--text-bright)' }}>YAML 실험실</div>
          <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>
            매니페스트를 붙여넣고 검증·적용하고, 무엇이 바뀌었는지 확인한 뒤 골라서 내보냅니다
          </div>
        </div>
        <button className="btn btn-sm" onClick={newItem} style={{ gap: 5 }}>
          <FilePlus2 size={13} /> 새로 만들기
        </button>
      </div>

      <div style={{ flex: 1, display: 'flex', minHeight: 0 }}>
        {/* ── 좌: 목록 ─────────────────────────────────────────────── */}
        <div style={{ width: 300, borderRight: '1px solid var(--border)', display: 'flex',
          flexDirection: 'column', minHeight: 0 }}>
          <div style={{ padding: '10px 12px', borderBottom: '1px solid var(--border)' }}>
            <div style={{ position: 'relative' }}>
              <Search size={13} style={{ position: 'absolute', left: 8, top: 8, color: 'var(--text-dim)' }} />
              <input
                value={query}
                onChange={e => { setQuery(e.target.value); refresh(e.target.value) }}
                placeholder="이름·태그·본문 검색"
                style={{ width: '100%', padding: '6px 8px 6px 26px', fontSize: 12,
                  background: 'var(--bg-2)', border: '1px solid var(--border)',
                  borderRadius: 6, color: 'var(--text)' }} />
            </div>
          </div>

          <div style={{ flex: 1, overflowY: 'auto' }}>
            {items.length === 0 && (
              <div style={{ padding: 20, fontSize: 12, color: 'var(--text-dim)', textAlign: 'center' }}>
                {query ? '검색 결과가 없습니다.' : '저장된 매니페스트가 없습니다.'}
              </div>
            )}
            {items.map(it => (
              <div key={it.id}
                style={{ display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 12px',
                  borderBottom: '1px solid var(--border)', cursor: 'pointer',
                  background: editor.id === it.id ? 'var(--bg-2)' : 'transparent' }}>
                <input type="checkbox" checked={selected.has(it.id)} style={{ marginTop: 3 }}
                  onChange={() => toggle(it.id)} onClick={e => e.stopPropagation()} />
                <div style={{ flex: 1, minWidth: 0 }} onClick={() => openItem(it.id)}>
                  <div style={{ fontSize: 12.5, color: 'var(--text-bright)', fontWeight: 600,
                    overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{it.name}</div>
                  {/* ns 와 클러스터 이름이 둘 다 'default' 일 수 있어 라벨을 붙인다 —
                      안 붙이면 「v6 · default · default」처럼 나와 구분이 안 된다 */}
                  <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
                    v{it.versions} · ns {it.namespace || '-'}
                  </div>
                  {it.cluster && (
                    <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 1 }}>
                      클러스터 {it.cluster}
                    </div>
                  )}
                  {it.tags && <div style={{ fontSize: 10.5, color: 'var(--nimbus)', marginTop: 2 }}>{it.tags}</div>}
                </div>
                <button className="btn btn-icon btn-sm" title="삭제"
                  onClick={e => { e.stopPropagation(); removeItem(it.id) }}>
                  <Trash2 size={12} />
                </button>
              </div>
            ))}
          </div>

          {/* 선택 반출 바 — GitLab 자동 승격 대신 이 경로로 형상관리에 수동 반영한다 */}
          {selected.size > 0 && (
            <div style={{ padding: '10px 12px', borderTop: '1px solid var(--border)',
              background: 'var(--bg-2)' }}>
              <div style={{ fontSize: 11.5, color: 'var(--text-dim)', marginBottom: 6 }}>
                {selected.size}건 선택됨
              </div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button className="btn btn-sm" style={{ flex: 1, gap: 4 }} onClick={copySelected}
                  disabled={busy === 'export'}>
                  <Copy size={12} /> 복사
                </button>
                <button className="btn btn-sm" style={{ flex: 1, gap: 4 }} onClick={exportFolder}
                  disabled={busy === 'export'}>
                  <FolderDown size={12} /> 내보내기
                </button>
              </div>
              <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 6, lineHeight: 1.5 }}>
                내보내기는 클러스터별 폴더로 <code>.yaml</code> 파일을 만듭니다.
              </div>
            </div>
          )}
        </div>

        {/* ── 우: 편집기 + 결과 ─────────────────────────────────────── */}
        <div style={{ flex: 1, display: 'flex', flexDirection: 'column', minHeight: 0 }}>
          <div style={{ display: 'flex', gap: 8, padding: '10px 16px', borderBottom: '1px solid var(--border)' }}>
            <input value={editor.name} onChange={e => setEditor({ ...editor, name: e.target.value })}
              placeholder="이름 (예: was-deploy)"
              style={{ flex: 1, padding: '6px 9px', fontSize: 12.5, background: 'var(--bg-2)',
                border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text)' }} />
            <input value={editor.tags} onChange={e => setEditor({ ...editor, tags: e.target.value })}
              placeholder="태그 (쉼표)"
              style={{ width: 160, padding: '6px 9px', fontSize: 12.5, background: 'var(--bg-2)',
                border: '1px solid var(--border)', borderRadius: 6, color: 'var(--text)' }} />
          </div>

          <textarea
            value={editor.content}
            onChange={e => setEditor({ ...editor, content: e.target.value })}
            spellCheck={false}
            placeholder={'여기에 YAML 을 붙여넣으세요.\n\n---  로 여러 문서를 한 번에 다룰 수 있습니다.'}
            style={{ flex: 1, minHeight: 180, resize: 'none', padding: '12px 16px',
              fontFamily: 'Consolas, monospace', fontSize: 12.5, lineHeight: 1.55,
              background: 'var(--bg-1)', border: 'none', borderBottom: '1px solid var(--border)',
              color: 'var(--text)', outline: 'none' }} />

          {/* 액션 바 */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, padding: '10px 16px',
            borderBottom: '1px solid var(--border)', flexWrap: 'wrap' }}>
            <button className="btn btn-sm" onClick={save} disabled={!!busy} style={{ gap: 4 }}>
              {busy === 'save' ? <Loader2 size={12} className="spin" /> : <Save size={12} />} 저장
            </button>
            <button className="btn btn-sm" onClick={runPreview} disabled={!!busy} style={{ gap: 4 }}>
              {busy === 'preview' ? <Loader2 size={12} className="spin" /> : <Eye size={12} />} 미리보기
            </button>
            <button className="btn btn-primary btn-sm" onClick={runApply} disabled={!!busy} style={{ gap: 4 }}>
              {busy === 'apply' ? <Loader2 size={12} className="spin" /> : <Play size={12} />} 적용
            </button>
            {job?.status === 'running' && (
              <button className="btn btn-sm" onClick={cancelWatch} style={{ gap: 4 }}>
                <Square size={11} /> 관찰 중단
              </button>
            )}
            <div style={{ flex: 1 }} />
            <button className="btn btn-sm" onClick={teardown} disabled={!!busy} style={{ gap: 4 }}
              title="kubectl delete -f - 로 이 매니페스트가 만든 것을 되돌립니다">
              {busy === 'teardown' ? <Loader2 size={12} className="spin" /> : <Trash2 size={12} />} 클러스터에서 정리
            </button>
          </div>

          {/* 결과 영역 */}
          <div style={{ flex: 1, overflowY: 'auto', padding: '12px 16px', minHeight: 0 }}>
            {msg && (
              <div style={{ marginBottom: 10, padding: '8px 12px', borderRadius: 6, fontSize: 12,
                background: msg.kind === 'ok' ? 'rgba(52,211,153,0.12)' : 'rgba(248,113,113,0.12)',
                color: msg.kind === 'ok' ? '#34d399' : '#f87171' }}>
                {msg.text}
              </div>
            )}

            {warnings.length > 0 && (
              <Panel icon={<AlertTriangle size={13} style={{ color: 'var(--yellow)' }} />}
                title={`평문 비밀 의심 ${warnings.length}건`} tone="#fbbf24">
                {warnings.map((w, i) => (
                  <div key={i} style={{ fontSize: 11.5, color: 'var(--text-dim)', marginBottom: 3 }}>
                    <b style={{ color: 'var(--text)' }}>{w.line}행 · {w.key}</b> — {w.hint}
                  </div>
                ))}
                <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 6 }}>
                  저장·적용은 그대로 진행됩니다. 알려만 드립니다.
                </div>
              </Panel>
            )}

            {preview && <PreviewPanel p={preview} />}
            {job && <ApplyPanel job={job} />}

            {detail?.versions?.length > 1 && (
              <Panel icon={<History size={13} style={{ color: 'var(--text-dim)' }} />}
                title={`버전 이력 ${detail.versions.length}개`}>
                <VersionList versions={detail.versions} />
              </Panel>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}

function Panel({ icon, title, tone, children }) {
  return (
    <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8,
      padding: '10px 14px', marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 8,
        fontSize: 12.5, fontWeight: 600, color: tone || 'var(--text-bright)' }}>
        {icon} {title}
      </div>
      {children}
    </div>
  )
}

function PreviewPanel({ p }) {
  const ok = p.valid !== false
  return (
    <Panel
      icon={ok ? <CheckCircle2 size={13} style={{ color: 'var(--green)' }} />
               : <AlertCircle size={13} style={{ color: 'var(--red)' }} />}
      title={ok ? `검증 통과 (${p.validate_mode || '-'} dry-run)` : '검증 실패'}
      tone={ok ? '#34d399' : '#f87171'}>
      {!ok && (p.validate_errors || []).map((e, i) => (
        <div key={i} style={{ fontSize: 11.5, color: 'var(--red)', marginBottom: 3 }}>{e}</div>
      ))}
      {p.targets?.length > 0 && (
        <div style={{ fontSize: 11.5, color: 'var(--text-dim)', marginBottom: 8 }}>
          대상 {p.targets.length}건 — {p.targets.map(t =>
            `${t.kind}/${t.name}${t.namespace ? ` (${t.namespace})` : ''}`).join(', ')}
        </div>
      )}
      {p.has_diff === false && (
        <div style={{ fontSize: 12, color: 'var(--text-dim)' }}>{p.diff_note}</div>
      )}
      {p.diff_error && (
        <div style={{ fontSize: 11.5, color: 'var(--text-dim)' }}>
          라이브 비교를 못 했습니다: {p.diff_error}
        </div>
      )}
      {p.has_diff && (
        <pre style={{ margin: 0, maxHeight: 320, overflow: 'auto', fontSize: 11.5,
          lineHeight: 1.5, fontFamily: 'Consolas, monospace', color: 'var(--text)' }}>
          {colorizeDiff(p.diff_text)}
        </pre>
      )}
    </Panel>
  )
}

function ApplyPanel({ job }) {
  const t = job.diff?.totals
  const tone = job.status === 'error' ? '#f87171'
             : job.status === 'done' ? '#34d399' : 'var(--nimbus)'
  return (
    <Panel
      icon={job.status === 'running' ? <Loader2 size={13} className="spin" style={{ color: tone }} />
                                     : <CheckCircle2 size={13} style={{ color: tone }} />}
      title={job.status === 'running' ? '적용 · 파급 관찰 중'
           : job.status === 'error' ? '적용 실패' : `적용 완료 (${job.elapsed ?? 0}초)`}
      tone={tone}>
      {job.error && <div style={{ fontSize: 11.5, color: 'var(--red)', marginBottom: 8 }}>{job.error}</div>}

      {t && (
        <div style={{ display: 'flex', gap: 14, fontSize: 12, marginBottom: 8 }}>
          <span style={{ color: 'var(--green)' }}>추가 {t.added}</span>
          <span style={{ color: 'var(--red)' }}>삭제 {t.removed}</span>
          <span style={{ color: 'var(--yellow)' }}>변경 {t.changed}</span>
        </div>
      )}

      {(job.diff?.kinds || []).map((k, i) => (
        <div key={i} style={{ marginBottom: 6, fontSize: 11.5 }}>
          <b style={{ color: 'var(--text-bright)' }}>{k.kind}</b>
          {k.added.map(a => <div key={a} style={{ color: 'var(--green)', paddingLeft: 10 }}>+ {a}</div>)}
          {k.removed.map(a => <div key={a} style={{ color: 'var(--red)', paddingLeft: 10 }}>− {a}</div>)}
          {k.changed.map(c => (
            <div key={c.key} style={{ color: 'var(--yellow)', paddingLeft: 10 }}>
              ~ {c.key} — {c.fields.map(f => `${f.field}: ${f.old} → ${f.new}`).join(', ')}
            </div>
          ))}
        </div>
      ))}

      {job.warnings?.length > 0 && (
        <div style={{ marginTop: 8 }}>
          <div style={{ fontSize: 12, color: 'var(--yellow)', marginBottom: 4 }}>
            적용 후 Warning 이벤트 {job.warnings.length}건
          </div>
          {job.warnings.slice(0, 10).map((w, i) => (
            <div key={i} style={{ fontSize: 11, color: 'var(--text-dim)', paddingLeft: 10 }}>
              {w.object} · {w.reason} — {w.message}
            </div>
          ))}
        </div>
      )}

      {job.logs?.length > 0 && (
        <pre style={{ margin: '8px 0 0', maxHeight: 160, overflow: 'auto', fontSize: 11,
          lineHeight: 1.5, fontFamily: 'Consolas, monospace', color: 'var(--text-dim)' }}>
          {job.logs.join('\n')}
        </pre>
      )}
    </Panel>
  )
}

function VersionList({ versions }) {
  const [diff, setDiff] = useState('')
  const [pair, setPair] = useState(null)

  async function compare(a, b) {
    setPair([a, b])
    const r = await api.labVersionDiff(a, b)
    setDiff(r?.ok ? (r.diff || '(차이 없음)') : (r?.error || '비교 실패'))
  }

  return (
    <div>
      {versions.map((v, i) => (
        <div key={v.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 11.5,
          color: 'var(--text-dim)', marginBottom: 3 }}>
          <b style={{ color: 'var(--text)' }}>v{v.version_no}</b>
          <span>{(v.created_at || '').replace('T', ' ').slice(0, 16)}</span>
          {i < versions.length - 1 && (
            <button className="btn btn-sm" style={{ padding: '1px 6px', fontSize: 10.5 }}
              onClick={() => compare(versions[i + 1].id, v.id)}>
              이전과 비교
            </button>
          )}
        </div>
      ))}
      {diff && (
        <pre style={{ marginTop: 8, maxHeight: 260, overflow: 'auto', fontSize: 11.5,
          lineHeight: 1.5, fontFamily: 'Consolas, monospace', color: 'var(--text)' }}>
          {colorizeDiff(diff)}
        </pre>
      )}
    </div>
  )
}

// unified diff 를 +/- 기준으로 색만 입힌다 (라이브러리 추가 없이)
function colorizeDiff(text) {
  return String(text || '').split('\n').map((line, i) => {
    let color = 'var(--text-dim)'
    if (line.startsWith('+') && !line.startsWith('+++')) color = '#34d399'
    else if (line.startsWith('-') && !line.startsWith('---')) color = '#f87171'
    else if (line.startsWith('@@')) color = 'var(--nimbus)'
    return <div key={i} style={{ color }}>{line || ' '}</div>
  })
}
