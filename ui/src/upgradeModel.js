/**
 * 업그레이드 사전 점검 화면 로직 (v1.4.1) — 순수 함수(upgradeCheck.test.mjs 가 고정).
 * 판정은 백엔드(src/upgradecheck.py)가 하고 여기서는 표시 문구만 만든다.
 */

export const SEV_STYLE = {
  block: { label: '먼저 해결', color: '#f87171' },
  warn:  { label: '주의',      color: '#fb923c' },
  info:  { label: '참고',      color: '#60a5fa' },
}

export const CATEGORY_KO = {
  version: '버전 경로', api: '사라지는 API', skew: '버전 차이', health: '지금 상태',
  drain: '노드 비우기', addon: '애드온', scope: '점검 범위',
  // v1.5.24 공식 표 판정 · 설치된 애플리케이션
  gate: '기능 게이트 · 플래그', storage: '스토리지', notes: '공식 안내', app: '애플리케이션',
  rke2: 'RKE2',   // v1.5.30 RKE2 업그레이드 경로
}

export function verdictText(r) {
  const c = r?.counts || {}
  const to = r?.target ? `1.${r.target_minor}` : ''
  if (r?.verdict === 'blocked') {
    return { color: '#f87171', title: `업그레이드 전에 먼저 해결해야 할 문제가 ${c.block}건 있습니다`,
             sub: `${to} 로 올리기 전에 「먼저 해결」 항목을 처리하세요.` + (c.warn ? ` 주의 ${c.warn}건도 함께 확인하세요.` : '') }
  }
  if (r?.verdict === 'caution') {
    return { color: '#fb923c', title: `업그레이드를 막는 문제는 없지만, 주의할 항목이 ${c.warn}건 있습니다`,
             sub: '작업 중 서비스 중단이나 다음 배포 실패로 이어질 수 있는 항목입니다.' }
  }
  return { color: '#34d399', title: '업그레이드를 막는 문제가 없습니다',
           sub: `${to} 로 올릴 준비가 되었습니다. 오른쪽의 업그레이드 순서대로 진행하세요.` + (c.info ? ` 참고 ${c.info}건.` : '') }
}

/** 결과 전체를 글로 — 작업 문서 · 메신저에 붙여 넣는 용도 */
export function resultText(r) {
  if (!r) return ''
  const v = verdictText(r)
  const out = [`[업그레이드 사전 점검] ${r.version} → ${r.target}`, `판정: ${v.title}`, '']
  for (const f of r.findings || []) {
    out.push(`■ [${SEV_STYLE[f.severity]?.label || f.severity}] ${f.title}`)
    if (f.detail) out.push(`  ${f.detail}`)
    if (f.action) out.push(`  조치: ${f.action}`)
    for (const it of f.items || []) out.push(`  - ${it}`)
    if (f.more) out.push(`  - 그 밖에 ${f.more}건`)
    out.push('')
  }
  if ((r.passed || []).length) {
    out.push('■ 확인 완료')
    for (const p of r.passed) out.push(`  - ${p}`)
    out.push('')
  }
  out.push('■ 업그레이드 순서')
  ;(r.checklist || []).forEach((t, i) => out.push(`  ${i + 1}. ${t}`))
  return out.join('\n')
}
