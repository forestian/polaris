# Bastion Changelog

이 문서는 Bastion (Windows Kubernetes 클러스터 관리 GUI) 의 모든 변경/패치 내역을 기록합니다.

버전 표기 규칙:
- `vX.0` — 메이저 (전면 개편)
- `vX.Y` — 마이너 (기능 추가)
- `vX.Y.Z` — 패치 (버그 수정 / 작은 개선)

---

## v3.8.0-r1 — 2026-05-19  ·  포트포워딩 GUI 관리 패널 + 앱 카탈로그 [실험적]

### 추가
- **포트포워딩 탭 추가**: 네임스페이스별 Service/Pod를 선택하고 원격 포트와 로컬 포트를 지정해 `kubectl port-forward` 세션을 GUI에서 시작할 수 있습니다.
- **상시 세션 목록**: 실행 중인 포트포워딩을 상태(`starting` / `running` / `error`), 흐름(`localhost:<port> -> resource:<port>`), PID, 연결 이벤트와 함께 확인할 수 있습니다.
- **원클릭 종료**: 세션별 종료 버튼으로 백그라운드 `kubectl port-forward` 프로세스를 즉시 정리합니다.
- **서비스/파드 포트 자동 인식**: Service `spec.ports[*].port`와 Pod container port를 읽어 포트 선택지를 자동 구성하며, 포트 정보가 없는 Pod는 직접 입력할 수 있습니다.

### 개선
- `kubectl -n <namespace> port-forward ...`, `kubectl --namespace <namespace> logs -f ...`, `kubectl get pods --watch`처럼 전역 옵션이 앞에 오는 스트리밍 명령도 터미널에서 정상적으로 백그라운드 실행으로 감지합니다.
- 클러스터 제거 또는 완전 종료 시 실행 중인 포트포워딩 세션을 함께 종료해 고아 `kubectl` 프로세스가 남지 않도록 했습니다.
- GitLab release 다운로드 링크가 브랜치 HEAD가 아니라 해당 태그의 EXE를 직접 가리키도록 릴리스 생성 스크립트를 보정했습니다.

### 유지
- `experimental` 브랜치의 앱 카탈로그 및 스택 설치 기능은 유지됩니다.

### 산출물
- `dist/bastion-v3.8.0-r1.exe` 생성 예정

---

## v3.7.15-r11 — 2026-05-18  ·  스택 묶음 3종 (LGTM / 로그+트레이싱 / 메트릭+Grafana) + 스택별 대시보드 자동 매핑 [실험적]

### 변경 (스택 묶음 설치 3종 구성)
사용자 피드백: "lgtm-full 카드에 Grafana 가 안 보여서 빠진 줄 알았다", "log-trace 가 Loki+Tempo 만 깔리니 어디서 보지?", "메트릭+Grafana 만 깔리는 옵션도 있으면 좋겠다".

기존 2종 → **3종 스택**으로 확장. 모두 Grafana 가 자동 설치되고 datasource·대시보드 자동 연동.

| 스택 ID | 앱 구성 | Grafana 출처 | 등록 datasource | 등록 대시보드 |
|---------|---------|-------------|----------------|--------------|
| **`lgtm-full`** | loki + tempo + alloy + kube-prometheus-stack | kube-prometheus-stack 내장 | (chart 기본) Prometheus/Alertmanager + Bastion ConfigMap Loki/Tempo | LGTM 통합 + Node Exporter Full + Logs App |
| **`log-trace`** | loki + tempo + alloy + **grafana (standalone)** | standalone grafana | Bastion ConfigMap Loki/Tempo | Logs App + **Traces App** |
| **`metrics-only`** (신규) | kube-prometheus-stack 만 | kube-prometheus-stack 내장 | (chart 기본) Prometheus/Alertmanager | **Node Exporter Full** |

### 추가 — `traces-app.json` 신규 대시보드 (10 패널)
폐쇄망 대응: grafana.com 의존 없는 자체 Tempo 트레이스 대시보드.
- 최근 트레이스 (table)
- 서비스 맵 (nodeGraph, Tempo serviceMap)
- 느린 트레이스 (`duration > 100ms`)
- 에러 트레이스 (`status = error`)
- TraceQL Metrics: 서비스별 트레이스 카운트 / 평균 지연 p95

### 내부 구조
- **`_build_grafana_k8s_manifests(..., *, datasources=None, dashboard_stems=None)`** — 시그니처 확장
  - `datasources`: `['prometheus'|'loki'|'tempo']` 부분집합. None = `['loki', 'tempo']` (기본). 빈 리스트 = datasource ConfigMap 안 만듦.
  - `dashboard_stems`: 적용할 대시보드 JSON 의 stem 리스트. None = 전체.
- **`_apply_grafana_k8s_manifests(..., datasources=None, dashboard_stems=None)`** — 동일 인자 그대로 전달.
- **`start_stack_install()`** — `catalog.json` 의 스택 메타에서 `grafana_datasources` / `grafana_dashboards` 를 읽어 hook 에 전달.
- **`catalog.json`** — 각 스택에 `grafana_datasources`, `grafana_dashboards`, `grafana_app_id` 필드 추가.

### 검증 (Rancher Desktop k3s 실증)
- 3 스택 모두 정상 설치 + Grafana 접속 후 datasource·대시보드 자동 등록 확인
- VERSION: `3.7.15-r10` → `3.7.15-r11`

---

## v3.7.15-r10 — 2026-05-18  ·  자체 대시보드 3종 + 한 번 설치로 Grafana 완전 연동 (폐쇄망 대응) [실험적]

### 목적
폐쇄망(인터넷 차단) 환경에서도 LGTM 풀체인 설치 한 번으로 Grafana 까지 **모든 datasource +
모든 핵심 대시보드**가 자동 등록되어 즉시 사용 가능하도록 한다. grafana.com gnetId
의존 완전 제거.

### 추가 — 자체 작성 대시보드 3종 (`catalog/dashboards/`)
- **`lgtm-integrated.json`** (기존, 15 패널) — 클러스터 헬스 · 노드 · 로그 · 트레이스 통합
- **`node-exporter-full.json`** (신규, **23 패널**) — Node Exporter Full 자체 작성판
  - 노드 개요 (Uptime / CPU 코어 / 메모리 / 사용률 / Load)
  - CPU 모드별 사용률 (user/system/iowait/idle/irq/softirq/steal/nice) + Load 평균
  - 메모리 분포 (used/buffers/cached/free) + Swap
  - 디스크 I/O Bytes/IOPS, 파일시스템 사용률 (마운트포인트별)
  - 네트워크 트래픽 (rx/tx bps) + 에러/드롭
  - 시스템 컨텍스트 스위치 + 인터럽트
  - 변수: Prometheus datasource 셀렉터 + node (multi-select)
- **`logs-app.json`** (신규, **13 패널**) — Loki 기반 로그 탐색
  - 개요 (총 로그 / ERROR / WARN / 활성 파드 수)
  - 네임스페이스 · 컨테이너별 수집량 추이 + Top 10 시끄러운 파드
  - 실시간 로그 스트림 (네임스페이스/검색어 정규식 필터)
  - 변수: Loki datasource + namespace 정규식 + 검색어 정규식

### 수정 (v3.7.14-r9 회귀 복구)
- **bastion.py post-install hook 경로 원복**: v3.7.14-r9 에서 `cat_dir / app_id` 로
  잘못 변경됐던 것을 `cat_dir` 로 되돌려 `catalog/dashboards/*.json` 을 정상 탐색.
  → 모든 대시보드 ConfigMap 이 정상 생성됨.
- **standalone grafana 차트 마운트 충돌 해결**: `catalog/grafana/values_*.yaml` 에서
  file-based `datasources` / `dashboardProviders` 블록을 완전히 제거.
  `chart 가 만드는 subPath 마운트 (datasources.yaml) vs sidecar emptyDir 디렉터리 마운트`
  가 같은 `/etc/grafana/provisioning/datasources` 에서 충돌하던 문제 (v3.7.14-r9 CrashLoopBackOff) 를
  근본 해결. **모든 datasource (Prometheus/Loki/Tempo) 는 Bastion ConfigMap 으로만 주입**.

### 내부 구조
- `_build_grafana_k8s_manifests(dash_dir, namespace, *, include_prometheus=False)` —
  `include_prometheus=True` 시 Prometheus datasource 도 ConfigMap 에 포함 (standalone grafana 용).
  kube-prometheus-stack 은 차트 자체가 Prometheus + Alertmanager 를 등록하므로 `False`.
- `_apply_grafana_k8s_manifests(..., *, app_id='')` — `app_id` 로 분기:
  - `'kube-prometheus-stack'` → Loki + Tempo + 대시보드 3종
  - `'grafana'` → Prometheus + Loki + Tempo + 대시보드 3종
- `start_catalog_install()` / `start_stack_install()` 양쪽 모두 `cat_dir` 전달 (sub-디렉터리 X)
- VERSION: `3.7.14-r9` → `3.7.15-r10`

### 검증 (Rancher Desktop k3s — 본 빌드 실증)
- LGTM 풀체인 (Loki → Tempo → Alloy → kube-prometheus-stack) 설치
- standalone grafana 도 분리 설치 (CrashLoopBackOff 재현 안 됨, 1/1 Ready)
- Grafana API `/api/datasources` → 4종 (Prometheus / Alertmanager / Loki / Tempo) 등록
- Grafana API `/api/search` → Bastion 폴더 + 3개 자체 대시보드 + chart 기본 28개 대시보드 등록
- 모든 패널 정상 렌더링 (Prometheus 메트릭 / Loki 로그 / Tempo 트레이스)

---

## v3.7.14-r9 — 2026-05-18  ·  standalone Grafana 데이터소스/대시보드 자동 연결 수정 [실험적]

### 수정
- **standalone `grafana` 앱: Loki·Tempo 데이터소스 미연결 + 대시보드 없음 수정**
  - 기존 `catalog/grafana/values_*.yaml`: Loki uid 없음, Tempo 포트 오류(3100→3200), sidecar 없음, dashboardProviders 가 빈 디렉터리를 가리킴
  - 신규: sidecar 활성화 (`sidecar.datasources.enabled: true` + `sidecar.dashboards.enabled: true`) → bastion post-install hook 이 ConfigMap 으로 Loki/Tempo datasource + 대시보드 자동 주입
  - `initChownData.enabled: false` 추가 (local-path / hostPath PVC 권한 충돌 방지)
  - Prometheus datasource 에 `uid: prometheus` 필드 추가

- **post-install hook 범위 확장**: `kube-prometheus-stack` 전용 → `kube-prometheus-stack`, `grafana` 공통으로 확장
  - `start_catalog_install()` / `start_stack_install()` 양 쪽 모두 수정
  - `cat_dir / app_id` 로 경로 교정 — 이전에는 `catalog/dashboards/` 를 탐색했으나 `catalog/<app_id>/dashboards/` 가 정확한 위치

---

## v3.7.13-r9 — 2026-05-18  ·  Tempo 차트 마이그레이션 + 내장 LGTM 대시보드 [실험적, app-catalog 기반]

### 변경 (Tempo 차트)
- **`grafana/tempo` → `grafana-community/tempo`** — deprecated 레포에서 공식 후속 레포로 이전
  - `repo_url`: `grafana.github.io/helm-charts` → `grafana-community.github.io/helm-charts`
  - 차트 버전: `1.24.4` → **`2.1.2`** / Tempo: `2.9.0` → **`2.10.5`**
  - values.yaml 구조 변경 없음 — 기존 설정 그대로 사용
  - Rancher Desktop 클러스터 직접 검증 완료

### 추가 (내장 대시보드 — kubectl apply 방식)
- **`grafana.com` gnetId 의존 완전 제거** — 폐쇄망·오프라인 환경 완전 대응
- **LGTM 통합 대시보드 (`lgtm-integrated.json`)** 신규 작성
  - 변수: Prometheus / Loki / Tempo 데이터소스 셀렉터 + 네임스페이스 필터
  - **클러스터 헬스**: Ready 노드, Running 파드, CPU/메모리 게이지, 24h 재시작, 비정상 파드
  - **노드 리소스**: 노드별 CPU·메모리 시계열 그래프 (mean/max 범례 테이블)
  - **로그(Loki)**: 레벨별 수집량 막대 차트 + 실시간 로그 스트림
  - **트레이스(Tempo)**: 최근 20건 트레이스 검색 패널

### 수정 (클러스터 실증 테스트 후 발견)
- **grafana chart 9.x sidecar 호환성 수정** — `grafana.dashboards` / `additionalDataSources`가 
  grafana chart 9.2.4 sidecar 모드에서 올바른 레이블 ConfigMap을 생성하지 않아 sidecar가 감지하지 못하는 문제
  - 기존: helm values 에 `grafana.dashboards` 블록 주입 → sidecar 감지 안 됨
  - 신규: kube-prometheus-stack helm 설치 완료 후 `kubectl apply` 로 ConfigMap 직접 생성
    - `bastion-lgtm-datasources` (label: `grafana_datasource: "1"`) — Loki + Tempo datasource
    - `bastion-dashboard-{name}` (label: `grafana_dashboard: "1"`, annotation: `grafana_folder: Bastion`) — 대시보드

### 내부 구조
- `_build_inline_dashboard_values()` → **`_build_grafana_k8s_manifests(dash_dir, namespace)`** 교체
  - 이전: helm values YAML block scalar 생성 (비작동)
  - 신규: kubectl apply 용 ConfigMap 매니페스트 YAML 생성 (multi-document)
- `_apply_grafana_k8s_manifests(kubectl, kube_flag, namespace, cat_dir, log)` 헬퍼 추가
  - `start_catalog_install()` / `start_stack_install()` 의 kube-prometheus-stack 설치 성공 시 자동 호출
- kube-prometheus-stack values (small/medium/large): `grafana.sidecar.dashboards.folderAnnotation: grafana_folder` 추가
  - Grafana "Bastion" 폴더에 대시보드 자동 분류

### 검증 (Rancher Desktop k3s 클러스터)
- LGTM 스택 4종 순서 설치: Loki ✅ → Tempo ✅ → Alloy ✅ → kube-prometheus-stack ✅
- 4종 datasource (Prometheus/Alertmanager/Loki/Tempo) Grafana 등록 ✅
- LGTM 통합 대시보드 Grafana 등록 ✅

---

## v3.7.14 — 2026-05-18  ·  앱 카탈로그 통합 (app-catalog-dev → master)

### 통합
- **app-catalog-dev 브랜치 → master 병합** — r1~r8.2 실험적 빌드에서 검증한 앱 카탈로그 기능을 정식 코드베이스에 통합
- 앱 카탈로그는 **실험적(Experimental)** 기능으로 유지 — 사이드바에 별도 표시
- 안정 버전 표기(v3.7.x)와 실험적 빌드(v3.7.x-rN) 트랙을 README에 구분 명시

### 포함된 변경 (r1 → r8.2 전체)
- 앱 카탈로그 페이지 신규 (kube-prometheus-stack / Grafana / Loki / Tempo / Alloy)
- 스택 묶음 설치 (`lgtm-full`, `log-trace`)
- 클러스터 프로필 자동 감지 + 프리셋 추천 (small/medium/large)
- Helm 자동 설치 (없을 경우 `~/.kube/helm.exe` 에 자동 다운로드)
- Helm 레이블 태깅 (`bastion-catalog=true`) + 설치 출처 구분 뱃지
- Grafana datasource 자동 등록 + 추천 대시보드 자동 임포트 (r8)
- Rancher Desktop 실 클러스터 검증 후 핫픽스 7건 (r8.1)
- PVC/PV 삭제 alias 버그 수정 (r8.2)
- subprocess `CREATE_NO_WINDOW` 일괄 적용 — CMD 창 깜빡임 제거 (r8.2)

### 빌드
- `dist/bastion-v3.7.14.exe` 예정 (코드베이스 통합, 빌드 별도 진행)

---

## v3.7.13-r8.2 — 2026-05-18  ·  PVC/PV 삭제 버그 + CMD 창 깜빡임 수정 [실험적, app-catalog-dev 브랜치]

사용자 보고 2건 수정. 실 클러스터 사용 중 발견된 UX 결함.

### 수정 (PVC/PV 삭제)
- **PVC/PV 삭제 시 `the server doesn't have a resource type "pvcs"` 에러** — `delete_resource()` 가 UI 측 short name(`pvcs`, `pvs`) 을 kubectl 정식 명(`persistentvolumeclaims`, `persistentvolumes`) 으로 변환하지 않고 그대로 전달하던 문제
  - `get_resource_yaml` / `get_resource_describe` 는 이미 `_KUBECTL_KIND_MAP` 으로 변환 중이었지만 `delete_resource` 에서만 누락
  - 이제 delete 호출 직전 alias 변환 추가

### 수정 (CMD 창 깜빡임)
- **카탈로그 / 스택 설치·제거 시 검은 cmd 창이 잠깐씩 깜빡이는 문제** — `subprocess.run` / `subprocess.Popen` 호출에 `creationflags=subprocess.CREATE_NO_WINDOW` 누락
- 누락 위치 9건 일괄 수정:
  - `start_catalog_install()` 의 helm repo add / repo update / kubectl create namespace / helm upgrade Popen
  - `start_stack_install()` 의 동일 4건
  - `uninstall_catalog_app()` 의 helm uninstall
- 추가로 Bastion 시작 시 매번 helm/kubectl 버전을 체크하던 `_probe()` 도 `_NO_WINDOW` 적용 (가장 잦았던 깜빡임 원인)

### 결과
- 카탈로그 설치·제거 시 콘솔 창이 더 이상 뜨지 않음
- Bastion 첫 실행 시 helm/kubectl probe 도 백그라운드 처리
- PVC / PV 모두 Bastion UI 에서 정상 삭제

---

## v3.7.13-r8.1 — 2026-05-18  ·  실 클러스터 검증 후 카탈로그 values 핫픽스 7건 [실험적, app-catalog-dev 브랜치]

Rancher Desktop 단일 노드 클러스터에서 LGTM 풀스택 직접 설치·검증 중 발견된 문제 일괄 수정.

### 수정 (Loki)
- **`chunks-cache` StatefulSet 메모리 9.6GiB 요청 → 단일 노드 OOM** — Loki 6.x 기본값이 분산 모드 기준이라 SingleBinary 모드에 과한 memcached subchart가 켜져 있었음
  - `chunksCache.enabled: false` + `resultsCache.enabled: false` (small/medium/large 3종)

### 수정 (Grafana datasource URL — 3건)
- **Loki URL** — `http://loki.logging.svc.cluster.local:3100` → **`http://loki-gateway.logging.svc.cluster.local`** (Loki helm 공식 권장 gateway 경유 URL)
  - kube-prometheus-stack `grafana.additionalDataSources` + Alloy `loki.write` 모두 수정
- **Tempo URL 포트 오기** — `:3100` → **`:3200`** (Tempo single-binary HTTP API 실제 포트, `:3100`은 Loki 포트라 혼동)
- **Loki datasource `uid` 명시** — Tempo 의 `tracesToLogsV2.datasourceUid: loki` 가 자동 생성 UID 와 불일치해 Tempo 화면에서 `"loki - not found"` 표시되던 문제. Loki datasource 에 `uid: loki` 고정.

### 수정 (Tempo)
- **ServiceMonitor CRD 누락 에러** — `serviceMonitor.enabled: true` 였으나 ServiceMonitor CRD 는 kube-prometheus-stack 이 설치하기 전이라 helm 이 `no matches for kind "ServiceMonitor"` 로 실패. `serviceMonitor.enabled: false` 로 끔 (필요 시 사용자가 켜기)

### 수정 (Grafana 재시작)
- **helm upgrade 시 grafana 새 파드 `init-chown-data` 권한 에러** — Rancher Desktop local-path PVC 가 이미 grafana uid 소유, busybox(root) 가 chown 못 함. `grafana.initChownData.enabled: false` (fsGroup 으로 충분)

### 검증 통과 항목 (Rancher Desktop 1 노드, k3s v1.35.4)
- ✅ 4개 helm 릴리스 모두 deployed, `bastion-catalog=true` 라벨 selector 정확 동작
- ✅ PVC 5개 모두 Bound (총 33Gi · local-path)
- ✅ Alloy DaemonSet 가 클러스터 전체 파드 로그 → Loki 인입 (1분당 ~2000줄)
- ✅ K8s 이벤트 실시간 인입 (`loki.source.kubernetes_events`)
- ✅ external_labels (`cluster=bastion-managed`, `source=alloy`) 정확
- ✅ Grafana datasource 자동 등록 (Prometheus / Loki / Tempo / Alertmanager)
- ✅ Loki / Prometheus Save & Test green
- ✅ Tempo `/api/echo` `/api/v2/search/tags` 정상 응답 (포트 정정 후)
- ✅ Bastion 폴더 자동 생성 + 대시보드 2개 자동 임포트 (Node Exporter Full #1860, Loki Logs #13639)

### 알려진 한계 (정상 동작)
- `grafana/tempo` chart deprecated 경고 — 작동은 함, r9 에서 후속 chart 마이그레이션 고려
- K3s / Rancher Desktop 의 일부 kube-prometheus-stack 기본 대시보드가 비어 보이는 현상 — etcd / scheduler / controller-manager 가 K3s 내장 프로세스라 별도 ServiceMonitor 없음 (r8.1 무관, K3s 특수성)

---

## v3.7.13-r8 — 2026-05-17  ·  즉시 사용 가능한 LGTM (Alloy + 자동 연동) [실험적, app-catalog-dev 브랜치]

### 추가
- **Grafana Alloy 카탈로그 앱 신규 추가** (`grafana/alloy` 차트 1.8.1 / Alloy v1.16.1)
  - DaemonSet 모드로 노드별 배포
  - **파드 로그** 수집: `discovery.kubernetes` (role=pod) + `loki.source.kubernetes`
  - **K8s 이벤트** 수집: `loki.source.kubernetes_events` (전체 클러스터 watch)
  - `loki.write` 로 `http://loki.logging.svc.cluster.local:3100/loki/api/v1/push` 자동 전송
  - external_labels: `cluster=bastion-managed`, `source=alloy`
- **Grafana datasource 자동 등록** (`kube-prometheus-stack` values 강화)
  - `additionalDataSources` 에 **Loki**, **Tempo** 자동 등록
  - Tempo ↔ Loki 트레이스→로그 자동 링크 (`tracesToLogsV2`)
  - Tempo serviceMap → Prometheus datasource 자동 연결
- **추천 대시보드 자동 임포트**
  - `Bastion` 폴더에 자동 생성
  - **Node Exporter Full** (Grafana.com #1860) — 노드 메트릭 종합
  - **Loki Logs / App** (Grafana.com #13639) — 로그 탐색

### 변경
- **Loki promtail 비활성화** — 로그·이벤트 수집은 Alloy 가 통합 담당
  - `loki/values_*.yaml` 의 `promtail.enabled: true` → `false`
- **LGTM 스택 재정의** (`lgtm-full`)
  - 기존: `kube-prometheus-stack + loki + tempo` (3개, 수동 연결 필요)
  - 신규: **`loki → tempo → alloy → kube-prometheus-stack`** (4개, 자동 연결)
  - 설치 순서가 중요: Loki/Tempo 가 먼저 떠야 Grafana datasource health check 가 성공
- **`log-trace` 스택** 도 Alloy 포함: `loki → tempo → alloy`

### 결과 (스택 설치 후)
- Grafana 접속 (admin/admin) → `Bastion` 폴더 → Node Exporter Full / Loki Logs 즉시 사용 가능
- Explore → Loki → `{cluster="bastion-managed"}` → 클러스터 파드 로그·이벤트 즉시 조회
- Explore → Tempo → 트레이스 (애플리케이션에서 OTLP 전송 시)

---

## v3.7.13-r7 — 2026-05-17  ·  스택 묶음 설치 [실험적, app-catalog-dev 브랜치]

### 추가
- **스택 묶음 설치** — 연관 앱 여러 개를 프리셋 하나로 순서대로 한번에 설치
  - `catalog.json` 에 `stacks` 배열 추가
    - **LGTM 풀 스택** (`lgtm-full`): Prometheus Stack + Loki + Tempo
    - **로그 + 트레이싱** (`log-trace`): Loki + Tempo
  - 백엔드 `start_stack_install()` — 앱별 values.yaml 자동 로드·치환 후 순차 설치, 레이블 자동 태깅 포함
  - 백엔드 `get_stack_install_status()` — 앱별 상태(`pending|running|done|error`) + 통합 로그 폴링
  - `get_catalog()` 에 `stacks` 필드 추가 (앱 메타 포함)
- **StackCard UI** — 카탈로그 탭 상단에 스택 카드 섹션 표시
  - 포함 앱 칩, 부분 설치 진행률 뱃지 (`N/M 설치됨`)
  - "한번에 설치 / 나머지 설치 / 전체 업그레이드" 상황별 버튼
- **StackInstallModal UI** — 스택 설치 전용 모달
  - 포함 앱 목록 + 앱별 설치 상태 아이콘 실시간 표시
  - 통합 프리셋 선택 (전체 앱 공통 적용)
  - 고급: 앱별 네임스페이스·릴리스 이름 개별 설정
  - 설치 로그 스트리밍 (2초 폴링)

---

## v3.7.13-r6 — 2026-05-17  ·  카탈로그 레이블 태깅 — 설치 출처 구분 [실험적, app-catalog-dev 브랜치]

### 추가
- **Helm 레이블 태깅** — `helm upgrade --install` 시 `--labels bastion-catalog=true,bastion-catalog-app-id=<id>` 플래그를 자동으로 추가
  - Helm 릴리스 메타데이터(K8s Secret)에 레이블이 영구 저장됨
  - `helm list --selector bastion-catalog=true` 로 카탈로그 설치 릴리스만 필터링 가능
- **레이블 기반 릴리스 식별** — `get_installed_catalog_apps()` 가 K8s Secret 레이블을 읽어 Bastion으로 설치된 릴리스를 신뢰성 있게 구분
  - `is_catalog_managed: true` — Bastion 카탈로그 설치 확인됨
  - `is_catalog_managed: false` — 차트명 퍼지 매칭만 됨 (수동 설치 또는 r6 이전 설치)
- **UI 출처 뱃지** — 카탈로그 카드 및 설치됨 탭에 **카탈로그 / 외부설치** 뱃지 추가
  - 레이블 확인된 릴리스: 초록 `카탈로그` 뱃지
  - 레이블 미확인 릴리스: 노란 `외부설치` 뱃지
- **제거 경고 강화** — 외부설치 릴리스 제거 시 "레이블 미확인 / 수동 설치 가능성" 경고 박스 표시

---

## v3.7.13-r5 — 2026-05-16  ·  카탈로그 차트 버전 업그레이드 + 앱 버전 표시 [실험적, app-catalog-dev 브랜치]

### 업그레이드
| 차트 | 구 버전 | 신 버전 | 실제 앱 버전 |
|------|---------|---------|------------|
| kube-prometheus-stack | 65.3.1 | **74.2.2** | Prometheus v3.4.1 · Grafana 12.0.1 |
| grafana | 8.3.4 | **10.5.15** | Grafana **12.3.1** |
| loki | 6.6.3 | **6.55.0** | Loki **3.6.7** (7.x는 GEL 전용 → OSS 최신 6.x 유지) |
| tempo | 1.9.0 | **1.24.4** | Tempo **2.9.0** |

### 추가
- **앱 버전 뱃지** — 카탈로그 카드에 차트 버전(helm chart 번호) 외에 실제 설치되는 앱 버전을 녹색 뱃지로 표시
  - `catalog.json` helm 객체에 `app_version` 필드 추가
- 모든 `values_*.yaml` 주석에 차트 버전 + 앱 버전 명시

---

## v3.7.13-r4 — 2026-05-16  ·  클러스터 메모리 0 버그 수정 + Helm 자동 설치 [실험적, app-catalog-dev 브랜치]

### 수정
- **클러스터 메모리 0 표시 버그** — `detect_cluster_profile()` 이 `get_nodes()` wrapper 를 사용해 `_raw` 없이 단순 dict 를 반환받았기 때문에 `status.allocatable` 접근에 실패하여 CPU·메모리가 항상 0으로 계산되던 문제 수정. `core.list_node().items` 를 직접 호출해 원시 k8s 객체에서 `allocatable` 을 읽도록 변경

### 추가
- **Helm 자동 설치** — 사전 점검에서 Helm CLI 가 없을 때 "자동 설치" 버튼 표시
  - `get.helm.sh/helm-latest-version` 에서 최신 버전 자동 조회 (실패 시 v3.17.3 폴백)
  - `helm-v{ver}-windows-amd64.zip` 다운로드 후 `~/.kube/helm.exe` 에 압축 해제
  - 설치 완료 즉시 사전 점검 화면을 자동 갱신해 Helm OK 상태 반영
  - 다운로드 중 스피너 표시, 실패 시 오류 메시지 인라인 표시

---

## v3.7.13-r3 — 2026-05-16  ·  앱 카탈로그 블랙스크린 수정 [실험적, app-catalog-dev 브랜치]

### 수정
- **탭 키 → 검은 화면 버그** — `InstallModal` / `UninstallConfirmModal` 백드롭 클릭 또는 `ESC` 키로 닫기 기능 추가 (Tab 포커스 → Space/Enter 오동작 시 모달이 화면을 가리는 문제 해결)
- 모달 외부(백드롭) 클릭 시 `onMouseDown` 이벤트로 닫기 처리 (설치 진행 중에는 비활성)
- `CatalogPage` 최상위 `div` 높이를 `height: '100%'` → `flex: 1, minHeight: 0` 으로 변경 — flex 부모에서 높이가 올바르게 계산되지 않아 콘텐츠 영역이 0px 로 축소되던 레이아웃 버그 해결
- `installedReleaseFor()` 의 `chartShort in (i.chart || '')` → `(i.chart || '').includes(chartShort)` 교정 (`in` 연산자는 문자열 포함 여부가 아닌 인덱스 존재를 검사함)

---

## v3.7.13-r2 — 2026-05-16  ·  앱 카탈로그 버그 수정 [실험적, app-catalog-dev 브랜치]

### 수정
- **카탈로그 앱 목록 빈 화면 버그** — `Promise.all` 구조 결함으로 `getInstalledCatalogApps` 실패 시 `getCatalog` 결과까지 묵살되던 문제 수정
- `_get_catalog_dir()` 경로 탐색을 `_MEIPASS → bastion.py → exe → cwd` 4단계 폴백으로 강화
- `_catalog_load_json()` 실패 원인을 `(data, error)` 튜플로 반환해 진단 가능하게 변경
- 카탈로그 로드 실패 시 에러 메시지 + 재시도 버튼을 UI에 표시

---

## v3.7.13-r1 — 2026-05-16  ·  앱 카탈로그 (App Catalog) [실험적, app-catalog-dev 브랜치]

### 추가 (실험적)
- **앱 카탈로그 페이지** — 사이드바 "앱 카탈로그" 메뉴로 접근, LGTM 스택을 클러스터에 원클릭 설치
  - 지원 앱 (Bitnami 미사용, 공식 차트만):
    - **kube-prometheus-stack** (prometheus-community) — Prometheus + Alertmanager + Grafana + Node Exporter 통합
    - **Grafana** (grafana/grafana) — 독립 설치 또는 기존 Prometheus 연결
    - **Loki** (grafana/loki 6.x) — 로그 수집, Promtail DaemonSet 자동 포함
    - **Tempo** (grafana/tempo) — 분산 트레이싱, OTLP/Jaeger/Zipkin 수신
  - **프리셋 3종** (small / medium / large) — 클러스터 노드 수 기반 자동 권장
  - **StorageClass 자동 감지** 및 values.yaml 플레이스홀더 자동 주입
  - **Preflight 체크** — helm CLI, 노드 수, 메모리, StorageClass 사전 검증
  - **실시간 설치 로그** — 2초 폴링, helm 출력 스트리밍
  - **고급 모드** — values.yaml 직접 편집 (토글)
  - **설치된 앱 탭** — Helm 릴리스와 카탈로그 앱 매핑하여 현황 표시
  - **제거 기능** — helm uninstall 래퍼
- **백엔드 API 추가**:
  - `get_catalog` — 카탈로그 앱 목록
  - `detect_cluster_profile` — 노드 수/StorageClass/CPU/메모리/권장 프리셋
  - `get_catalog_app_values` — 프리셋별 values.yaml 클러스터 자동 주입
  - `catalog_preflight` — 설치 전 사전 점검
  - `start_catalog_install` — 비동기 helm install/upgrade
  - `get_catalog_install_status` — 설치 진행 폴링
  - `uninstall_catalog_app` — helm uninstall
  - `get_installed_catalog_apps` — 설치된 카탈로그 앱 목록

### 카탈로그 구조
- `catalog/catalog.json` — 앱 인덱스 (메타, 차트 정보, preflight 조건)
- `catalog/<app>/values_{small,medium,large}.yaml` — 프리셋별 values 템플릿

### 비고
- Bitnami 차트 미사용 (prometheus-community + grafana 공식 차트만)
- 실험적 브랜치 `app-catalog-dev` — v3.7.13 기반, master 미병합
- EXE 빌드 시 `catalog/` 디렉터리 포함 (Bastion.spec 업데이트)

---

## v3.7.13 — 2026-05-15  ·  완전 종료 시 세션 초기화

### 수정
- **완전 종료 의미 정리**
  - 설정에서 `즉시 완전 종료`를 선택하고 X/Alt+F4로 닫는 경우 저장된 `~/.bastion/session.json`을 삭제하도록 변경
  - 트레이 메뉴의 `종료`도 `autoRestore` 설정과 관계없이 저장된 클러스터 탭 세션을 항상 삭제하도록 변경
  - 종료 중 React의 지연 자동 저장이 다시 세션 파일을 만들지 못하도록 백엔드 저장 차단 추가
  - 다시 EXE를 실행하면 이전 클러스터 탭이 복원되지 않고 빈 상태로 시작
- **트레이 최소화 동작 유지**
  - X/Alt+F4가 `시스템 트레이로 최소화`로 설정된 경우에는 창만 숨기고 현재 연결/탭은 유지

### UI/검증
- 설정 모달 문구를 완전 종료와 자동 복원 정책에 맞게 조정
- 완전 종료 및 트레이 종료의 세션 삭제/재저장 차단 회귀 테스트 추가
- `dist/bastion-v3.7.13.exe` 생성

---

## v3.7.12 — 2026-05-15  ·  시스템 트레이 종료/복구 안정화

### 수정
- **트레이 열기/종료 먹통 수정**
  - 트레이 메뉴 콜백에서 `window.show()`, `window.destroy()`, `icon.stop()`을 직접 호출하지 않고 생명주기 명령 큐로 전달하도록 변경
  - 닫기 이벤트(`closing`) 안에서 동기 `evaluate_js()` 알림을 호출하던 경로를 제거해 WebView/UI 루프 교착 가능성 차단
  - 트레이 `종료`는 세션 정책 처리, 클러스터 연결 해제, 창 destroy를 순서대로 수행하고 트레이 아이콘 정리는 메인 루프 종료 후 처리
- **중복 실행 방지**
  - 로컬 인스턴스 신호 서버(`127.0.0.1:43711`)를 추가해 이미 실행 중인 경우 새 프로세스는 기존 인스턴스에 "열기" 요청만 전달하고 종료
  - EXE를 반복 실행해도 프로세스와 트레이 아이콘이 계속 누적되지 않도록 방지
- **백그라운드 polling 가시성 처리 안정화**
  - 백엔드 JS 주입 의존도를 줄이고 프론트엔드에서 `visibilitychange` / `focus` / `blur` 이벤트를 함께 사용하도록 변경

### 빌드/검증
- `build.py --check`가 `pystray`, `PIL(Pillow)` 런타임 의존성까지 검사하도록 보강
- Vite 개발 의존성을 `vite@8.0.13`, `@vitejs/plugin-react@6.0.2`로 업데이트해 `npm audit` 취약점 0건 확인
- 트레이 닫기/큐 동작 회귀 테스트 추가
- `dist/bastion-v3.7.12.exe` 생성

---

## v3.7.11 — 2026-05-15  ·  시스템 트레이 + 자동 복원 옵션 + 백그라운드 polling 일시정지

### 추가
- **시스템 트레이 통합** — X 버튼 / Alt+F4를 누르면 작업 표시줄에서 사라지고 트레이로 이동
  - 트레이 우클릭 메뉴: **열기** (더블클릭과 동일) / **종료**
  - 트레이 "종료" 클릭 시: 모든 클러스터 연결 해제 + 프로세스 완전 종료
  - 아이콘은 nimbus 그린 배경 + 흰색 'B' 글자 (PIL로 동적 생성, 별도 파일 의존성 없음)
  - `pystray` + `Pillow` 의존성 추가
- **설정 페이지 (타이틀바 → 톱니바퀴 아이콘)** — 두 가지 토글
  - **창 닫기 동작**: 트레이로 최소화 (기본) / 즉시 완전 종료
  - **다음 실행 시 자동 복원**: 자동 복원 (기본) / 복원 안 함
    - "복원 안 함" 선택 시 종료 시점에 `~/.bastion/session.json` 자동 삭제
  - 저장 위치: `~/.bastion/settings.json`
- **백그라운드 polling 자동 일시정지** — 트레이로 hide된 동안 K8s API 폴링 일시정지
  - **MetricsTab**: 5초 폴링 중단 (windowVisible AND paused 가드)
  - **EventsPage**: autoRefresh 폴링 중단
  - **LogPage**: 로그 스트림 폴링 콜백 스킵 (백엔드 job은 살림)
  - 복원 시 자동 재개
- **백엔드 API**:
  - `get_settings()` / `save_settings(state)` 추가
  - `_notify_visibility(state)` — JS 커스텀 이벤트 `bastion:visibility` 발행
  - `_disconnect_all_clusters()` — 트레이 종료 시 일괄 정리

### 변경
- pywebview window의 `closing` 이벤트 가로채기 — 설정에 따라 hide 또는 destroy 선택

### 보안
- GitLab 릴리스 생성 스크립트의 토큰 하드코딩을 제거하고 `GITLAB_TOKEN` 환경변수 기반으로 변경

### 빌드
- `dist/bastion-v3.7.11.exe` 생성 (~23 MB, +2 MB Pillow)

---

## v3.7.10 — 2026-05-15  ·  이벤트 fallback 버그 수정

### 수정
- **v3.7.9 핫픽스** — `_format_events_core` / `_format_events_v1` 헬퍼가 잘못된 클래스(K8sManager)에 정의되어 `'BastionAPI' object has no attribute '_format_events_core'` 에러로 모든 클러스터의 이벤트 조회가 실패하던 문제 수정
- 헬퍼 메서드들을 `BastionAPI.get_cluster_events` 와 동일 클래스로 이동

### 빌드
- `dist/bastion-v3.7.10.exe` 생성

---

## v3.7.9 — 2026-05-15  ·  이벤트 수집 다중 fallback

### 개선
- **이벤트 수집 안정성** — 일부 클러스터에서 `list_event_for_all_namespaces` API가 RBAC/호환성 문제로 실패해 이벤트가 0건으로 보이던 문제 해결
  - **Path A**: `list_event_for_all_namespaces` 시도 (빠른 경로)
  - **Path B**: 실패 시 → 네임스페이스 순회 + namespaced 조회로 우회 (cluster-wide list 권한 없는 환경 대응)
  - **Path C**: B도 실패 시 → `events.k8s.io/v1` 신규 API 시도
  - 모든 시도 실패 시 → 시도 내역과 함께 에러 메시지 노출 (기존엔 조용히 빈 배열)
- **부분 실패 경고 표시** — 일부 네임스페이스 권한 없을 때 "N개 네임스페이스 권한 부족" 안내 노출
- **수집 방식 표시** — `all-ns` / `per-ns` / `events.k8s.io/v1` 중 어느 경로로 가져왔는지 UI에 표시
- **에러 시도 내역** — `<details>` 펼침으로 각 API 호출 결과 디버그 가능

### 변경 (호환성)
- `get_cluster_events` 반환 형식이 배열 → `{ok, events, source, warning?, error?, attempts}` 객체로 변경
- 프론트엔드는 구버전 배열 응답도 호환 처리

### 빌드
- `dist/bastion-v3.7.9.exe` 생성

---

## v3.7.8 — 2026-05-15  ·  파드 메트릭 실시간 그래프

### 추가
- **파드 메트릭 탭** — 리소스 패널(파드)에 "메트릭" 탭 신규
  - 5초마다 `metrics.k8s.io` API 폴링하여 시계열로 축적
  - **CPU / Memory 라인 차트 2개** — SVG 평활화(Catmull-Rom Bezier), 그라데이션 fill, 격자 + y축 눈금
  - **컨테이너별 라인** — 컨테이너 N개 시 N개 라인 + 색상 범례 (현재값 동시 표시)
  - **request / limit 임계선** — 노랑(req) / 빨강(lim) 점선 오버레이
  - **통계 칩** — 현재 / 평균 / 최대 (mCore / MiB)
  - **시간 윈도우 토글** — 5분 / 15분 / 1시간
  - **호버 인디케이터** — 차트 위 커서 위치의 정확한 시점 값 표시
  - **일시정지 / 재개** — 폴링 토글 버튼
  - metrics-server 미설치 시 안내 카드 + 설치 명령어 안내
- **백엔드 API** — `get_pod_metrics(ns, name)` 추가
  - 컨테이너별 CPU(mCore) / Memory(MiB), 합산, pod spec의 requests/limits 동시 반환

### 빌드
- `dist/bastion-v3.7.8.exe` 생성

---

## v3.7.7 — 2026-05-15  ·  아이콘 수정 + 다중 context 연결

### 수정
- **K9sPage 아이콘** — 페이지 헤더·플레이스홀더·버튼 아이콘이 `Terminal`로 표시되던 버그 수정 → `Monitor`로 변경
- **LogPage 아이콘** — 헤더·빈 상태 아이콘이 `Terminal`로 표시되던 버그 수정 → `ScrollText`로 변경

### 추가
- **kubeconfig 다중 context 연결** — 하나의 kubeconfig 파일에 여러 context가 있을 때 선택하여 각각 별도 탭으로 연결
  - 클러스터 연결 모달에서 파일 탐색 시 context 목록 자동 조회
  - 직접 경로 입력 시 "컨텍스트 불러오기" 버튼으로 수동 조회
  - current-context는 기본 선택, 체크박스로 복수 선택 가능
  - 단일 context 파일: 기존과 동일하게 즉시 연결
  - 복수 context 파일: context 목록 표시 → 선택 → "N개 연결" 버튼
  - 다른 kubeconfig 파일 불러오기 기능 그대로 유지
- **백엔드 API** — `list_kubeconfig_contexts(path)` 추가, `add_cluster(path, context)` 파라미터 확장
- **세션 복원** — 다중 context로 연결된 탭도 path+context 복합 키로 정확히 복원

### 빌드
- `dist/bastion-v3.7.7.exe` 생성

---

## v3.7.6 — 2026-05-15  ·  사이드바 상단 탐색 개편

### 변경
- **사이드바 TOP_PAGES에 로그뷰어 / k9s / kubectl 터미널 추가** — 보고서 아래 순서로 상단 고정 버튼으로 배치
- **사이드바 TREE "도구" 카테고리 제거** — 세 항목이 상단 스트립으로 이동하여 중복 제거
- **CommandPalette ⌘K 그룹 조정** — 로그뷰어·k9s·kubectl 터미널이 "도구" → "페이지" 그룹으로 이동

### 빌드
- `dist/bastion-v3.7.6.exe` 생성

---

## v3.7.5 — 2026-05-15  ·  이벤트 타임라인 + CronJob 즉시 실행

### 추가
- **이벤트 타임라인 페이지** — 사이드바 "이벤트" / ⌘K "이벤트 타임라인"으로 진입
  - 백엔드 `get_cluster_events(namespace, limit, types)` API 추가 — 활성 클러스터(또는 선택된 네임스페이스)의 이벤트 최대 500건
  - 시간축 SVG 차트: 1시간 / 6시간 / 24시간 윈도우, 분 단위(또는 5/15분) 버킷, Warning(빨강) + Normal(회색) 스택 막대
  - 버킷 클릭 → 해당 시간대 이벤트만 필터링, 다시 클릭으로 해제
  - 타입 필터(전체 / Warning / Normal) + 이유·대상·메시지 자유 텍스트 검색
  - 10초 자동 새로고침 토글
  - 이벤트 표: 시각 · 타입 · 이유 · 대상 · 메시지 · 횟수
- **CronJob 즉시 실행 (Trigger Now)** — ResourcePanel에서 CronJob 보기 시 "지금 실행" 버튼 노출
  - 백엔드 `trigger_cronjob(namespace, name)` API 추가 — 내부적으로 `kubectl create job <name>-manual-<unix-ts> --from=cronjob/<name>` 실행
  - 네임스페이스/이름 RFC1123 검증, Job 이름 63자 제한 보존
  - 확인 다이얼로그 후 실행, 결과를 패널 상단 인라인 메시지로 표시 (성공 시 생성된 Job 이름 안내)

### 빌드
- `dist/bastion-v3.7.5.exe` 생성

---

## v3.7.4 — 2026-05-15  ·  ⌘K 명령 팔레트 리소스 검색 확장

### 추가
- **리소스 이름 검색** — ⌘K 팔레트에서 클러스터의 실제 리소스 이름으로 검색 가능
  - 백엔드 `get_search_index` API 추가 — 활성 클러스터의 14종 리소스(Node/Namespace/Pod/Deployment/StatefulSet/DaemonSet/Service/Ingress/ConfigMap/Secret/PVC/PV/Job/CronJob)의 `(kind, name, namespace)` 경량 인덱스 반환
  - 클러스터별 30초 캐시 → 두 번째 ⌘K 열기는 즉시 표시
  - 쿼리 입력 시 매칭 리소스가 정적 메뉴 위에 우선 노출 (최대 60건)
  - 리소스 선택 시 해당 네임스페이스로 자동 전환 후 리소스 브라우저 열기
- **팔레트 푸터 상태 표시** — 인덱싱 진행 / 인덱스 건수 / 실패 메시지 노출

### 빌드
- `dist/bastion-v3.7.4.exe` 생성

---

## v3.7.3 — 2026-05-15  ·  세션 자동 복원 + ⌘K 명령 팔레트

### 추가
- **세션 자동 복원** — 앱 종료 시 마지막 클러스터 탭 구성과 활성 탭, 페이지, 네임스페이스를 `~/.bastion/session.json` 에 저장하고 재실행 시 자동 복원
  - 백엔드 API: `get_session`, `save_session`, `clear_session` 추가 (BastionAPI)
  - 프론트엔드 자동 저장(500 ms debounce): clusters · activeClusterId · activePage · activeResource · namespace 변경 시
  - 시작 시 저장된 path 목록을 순차적으로 `add_cluster()` 로 재연결하고 사용자 지정 이름은 `rename_cluster()` 로 재적용
  - 복원 실패는 조용히 skip 후 빈 상태로 fallback — 첫 실행 또는 kubeconfig 이동 시 안전하게 동작
- **⌘K 명령 팔레트** — 타이틀바의 검색 입력이 이제 실제 동작 (`Ctrl+K` / `Cmd+K` 단축키로도 토글)
  - 새 컴포넌트 `CommandPalette.jsx` — 페이지·리소스·클러스터 전환·명령을 단일 검색으로 통합
  - 키보드 네비게이션: ↑↓ 이동, Enter 실행, Esc 닫기
  - 검색 항목: 대시보드/토폴로지/보고서, 15종 리소스, Helm/ArgoCD/터미널/k9s/로그, 클러스터 전환, 새 클러스터 연결·새로고침 명령
  - 연결되지 않은 상태에서는 클러스터가 필요한 항목 자동 숨김

### 빌드
- `dist/bastion-v3.7.3.exe` 생성

---

## v3.7.2 — 2026-05-14  ·  클러스터 탭 전환 시 리소스 종류 유지 버그 수정

### 버그 수정
- **클러스터 탭 전환 시 리소스 브라우저 종류 미복원 수정** — 한쪽 탭에서 파드를, 다른 탭에서 레플리카셋을 보고 있다가 탭을 전환하면 리소스 종류가 유지되지 않던 문제 수정
  - `lastResource` 필드를 클러스터별로 저장하도록 추가
  - `navigate('resources', item)` 호출 시 `lastPage`와 함께 `lastResource`도 클러스터 상태에 저장
  - `switchCluster()` 복원 시 `lastPage`·`lastNamespace`에 더해 `lastResource`도 복원
  - `refreshClusters()` 병합 시 `lastResource` 필드 보존

### 빌드
- `dist/bastion-v3.7.2.exe` 생성

---

## v3.7.1-s1 — 2026-05-14  ·  보안 패치 (Security)

### 보안 수정
- **[긴급] `bastion_tk.py` 커맨드 인젝션 차단** — `shell=True` + f-string 패턴으로 파드 이름·네임스페이스가 Windows 셸에 직접 전달되던 문제 수정. `_build_pod_exec_cmd()` 헬퍼를 도입해 리스트 방식(`shell=False`)으로 교체 (`_open_exec`, `_ps_action_terminal`, `_exec_pod` 3곳)
- **[중간] LLM URL 스킴 검증 추가** — `_llm_ask(url, ...)` 에서 `http`·`https` 이외의 스킴(`file://`, `ftp://` 등)을 차단. 악의적인 URL로 로컬 파일 내용이 외부로 전송되는 경로를 제거

### 빌드
- `dist/bastion-v3.7.1-s1.exe` 생성

---

## v3.7.1 — 2026-05-14  ·  클러스터 탭 전환 시 페이지 복원 및 자동 새로고침

### 추가
- **클러스터별 페이지 기억** — 각 클러스터 탭에서 마지막으로 보던 기능 탭(대시보드, 터미널 등)을 기억하고, 탭 전환 시 자동 복원
- **클러스터별 네임스페이스 기억** — 탭 전환 시 해당 클러스터에서 마지막으로 선택한 네임스페이스 복원
- **탭 전환 시 화면 자동 새로고침** — 같은 페이지여도 클러스터 전환 시 `clusterSwitchKey` 기반 강제 재마운트로 데이터 항상 갱신

### 설계
- 탭 이름(`display_name`) 변경과 완전히 분리 — 내부 식별자 `id` 기반으로 `lastPage`/`lastNamespace` 관리하므로 이름을 바꿔도 페이지 기억 상태 유지
- `PageView` 컴포넌트를 `MainContent`에서 분리, `key={clusterSwitchKey}` 적용 → 기존 페이지 코드 수정 없이 모든 페이지 일괄 적용
- `refreshClusters` 시 백엔드 목록과 프론트엔드 전용 필드(`lastPage`, `lastNamespace`) 병합 보존

### 빌드
- `dist/bastion-v3.7.1.exe` 생성

---

## v3.7.0 — 2026-05-14  ·  멀티클러스터 탭 지원

### 추가
- **멀티클러스터 탭 관리** — 여러 kubeconfig를 동시에 연결하고 탭으로 전환
  - 타이틀바 `+` 버튼으로 새 클러스터 연결 → 즉시 탭 추가
  - 탭 클릭으로 클러스터 전환 (각 클러스터의 네임스페이스·연결 상태 독립 유지)
  - 탭 이름 클릭(활성 탭) → 인라인 편집으로 이름 수정 가능
  - 같은 context 이름 중복 시 자동 번호 부여 (`default` → `default (2)`)
  - 탭 × 버튼으로 개별 클러스터 제거 및 연결 해제

### 수정
- **전역 kubeconfig 충돌 해결** — `K8sManager.connect()`가 `load_kube_config()`를 전역으로
  덮어쓰던 버그 수정 → 인스턴스별 `kubernetes.client.Configuration` 객체 사용으로 완전 분리
- **로그 스트리밍 클러스터 혼선 버그 수정** — 백그라운드 스레드가 클러스터 전환 후
  잘못된 kubeconfig를 참조하던 문제 해결 (호출 시점에 값 캡처)
- `K8sManager.disconnect()`에서 ApiClient 연결 풀 명시적 해제 추가

### 내부 구조
- `BastionAPI`: 단일 `K8sManager` → `{cluster_id: K8sManager}` 딕셔너리로 전환
- `BastionAPI.k8s` 프로퍼티로 활성 클러스터 투명 접근 (기존 모든 API 하위 호환 유지)
- 신규 API: `add_cluster`, `remove_cluster`, `switch_cluster`, `rename_cluster`, `get_clusters`
- React `store.jsx`: `clusters[]` + `activeClusterId` 추가, 파생 상태(`connected`, `clusterName`, `kubeVersion`)로 기존 UI 호환
- `ClusterTab` / `ClusterTabStrip` 컴포넌트 추가 (App.jsx 타이틀바)

### 빌드
- `dist/bastion-v3.7.0.exe` 생성

---

## v3.6.3 — 2026-05-14  ·  LLM 섹션별 분산 분석 + max_tokens 제한 제거

### 변경
- **AI 분석 구조 전면 개편** — 단일 요약 블록(섹션 10) 제거, 각 섹션 끝에 AI 한 마디 분산 삽입
  - 섹션별 AI 코멘트: 클러스터 개요 / 워크로드 / HPA / Ingress-Service / 스토리지 / 보안 / 발견사항 종합 (총 7회)
  - 각 섹션 데이터만 축약해 전송 → 맥락 집중도 향상, 응답 품질 개선
  - `▶ AI:` 접두사 + 이탤릭 파란 텍스트로 섹션 하단에 렌더링
- **max_tokens 제한 제거** — `_llm_ask` 페이로드에서 `max_tokens` 파라미터 완전 삭제 (모델 기본값 사용)
- **timeout 30s → 120s** — 긴 응답에 대비
- `_report_call_llm` → `_llm_ask` 리팩터링 (단순 범용 호출 함수)
- 보고서 생성 단계 번호 11단계 → 10단계로 갱신
- README 다운로드 표를 GitLab 태그/원시 EXE 링크 기준으로 정리해 master 브랜치에서 바로 최신 산출물을 받을 수 있도록 갱신

### 빌드
- `dist/bastion-v3.6.3.exe` 생성

---

## v3.6.2 — 2026-05-14  ·  보고서 v2 스타일 전면 개편 + v1 자동 분석 내용 통합

### 변경
- **보고서 DOCX 전면 개편** — v2 스타일 DocBuilder 기반으로 재작성
  - `h1` 헤딩: 네이비 배경(`#1F3864`), 흰색 굵은 글씨
  - `h2` 헤딩: 파란 왼쪽 테두리(`#2E75B6`), 네이비 텍스트
  - 심각도별 색상 셀: CRITICAL(빨강), HIGH(주황), MEDIUM(노랑), LOW/INFO(초록)
  - Callout 박스: 색상 배경 강조 영역 (긴급 이슈·비정상 상태 경고)
  - 표지 개선: 심각도 칩 4열 테이블 (긴급/높음/중간/낮음 건수)
  - 페이지 헤더: 제목 텍스트 + 회색 구분선
  - 페이지 푸터: 중앙 페이지 번호 (`- N -`)
  - 한국어 폰트 `맑은 고딕` eastAsia XML 자동 주입 (저장 시 전 run 일괄 처리)
  - 컬럼 너비 명시 (16.5cm 기준 테이블별 최적화)
  - 비정상 파드·NotReady 노드·Pending PVC·Helm 비정상 등 조건부 callout 자동 삽입
- **v1 자동 분석 항목 통합** — 수동 분석 문서의 자동 생성 가능 항목 추출·포함
  - **2.3 주요 관찰사항**: Deployment/StatefulSet ready 불일치 자동 감지, ArgoCD/Helm 감지
  - **2.4 네임스페이스 목록**: 8개 단위 compact row 테이블
  - **3.x 노드 분석**: 역할(control-plane/worker) 분리 여부, 커널 버전 이질성 경고
  - **4.2 HPA 미적용 워크로드**: Deployment/StatefulSet ↔ HPA 교차 참조 테이블
  - **5.x 인그레스**: Ingress Class 분포 테이블, no-class 네임스페이스 목록, cert-manager 감지
  - **6.x 스토리지**: NFS SPOF 경고, 대용량 PVC(50Gi+) 테이블
  - **9. 예상 개선 작업**: 발견사항 기반 작업명·담당영역·예상공수·우선순위 자동 테이블
- **서비스 테이블 컬럼 최적화**: External-IP 컬럼 제거, 이름 5.5cm·포트 3.0cm·Age 1.5cm
- **Dashboard 버그 수정**: 파드 목록 `재시작`/`AGE` 컬럼이 붙어 보이던 문제 수정
  - `columnGap: 8` 추가, 컬럼 너비 조정 (`72px`, `68px`)
  - 헤더 레이블 `나이` → `AGE`
- **노드 데이터 확장**: `get_node_extended()` — `status`, `roles`, `version`, `age`, `kernel` 필드 추가

### 빌드
- `dist/bastion-v3.6.2.exe` 생성

---

## v3.6.1 — 2026-05-14  ·  페이지 인테리어 시안 B 적용

### 변경
- **ArgoPage 개편**
  - 왼쪽 필터 사이드바: Sync 상태 필터(All/Synced/OutOfSync/Degraded) + 프로젝트 필터 + 앱 검색
  - 상단 KPI 스트립 4개: 전체 앱 / Synced / OutOfSync / Degraded 카운트
  - 앱 목록: 테이블 → 3열 카드 그리드 (상태 칩, 레포/프로젝트 정보, 인라인 액션 버튼)
  - CRUD 모달·롤백·상세 패널 기존 기능 전부 유지
- **TerminalPage 개편**
  - 오른쪽 패널: 빠른 명령어 10개 (클릭 즉시 실행) + 최근 이력 목록
  - 터미널 입력 영역 배경 개선 (`bg-2` → `bg-3`)
- **TopologyPage 개편**
  - 왼쪽 필터 패널: 네임스페이스 셀렉터 + 리소스 타입 체크박스 (워크로드/서비스/설정/스토리지)
  - 타입 체크박스 토글 → 그래프 노드 실시간 dimming
  - 상단 KPI 스트립: 리소스 타입별 카운트 4개 (클릭으로 토글)
  - 범례를 왼쪽 패널 하단으로 이동
- **ReportPage 개편**
  - 3단계 위저드 UI: 대상 선택 → 포함 섹션 → AI 분석·생성
  - 섹션 토글 2열 카드 그리드 (노드/파드/디플로이먼트/서비스/이벤트/리소스 요약)
  - 생성 전 요약 확인 영역
  - 섹션 목록을 `sections` 파라미터로 백엔드에 전달
- **ResourceBrowser 개편 (파드)**
  - 파드 리소스 표시 시 상단 KPI 스트립: 총 파드 / Running / Pending / 비정상

---

## v3.6.0 — 2026-05-14  ·  UI 전면 개편 (시안 B — Cloud Modern)

### 변경
- **타이틀바 전면 개편**
  - Nimbus 로고 마크: 그라데이션 N SVG (민트 `#34d399` → 블루 `#60a5fa`)
  - "BASTION" 텍스트 그라데이션 + 버전/NIMBUS 서브타이틀
  - 글로벌 검색바 (⌘K 단축키 표시)
  - 클러스터 상태 칩: 클러스터명 + k8s 버전 + 연결 상태 글로우 닷
  - 네임스페이스 셀렉터 타이틀바로 이동
  - 새로고침 버튼
  - 높이 40px → 48px, `linear-gradient(180deg, bg-2, bg-1)` 배경
- **사이드바 개편**
  - 배경 `var(--bg-1)` → `var(--bg-2)`
  - 활성 항목: 녹→청 그라데이션 배경 + 2px 녹색 좌측 보더
  - 하단 클러스터 위젯: 클러스터명 + 버전 + 그라데이션 바
- **대시보드 개편**
  - 상단 도넛 차트 제거, 인포그래픽 KPI 카드 4개 (큰 숫자 스타일)
  - 대시보드 헤더: 클러스터 상태 한 문장 요약
  - RECENT PODS 테이블: 글로우 상태 닷, 더 선명한 레이아웃
- **상태바 개편**
  - 좌측: 글로우 닷 + "연결됨 · 클러스터명" + k8s 버전
  - 우측: "F5 새로고침 · ⌘K 검색" + Bastion 버전
- **백엔드**: kubeconfig 활성 컨텍스트 이름 추출 → `get_status()` 응답에 포함

---

## v3.5.16 — 2026-05-14  ·  파드 Exec 터미널 Windows Terminal로 전환

### 변경
- 파드 상세 패널의 Exec (터미널 열기) 기능을 CMD 창에서 Windows Terminal로 전환
  - 탭 제목: `Bastion — {namespace}/{pod명}` 형태로 표시
  - Bastion 컬러 스킴(`#060e1c` 배경) 자동 적용
  - kubeconfig를 `--kubeconfig` 플래그로 명시적 전달 (환경변수 상속 불필요)
  - wt.exe 미설치 시 기존 CMD 창으로 폴백

---

## v3.5.15 — 2026-05-14  ·  k9s Windows Terminal Bastion 테마 적용

### 변경
- k9s 실행 시 Windows Terminal settings.json에 "Bastion" 컬러 스킴 자동 주입
  - 배경 `#060e1c` (--bg-0), 전경 `#c4d4e8` (--text)
  - 커서 `#34d399` (--nimbus), 선택영역 `#182640` (--bg-3)
  - ANSI 16색 모두 Bastion 팔레트로 매핑 (green/red/yellow/blue/cyan/purple)
- 탭 색상 `--tabColor #060e1c` 로 탭 헤더도 Bastion 배경색 적용
- settings.json 쓰기 실패 시 기본 스킴으로 자동 폴백 (오류 무시)
- `_find_wt_settings()` — Stable/Preview/Portable 3가지 설치 경로 자동 탐색

---

## v3.5.14 — 2026-05-14  ·  k9s Windows Terminal 지원

### 변경
- k9s 런처 — CMD 창 대신 Windows Terminal(`wt.exe`)로 열기
  - `%LOCALAPPDATA%\Microsoft\WindowsApps\wt.exe` 및 PATH 자동 탐색
  - Windows Terminal 없는 환경은 기존 CMD 창으로 자동 폴백
  - `wt new-tab --title "Bastion — k9s"` 형식으로 새 탭 오픈
- K9sPage 성공 메시지에 실제 사용된 터미널 종류 표시
  (예: "k9s가 Windows Terminal에서 실행되었습니다.")

---

## v3.5.13 — 2026-05-14  ·  보안 강화 및 연결 오류 진단 개선

### 변경
- **연결 실패 원인 진단** — `_diagnose_connect_error()` 함수 추가:
  - 포트 접근 불가 (ConnectionRefused / MaxRetries) → 서버 주소·포트·방화벽 안내
  - 연결 타임아웃 → VPN/네트워크 확인 안내
  - SSL/TLS 인증서 오류 → CA 인증서 확인 안내
  - 인증 실패 (401) → 자격증명 만료 안내
  - 권한 없음 (403) → RBAC 안내
  - DNS 해석 실패 → VPN·DNS 설정 안내
  - kubeconfig 형식 오류 → YAML 파싱 오류 안내
  - ConnectionModal 에러 박스에 `pre-wrap`으로 여러 줄 표시
- **kubeconfig 사전 검증** — 연결 전 파일 존재·5 MB 크기 제한 확인
- **보고서 save_path 검증** — `.docx` 확장자 확인 + 절대경로 정규화
- **Job ID 전체 UUID 사용** — `uuid.uuid4()[:8]` → `uuid.uuid4()` 전체 (로그·보고서 양쪽)
- **traceback 프런트엔드 노출 제거** — 보고서 에러 시 traceback이 JS에 전달되던 문제 수정,
  대신 `logging.exception()`으로 내부 로그에만 기록

---

## v3.5.12 — 2026-05-14  ·  버전 표시 pywebviewready 대기 수정

### 수정
- `store.jsx` 버전 로드 타이밍 수정 — `useEffect` 마운트 시 `window.pywebview?.api`가  
  아직 null인 경우 `pywebviewready` 이벤트를 기다렸다가 `get_app_version()` 호출  
  (이전 v3.5.11 방식은 pywebview 브릿지 준비 전에 호출해 버전이 빈 값으로 남는 문제)

---

## v3.5.11 — 2026-05-14  ·  UI 버전 표시 동적 연동

### 변경
- **타이틀바·상태바 버전 표시 동적 연동** — 기존 하드코딩(`v3.5.0`, `v3.0.0`)을  
  `get_app_version` API로 교체, 백엔드 `VERSION` 상수를 UI가 마운트 시 읽어와  
  타이틀바(`⎈ BASTION vX.X.X`)와 상태바 우측 하단(`Bastion vX.X.X`) 양쪽에 표시
- `get_app_version()` BastionAPI 메서드 추가 (연결 전에도 호출 가능)
- `store.jsx` 마운트 시 `appVersion` 로드, `Titlebar` / `StatusBar` 컴포넌트에서 읽기

### 검증
- `python -m py_compile bastion.py`
- `corepack npm run build`

---

## v3.5.10 — 2026-05-14  ·  노드 카드 레이아웃 개선 및 PVC/PV YAML·Describe 오류 수정

### 변경
- **대시보드 노드 카드** — flexbox 가변 레이아웃에서 4열 CSS Grid 레이아웃으로 교체  
  4개씩 1행, 5개째부터 자동 줄바꿈, 창 너비에 맞게 카드 너비 자동 조절
- **스토리지 PVC·PV YAML/Describe 오류 수정** — 내부 키 `pvcs`/`pvs`를 kubectl 명령 실행 전  
  `persistentvolumeclaims`/`persistentvolumes`로 자동 변환하여  
  `the server doesn't have a resource type "pvcs"` 오류 제거

### 검증
- `python -m py_compile bastion.py`
- `corepack npm run build`

---

## v3.5.9 — 2026-05-14  ·  잔여 회귀 안정화

### 변경
- ArgoCD Application 변환에서 `spec.sources` multi-source 앱을 감지하고 첫 번째 소스와 추가 소스 개수를 함께 표시
- multi-source 앱 수정 시 단일 `spec.source`로 덮어쓰지 않고 기존 `spec.sources` 목록을 보존
- multi-source 앱 Sync 요청에서는 단일 `revision: HEAD`를 생략해 ArgoCD가 source 목록 기준으로 동기화하도록 처리
- 리소스 상세 이벤트 조회를 `involvedObject.kind` + `involvedObject.name` 조합으로 필터링해 같은 이름의 다른 kind 이벤트 혼입을 줄임
- k9s 실행 명령에 현재 연결된 kubeconfig를 `--kubeconfig` 인자로 명시적으로 전달
- ArgoCD multi-source, 이벤트 selector, k9s 실행 명령 회귀 테스트 추가

### 검증
- `python build.py --check`
- `python -m unittest tests.test_common_foundation -v`
- `python -m py_compile bastion.py build.py bastion_tk.py tests/test_common_foundation.py`
- `corepack npm test`
- `corepack npm run build`

---

## v3.5.8 — 2026-05-14  ·  EXE 빌드 의존성 누락 핫픽스

### 변경
- `build.py --check`가 PyInstaller 빌드 전에 `kubernetes`, `pywebview`, `python-docx`, `PyInstaller` import 가능 여부를 검사하도록 보강
- 필수 런타임 패키지가 빠진 환경에서는 빌드를 중단하고 `python -m pip install -r requirements.txt` 안내를 표시
- v3.5.7에서 발생한 작은 EXE/실행 불가 산출물 문제를 재발 방지 테스트로 고정
- `requirements.txt` 기준 패키지를 설치한 런타임에서 Windows EXE를 다시 빌드

### 검증
- `python build.py --check`
- `python -m unittest tests.test_common_foundation -v`
- `python -m py_compile bastion.py build.py bastion_tk.py tests/test_common_foundation.py`
- `corepack npm test`
- `corepack npm run build`

---

## v3.5.7 — 2026-05-14  ·  보고서 품질/진단 parity 복원

### 변경
- 보고서 수집 데이터셋에 Node metrics, Job, CronJob, ResourceQuota, LimitRange, IngressClass, Warning 이벤트를 추가
- 발견 사항 모델을 `severity`, 대상, 현황, 설명, 권장 조치가 분리된 구조로 보강
- Pod 재시작, 노드 NotReady/Pressure, NodePort, HPA 부족, PVC/PDB, StorageClass 기본값, kube-system, Deployment 레플리카 부족을 운영 보고서용 심각도 기준으로 재정리
- DOCX 보고서에 네임스페이스 제한 정책, Job/CronJob, IngressClass, Warning 이벤트, 개선 우선순위 섹션을 추가
- TXT 폴백 보고서도 동일한 진단 필드와 우선순위 요약을 표시하도록 보강
- 보고서 parity 회귀 테스트를 추가해 필수 데이터셋, 권장 조치 포함 진단, 즉시/단기/추적 우선순위 그룹을 고정

### 검증
- `python -m unittest tests.test_common_foundation -v`
- `python -m py_compile bastion.py build.py bastion_tk.py tests/test_common_foundation.py`
- `corepack npm test`
- `corepack npm run build`

---

## v3.5.6 — 2026-05-14  ·  토폴로지 간격/Job·CronJob 관계 복원

### 변경
- React 토폴로지 그래프를 5컬럼에서 `Ingress → Service → Schedule → Workload → Config/Storage → PV` 6컬럼 구조로 확장
- 컬럼 사이 여백과 세로 간격을 넓혀 노드와 엣지가 지나치게 붙어 보이는 문제 완화
- Python backend의 토폴로지 데이터에 CronJob 노드와 Job 워크로드 노드를 추가
- CronJob ownerReference를 따라 `CronJob → Job` 엣지를 생성하고, Job ownerReference를 파드 워크로드 매핑에 포함
- Job 노드에 성공/실패/실행 중/완료 목표와 파드 실행/전체 카운트를 표시
- React 그래프 계산을 `ui/src/topologyGraph.js`로 분리해 컬럼 배치와 간격을 회귀 테스트로 검증 가능하게 정리

### 검증
- `python -m unittest tests.test_common_foundation -v`
- `corepack npm test`
- `python -m py_compile bastion.py build.py bastion_tk.py tests/test_common_foundation.py`
- `corepack npm run build`

---

## v3.5.5 — 2026-05-13  ·  로그뷰어 워크로드/인그레스 통합 로그 복원

### 변경
- 로그뷰어에 Pod, Deployment, StatefulSet, DaemonSet, ReplicaSet, Job, Ingress 통합 로그 소스 선택을 추가
- 워크로드 선택 시 ownerReference와 label selector를 함께 사용해 하위 파드를 찾고 여러 파드 로그를 한 스트림으로 통합 표시
- Ingress 통합 로그 모드에서 ingress-nginx, traefik, contour, istio ingress gateway 계열 controller 파드를 자동 탐색
- 여러 파드 로그를 볼 때 `[namespace/pod]` prefix와 시작 헤더를 붙여 어느 controller/파드에서 나온 로그인지 구분 가능
- Python backend의 `start_log_stream` API를 pod/workload/ingress 공통 스트리밍 모델로 확장
- React 로그뷰어의 대상 선택 UI를 로그 소스별로 재구성하고 ingress 모드는 controller 자동 탐색 안내로 단순화
- `tests/test_common_foundation.py`와 `ui/src/logTargets.test.mjs`에 로그 소스/인자 생성/ingress 탐지 회귀 테스트 추가

### 검증
- `node --test ui/src/logTargets.test.mjs ui/src/navigationTargets.test.mjs`
- `python -m unittest tests.test_common_foundation -v`
- `python -m py_compile bastion.py build.py bastion_tk.py tests/test_common_foundation.py`
- `corepack npm run build`

---

## v3.5.4 — 2026-05-13  ·  파드 로그/Exec 상세 패널 복원

### 변경
- 파드 상세 패널 상단에 `Logs`와 `Exec` 액션 버튼 추가
- `Logs` 버튼은 선택한 namespace/pod/container/tail 값을 로그 뷰어로 전달하고 자동으로 로그 스트림을 시작
- 로그 탭 내부에도 `Log Viewer` 버튼을 추가해 작은 패널 로그에서 큰 로그 화면으로 바로 이동 가능
- `Exec` 버튼은 Windows cmd 창에서 `kubectl exec -it -n <namespace> <pod> [-c container] -- sh`를 실행해 대화형 파드 셸을 열도록 복원
- 외부 cmd 실행 실패 시 앱 내 kubectl 터미널 탭으로 이동해 동일 exec 명령을 자동 입력하는 fallback 추가
- React 전역 store에 `logTarget`, `terminalCommand` 전달 상태 추가
- `tests/test_common_foundation.py`와 `ui/src/navigationTargets.test.mjs`에 파드 로그/exec 회귀 테스트 추가

### 검증
- `node --test ui/src/navigationTargets.test.mjs`
- `python -m unittest tests.test_common_foundation -v`
- `corepack npm run build`

---

## v3.5.3 — 2026-05-13  ·  대시보드 노드 CPU/MEM 사용률 복원

### 변경

- v2 대시보드의 노드별 CPU/MEM 사용 퍼센트 표시를 v3 React 대시보드에 복원
- Python backend에 Node metrics 수집/변환/병합 헬퍼 추가
  - `metrics.k8s.io/v1beta1` Node metrics 조회
  - CPU millicore, Memory MiB 변환
  - allocatable 대비 CPU/MEM 퍼센트 계산
  - metrics-server 미설치 또는 조회 실패 시 기존 allocatable 표시 유지
- React `Dashboard` 노드 카드에 CPU/MEM 사용률 progress bar와 `used / allocatable (%)` 표시 추가
- `tests/test_common_foundation.py`에 Node metrics 회귀 테스트 추가

### 검증

- `python -m unittest tests.test_common_foundation -v`
- `corepack npm run build`

---

## v3.5.2 — 2026-05-13  ·  공통 기반/빌드 리스크 정리

### 변경

- `requirements.txt`에 `python-docx`, `pyinstaller`를 명시해 DOCX 보고서와 로컬 빌드 의존성 누락 위험을 낮춤
- `Bastion.spec`와 `bastion-v3.5.2.spec`에 `docx`, `kubernetes`, `webview` hidden import를 명시
- kubectl 터미널 명령 파싱을 `shlex.split` 기반으로 변경
  - `kubectl`/`kubectl.exe` prefix는 backend에서 한 번 더 제거
  - `jsonpath="{...}"`, `patch -p '{"spec":...}'` 같은 quoted argument를 단일 인자로 유지
  - 닫히지 않은 따옴표는 사용자에게 파싱 오류로 반환
- `build.py`의 UI 빌드가 깨진 `npm` 대신 `corepack npm`으로 자동 fallback 가능하도록 개선
- `package-lock.json`이 있으면 `npm install` 대신 `npm ci`를 사용해 재현 가능한 UI 빌드를 수행
- `build.py`가 `dist/bastion-vX.Y.Z.exe`를 자동 복사하도록 개선
- `tests/test_common_foundation.py` 추가
  - kubectl quoted argument 파싱
  - npm/corepack 선택 로직

### 검증

- `python -m unittest tests.test_common_foundation -v`

---

## v3.5.1 — 2026-05-13  ·  v2/v3 기능 Parity 기준선 확정

### 변경

- `origin/master` v2.4.2 대비 `origin/v3.0-dev` v3.5.0에서 누락되거나 축소된 기능을 `docs/v3-parity-baseline.md`에 정리
- 대시보드 노드 CPU/MEM, 토폴로지 Job/CronJob, 보고서 품질, 파드 로그/exec, 로그뷰어 워크로드/인그레스 통합 로그, kubectl 인자 파싱, ArgoCD multi-source 등 후속 패치 대상을 우선순위화
- README 다운로드 표와 최신 버전 표기를 v3.5.1로 갱신
- 버전별 PyInstaller spec `bastion-v3.5.1.spec` 추가

### 범위

- 이번 릴리스는 기능 복원 구현이 아니라 parity 기준선을 고정하는 문서/릴리스 메타데이터 패치입니다.
- 실제 기능 복원은 v3.5.x 패치에서 순차적으로 진행합니다.

---

## v3.0.0 — 2026-05-13  ·  전면 UI 재설계 — PyWebView + React/Vite

### 변경 (Breaking)

- **UI 프레임워크 전환**: tkinter → PyWebView + React 18 / Vite 5
  - `bastion_tk.py` 로 v2.4.2 tkinter 버전 롤백 보존
  - 새 `bastion.py` = pywebview 진입점 + BastionAPI 퍼사드
- **Nimbus Design System v3** 적용 — 다크 네이비 컬러 팔레트 (`#060e1c` 베이스, `#34d399` 액센트)

### 신규

- React 페이지: Dashboard / ResourceBrowser / ArgoPage / HelmPage / TerminalPage
- 재사용 컴포넌트: `ResourceTable` (클라이언트 검색·정렬), `ConnectionModal`, `Sidebar`, `StatusBar`
- `BastionAPI` Python 클래스 — K8sManager 래핑, JSON API 퍼사드
- `build.py` — npm 빌드 스텝 추가 (PyInstaller 전 `npm run build` 자동 실행)
- `Bastion.spec` — `ui/dist` 포함, `tkinter` 제외

### 아키텍처

```
bastion.py (v3)
  └── BastionAPI (pywebview JS API)
        └── K8sManager (kubernetes Python client)
ui/ (React + Vite)
  ├── src/App.jsx          메인 레이아웃
  ├── src/store.jsx        전역 상태 (Context)
  ├── src/api.js           pywebview 브릿지
  ├── src/components/      Sidebar · StatusBar · ConnectionModal · ResourceTable
  └── src/pages/           Dashboard · ResourceBrowser · ArgoPage · HelmPage · TerminalPage
```

---

## v2.4.2 — 2026-05-13  ·  ArgoCD UI 정리 — 앱 목록에 생성·수정·삭제 통합

### 변경

- **앱 배포 탭 제거** — 별도 탭 불필요, 앱 목록 탭에 통합
- **앱 목록 툴바에 버튼 3개 추가**: `+ 생성` / `✎ 수정` / `🗑 삭제`
  - `+ 생성`: 항상 활성, 클릭 시 앱 생성 폼 다이얼로그
  - `✎ 수정`: 앱 선택 시 활성, 현재 값 사전 채움 후 수정
  - `🗑 삭제`: 앱 선택 시 활성, 확인 팝업 후 Application CR 삭제
- 사이드바 `배포` 카테고리에서 `앱 배포` 항목 제거

---

## v2.4.1 — 2026-05-13  ·  ArgoCD 앱 배포 (생성·수정·삭제) 추가

### 변경

- **배포 이력 탭 제거** — 앱 목록 사이드 패널에 이미 최근 이력이 있어 별도 탭 불필요
- **앱 배포 탭 신설** — 사이드바 `앱 배포` 클릭 시 활성화
  - 앱 목록 + `수정` / `삭제` 버튼 (앱 선택 시 활성화)
  - `+ 새 앱 생성` 버튼 → 폼 다이얼로그 (앱 이름, 프로젝트, Repo URL, 경로, 브랜치, 대상 NS, 클러스터, 동기화 정책)
  - 수정 클릭 시 현재 값 사전 채움
  - 삭제 클릭 시 확인 팝업 후 Application CR 제거

---

## v2.4.0 — 2026-05-13  ·  ArgoCD 배포 탭

### 새 기능

- **EXPLORER "배포" 카테고리** — 사이드바에 HELM 과 도구 사이에 `배포` 카테고리 추가
- **앱 목록** — ArgoCD Application CRD 목록 조회 (이름, 대상 네임스페이스, Sync 상태, Health 상태, 최근 동기화, Git Repo)
- **앱 상세 사이드 패널** — 앱 클릭 시 상태 칩, Source 정보, 배포 이력(최근 5건) 인라인 표시
- **Sync 트리거** — 사이드 패널 `Sync` 버튼 → ArgoCD Application CR의 `.operation.sync` 패치로 동기화 트리거 (이미 실행 중이면 비활성화)
- **롤백** — 사이드 패널 `롤백` 버튼 → 배포 이력 선택 다이얼로그 → `.operation.rollback.id` 패치
- **배포 이력** — 클러스터 전체 또는 앱별 배포 이력 테이블 (앱명, 순번, Revision, 배포시각, 배포자)
- **ArgoCD 미설치 안내** — CRD 조회 실패(404) 시 `ArgoCD가 설치되지 않았습니다` 메시지 표시

### 기술 세부
- ArgoCD API 서버 없이 kubeconfig 하나(6443)로 `CustomObjectsApi` 통해 CRD 직접 조회/패치
- multi-source 앱(`spec.sources`) 호환 처리

---

## v2.3.4 — 2026-05-13  ·  보고서 중복 파일명 자동 증가

### 버그 수정

- **보고서 중복 파일명 처리** — 이미 존재하는 경로로 생성 시도 시 에러 대신 `파일명 (1).docx`, `(2).docx` 형태로 자동 증가. 진행 로그에 `⚠ 동일 파일 존재 — ...으로 저장합니다` 안내 출력, 저장 경로 입력란도 자동 갱신

---

## v2.3.3 — 2026-05-13  ·  HELM 차트조회 탭 제거 + 보고서 한글 폰트 수정

### 변경

- **HELM 차트조회 탭 제거** — EXPLORER 사이드바에서 `차트 조회` 항목 삭제, HelmTab 내 관련 뷰·메서드 전체 제거 (로컬 helm 레포만 조회되는 구조적 한계)

### 버그 수정

- **보고서 한글 폰트 깨짐 수정** — python-docx의 `font.name` 설정은 `w:ascii`/`w:hAnsi`만 적용하고 한글용 `w:eastAsia` 속성은 설정하지 않아 MS Mincho(일본 폰트)로 폴백되던 문제 수정
  - Normal 스타일에 `w:eastAsia = 맑은 고딕` 명시 적용
  - 저장 직전 모든 단락·테이블 셀 run에 `w:eastAsia` 일괄 보정

---

## v2.3.2 — 2026-05-12  ·  HELM Repo List 탭 제거

### 변경

- **Helm Repo List 탭 제거** — EXPLORER 사이드바에서 `Helm Repo List` 항목 삭제, HelmTab 내 관련 뷰·메서드 전체 제거

---

## v2.3.1 — 2026-05-12  ·  HELM 사이드바 스타일 수정 + Repo List 추가

### 버그 수정 / 개선

- **CMD 창 깜빡임 제거** — helm CLI 호출 시 `CREATE_NO_WINDOW` 플래그 적용으로 콘솔 창이 순간 표시되는 현상 수정
- **HELM 사이드바 색상·정렬 통일** — 아이콘 제거, 색상을 일반 리소스 항목(text_head)과 동일하게 변경
- **도구 사이드바 정렬 수정** — kubectl 터미널 / k9s 항목 들여쓰기 통일
- **Helm Repo List 추가** — HELM 하위에 세 번째 항목 추가, 클러스터에 등록된 helm 레포지토리 목록을 테이블로 표시

---

## v2.3.0 — 2026-05-12  ·  HELM 카테고리 추가 (릴리즈 현황 + 차트 조회)

### 새 기능

- **사이드바 HELM 섹션** — 스토리지 아래, 도구 위에 HELM 카테고리 추가
  - `📦 실행중인 Helm 현황` — 클러스터에 배포된 Helm 릴리즈 테이블 (helm CLI 우선, K8s Secret 폴백). 네임스페이스 필터·이름/차트 검색·컬럼 정렬 지원. 상태별 색상 (초록/빨강/주황)
  - `🔍 차트 조회` — 로컬 helm 레포지토리 목록 + `helm search repo` 차트 검색 (Enter 또는 검색 버튼)
- **⎈ Helm 탭** — 두 뷰를 수용하는 고정 탭 추가
- `_find_helm()` 자동 탐지 함수 및 K8sManager helm 메서드 3개 추가

---

## v2.2.10 — 2026-05-12  ·  사이드 패널 터미널 버튼 cmd 창 방식으로 수정

### 버그 수정

- **터미널 버튼 동작 변경** — 내장 kubectl 탭 대신 `start cmd /k kubectl exec -it` 로 별도 cmd 창을 여는 방식으로 수정 (우클릭 → 터미널 실행과 동일)

---

## v2.2.9 — 2026-05-12  ·  파드 사이드 패널 버튼 개편 + 이벤트 인라인 뷰

### 변경 사항

- **파드 사이드 패널 버튼 재구성** — 삭제·Exec 버튼 제거, 이벤트(초록 강조) / 터미널 / 로그보기 3개 버튼으로 교체
- **이벤트 인라인 표시** — 이벤트 버튼 클릭 시 파드 이벤트 목록을 패널 하단 스크롤 영역에 바로 표시. Warning 이벤트는 주황 강조, 원인·메시지·나이 함께 표시
- **터미널 버튼** — 클릭 시 터미널 탭으로 전환 후 `kubectl exec -it` 명령어 자동 입력

---

## v2.2.8 — 2026-05-12  ·  파드 사이드 패널 place 레이아웃 전환

### 버그 수정

- **파드 상세 사이드 패널 폭 정확 보장** — `pack`+`width=` 방식에서 `place` 지오메트리 매니저로 전환. 테이블 72% / 구분선 0.3% / 패널 27.7% (정확히 화면의 약 1/4) 으로 항상 올바른 크기 유지

---

## v2.2.7 — 2026-05-12  ·  파드 사이드 패널 폭 수정

### 버그 수정

- **파드 상세 사이드 패널 너비 수정** — `pack_propagate(False)` 를 자식 위젯 추가 전에 설정하도록 변경, 고정 너비 340 → 420px 으로 확대 (화면의 약 1/4)

---

## v2.2.6 — 2026-05-12  ·  노드 카드 균등 분배 + 파드 상세 사이드 패널

### 기능 추가

- **리소스 탐색기 파드 상세 사이드 패널** — 워크로드→파드 목록에서 파드 클릭 시 우측에 상세 패널 표시
  - 파드 이름 / 상태 칩 / 네임스페이스
  - Ready · 재시작 · 나이 · IP · 노드 · QoS · HostIP 메타 정보
  - 컨테이너 목록 (이름 + 이미지)
  - 로그 보기 / Exec / 삭제 액션 버튼
  - ✕ 버튼으로 닫기, 파드 외 다른 리소스 전환 시 자동 숨김

### 개선

- **대시보드 노드 카드 균등 분배** — grid columnconfigure(weight=1) 적용으로 창 크기에 따라 카드가 균등하게 늘어남

---

## v2.2.5 — 2026-05-12  ·  대시보드 UX 개선

### 개선

- **헬스 % 설명 추가** — OVERVIEW 제목에 괄호로 설명 추가 (전체 N개 파드 중 M개 Running)
- **노드 카드 줄바꿈** — 노드가 4개 초과 시 다음 줄로 자동 줄바꿈 (4열 고정)
- **연결 시 대시보드 자동 전환** — kubeconfig 연결 성공 시 대시보드 탭으로 자동 전환 후 갱신

---

## v2.2.4 — 2026-05-12  ·  대시보드 탭 V2 전면 개편

### 기능 변경

- **대시보드 탭 V2 클라우드 대시보드로 교체**
  - 기존 3-Panel Inspector → KPI 카드 + 노드 도넛 차트 + 파드 테이블 레이아웃으로 전면 교체
  - 파드/노드/네임스페이스/전체재시작 4개 KPI 카드 (스파크라인 제외 심플 버전)
  - 노드별 CPU/메모리/파드수 도넛 링 차트 카드 (metrics-server 미설치 시 0% 표시)
  - 최근 파드 50개 Treeview 테이블 (이름/네임스페이스/Ready/상태/재시작/나이/IP/노드)
  - 60초 자동 갱신
- **`DonutChart` 위젯 추가** — tkinter Canvas 기반 링 차트 공통 컴포넌트
- **`K8sManager.get_dashboard_data()`** — 대시보드용 데이터 일괄 수집 메서드 추가

---

## v2.2.3 — 2026-05-12  ·  토폴로지 컬럼 간격 확장

### 개선

- **토폴로지 컬럼 간격 확장** — 컬럼 X 간격 200px → 240px (총 캔버스 폭 1460 → 1740px)

---

## v2.2.2 — 2026-05-12  ·  토폴로지 그래프 빌드 버그 수정

### 버그 수정

- **토폴로지 "리소스 없음" 오류 수정** — `_build_graph` 내 `configmaps/secrets/pvcs/pvs` 변수 미추출로 인한 NameError 수정
- **`_apply` 예외 처리 추가** — 그래프 빌드 실패 시 빈 화면 대신 오류 메시지 표시

---

## v2.2.1 — 2026-05-12  ·  토폴로지 탭 추가 + ConfigMap/Secret/PVC/PV 연결도

### 신규 기능 / 변경

- **토폴로지 탭 추가** — 대시보드 옆 `◈ 토폴로지` 탭 신설
  - Ingress → Service → Workload → Pod/Pods → ConfigMap / Secret / PVC → PV 컬럼 레이아웃
  - CronJob → Job → Pod/Pods 영역 별도 구분
  - 상태 색상: 초록(healthy) / 노랑(warning) / 빨강(danger) / 파랑(info)
  - Pod 3개 초과 시 `Pods ×N` 그룹 노드로 자동 묶음
  - 노드 클릭 시 연결 리소스 하이라이트 + 우측 상세 패널
  - 드래그 패닝, 마우스 휠/버튼 줌 지원
- **연결 규칙 개선**
  - Service → Workload(Deployment/StatefulSet/DaemonSet) 레이블 셀렉터 매칭
  - Service → Pod 직접 연결 제거 (Workload 경유만 허용)
  - Pod/Pods → ConfigMap (volumes, envFrom, env.valueFrom 참조 기반)
  - Pod/Pods → Secret (동일, 서비스어카운트 토큰·Helm 릴리즈 시크릿 자동 제외)
  - Pod/Pods → PVC → PV 바인딩 연결
  - 실제 참조하지 않는 ConfigMap/Secret 노드 미생성

---

## v2.2.0 — 2026-05-12  ·  보고서 데이터 수집 대폭 확장 + LLM URL 기본값 변경

### 신규 기능 / 변경

- **K8sManager 확장 getter 추가 (v2.2.0)**
  - `get_node_extended()`: 노드별 conditions, taints, allocatable CPU/MEM, OS, kernel, container_runtime
  - `get_namespaces_extended()`: 네임스페이스 + labels + status
  - `get_pod_metrics_all()`: `top pods -A` 전체 파드 메트릭 (CPU/MEM top 정렬)
  - `get_hpa_extended()`: target CPU%, current CPU%, desired replicas 포함
  - `get_pdbs()`: PodDisruptionBudget (PolicyV1Api) — current/desired_healthy, disruptions_allowed
  - `get_network_policies()`: NetworkPolicy ingress/egress 규칙 수
  - `get_ingress_classes()`: IngressClass + is-default-class annotation
  - `get_storage_classes()`: StorageClass + reclaim_policy, binding_mode, is-default-class
  - `get_resource_quotas()`: ResourceQuota hard/used 매핑
  - `get_limit_ranges()`: LimitRange default/defaultRequest/max/min
  - `get_rbac_summary()`: ClusterRole/ClusterRoleBinding/Role/RoleBinding/ServiceAccount 수 + 사용자 정의 목록
  - `get_kube_system_info()`: kube-system 파드/Deployment/DaemonSet/Service 현황
  - `get_deployments_extended()`, `get_statefulsets_extended()`, `get_daemonsets_extended()`: ready/desired 포함
  - **connect()**: autoscaling, policy, storage, rbac API 클라이언트 추가

- **보고서 섹션 8개 → 12개로 확장**
  - 1.점검개요 (전체 카운트 테이블 확장)
  - 2.클러스터현황 (네임스페이스 + 노드상세 + Taint + 메트릭)
  - 3.워크로드상태 (Deployment/StatefulSet/DaemonSet 상세 + 비정상Pod)
  - 4.리소스사용량 (Top pods CPU/MEM + ResourceQuota + LimitRange)
  - 5.HPA/PDB (HPA 상세 CPU% + PodDisruptionBudget)
  - 6.네트워크 (IngressClass + Ingress + NodePort + NetworkPolicy)
  - 7.스토리지 (StorageClass + PV + PVC)
  - 8.RBAC/보안 (ClusterRole 목록 + 보안 권고)
  - 9.kube-system (파드/컴포넌트 상태)
  - 10.Warning이벤트 (150건, 최근시간 포함)
  - 11.장애가능성 (AI 분석 + 위험요소 요약)
  - 12.개선우선순위 (긴급/중간/낮음 3단계)

- **_evaluate() 규칙 추가**
  - 노드 NotReady / MemoryPressure / DiskPressure / PIDPressure 감지
  - PDB current_healthy < desired_healthy 감지
  - Default StorageClass 없음 감지
  - Deployment ready < desired 감지
  - kube-system 비정상 파드 감지

- **ReportDialog UI 변경**
  - "LM Studio URL" → "LLM URL"
  - 기본 URL: `http://localhost:1234` (사용 환경에 맞게 변경)
  - 기본 모델: `local-model` (사용 모델명으로 변경)

### 버전
- VERSION 2.1.1 → 2.2.0

---

## v2.1.1 — 2026-05-11  ·  보고서 양식 개선 + 버튼 가시성 수정

### 수정
- **(중요) 보고서 DOCX 양식을 클러스터_리포트_생성기의 원본 양식과 동일하게 맞춤**
  - 기존: 단순 텍스트/단락 나열 형식 (h1 파란 텍스트)
  - 변경: `클러스터_운영_점검_리포트` 와 동일한 `DocBuilder` 패턴 완전 포팅
    - **표지**: "Kubernetes 클러스터 / 운영 점검 리포트" 타이틀 + 구분선 + 메타 + 심각도 뱃지(긴급/높음/중간/낮음 컬러 칩) + 페이지 나눔
    - **h1 헤딩**: Navy 배경 + 흰 글씨 (섹션 구분)
    - **h2 소제목**: 파란 좌측 악센트 선 + Navy 텍스트
    - **표**: Navy 헤더 + 흰 글씨, 짝수 행 회색 교대 배경, `Table Grid` 스타일
    - **callout**: 착색 배경 강조 단락 (긴급=분홍, 높음=살구, 중간=노랑)
    - **푸터**: `— N —` 페이지 번호
    - **헤더**: 우측 정렬 "Kubernetes 클러스터 운영 점검 리포트" + 하단 구분선
  - 섹션 구성 (8개): 1.점검개요 / 2.클러스터현황 / 3.워크로드상태 / 4.HPA / 5.Ingress-Service / 6.PVC / 7.장애가능성 / 8.개선우선순위

- **(UX) 보고서 생성 버튼이 창이 작을 때 보이지 않던 문제 수정**
  - 기존: 버튼이 진행 로그 아래(최하단)에 위치 → 창이 작으면 가려짐
  - 변경: 버튼 행을 설정 그리드 바로 아래로 이동, 진행 로그가 그 아래에 위치
  - 결과: 창 크기와 무관하게 "보고서 생성" / "닫기" 버튼이 항상 보임

### 버전
- VERSION 2.1.0 → 2.1.1

---

## v2.1.0 — 2026-05-11  ·  클러스터 보고서 생성 기능 추가

### 신규 기능

- **타이틀바 "보고서" 버튼 추가**
  - 위치: 우측 `⟳ 새로고침` 버튼 왼쪽
  - 클러스터 미연결 시 비활성(disabled), 연결 후 자동 활성화
  - 클릭 시 `ReportDialog` (전용 진행 다이얼로그) 오픈

- **ReportDialog — 보고서 생성 다이얼로그** (`class ReportDialog(tk.Toplevel)`)
  - 설정: LM Studio URL / 모델명 / 저장 경로 (파일 탐색기 연동)
  - 진행 로그 영역: 단계별 수집·분석·LM호출·저장 상태를 실시간 출력
  - 백그라운드 스레드 실행 — UI 블로킹 없음
  - 완료 시 `showinfo` 팝업 표시

- **데이터 수집 (`_collect`)** — K8sManager 기존 메서드 활용
  - 노드, 파드, 서비스, 인그레스, PVC, 노드 메트릭 수집
  - HPA: `AutoscalingV1Api.list_horizontal_pod_autoscaler_for_all_namespaces`
  - Warning 이벤트: `CoreV1Api.list_event_for_all_namespaces(field_selector='type=Warning', limit=100)`

- **규칙 분석 엔진 (`_evaluate`)** — 인라인 구현 (외부 의존 없음)
  - 파드 재시작 횟수: 10↑ low / 50↑ medium / 200↑ high / 1000↑ critical
  - 비정상 파드 상태: Running / Completed / Succeeded 이외 → high
  - NodePort 서비스: 민감 포트 포함 시 high, 그 외 medium
  - HPA 3개 미만: medium
  - Lost PVC: critical

- **LM Studio 연동 (`_call_llm`)** — OpenAI 호환 엔드포인트 사용
  - 엔드포인트: `{url}/v1/chat/completions` (올바른 OpenAI-compatible 경로)
  - system prompt: 한국어 종합 평가 300자 요약
  - requests 없으면 호출 생략 후 보고서 계속 생성

- **DOCX 생성 (`_write_docx`)** — `python-docx` 사용
  - 섹션: 제목·메타 / AI 종합 평가(있을 때) / 규칙 분석 결과 / 노드 현황 / 비정상 파드 / Warning 이벤트
  - 심각도별 글자 색상: 긴급(빨강) / 높음(주황) / 중간(노랑계) / 낮음(회색)
  - python-docx 미설치 시 → `.txt` 폴백으로 자동 전환

### 변경

- **`Bastion.spec` hiddenimports** 에 `docx`, `docx.shared`, `docx.enum.text`, `docx.oxml`, `docx.oxml.ns`, `requests` 추가
- **imports**: `from pathlib import Path`, `import re as _re` 추가 (ReportDialog 내부 사용)
- **VERSION** 2.0.4 → 2.1.0 / VERSION_NAME 업데이트

### 검증

- ✅ 타이틀바 "보고서" 버튼 표시 확인
- ✅ 연결 전 비활성 / 연결 후 활성 전환 확인
- ✅ 다이얼로그 열림 및 설정 입력 확인
- ✅ 데이터 수집 단계 로그 출력 확인
- ✅ LM Studio 없을 때 graceful skip 후 DOCX 생성 계속
- ✅ python-docx 없을 때 .txt 폴백 동작 확인

---

## v2.0.4 — 2026-04-30  ·  대시보드 파드 리스트 Treeview 화 + 워크로드 로그 진단

### 수정
- **(Critical) 대시보드 가운데 파드 리스트가 1개만 표시되던 문제 해결**
  - 증상: 헤더에 "파드 12 개" 라고 보이는데 실제 클릭 가능한 행은 1개. 클릭해도 선택 안 됨.
  - 원인 분석: 직접 `tk.Canvas` 안에 `tk.Frame` 윈도우를 넣고 행을 동적으로 packing 하던 구조에서 — `pack_propagate(False)` + 명시적 `height=26` + `fill='x'` 의 조합이 특정 시점에 행을 0폭으로 그리거나 안 그리는 경우가 발생. 캔버스 width 동기화 (`v2.0.3` 패치) 만으로는 충분히 안정적이지 않음.
  - 조치: 파드 리스트를 **`ttk.Treeview` 로 전면 교체**. 이미 검증된 위젯 + 네이티브 스크롤/선택/정렬.
    - 컬럼: 이름(트리), 네임스페이스, Ready, 재시작, 나이
    - 상태별 행 컬러 태그: `running` (그린), `pending` (옐로), `failed` (레드)
    - 상태 마커 글리프 이름 앞에 표시: `●` Running / `◐` Pending / `○` Failed
    - 단일 클릭(`<<TreeviewSelect>>`) → 우측 인스펙터로 디테일 로드
    - **더블 클릭** → 즉시 로그 보기 액션 (빠른 진입)
    - 정렬: 이름 사전순. 이전 선택은 새로고침 후에도 유지.
  - 부수 효과: 파드 수가 100+ 여도 부드럽게 스크롤 / 즉시 선택. 행 가시성 100% 보장.

- **(Critical) 워크로드 로그 "파드를 찾을 수 없습니다" 오진 수정**
  - 증상: 리소스 탐색기에서 ReplicaSet 더블클릭 → 디테일 탭 → "로그 보기" 클릭 → 로그 뷰어에 옵션은 잘 잡히지만 "파드를 찾을 수 없습니다: replicaset/argocd-applicationset-controller-79658dcbc9" 에러.
  - 진짜 원인: 그 ReplicaSet 이 **이전 revision (rollout 후 0개로 스케일된 RS)** 일 가능성이 높음. 기존 코드는 label selector 만 사용 → 파드와 RS 의 `pod-template-hash` 가 달라 매칭 실패.
  - 조치: `_get_pods_for_workload` 를 `get_workload_pods(ns, wl_type, wl_name)` 으로 확장. 다음 3단계 탐색:
    1. **ownerReferences 기반** (가장 신뢰성 높음) — 파드의 `metadata.ownerReferences[].uid` 가 워크로드 UID 와 일치하는지 직접 확인
    2. **Deployment 의 경우**: Deployment → 소속 RS 들 (UID 매칭) → 그 RS 들이 소유한 파드까지 2단계 traversal
    3. label selector 폴백 (기존 동작)
  - 그래도 파드가 없으면 **사유를 명확히 진단**:
    - `desired replicas=0` → "스케일 다운됨" 안내
    - ReplicaSet 일 때 → "이전 revision 일 수 있습니다 — 부모 Deployment 에서 보세요" 안내
    - 일반 → `desired/ready` 카운트 표시
  - 추가: 정상 케이스에 헤더 라인 출력 — `[워크로드 로그] replicaset/foo → 파드 3개: a, b, c`

### 호환성
- `K8sManager._get_pods_for_workload` (구 API) 는 그대로 유지 — 새 `get_workload_pods` 를 호출하는 thin wrapper. 외부 코드 변경 불필요.

### 검증
- ✅ Treeview 12행 렌더 — 모두 클릭 가능
- ✅ 활성 deployment → owner-ref 경유로 현재 active RS 의 파드 정상 발견
- ✅ 스케일 다운된 RS → 명확한 사유 메시지 표시
- ✅ 정상 워크로드 → 헤더 라인 + 모든 파드 로그 병렬 스트리밍

---

## v2.0.3 — 2026-04-30  ·  대시보드 렌더링 + 라우팅 수정

### 수정
- **(중요) 대시보드 가운데 파드 리스트가 비어 보이던 문제 해결**
  - 증상: 네임스페이스를 클릭해도 헤더에 "파드 45 개" 라고 카운트는 표시되지만 실제 행은 한 개도 보이지 않음.
  - 원인: `tk.Canvas` 내부에 만든 `inner_frame` 윈도우의 폭이 캔버스 폭에 동기화되어 있지 않음. 행은 `pack(fill='x')` 로 부모 폭만큼 펼쳐져야 하는데, 부모 폭이 0이라 행이 0×26 (보이지 않음) 상태.
  - 조치: 3개의 캔버스(`ns_canvas` / `list_canvas` / `ev_canvas`) 모두에 다음 바인딩 추가
    ```python
    canvas.bind('<Configure>',
        lambda e: canvas.itemconfig(window_id, width=e.width))
    ```
    이로써 캔버스 폭이 변할 때마다 안쪽 프레임도 같은 폭으로 리사이즈 → 행이 정상적으로 펼쳐짐.

- **(중요) 사이드바 "파드" 클릭 라우팅 v1.0 복원**
  - 증상: 사이드바에서 "파드" 를 클릭하면 대시보드 탭으로 이동했음.
  - 사용자 의도: v1.0 처럼 모든 사이드바 리소스 클릭은 **리소스 탐색기 탭의 표 형태** 로 가야 함. 대시보드는 별도 탭에서 직접 클릭해야만 진입.
  - 조치: `_on_sidebar_select()` 의 `if item == 'pods'` 분기 제거. 모든 리소스가 동일하게 `_tabbar.activate('resources')` + `_load_resource(item)` 흐름.

- **연결 시 동작 정리**
  - 이전: `selection_set('pods')` 호출 → 사이드바 콜백 트리거 → 리소스 탭으로 강제 전환
  - 변경: 대시보드 탭은 그대로 활성 유지 + 백그라운드에서 `_load_resource('pods')` 만 호출하여 리소스 탐색기 데이터를 미리 로드 (사용자가 사이드바 "파드" 를 클릭하면 즉시 표시)

### 개선
- **메트릭 미설치 시 안내** — 클러스터에 `metrics-server` 가 없으면 메트릭 카드가 단순히 `N/A` 만 보였던 것을 `metrics-server 없음` 이라고 명시. CPU 값은 `—`, 스파크라인은 빈 상태로 클리어.
- 메트릭이 정상으로 들어올 때는 폰트(`16pt bold`) 와 색상(그린/블루) 을 다시 적용해서 토글 시 시각적으로 확실히 구분.

### 검증
- ✅ 캔버스 폭 동기화 — `<Configure>` 이벤트가 도착할 때마다 `itemconfig(width=e.width)` 호출
- ✅ 사이드바 "파드" 클릭 → 리소스 탐색기 탭 활성화 + 표 표시
- ✅ 대시보드 탭은 별도 클릭 시에만 인스펙터 뷰 진입
- ✅ 연결 직후 대시보드 탭이 활성 상태 유지

---

## v2.0.2 — 2026-04-30  ·  버전 동기화 가드

### 수정
- **(중요) `bastion.py` 의 `VERSION` 상수가 CHANGELOG 와 어긋나는 문제 해결**
  - 증상: v2.0.1 패치를 CHANGELOG 에 기록했지만 `bastion.py` 의 `VERSION = '2.0.0'` 을 올리지 않아, 빌드된 `.exe` 의 타이틀에는 여전히 `v2.0.0` 이 표시됨.
  - 원인: 두 파일을 사람이 수동으로 동기화. 한쪽을 빠뜨려도 빌드가 막힘 없이 진행됨.
  - 조치:
    1. `bastion.py` 의 `VERSION` 을 `2.0.2` 로 갱신
    2. **신규 빌드 스크립트 `build.py` 추가** — 빌드 전에 자동으로 다음을 검사:
       - `bastion.py` 의 `VERSION = "X.Y.Z"` 추출
       - `CHANGELOG.md` 의 최상단 `## vX.Y.Z` 헤더 추출
       - 두 값이 일치하지 않으면 `[FAIL]` 로 빌드 중단 + 해결 방법 안내
    3. `build_exe.bat` 가 `build.py` 를 호출하도록 변경
    4. `build/`, `__pycache__/`, `dist/Bastion.exe` 자동 클린업 후 빌드
    5. 빌드 완료 후 산출물의 크기 / timestamp / 버전 자동 출력

### 새 도구
- `build.py` — 명령행 옵션:
  - `python build.py` — 가드 통과 시 빌드
  - `python build.py --check` — 가드만 검사 (빌드 안 함, CI 에서 PR 검사 용)
  - `python build.py --force` — 가드 무시 강행 (권장하지 않음)

### 운영 규칙 (앞으로)
새 버전을 낼 때는 **반드시 다음 두 곳을 같이 수정**:
1. `bastion.py` 상단의 `VERSION = 'X.Y.Z'`
2. `CHANGELOG.md` 최상단에 `## vX.Y.Z — YYYY-MM-DD` 헤더 추가

빠뜨려도 `python build.py` 가 차단해 주니 안심.

---

## v2.0.1 — 2026-04-30  ·  배포 빌드 갱신

### 수정
- **(중요) `dist/Bastion.exe` 재빌드** — v2.0.0 의 모든 코드 변경이 기존 `.exe` 에 반영되어 있지 않던 문제 해결.
  - 증상: `Bastion.exe` 실행 시 v1.x 의 VSCode Dark+ 디자인이 그대로 표시됨.
  - 원인: PyInstaller `.exe` 는 빌드 시점의 `bastion.py` 스냅샷을 번들링. v2.0.0 코드 작성 후 재빌드를 누락.
  - 조치: `pyinstaller --noconfirm Bastion.spec` 으로 재빌드. 새 exe (19.7MB) 생성 확인.
  - 빌드 명령: `pyinstaller --noconfirm Bastion.spec` (또는 `build_exe.bat` 실행)
  - 빌드 산출물: `dist/Bastion.exe` (timestamp: 2026-04-30 13:43)

### 검증
- ✅ 신규 `.exe` 4초 실행 → 정상 동작, 크래시 없이 종료
- ✅ `Bastion.spec` 의 `pyte` / `winpty` hidden imports 정상 포함

---

## v2.0.0 — 2026-04-30  ·  Warm Dark Operator + Inspector Dashboard

기존 `v1.x` (VSCode Dark+ 기반 4분할) 에서 **전면 개편**.
Claude Design 으로 받은 시안 1 (Warm Dark Operator) + 시안 6 (3-Panel Inspector) 기반.

### 디자인 시스템 (BREAKING)
- **컬러 팔레트 전체 교체**: VSCode Dark+ → **Warm Dark + Nimbus Networks**
  - 기존: `#1e1e1e` (editor) + `#007acc` (accent)
  - 신규: `#1c1a16` (warm dark, 갈색조) + `#7CB342` (Nimbus 그린) + `#4A6FA5` (Nimbus 블루)
  - 텍스트: `#d4d4d4` (cool white) → `#f5ead6` (warm white)
- `C` dict 키 확장:
  - 추가: `bg_0` ~ `bg_5` (단계별 배경), `nimbus_g/gl/gd/b/bl/bd`, `text_4`, `info_purple/cyan/rose/amber`
  - 유지 (별칭으로 매핑): `editor`, `sidebar`, `tab_bar`, `accent`, `teal`, `green`, `blue`, `red`, `yellow`, `orange`, `border`, `hover`, `selection`, `scrollbar`, `tag_run/pend/fail`, `st_ok/err/warn`, `term_bg/text` 등 — 기존 코드 호환 유지
- **폰트**: `Malgun Gothic` 고정 → `Pretendard` / `Noto Sans KR` / `Malgun Gothic` 자동 폴백
  - `_resolve_fonts()` 가 root 생성 후 가용 폰트 탐색
  - 폰트 크기 토큰 추가: `FS_S=9` (소형), `FS_L=13` (타이틀), `FS_H=11` (헤더)

### 새 기능
- **🆕 대시보드 탭 (DashboardTab)** — 시안 6 Inspector 레이아웃 기반, 첫 번째 활성 탭
  - 좌(200px): 네임스페이스 트리. 파드 수 표시. 클릭 시 해당 NS만 필터링.
  - 중(가변): 파드 컴팩트 리스트. 상태 점, 이름, NS, Ready, 재시작, 나이 컬럼.
  - 우(380px): 선택된 파드의 상세 인스펙터
    - 파드 이름 + 네임스페이스 + StatusChip
    - **METRICS · LIVE**: CPU/Memory 카드 (값 + 미니 스파크라인). 5초 폴링.
    - **METADATA**: Node, IP, Host IP, QoS, Age, Image
    - **EVENTS**: 파드 관련 이벤트 (최신순, 최대 20건). Warning은 황색 강조.
    - **액션 버튼**: `로그 보기`, `Exec`, `삭제`
- **🆕 인스펙터 액션 통합**
  - 로그 보기 → 로그 뷰어 탭으로 자동 전환 + pod_logs 모드 + 해당 파드 자동 선택 + 스트리밍 시작
  - Exec → kubectl 터미널 탭으로 전환 + `exec -it -n <ns> <name> -- sh` 명령 미리 입력
  - 삭제 → 확인 다이얼로그 후 `core_v1.delete_namespaced_pod()` 호출
- **🆕 사이드바 라우팅 변경**
  - 사이드바에서 `파드` 클릭 → 대시보드 탭 활성화 (기존: 리소스 탐색기)
  - 그 외 리소스(노드, 디플로이먼트 등) → 기존대로 리소스 탐색기 탭

### K8sManager API 추가
- `get_pod_metrics(ns, name)` — `metrics.k8s.io/v1beta1` Custom API. 실패 시 `None`. `cpu_m`(millicore), `mem_mi`(MiB) 반환.
- `get_node_metrics()` — 전체 노드 메트릭. 실패 시 빈 리스트.
- `get_pod_events(ns, name, limit=20)` — `field_selector=involvedObject.kind=Pod,involvedObject.name=<>` 로 이벤트 조회. 최신순 정렬.
- `get_pod_detail(ns, name)` — IP, Node, QoS, 컨테이너, 이미지 등 상세 정보.
- `delete_pod(ns, name)` — 파드 삭제. `(ok, msg)` 반환.
- `connect()` 에 `CustomObjectsApi` 초기화 추가.

### 새 위젯 클래스
- **`NimbusMark(tk.Canvas)`** — Nimbus Networks 로고 마크 (NK 형태). `size` 파라미터로 크기 조정.
- **`Sparkline(tk.Canvas)`** — 미니 라인 차트. `set_data(seq)` 로 갱신. CPU/Mem 카드에서 사용.
- **`StatusChip(tk.Frame)`** — 파드 상태 칩 (점 + 텍스트 + 색상 배경). `Running`/`Pending`/`CrashLoopBackOff` 등 매핑.

### UI 개편 (시안 1 적용)
- **타이틀바** (44px 고정)
  - 좌측: NimbusMark + `Bastion` 라벨 (그린)
  - Config 입력 + 찾기 버튼 + **연결 버튼 (그린, 연결 시 다크 변경)**
  - NS 콤보박스 + 검색 입력 + F5 키 힌트 + 새로고침 버튼
- **사이드바** (232px, 리사이즈 가능)
  - `EXPLORER` 헤더 (작은 글자, 자간 강조)
  - 카테고리 → 리소스 → 도구 항목 색상 분리
  - 도구 항목 (kubectl 터미널 / k9s) 은 `nimbus_gl` 라이트 그린
- **탭바** (36px)
  - 활성 탭: 하단 2px **그린 인디케이터** + 본문과 같은 어두운 배경 (`bg_1`)
  - 비활성 탭: `bg_3` 배경, `text_dim` 흐린 글자
  - 탭 5개: `대시보드` / `리소스 탐색기` / `로그 뷰어` / `kubectl 터미널` / `k9s`
- **상태바**
  - 연결 시: `nimbus_gd` (#5E8C2F, 그린 딤) + `Bastion v2.0.0` 버전 표기
  - 연결 안됨: `st_err` (#8c3a2f, warm red)

### 헬퍼 함수
- `_pick_font(*candidates)` — 시스템에 설치된 첫 번째 폰트 패밀리 반환.
- `_parse_cpu(s)` — metrics.k8s.io 의 cpu 값 (`123n`/`45m`/`0.1`) → millicore int.
- `_parse_mem(s)` — memory 값 (`123Ki`/`456Mi`) → bytes int.

### 호환성
- 기존 `LogViewerTab`, `KubectlTerminalTab`, `K9sTerminal` 클래스는 모두 그대로 유지. 새 색상 팔레트의 별칭 키 (`editor`, `accent` 등) 가 자동으로 새 색상에 매핑되어 **코드 변경 없이 재스타일링** 됨.
- 기존 사용자의 `~/.kube/kubectl.exe`, `~/.kube/k9s.exe` 캐시는 그대로 사용 가능.

### 검증
- ✅ `python -c "import bastion"` — 임포트 통과
- ✅ `BastionApp(tk.Tk())` 인스턴스화 — 위젯 트리 정상 빌드
- ✅ 5개 탭 (`dashboard`, `resources`, `logs`, `terminal`, `k9s`) 순차 활성화 — 오류 없음
- ✅ 활성 탭이 `dashboard` 로 자동 설정됨
- ✅ `Sparkline`, `NimbusMark`, `StatusChip` 인스턴스 생성 정상

---

## v1.x 이전 (참고용)

본 프로젝트의 v1 시리즈는 VSCode Dark+ 컬러 팔레트 기반 4분할 운영 도구였습니다.
주요 마일스톤:
- 초기 버전: 클러스터 연결 + 리소스 테이블 (Treeview)
- v1.1 — 인라인 탭 상세 보기
- v1.2 — 실시간 로그 뷰어 탭 (`LogViewerTab`)
- v1.3 — kubectl 자동 다운로드, 임베디드 kubectl 터미널 탭
- v1.4 — k9s 임베디드 터미널 (pywinpty + pyte VT100), 자동 다운로드, 파일 존재 기반 캐싱
- v1.5 — 인그레스 통합 로그 뷰, 워크로드별 로그 필터링
- v1.6 — `DESIGN_CONTEXT.md` 작성 (Claude Design 핸드오프 준비)

상세한 기능 변경 이력은 `bastion.py` 내부의 `# ─` 섹션 주석을 참고하세요.

---

## 향후 계획 (Roadmap)

| 버전 | 항목 | 상태 |
|---|---|---|
| v2.0.1 | 대시보드 진입 시 자동 새로고침 후 첫 파드 자동 선택 | 백로그 |
| v2.0.x | 노드 대시보드 (시안 6 inspector를 노드용으로 확장) | 백로그 |
| v2.1.0 | 토폴로지 뷰 (시안 4 참고) | 백로그 |
| v2.1.x | 글로벌 검색 (Cmd+P / Ctrl+P, 시안 3 참고) | 백로그 |
| v2.2.0 | KPI 카드 대시보드 (시안 2 참고, 클러스터 전체 메트릭) | 백로그 |

---

## 패치 기록 양식 (v2.0.x 부터 적용)

```
## v2.0.1 — YYYY-MM-DD
### 수정
- (버그) 어떤 증상이 어떤 원인으로 발생했고 어떻게 고쳤는지

### 개선
- 어떤 부분이 어떻게 개선됐는지

### 새 기능
- (있다면)
```
