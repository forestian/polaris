import React, { useEffect, useState } from 'react'
import { api } from '../api.js'
import { useApp } from '../store.jsx'
import { Server, RefreshCw, ShieldCheck, ShieldAlert, ShieldQuestion } from 'lucide-react'

/** ISO8601 → '2시간 전' 같은 상대 시각. 값이 없으면 '—'. */
function relTime(iso) {
  if (!iso) return '—'
  const t = Date.parse(iso)
  if (Number.isNaN(t)) return '—'
  const s = Math.max(0, Math.floor((Date.now() - t) / 1000))
  if (s < 60) return '방금'
  if (s < 3600) return `${Math.floor(s / 60)}분 전`
  if (s < 86400) return `${Math.floor(s / 3600)}시간 전`
  return `${Math.floor(s / 86400)}일 전`
}

// ── 컨트롤 플레인 준비 상태 (/readyz) ─────────────────────────────────────────
// **fail-open**: 조회가 막힌 클러스터(403/404)나 응답 없음은 「확인 불가」 회색으로 둔다.
// 못 읽은 것을 빨간불로 표시하면 멀쩡한 클러스터를 장애로 신고하는 셈이 된다.
function ControlPlaneCard({ readyz }) {
  if (!readyz) return null

  const unknown = !readyz.available
  const ok = !unknown && readyz.ok
  const failed = readyz.failed || []

  const tone = unknown ? 'var(--text-dim)' : ok ? 'var(--green)' : 'var(--red)'
  const Icon = unknown ? ShieldQuestion : ok ? ShieldCheck : ShieldAlert
  const title = unknown ? '컨트롤 플레인 — 확인 불가'
    : ok ? '컨트롤 플레인 정상'
    : `컨트롤 플레인 점검 필요 — ${failed.length}개 항목 실패`

  return (
    <div style={{
      background: 'var(--bg-2)', border: `1px solid ${unknown ? 'var(--border)' : tone}`,
      borderRadius: 10, padding: '12px 14px', marginBottom: 18,
    }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
        <Icon size={15} style={{ color: tone, flexShrink: 0 }} />
        <div style={{ fontSize: 13, fontWeight: 600, color: unknown ? 'var(--text)' : tone }}>
          {title}
        </div>
        <div style={{ flex: 1 }} />
        {!unknown && (
          <div style={{ fontSize: 11, color: 'var(--text-dim)', fontVariantNumeric: 'tabular-nums' }}>
            {readyz.passed}/{readyz.total} 통과
          </div>
        )}
      </div>

      {unknown && (
        <div style={{ fontSize: 11.5, color: 'var(--text-dim)', marginTop: 6, lineHeight: 1.5 }}>
          {readyz.reason || '조회할 수 없습니다.'}
          <br />
          장애를 뜻하는 것이 아닙니다 — 이 클러스터에서 <code>/readyz</code> 조회가 허용되지
          않았을 뿐입니다.
        </div>
      )}

      {!unknown && failed.length > 0 && (
        <div style={{ marginTop: 8 }}>
          {failed.slice(0, 6).map((f, i) => (
            <div key={i} style={{ fontSize: 11.5, color: 'var(--red)', paddingLeft: 23 }}>
              ✗ {f.name}{f.detail && f.detail !== f.name ? ` — ${f.detail}` : ''}
            </div>
          ))}
          {failed.length > 6 && (
            <div style={{ fontSize: 11, color: 'var(--text-dim)', paddingLeft: 23, marginTop: 2 }}>
              외 {failed.length - 6}건
            </div>
          )}
        </div>
      )}

      {!unknown && ok && (
        <div style={{ fontSize: 11.5, color: 'var(--text-dim)', marginTop: 5, paddingLeft: 23 }}>
          etcd · scheduler · controller-manager 등 API 서버가 보고하는 준비 항목 전체 통과
        </div>
      )}
    </div>
  )
}

// ── KPI 카드 (시안 B 스타일) ───────────────────────────────────────────────────
function KpiCard({ label, value, suffix, sub, color = 'var(--nimbus)' }) {
  return (
    <div style={{
      background: 'var(--bg-2)', border: '1px solid var(--border)',
      borderRadius: 10, padding: 14, position: 'relative', overflow: 'hidden',
    }}>
      <div style={{
        fontSize: 10.5, color: 'var(--text-dim)', letterSpacing: '0.06em',
        textTransform: 'uppercase', fontWeight: 600,
      }}>{label}</div>
      <div style={{ marginTop: 6, display: 'flex', alignItems: 'baseline', gap: 4 }}>
        <span style={{
          fontSize: 30, fontWeight: 700, color, letterSpacing: '-0.02em',
          fontVariantNumeric: 'tabular-nums', lineHeight: 1,
        }}>{value ?? '—'}</span>
        {suffix && <span style={{ fontSize: 14, color: 'var(--text-dim)' }}>{suffix}</span>}
      </div>
      {sub && <div style={{ fontSize: 11, color: 'var(--text-dim)', marginTop: 3 }}>{sub}</div>}
    </div>
  )
}

// ── 섹션 제목 ─────────────────────────────────────────────────────────────────
function SectionTitle({ children, right }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 10 }}>
      <div style={{
        fontSize: 11, fontWeight: 700, color: 'var(--text-mid)',
        letterSpacing: '0.07em', textTransform: 'uppercase',
      }}>{children}</div>
      {right}
    </div>
  )
}

// ── 사용률 바 ─────────────────────────────────────────────────────────────────
function UsageBar({ label, pct, used, total, color }) {
  const width = Math.max(0, Math.min(Number(pct) || 0, 100))
  return (
    <div style={{ marginBottom: 8 }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
        <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>{label}</span>
        <span style={{ fontSize: 10, color: 'var(--text-mid)', whiteSpace: 'nowrap' }}>
          {used} / {total} ({width}%)
        </span>
      </div>
      <div style={{ height: 4, borderRadius: 2, background: 'var(--bg-4)', overflow: 'hidden' }}>
        <div style={{
          height: '100%', borderRadius: 2, width: `${width}%`,
          background: width > 85 ? 'var(--red)' : width > 70 ? 'var(--yellow)' : color,
          transition: 'width 0.5s ease',
        }} />
      </div>
    </div>
  )
}

// ── 노드 카드 ────────────────────────────────────────────────────────────────
function formatCpu(m = 0) {
  const v = Number(m) || 0
  return v >= 1000 ? `${(v / 1000).toFixed(1)}Core` : `${v}m`
}
function formatMem(mi = 0) {
  const v = Number(mi) || 0
  return v >= 1024 ? `${(v / 1024).toFixed(1)}GiB` : `${v}MiB`
}

function NodeCard({ node }) {
  const ok = node.status === 'Ready'
  const podPct = node.max_pods > 0 ? Math.round(node.pod_count / node.max_pods * 100) : 0
  const cpuStr = formatCpu(node.cpu_alloc_m)
  const memStr = formatMem(node.mem_alloc_mi)
  const hasMetrics = Boolean(node.metrics_available)

  return (
    <div style={{
      background: 'var(--bg-2)',
      border: `1px solid ${ok ? 'var(--border)' : '#7f1d1d'}`,
      borderRadius: 10, padding: '14px 16px', minWidth: 0,
    }}>
      {/* 이름 + 상태 */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8, minWidth: 0 }}>
          <div style={{
            width: 8, height: 8, borderRadius: '50%', flexShrink: 0,
            background: ok ? 'var(--nimbus)' : 'var(--red)',
            boxShadow: ok ? '0 0 6px var(--nimbus)' : 'none',
          }} />
          <div style={{ minWidth: 0 }}>
            <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--text-bright)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
              {node.name}
            </div>
            <div style={{ fontSize: 9.5, color: 'var(--text-dim)', fontFamily: 'var(--font-mono)' }}>
              {node.role}
            </div>
          </div>
        </div>
        <span className={`chip ${ok ? 'chip-green' : 'chip-red'}`} style={{ fontSize: 10 }}>
          {node.status}
        </span>
      </div>

      {/* 파드 */}
      <div style={{ marginBottom: 6 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
          <span style={{ fontSize: 10, color: 'var(--text-dim)' }}>파드</span>
          <span style={{ fontSize: 10, color: 'var(--text-mid)' }}>{node.pod_count} / {node.max_pods}</span>
        </div>
        <div style={{ height: 4, borderRadius: 2, background: 'var(--bg-4)', overflow: 'hidden' }}>
          <div style={{
            height: '100%', borderRadius: 2,
            width: `${podPct}%`,
            background: podPct > 80 ? 'var(--yellow)' : 'var(--nimbus)',
            transition: 'width 0.5s ease',
          }} />
        </div>
      </div>

      {hasMetrics ? (
        <>
          <UsageBar label="CPU" pct={node.cpu_pct} used={formatCpu(node.cpu_used_m)} total={cpuStr} color="var(--nimbus)" />
          <UsageBar label="MEM" pct={node.mem_pct} used={formatMem(node.mem_used_mi)} total={memStr} color="var(--blue)" />
        </>
      ) : node.cpu_alloc_m > 0 && (
        <div style={{ fontSize: 10, color: 'var(--text-dim)', lineHeight: 1.6 }}>
          <div>CPU {cpuStr} · MEM {memStr}</div>
          {/* --text-dim 위에 opacity 를 또 얹으면 이중으로 흐려진다 — 색만으로 충분히 옅다 */}
          <div style={{ color: 'var(--text-dim)' }}>metrics-server 없음</div>
        </div>
      )}
    </div>
  )
}

// ── 상태 칩 ──────────────────────────────────────────────────────────────────
function StatusBadge({ status }) {
  const s = String(status || '').toLowerCase()
  const isOk   = s === 'running' || s === 'succeeded' || s === 'completed'
  const isWarn = s === 'pending' || s.startsWith('containercreating') || s.startsWith('init')
  return (
    <span className={`chip ${isOk ? 'chip-green' : isWarn ? 'chip-yellow' : 'chip-red'}`}>
      {status}
    </span>
  )
}

// ── 메인 페이지 ──────────────────────────────────────────────────────────────
export default function Dashboard() {
  const { connected, clusterName, setShowConnect } = useApp()
  const [data, setData]       = useState(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    if (!connected) return
    setLoading(true)
    try { setData(await api.getDashboard()) } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [connected])

  if (!connected) return (
    <div className="empty-state" style={{ height: '100%' }}>
      <Server size={40} opacity={0.3} />
      <p>클러스터에 연결되지 않았습니다.</p>
      <button className="btn btn-primary" onClick={() => setShowConnect(true)}>
        kubeconfig 연결
      </button>
    </div>
  )

  const pods    = data?.pods  || []
  const nodes   = data?.nodes || []
  const running  = pods.filter(p => p.status === 'Running').length
  const notReady = nodes.filter(n => n.status !== 'Ready').length
  const restarts = data?.total_restarts || 0
  const nsCnt    = data?.namespace_count || 0

  // 「주의가 필요한 파드」 — 선별은 백엔드 select_attention_pods(순수 함수)가 한다.
  // 규칙 두 개: ① 지금 비정상이면 항상 ② 정상인데 3일 내 재시작. 최대 10건.
  // ①이 없으면 ImagePullBackOff·Pending 처럼 **한 번도 못 뜬 파드**(restarts=0)가
  // 기간 필터에 걸려 사라진다 — 정작 가장 급한 것들이다.
  const attention = data?.attention || { items: [], total: 0, truncated: false }
  const attnPods = attention.items || []

  return (
    <div style={{ height: '100%', overflowY: 'auto', padding: '20px 22px' }}>

      {/* ── 헤더 ── */}
      <div style={{ marginBottom: 18 }}>
        <div style={{ fontSize: 10.5, color: 'var(--text-dim)', letterSpacing: '0.1em', textTransform: 'uppercase' }}>
          DASHBOARD{clusterName ? ` · ${clusterName}` : ''}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 4 }}>
          <h1 style={{ fontSize: 20, fontWeight: 700, color: 'var(--text-bright)', letterSpacing: '-0.02em', margin: 0 }}>
            {/* 비정상 판정을 백엔드와 같은 기준으로 쓴다. 예전엔 phase 만 봐서
                CrashLoopBackOff(phase=Running) 파드가 있어도 '양호합니다'가 떴다 —
                아래 표에는 빨갛게 나오는데 제목은 양호라고 하는 모순이었다. */}
            {notReady === 0 && (attention.abnormal_count || 0) === 0
             && (data?.readyz?.available ? data.readyz.ok : true)
              ? '클러스터 상태가 양호합니다'
              : '클러스터 점검이 필요합니다'}
          </h1>
          <button className="btn btn-default btn-sm" onClick={load} disabled={loading}>
            <RefreshCw size={12} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
            새로고침
          </button>
        </div>
        <div style={{ fontSize: 12, color: 'var(--text-dim)', marginTop: 4 }}>
          {nodes.length}개 노드 · {pods.length}개 파드 · {nsCnt}개 네임스페이스
        </div>
      </div>

      {/* ── KPI 카드 ── */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12, marginBottom: 18 }}>
        <KpiCard
          label="노드"
          value={nodes.length}
          sub={notReady > 0 ? `NotReady ${notReady}개` : '모두 Ready'}
          color={notReady > 0 ? 'var(--red)' : 'var(--nimbus)'}
        />
        <KpiCard
          label="파드"
          value={pods.length}
          sub={`Running ${running}개`}
          color="var(--blue)"
        />
        <KpiCard
          label="네임스페이스"
          value={nsCnt || '—'}
          sub="활성 워크로드"
          color="var(--purple)"
        />
        <KpiCard
          label="총 재시작"
          value={restarts}
          sub={restarts > 50 ? '점검 권장' : '정상 범위'}
          color={restarts > 100 ? 'var(--red)' : restarts > 30 ? 'var(--yellow)' : 'var(--text-bright)'}
        />
      </div>

      {/* ── 컨트롤 플레인 준비 상태 ── */}
      <ControlPlaneCard readyz={data?.readyz} />

      {/* ── 노드 상태 ── */}
      {nodes.length > 0 && (
        <section style={{ marginBottom: 20 }}>
          <SectionTitle>NODES</SectionTitle>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 10 }}>
            {nodes.map(n => <NodeCard key={n.name} node={n} />)}
          </div>
        </section>
      )}

      {/* ── 주의가 필요한 파드 ── */}
      {pods.length > 0 && (
        <section>
          <SectionTitle
            right={
              <span style={{ fontSize: 11, color: 'var(--text-dim)' }}>
                {attention.abnormal_count > 0 && (
                  <span style={{ color: 'var(--red)', fontWeight: 600, marginRight: 10 }}>
                    ⚠ 비정상 {attention.abnormal_count}개
                  </span>
                )}
                {/* 상한으로 자른 걸 조용히 숨기면 "10개뿐"으로 오독된다 */}
                {attention.truncated
                  ? `${attnPods.length}개 표시 · 전체 ${attention.total}개`
                  : `${attention.total}개`}
              </span>
            }
          >
            주의가 필요한 파드
          </SectionTitle>

          <div style={{ background: 'var(--bg-2)', border: '1px solid var(--border)', borderRadius: 10, overflow: 'hidden' }}>
            {attnPods.length === 0 ? (
              <div style={{ padding: '18px 14px', fontSize: 12, color: 'var(--text-dim)' }}>
                비정상 파드가 없고, 최근 {attention.window_days ?? 3}일 내 재시작한 파드도 없습니다.
              </div>
            ) : (<>
            {/* 헤더 — AGE(파드 생성 나이) 대신 「최근 재시작」을 둔다. 이 목록에서는
                파드가 얼마나 오래됐는지보다 언제 재시작했는지가 판단에 쓰인다. */}
            <div style={{
              display: 'grid',
              gridTemplateColumns: '2.3fr 1.2fr 130px 66px 88px 100px',
              columnGap: 8,
              padding: '10px 14px', fontSize: 10, fontWeight: 600,
              color: 'var(--text-mid)', textTransform: 'uppercase',
              letterSpacing: '0.05em', borderBottom: '1px solid var(--border)',
              position: 'sticky', top: 0, background: 'var(--bg-2)',
            }}>
              <div>이름</div>
              <div>네임스페이스</div>
              <div>상태 · 사유</div>
              <div style={{ textAlign: 'right' }}>재시작</div>
              <div>최근 재시작</div>
              <div>노드</div>
            </div>

            {/* 행 */}
            {attnPods.map((p, i) => (
              <div key={`${p.namespace}/${p.name}`} style={{
                display: 'grid',
                gridTemplateColumns: '2.3fr 1.2fr 130px 66px 88px 100px',
                columnGap: 8,
                padding: '8px 14px', fontSize: 12,
                borderBottom: i < attnPods.length - 1 ? '1px solid var(--border)' : 'none',
                fontVariantNumeric: 'tabular-nums',
                background: p.abnormal ? 'rgba(248,113,113,0.04)' : 'transparent',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, overflow: 'hidden' }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
                    background: p.abnormal ? 'var(--red)'
                      : p.status === 'Pending' ? 'var(--yellow)' : 'var(--green)',
                    boxShadow: p.abnormal ? 'none' : '0 0 5px var(--green)',
                  }} />
                  <span style={{ color: 'var(--text-bright)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', fontFamily: 'var(--font-mono)', fontSize: 11 }}>
                    {p.name}
                  </span>
                </div>
                <div style={{ color: 'var(--blue)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.namespace}</div>
                {/* 사유가 있으면 사유를 보여준다 — kubectl 의 STATUS 열과 같은 방식.
                    CrashLoopBackOff 파드의 phase 는 'Running' 이라 phase 만 쓰면 정상으로 보인다. */}
                <div style={{ overflow: 'hidden' }}><StatusBadge status={p.reason || p.status} /></div>
                <div style={{ textAlign: 'right', color: parseInt(p.restarts || 0) > 30 ? 'var(--yellow)' : 'var(--text)' }}>
                  {p.restarts}
                </div>
                <div style={{ color: p.recent_restart ? 'var(--yellow)' : 'var(--text-dim)' }}>
                  {relTime(p.restarted_at)}
                </div>
                <div style={{ color: 'var(--text-dim)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{p.node}</div>
              </div>
            ))}
            {attention.truncated && (
              <div style={{ padding: '8px 14px', fontSize: 11, color: 'var(--text-dim)',
                borderTop: '1px solid var(--border)' }}>
                외 {attention.total - attnPods.length}건 — 전체는 리소스 트리의 파드 목록에서 확인하세요.
              </div>
            )}
            </>)}
          </div>
        </section>
      )}

    </div>
  )
}
