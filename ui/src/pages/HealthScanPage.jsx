import CheckPageHead from '../components/CheckPageHead.jsx'
import React, { useState, useEffect } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { HeartPulse, Play, Loader2, AlertCircle, Sparkles, ShieldCheck, Network } from 'lucide-react'
import LlmConnectionTest from '../components/LlmConnectionTest.jsx'

// 탭을 떠났다 돌아와도 스캔 결과/옵션이 초기화되지 않도록 모듈 스코프에 유지
// (K8sPageView 가 activePage 별로 switch 렌더 → 탭 전환 시 이 컴포넌트가 언마운트됨).
// 클러스터를 바꾸면(switchKey 변경) 다른 클러스터의 결과이므로 캐시를 폐기한다.
let _scanCache = null   // { switchKey, result, err, netScan, useAI, llmUrl, llmModel, llmModels }

// 규칙 기반 클러스터 스캔 — 보고서와 동일한 평가 규칙을 온디맨드로 즉시 실행(파일 생성 없음).
// 「네트워크 스캔」을 켜면 네트워크 점검이 함께 수행된다(v1.2.121).
// 선택적으로 로컬 LLM 이 우선 조치를 요약해준다.
// 등급 색은 **토큰으로** (v1.3.36). 예전엔 빨강·주황·노랑·파랑을 박아 뒀는데,
// 밝은 테마에서 1.8~2.2:1 까지 떨어져 등급 글자가 안 보였다. 토큰은 4단계를
// 다 표현하진 못하지만 **빨강 → 노랑 → 파랑 → 흐림** 으로 내려가는 순서는
// 그대로 읽히고, 무엇보다 등급 이름(심각/높음/중간/낮음)이 옆에 적혀 있다.
const SEV = {
  critical: { label: '심각', color: 'var(--red)',      bg: 'rgba(248,113,113,0.14)' },
  high:     { label: '높음', color: 'var(--yellow)',   bg: 'rgba(251,146,60,0.14)' },
  medium:   { label: '중간', color: 'var(--blue)',     bg: 'rgba(251,191,36,0.14)' },
  low:      { label: '낮음', color: 'var(--text-mid)', bg: 'rgba(96,165,250,0.14)' },
  info:     { label: '정보', color: 'var(--text-dim)', bg: 'rgba(148,163,184,0.12)' },
}

export default function HealthScanPage() {
  const { connected, clusterSwitchKey } = useApp()
  // 현재 클러스터의 캐시만 복원(다른 클러스터 결과는 무시). K8sPageView 는 clusterSwitchKey
  // 로 재마운트되므로 컴포넌트 수명 동안 switchKey 는 불변 → seed 는 최초 1회만 평가.
  const seed = (_scanCache && _scanCache.switchKey === clusterSwitchKey) ? _scanCache : null
  const [result, setResult] = useState(seed?.result ?? null)
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState(seed?.err ?? '')
  const [netScan, setNetScan] = useState(seed?.netScan ?? false)
  const [useAI, setUseAI] = useState(seed?.useAI ?? false)
  const [llmUrl, setLlmUrl] = useState(seed?.llmUrl ?? 'http://localhost:1234')
  const [llmModel, setLlmModel] = useState(seed?.llmModel ?? 'local-model')
  const [llmModels, setLlmModels] = useState(seed?.llmModels ?? [])

  // 상태 변경 시마다 모듈 캐시에 기록 → 다음 마운트에서 복원. loading 은 저장하지 않는다
  // (스캔 도중 탭을 떠나면 재진입 시 다시 실행 가능한 상태여야 하므로).
  useEffect(() => {
    _scanCache = { switchKey: clusterSwitchKey, result, err, netScan, useAI, llmUrl, llmModel, llmModels }
  }, [clusterSwitchKey, result, err, netScan, useAI, llmUrl, llmModel, llmModels])

  function handleLlmModels(models) {
    setLlmModels(models)
    if (models.length && (!llmModel || llmModel === 'local-model')) setLlmModel(models[0])
  }

  async function scan() {
    setLoading(true); setErr('')
    try {
      // netScan 은 4번째 인자 — api.healthScan 이 positional 이라 순서가 고정이다
      const r = await api.healthScan(useAI, useAI ? llmUrl : '', llmModel, netScan)
      if (r?.ok) setResult(r)
      else { setResult(null); setErr(r?.error || '스캔 실패') }
    } catch (e) { setResult(null); setErr(String(e)) }
    finally { setLoading(false) }
  }

  if (!connected) {
    return <div style={{ padding: 40, color: 'var(--text-dim)', display: 'flex', alignItems: 'center', gap: 8 }}>
      <AlertCircle size={16} /> 클러스터에 연결되지 않았습니다.
    </div>
  }

  const counts = result?.counts || {}
  const groups = result ? [
    { key: 'immediate', label: '즉시 조치 (심각·높음)', items: result.immediate || [] },
    { key: 'short_term', label: '단기 조치 (중간)', items: result.short_term || [] },
    { key: 'backlog', label: '백로그 (낮음·정보)', items: result.backlog || [] },
  ] : []

  return (
    <div style={{ padding: '18px 22px', height: '100%', overflowY: 'auto' }}>
      <CheckPageHead page="health" icon={HeartPulse} style={{ marginBottom: 16 }}
        actions={<button className="btn btn-primary btn-sm" onClick={scan} disabled={loading} style={{ gap: 5 }}>
          {loading ? <Loader2 size={13} className="spin" /> : <Play size={13} />} 스캔 실행
        </button>} />

      {/* 네트워크 스캔 옵션 — 스캔 실행 전에 포함 여부를 고른다 */}
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8,
        padding: '10px 14px', marginBottom: 10 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12.5 }}>
          <input type="checkbox" checked={netScan} onChange={e => setNetScan(e.target.checked)} />
          <Network size={13} style={{ color: 'var(--nimbus)' }} />
          <span style={{ color: 'var(--text)' }}>
            네트워크 스캔 포함 (Service·Ingress 정합성 · 도달성 · TLS 인증서 만료)
          </span>
        </label>
        <div style={{ fontSize: 11.5, color: 'var(--text-dim)', marginTop: 6, lineHeight: 1.55 }}>
          <span style={{ color: 'var(--yellow)' }}>스캔 시간이 늘어납니다</span>
          {' '}— 대상 수에 따라 보통 <b style={{ color: 'var(--text)' }}>10~30초</b> 추가되며,
          최대 60초에서 끊고 남은 대상은 미점검으로 표시합니다.
          <br />
          클러스터에 아무것도 배포하지 않고 API 서버를 경유해 점검합니다. 시스템 네임스페이스는 제외합니다.
          <br />
          ClusterIP·kube-proxy 경로와 파드 간 통신(NetworkPolicy·CNI)은 점검 범위가 아닙니다.
        </div>
      </div>

      {/* AI 설명 옵션 */}
      <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8,
        padding: '10px 14px', marginBottom: 16 }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer', fontSize: 12.5 }}>
          <input type="checkbox" checked={useAI} onChange={e => setUseAI(e.target.checked)} />
          <Sparkles size={13} style={{ color: 'var(--nimbus)' }} />
          <span style={{ color: 'var(--text)' }}>AI 설명 포함 (로컬 LLM — 발견사항 근거로 우선 조치 요약)</span>
        </label>
        {useAI && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 10 }}>
            <div style={{ display: 'flex', gap: 8 }}>
              <input className="input" value={llmUrl} onChange={e => setLlmUrl(e.target.value)}
                placeholder="http://localhost:1234"
                style={{ flex: 2, minWidth: 0, fontSize: 12, fontFamily: 'var(--font-mono)' }} />
              <LlmConnectionTest url={llmUrl} onModels={handleLlmModels} compact />
            </div>
            <div>
              <input className="input" value={llmModel} onChange={e => setLlmModel(e.target.value)}
                placeholder="local-model" list="llm-models-health"
                style={{ width: '100%', fontSize: 12, fontFamily: 'var(--font-mono)' }} />
              {llmModels.length > 0 && (
                <datalist id="llm-models-health">
                  {llmModels.map(m => <option key={m} value={m} />)}
                </datalist>
              )}
            </div>
          </div>
        )}
      </div>

      {err && (
        <div style={{ padding: '10px 14px', borderRadius: 8, marginBottom: 14, fontSize: 12,
          background: 'rgba(239,68,68,0.12)', border: '1px solid rgba(239,68,68,0.3)', color: 'var(--red)' }}>
          {err}
        </div>
      )}

      {!result && !loading && (
        <div style={{ color: 'var(--text-dim)', fontSize: 13, padding: 20 }}>
          「스캔 실행」을 눌러 클러스터를 점검하세요.
        </div>
      )}

      {result && (
        <>
          {/* 심각도 카운트 */}
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
            {Object.entries(SEV).map(([k, s]) => (
              <div key={k} style={{ background: s.bg, borderRadius: 8, padding: '8px 14px', minWidth: 78 }}>
                <div style={{ fontSize: 22, fontWeight: 700, color: s.color, lineHeight: 1 }}>{counts[k] || 0}</div>
                <div style={{ fontSize: 10.5, color: 'var(--text-dim)', marginTop: 3 }}>{s.label}</div>
              </div>
            ))}
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginLeft: 'auto',
              color: (result.total === 0) ? 'var(--nimbus)' : 'var(--text-dim)', fontSize: 12 }}>
              {result.total === 0 && <ShieldCheck size={15} />}
              {result.total === 0 ? '이상 징후 없음' : `총 ${result.total}건 발견`}
            </div>
          </div>

          {/* 네트워크 스캔 점검 범위 — 무엇을 봤고 무엇을 안 봤는지 밝힌다.
              상한에 걸려 잘렸는데 "발견 없음"으로 읽히면 오독이므로 반드시 노출한다. */}
          {result.netscan && (
            <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)',
              borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 11.5,
              color: 'var(--text-dim)', lineHeight: 1.6 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 4,
                fontSize: 12, fontWeight: 600, color: 'var(--text)' }}>
                <Network size={13} style={{ color: 'var(--nimbus)' }} /> 네트워크 스캔 점검 범위
              </div>
              도달성 {result.netscan.probed_count}/{result.netscan.target_count}건
              {result.netscan.truncated && ` (후보 ${result.netscan.total_candidates}건)`}
              {' · '}제외 {result.netscan.skipped_count}건
              {' · '}TLS 인증서 {result.netscan.cert_count}
              {result.netscan.certs_total > 0 && `/${result.netscan.certs_total}`}건
              {' · '}{result.netscan.duration_s}초
              {/* 예산 초과로 못 본 게 있으면 반드시 밝힌다 — 조용히 빠지면 "정상"으로 오독된다 */}
              {result.netscan.budget_exceeded && (
                <div style={{ color: 'var(--yellow)', marginTop: 4, fontWeight: 600 }}>
                  ⚠ 시간이 초과되어 일부를 점검하지 못했습니다
                  {result.netscan.certs_skipped > 0
                    && ` (TLS 인증서 ${result.netscan.certs_skipped}건 미점검)`}
                  {result.netscan.target_count > result.netscan.probed_count
                    && ` (도달성 ${result.netscan.target_count - result.netscan.probed_count}건 미점검)`}
                  {' '}— 「발견 없음」이 「정상」을 뜻하지 않습니다.
                </div>
              )}
              {result.netscan.truncated && (
                <div style={{ color: 'var(--yellow)', marginTop: 4 }}>
                  대상이 상한을 넘어 일부만 점검했습니다 — 「발견 없음」이 「정상」을 뜻하지 않습니다.
                </div>
              )}
              {result.netscan.permission === 'denied' && (
                <div style={{ color: 'var(--yellow)', marginTop: 4 }}>
                  이 kubeconfig 에 services/proxy 권한이 없어 도달성 점검을 건너뛰었습니다
                  (정합성·TLS 결과만 유효).
                </div>
              )}
            </div>
          )}

          {/* AI 설명 */}
          {result.explanation && (
            <div style={{ background: 'rgba(52,211,153,0.08)', border: '1px solid rgba(52,211,153,0.3)',
              borderRadius: 8, padding: '12px 14px', marginBottom: 16 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 6, marginBottom: 6,
                fontSize: 12, fontWeight: 600, color: 'var(--nimbus)' }}>
                <Sparkles size={13} /> AI 우선 조치 요약
              </div>
              <div style={{ fontSize: 12.5, color: 'var(--text)', lineHeight: 1.6, whiteSpace: 'pre-wrap' }}>
                {result.explanation}
              </div>
            </div>
          )}
          {result.explain_error && (
            <div style={{ fontSize: 11.5, color: 'var(--red)', marginBottom: 14 }}>{result.explain_error}</div>
          )}

          {/* 그룹별 발견사항 */}
          {groups.map(g => g.items.length > 0 && (
            <div key={g.key} style={{ marginBottom: 18 }}>
              <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)', marginBottom: 8 }}>
                {g.label} <span style={{ color: 'var(--text-dim)', fontWeight: 400 }}>· {g.items.length}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {g.items.map((it, i) => {
                  const s = SEV[it.severity] || SEV.info
                  return (
                    <div key={i} style={{ display: 'flex', gap: 10, alignItems: 'flex-start',
                      background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 8,
                      padding: '9px 12px' }}>
                      <span style={{ flexShrink: 0, fontSize: 10, fontWeight: 700, padding: '2px 7px',
                        borderRadius: 4, background: s.bg, color: s.color }}>{s.label}</span>
                      <div style={{ minWidth: 0, flex: 1 }}>
                        <div style={{ fontSize: 12, color: 'var(--text-bright)', fontFamily: 'var(--font-mono)',
                          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                          {it.target} <span style={{ color: 'var(--text-dim)' }}>· {it.value}</span>
                        </div>
                        <div style={{ fontSize: 11.5, color: 'var(--text)', marginTop: 2 }}>{it.detail}</div>
                        {it.recommendation && (
                          <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 2 }}>
                            권장: {it.recommendation}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
            </div>
          ))}
        </>
      )}
    </div>
  )
}
