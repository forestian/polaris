/**
 * CHECK 탭 — 클러스터 점검 · 보고서 화면 목록.
 *
 * 사이드바(components/CheckSidebar.jsx)와 명령 팔레트가 **같은 목록**을 쓴다.
 * cluster: 클러스터를 대상으로 하는 화면 — 제목표시줄에 클러스터 탭을 띄우고, 연결이 없으면 안내한다.
 * line · target · output 은 화면 맨 위 공통 머리(CheckPageHead)에 그대로 나온다 — 한 줄로 짧게.
 */
export const CHECK_GROUPS = [
  {
    id: 'cluster', label: '클러스터',
    items: [
      { id: 'health', label: '클러스터 스캔', sub: '헬스 체크 · 네트워크 스캔', cluster: true,
        line: '정해진 규칙으로 클러스터의 이상 징후를 바로 찾습니다.',
        target: '클러스터', output: '화면' },
      { id: 'upgrade', label: '업그레이드 사전 점검', sub: '사라지는 API · 버전 차이', keys: 'drain 방해', cluster: true,
        line: '목표 버전으로 올리기 전에 막히거나 서비스가 끊길 곳(사라지는 API · drain 방해 · 애드온)을 찾습니다.',
        target: '클러스터', output: '화면 · DOCX' },
      { id: 'report', label: '클러스터 보고서', sub: '점검 결과 DOCX', cluster: true,
        line: '연결한 클러스터를 점검해 단계별로 고른 내용을 보고서로 냅니다.',
        target: '클러스터', output: 'DOCX' },
    ],
  },
]

export const CHECK_PAGES = CHECK_GROUPS.flatMap(g => g.items.map(it => ({ ...it, group: g.id })))

export function visibleCheckGroups() {
  return CHECK_GROUPS
}

export function checkPage(id) {
  return CHECK_PAGES.find(p => p.id === id) || null
}

/** 저장된 화면이 지금 없으면 첫 화면으로 */
export function resolveCheckPage(id) {
  return (CHECK_PAGES.find(p => p.id === id) || CHECK_PAGES[0]).id
}

/** 명령 팔레트 항목 */
export function checkPageItems(q) {
  const all = CHECK_PAGES.map(p => ({
    id: 'check:' + p.id, label: p.label, sub: p.sub, keys: p.keys, checkPage: p.id, kind: 'check-page', group: 'CHECK',
  }))
  if (!q) return all
  return all.filter(it => (it.label + ' ' + it.sub + ' ' + (it.keys || '') + ' ' + it.checkPage).toLowerCase().includes(q))
}
