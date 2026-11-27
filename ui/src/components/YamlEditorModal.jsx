import React, { useEffect, useRef, useState } from 'react'
import { basicSetup } from 'codemirror'
import { EditorView } from '@codemirror/view'
import { EditorState } from '@codemirror/state'
import { HighlightStyle, syntaxHighlighting } from '@codemirror/language'
import { tags as t } from '@lezer/highlight'
import { yaml as yamlLang } from '@codemirror/lang-yaml'
import { linter, lintGutter } from '@codemirror/lint'
import { MergeView } from '@codemirror/merge'
import jsyaml from 'js-yaml'
import { X, Check, AlertTriangle, RotateCcw, ShieldCheck, ShieldAlert, Loader2 } from 'lucide-react'
import { api } from '../api.js'

// 흔한 쿠버네티스 매니페스트 키 — 정적 자동완성(오프라인·airgap 안전). 스키마 전체가 아니라
// 자주 쓰는 키 힌트로 오타/구조 실수를 줄인다(권위 검증은 아래 서버 dry-run 이 담당).
const K8S_KEYS = [
  'apiVersion', 'kind', 'metadata', 'name', 'namespace', 'labels', 'annotations',
  'spec', 'status', 'replicas', 'selector', 'matchLabels', 'matchExpressions',
  'template', 'containers', 'initContainers', 'image', 'imagePullPolicy',
  'command', 'args', 'ports', 'containerPort', 'protocol', 'env', 'envFrom',
  'valueFrom', 'configMapKeyRef', 'secretKeyRef', 'fieldRef',
  'resources', 'limits', 'requests', 'cpu', 'memory', 'ephemeral-storage',
  'volumeMounts', 'mountPath', 'readOnly', 'subPath', 'volumes', 'configMap',
  'secret', 'emptyDir', 'hostPath', 'persistentVolumeClaim', 'claimName',
  'restartPolicy', 'serviceAccountName', 'securityContext', 'runAsUser', 'fsGroup',
  'nodeSelector', 'tolerations', 'affinity', 'nodeName', 'priorityClassName',
  'strategy', 'type', 'rollingUpdate', 'maxSurge', 'maxUnavailable',
  'livenessProbe', 'readinessProbe', 'startupProbe', 'httpGet', 'exec', 'tcpSocket',
  'path', 'port', 'scheme', 'initialDelaySeconds', 'periodSeconds', 'timeoutSeconds',
  'successThreshold', 'failureThreshold', 'data', 'stringData', 'binaryData',
  'rules', 'host', 'http', 'paths', 'pathType', 'backend', 'service', 'number',
  'targetPort', 'nodePort', 'clusterIP', 'externalName', 'sessionAffinity',
  'ingressClassName', 'storageClassName', 'accessModes', 'capacity', 'volumeMode',
  'schedule', 'jobTemplate', 'concurrencyPolicy', 'suspend', 'completions', 'parallelism',
]

function k8sCompletionSource(context) {
  const word = context.matchBefore(/[\w.\-/]*/)
  if (!word || (word.from === word.to && !context.explicit)) return null
  const q = word.text
  const opts = K8S_KEYS.filter(k => k.toLowerCase().startsWith(q.toLowerCase()))
    .map(k => ({ label: k, type: 'property' }))
  if (!opts.length) return null
  return { from: word.from, options: opts }
}

/**
 * 대형 YAML 편집 모달.
 *  - 좌: 원본(읽기전용) / 우: 편집 (CodeMirror MergeView — 변경 줄 실시간 하이라이트)
 *  - js-yaml 로 문법 검사 → 오류 줄 표시 + 적용 버튼 비활성
 *  - 적용은 부모(onApply(text))가 기존 확인 모달 → kubectl apply 로 처리
 * ResourcePanel / CRD / ArgoCD 등에서 재사용 가능.
 */

function validateYaml(text) {
  if (!text || !text.trim()) return { valid: false, message: '내용이 비어 있습니다.' }
  try { jsyaml.load(text); return { valid: true, message: '' } }
  catch (e) {
    return {
      valid: false,
      line: e && e.mark ? e.mark.line + 1 : null,
      message: (e && (e.reason || e.message)) || 'YAML 파싱 오류',
    }
  }
}

function makeYamlLinter() {
  return linter((view) => {
    const doc = view.state.doc
    const text = doc.toString()
    if (!text.trim()) return []
    try { jsyaml.load(text); return [] }
    catch (e) {
      const len = Math.max(0, text.length - 1)
      const pos = (e && e.mark && typeof e.mark.position === 'number')
        ? Math.max(0, Math.min(e.mark.position, len)) : 0
      const line = doc.lineAt(pos)
      return [{
        from: line.from, to: line.to, severity: 'error',
        message: (e && (e.reason || e.message)) || 'YAML 파싱 오류',
      }]
    }
  }, { delay: 250 })
}

// 구문 색 — **토큰으로 쓴다** (v1.3.36).
//
// 예전에는 Material 계열 색(#c792ea, #c3e88d …)을 박아 뒀다. 어두운 배경만
// 있던 시절에는 괜찮았지만, 밝은 테마에서는 배경과 1.1:1 까지 떨어져 **글자가
// 사실상 사라졌다**(사용자 신고 — 메모의 코드블록이 같은 이유였다).
// 토큰을 쓰면 테마마다 읽히는 값이 따라온다.
const darkHighlight = HighlightStyle.define([
  { tag: t.keyword, color: 'var(--purple)' },
  { tag: [t.atom, t.bool, t.number], color: 'var(--yellow)' },
  { tag: [t.string, t.special(t.string)], color: 'var(--green)' },
  { tag: [t.propertyName, t.definition(t.propertyName)], color: 'var(--blue)' },
  { tag: [t.comment], color: 'var(--text-dim)', fontStyle: 'italic' },
  { tag: [t.punctuation, t.separator, t.operator], color: 'var(--text-mid)' },
  { tag: t.invalid, color: 'var(--red)' },
])

const cmTheme = EditorView.theme({
  '&': { height: '100%', fontSize: '13px', backgroundColor: 'var(--bg-0, #070b13)', color: 'var(--text, #cdd6e6)' },
  '.cm-scroller': { fontFamily: "var(--font-mono, 'JetBrains Mono', monospace)", lineHeight: '1.6', overflow: 'auto' },
  '.cm-gutters': { backgroundColor: 'transparent', border: 'none', color: 'var(--text-dim, #5b647a)' },
  '.cm-activeLine': { backgroundColor: 'rgba(255,255,255,0.035)' },
  '.cm-activeLineGutter': { backgroundColor: 'transparent', color: 'var(--text, #cdd6e6)' },
  '.cm-content': { caretColor: 'var(--nimbus, #34d399)' },
  '&.cm-focused': { outline: 'none' },
}, { dark: true })

const MERGE_CSS = `
/* @codemirror/merge 는 '.cm-mergeView' 자체를 스크롤 컨테이너로 쓴다(overflow-y:auto 내장).
   내부 .cm-editor/.cm-scroller 는 height:auto·overflow-y:visible 로 !important 고정하므로
   "에디터 높이 100%" 방식은 먹히지 않는다(긴 values 가 안 내려가던 원인).
   → 편집 영역(host)을 position:relative 로 두고 .cm-mergeView 를 absolute inset:0 으로
   꽉 채워 '확실한 픽셀 높이'를 주면, flex 의 height:100% 미해석 문제 없이 내장 스크롤이 동작한다. */
.pol-yaml-merge { position: relative; }
.pol-yaml-merge > .cm-mergeView { position: absolute; inset: 0; overflow-y: auto; }
.pol-yaml-merge .cm-changedLine { background-color: rgba(125,211,252,0.07); }
.pol-yaml-merge .cm-deletedChunk { background-color: rgba(248,113,113,0.10); }
`

export default function YamlEditorModal({
  original, kind, namespace, name, busy, onApply, onClose,
  title = 'YAML 편집',
  applyLabel = '적용 (Apply)',
  hint = '적용은 kubectl apply 와 동일하게 동작합니다.',
  footerExtra = null,   // 푸터 좌측에 끼워넣을 추가 컨트롤(예: --take-ownership 토글)
}) {
  const hostRef = useRef(null)
  const mvRef = useRef(null)
  const [text, setText] = useState(original || '')
  // 상태배지(문법 OK/오류) 용 검증 결과 — text 와 별도 state 로 분리해 디바운스한다.
  // 예전엔 render 본문에서 매 키 입력마다 validateYaml(text)(=jsyaml.load 전체 재파싱)를
  // 동기 호출했는데, CodeMirror 의 makeYamlLinter() 도 같은 문서를 250ms 디바운스로 파싱하고
  // 있어 대형 YAML(수백KB Helm values)에서 같은 파싱이 두 번 겹쳤다. linter 와 같은 리듬(250ms)
  // 으로만 배지를 갱신 — 에디터 안 오류 표시(gutter)와 배지가 함께 늦게 바뀌므로 체감 불일치도 없다.
  const [validation, setValidation] = useState(() => validateYaml(original || ''))
  const validateTimerRef = useRef(null)
  // 스키마 검증(서버 dry-run) 결과 — null | {loading} | {ok, valid, mode, message, errors}
  const [schemaCheck, setSchemaCheck] = useState(null)

  useEffect(() => {
    if (!hostRef.current) return undefined
    const common = [basicSetup, yamlLang(), syntaxHighlighting(darkHighlight), cmTheme]
    const mv = new MergeView({
      parent: hostRef.current,
      orientation: 'a-b',
      highlightChanges: true,
      gutter: true,
      a: {
        doc: original || '',
        extensions: [...common, EditorState.readOnly.of(true), EditorView.editable.of(false)],
      },
      b: {
        doc: original || '',
        extensions: [
          ...common, makeYamlLinter(), lintGutter(),
          // k8s 키 자동완성 — basicSetup 의 autocompletion 이 언어 데이터로 이 소스를 병합
          yamlLang().language.data.of({ autocomplete: k8sCompletionSource }),
          EditorView.updateListener.of((u) => {
            if (u.docChanged) setText(u.state.doc.toString())
          }),
        ],
      },
    })
    mvRef.current = mv
    setText(original || '')
    setValidation(validateYaml(original || ''))   // 리소스 전환 시엔 즉시 반영(디바운스 없이)
    return () => {
      try { mv.destroy() } catch { /* noop */ }
      mvRef.current = null
      if (validateTimerRef.current) clearTimeout(validateTimerRef.current)
    }
  }, [original])

  useEffect(() => {
    if (validateTimerRef.current) clearTimeout(validateTimerRef.current)
    validateTimerRef.current = setTimeout(() => setValidation(validateYaml(text)), 250)
    return () => clearTimeout(validateTimerRef.current)
  }, [text])

  // 편집이 바뀌면 이전 스키마 검증 결과는 무효(오해 방지)
  useEffect(() => { setSchemaCheck(null) }, [text])

  async function runSchemaCheck() {
    setSchemaCheck({ loading: true })
    let r
    try { r = await api.validateResourceYaml(text) }
    catch (e) { r = { ok: false, error: String(e) } }
    setSchemaCheck(r || { ok: false, error: '검증 실패' })
  }

  function revert() {
    const mv = mvRef.current
    if (!mv) return
    mv.b.dispatch({ changes: { from: 0, to: mv.b.state.doc.length, insert: original || '' } })
  }

  const v = validation
  const changed = text !== (original || '')

  return (
    <div onClick={onClose} style={S.overlay}>
      <style>{MERGE_CSS}</style>
      <div onClick={(e) => e.stopPropagation()} style={S.panel}>
        {/* 헤더 */}
        <div style={S.header}>
          <div style={{ minWidth: 0 }}>
            <div style={S.title}>{title}</div>
            <div style={S.sub}>{kind}{namespace ? ` · ${namespace}` : ''} / {name}</div>
          </div>
          <div style={{ flex: 1 }} />
          <div style={S.legend}>왼쪽 원본 · 오른쪽 편집 (변경 줄 하이라이트)</div>
          <button className="btn btn-ghost btn-sm" onClick={onClose} style={{ marginLeft: 10 }}>
            <X size={14} />
          </button>
        </div>

        {/* 상태 바 */}
        <div style={S.bar}>
          {v.valid
            ? <span style={S.okBadge}><Check size={12} /> 문법 OK{changed ? ' · 변경됨' : ' · 변경 없음'}</span>
            : <span style={S.errBadge}><AlertTriangle size={12} /> YAML 오류{v.line ? ` (line ${v.line})` : ''}: {v.message}</span>}
          <span style={{ flex: 1 }} />
          <button className="btn btn-ghost btn-sm" onClick={runSchemaCheck}
            disabled={!v.valid || (schemaCheck && schemaCheck.loading)}
            title="kubectl 서버 dry-run 으로 스키마·CRD·admission 까지 검증(적용 안 함)"
            style={{ gap: 4 }}>
            {schemaCheck && schemaCheck.loading
              ? <><Loader2 size={12} className="spin" /> 검증 중…</>
              : <><ShieldCheck size={12} /> 스키마 검증</>}
          </button>
          <button className="btn btn-ghost btn-sm" onClick={revert} disabled={!changed}>
            <RotateCcw size={12} /> 원본 되돌리기
          </button>
        </div>

        {/* 스키마 검증 결과 */}
        {schemaCheck && !schemaCheck.loading && (
          <div style={{
            ...S.schemaBar,
            background: schemaCheck.valid ? 'rgba(52,211,153,0.10)'
              : 'rgba(248,113,113,0.10)',
            borderBottom: `1px solid ${schemaCheck.valid ? 'rgba(52,211,153,0.3)' : 'rgba(248,113,113,0.3)'}`,
          }}>
            {!schemaCheck.ok ? (
              <span style={S.errBadge}>
                <AlertTriangle size={12} /> 검증 실행 불가: {schemaCheck.error}
              </span>
            ) : schemaCheck.valid ? (
              <span style={S.okBadge}>
                <ShieldCheck size={12} /> 스키마 검증 통과
                <span style={S.modeTag}>{schemaCheck.mode === 'client' ? 'client dry-run' : 'server dry-run'}</span>
              </span>
            ) : (
              <div style={{ minWidth: 0, flex: 1 }}>
                <div style={S.errBadge}>
                  <ShieldAlert size={12} /> 스키마 위반 — 적용 시 거부됩니다
                  <span style={S.modeTag}>{schemaCheck.mode === 'client' ? 'client' : 'server'}</span>
                </div>
                <pre style={S.errList}>{(schemaCheck.errors || [schemaCheck.detail]).join('\n')}</pre>
              </div>
            )}
            <span style={{ flex: 1 }} />
            <button className="btn btn-ghost btn-sm" onClick={() => setSchemaCheck(null)}
              style={{ flexShrink: 0 }}><X size={12} /></button>
          </div>
        )}

        {/* 에디터 (MergeView) */}
        <div ref={hostRef} className="pol-yaml-merge" style={S.editorHost} />

        {/* 푸터 */}
        <div style={S.footer}>
          {footerExtra}
          <span style={S.hint}>{hint}</span>
          <span style={{ flex: 1 }} />
          <button className="btn btn-ghost btn-sm" onClick={onClose} disabled={busy}>취소</button>
          <button className="btn btn-primary btn-sm" onClick={() => onApply(text)}
            disabled={busy || !v.valid || !changed} style={{ gap: 4 }}>
            <Check size={12} /> {applyLabel}
          </button>
        </div>
      </div>
    </div>
  )
}

const S = {
  overlay: { position: 'fixed', inset: 0, zIndex: 1100, background: 'rgba(0,0,0,0.62)', display: 'grid', placeItems: 'center', padding: '2vh' },
  panel: { width: '92vw', height: '88vh', maxWidth: 1500, background: 'var(--bg-1, #0b0f1a)', border: '1px solid var(--border, #1c2133)', borderRadius: 10, boxShadow: '0 18px 64px rgba(0,0,0,0.6)', display: 'flex', flexDirection: 'column', overflow: 'hidden' },
  header: { display: 'flex', alignItems: 'center', gap: 8, padding: '12px 16px', borderBottom: '1px solid var(--border,#1c2133)', flexShrink: 0 },
  title: { fontSize: 14, fontWeight: 700, color: 'var(--text-bright,#f0f3fa)' },
  sub: { fontSize: 11.5, color: 'var(--text-dim,#8b93a7)', fontFamily: "var(--font-mono, monospace)", whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' },
  legend: { fontSize: 11, color: 'var(--text-dim,#8b93a7)', whiteSpace: 'nowrap' },
  bar: { display: 'flex', alignItems: 'center', gap: 8, padding: '8px 16px', borderBottom: '1px solid var(--border,#1c2133)', background: 'var(--bg-2,#0e1422)', flexShrink: 0 },
  okBadge: { display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--nimbus,#34d399)' },
  errBadge: { display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 11.5, color: 'var(--red,#f87171)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '72%' },
  editorHost: { flex: 1, minHeight: 0, overflow: 'hidden' },
  footer: { display: 'flex', alignItems: 'center', gap: 8, padding: '10px 16px', borderTop: '1px solid var(--border,#1c2133)', flexShrink: 0 },
  hint: { fontSize: 10.5, color: 'var(--text-dim,#8b93a7)' },
  schemaBar: { display: 'flex', alignItems: 'flex-start', gap: 8, padding: '8px 16px', flexShrink: 0, maxHeight: '28vh', overflowY: 'auto' },
  modeTag: { marginLeft: 8, fontSize: 9.5, padding: '1px 6px', borderRadius: 4, background: 'rgba(148,163,184,0.18)', color: 'var(--text-dim,#8b93a7)', fontWeight: 600 },
  errList: { margin: '6px 0 0', fontSize: 10.5, lineHeight: 1.5, color: 'var(--text,#cdd6e6)', fontFamily: "var(--font-mono, monospace)", whiteSpace: 'pre-wrap', wordBreak: 'break-word' },
}
