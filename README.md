<div align="center">

<img src="docs/polaris-banner.png" alt="POLARIS">

# POLARIS

### Kubernetes Cluster Management GUI for Windows

**Free Build (no app catalog · no infra managing)** · v1.2.2-f1

[![Latest](https://img.shields.io/badge/release-v1.2.2--f1-f3c969?style=flat-square)](https://github.com/forestian/polaris/releases)
[![Build](https://img.shields.io/badge/build-free%20edition-7dd3fc?style=flat-square)](https://github.com/forestian/polaris)
[![Platform](https://img.shields.io/badge/platform-Windows%2064--bit-c8c4dc?style=flat-square)](#)
[![License](https://img.shields.io/badge/license-MIT-7dd3fc?style=flat-square)](./LICENSE)
[![Kubernetes](https://img.shields.io/badge/Kubernetes-1.30--1.36-326CE5?style=flat-square&logo=kubernetes&logoColor=white)](#kubernetes-호환성)
[![Security Policy](https://img.shields.io/badge/security-policy-7dd3fc?style=flat-square)](./SECURITY.md)
[![Checksum](https://img.shields.io/badge/checksum-SHA256%2FSHA512-f3c969?style=flat-square)](https://github.com/forestian/polaris/releases)
[![CI](https://github.com/forestian/polaris/actions/workflows/ci.yml/badge.svg)](https://github.com/forestian/polaris/actions/workflows/ci.yml)

[**한국어**](#-한국어) · [**English**](#-english)

</div>

---

<a id="-한국어"></a>

<details open>
<summary><h2> 한국어</h2></summary>

### Polaris 란?

윈도우용 **단일 EXE 쿠버네티스 클러스터 관리 데스크톱 앱**.
PyWebView + React 로 만들어졌고, 파이썬 설치 없이 실행됩니다. kubeconfig 로
클러스터에 연결해 리소스 탐색 / 로그 스트리밍 / kubectl·k9s 실행 / **클러스터
스냅샷 시점 비교** / **RBAC 권한 분석** / **DOCX 운영 점검 보고서** 생성을, 그리고
민감한 설정을 **암호화 보안 보관함**에 담아 — 한 UI 에서.

### 스크린샷

<div align="center">

| | |
|:---:|:---:|
| <img src="docs/screenshots/polaris-02-resources.png" width="480" alt="리소스 브라우저"> | <img src="docs/screenshots/polaris-01-dashboard.png" width="480" alt="대시보드"> |
| **리소스 브라우저** — 파드 목록 + 우측 상세 패널 | **대시보드** — 클러스터 상태 + 노드 CPU/MEM |
| <img src="docs/screenshots/polaris-04-topology.png" width="480" alt="토폴로지"> | <img src="docs/screenshots/polaris-03-logs.png" width="480" alt="로그 뷰어"> |
| **토폴로지 그래프** — Ingress → Service → Workload → Config/Storage | **로그 뷰어** — Deployment / StatefulSet 로그 스트리밍 |

</div>

### 다운로드

| 버전 | 다운로드 | 비고 |
|---|---|---|
| **v1.2.2-f1** (최신) | [polaris.exe](https://github.com/forestian/polaris/releases/download/v1.2.2-f1/polaris.exe) | 보안 보관함 · 스냅샷/Diff · RBAC 분석 · CRD |
| v1.0.13-e1 | [polaris.exe](https://github.com/forestian/polaris/releases/download/v1.0.13-e1/polaris.exe) | k9s 원클릭 설치 |

> 단일 실행 파일. Python / Node.js 설치 불필요. 유효한 kubeconfig와 Kubernetes API 서버 접근 권한이 있으면 실행 가능합니다.

**무결성 검증** (선택):
- [polaris.exe.sha256](https://github.com/forestian/polaris/releases/download/v1.2.2-f1/polaris.exe.sha256) · [polaris.exe.sha512](https://github.com/forestian/polaris/releases/download/v1.2.2-f1/polaris.exe.sha512)
- **PowerShell**: `Get-FileHash polaris.exe -Algorithm SHA256` → 출력된 Hash 값을 위 파일 내용과 비교
- **Bash / Git Bash** (sha256 파일을 polaris.exe 와 같은 폴더에 두고): `sha256sum -c polaris.exe.sha256` → `polaris.exe: OK`

### ⚠️ Windows SmartScreen 경고

현재 Polaris EXE는 코드서명 인증서로 서명되어 있지 않습니다.
Windows에서 처음 실행할 때 SmartScreen 경고가 표시될 수 있습니다.

공식 [GitHub Releases](https://github.com/forestian/polaris/releases)에서 다운로드한 파일이라면 아래 순서로 실행할 수 있습니다:

1. **추가 정보** 클릭
2. **실행** 클릭

> SHA256/SHA512 체크섬으로 파일 무결성을 먼저 확인하는 것을 권장합니다.  
> 향후 코드서명 적용을 검토 중입니다.

### 주요 기능

#### 코어 클러스터 관리
- **멀티클러스터 탭** — 여러 kubeconfig 동시 연결, 탭으로 전환
- **리소스 브라우저** — 15종 (Pods / Deployments / Services / Ingresses / PVCs / Secrets 등)
- **CRD 자동 발견** — 클러스터에 설치된 모든 CustomResourceDefinition 탐색 + 커스텀 객체 조회 (additionalPrinterColumns 반영, 객체 YAML 편집/삭제)
- **리소스 쓰기** — YAML 편집 후 적용(`kubectl apply`), **Scale**(replicas 조정), **Rollout Restart** — 모두 확인 모달 거침
- **리소스 상세 패널** — 개요 · 이벤트 · 메트릭 · 로그 · YAML · Describe
- **Secret 자동 마스킹** — base64 토큰 / TLS key 평문 노출 차단
- **검색 / 필터** — 실시간 검색, 네임스페이스 필터, 컬럼 정렬

#### 운영 점검 *(v1.2~)*
- **클러스터 스냅샷 + 시점 비교(Diff)** — 클러스터 전체 상태를 시점별로 저장하고 두 시점을 비교:
  리소스 추가(+)/삭제(−)/변경(~) + 변경 필드별 `old → new`, 그리고 새로 생긴/해결된 이슈 추이
- **RBAC 분석** — ServiceAccount 가 무엇을 할 수 있는지 역추적(binding → role → 권한),
  `verbs:*` 전체 권한 / cluster-admin 경고
- **DOCX 운영 점검 보고서** — 클러스터 개요 · 노드 · 워크로드 · 스토리지 · 발견 사항(과도 권한 포함) 자동 정리 (선택적 LLM 분석)

#### 보안 보관함 (Vault)
- **시작 잠금** — 프로그램을 열면 메인 UI 전에 마스터 비밀번호로 잠금 해제 (첫 실행은 생성)
- **암호화 보관** — kubeconfig 와 클러스터 스냅샷을 **AES-256-GCM + scrypt** 로 암호화 저장.
  스냅샷은 raw 파일로 열어도 내용을 알아볼 수 없고, 앱에서 잠금 해제했을 때만 열람·비교 가능
- **kubeconfig 자동 복원** — 한 번 연결한 클러스터는 다음 실행부터 원본 파일 없이 보관함에서 복원
- **잠금 방식 선택** — 매번 비밀번호 입력(기본·권장) 또는 현재 Windows 계정에서 자동 잠금 해제
- **데이터 폴더 위치 변경** — 모든 데이터 저장 위치를 원하는 폴더로 이동

#### 옵저버빌리티
- **대시보드** — 도넛 차트 3개 (노드 Ready율 / 파드 Running율 / 파드 수용률) + KPI 카드
- **파드 메트릭 그래프** — CPU/Memory 라인 차트 + request/limit 임계선 (5초 폴링)
- **토폴로지 그래프** — 6컬럼 SVG (Ingress → Service → Workload → Config/Storage → PV)
- **클러스터 이벤트** — 리소스별 필터링된 실시간 타임라인

#### 운영
- **kubectl 터미널** — 빌트인 터미널, 스트리밍 명령 자동 감지
- **k9s 런처** — Polaris 컬러 스킴 적용된 Windows Terminal 에서 k9s 실행, 미설치 시 **원클릭 설치** 버튼 제공
- **파드 셸** — 원클릭 `kubectl exec -it ... -- sh` 새 터미널에서
- **포트포워딩 GUI** — 시각적 포트포워드 관리 (시작/중지/목록)
- **CronJob 즉시 실행** — 스케줄 수정 없이 수동 실행
- **리소스 삭제** — 확인 모달로 실수 방지

#### 외부 연동
- **ArgoCD** — Application 목록 / Sync / Rollback / Create / Update / Delete
- **Helm 릴리스** — Helm CLI 또는 K8s Secret 폴백으로 릴리스 조회

#### UI / UX
- **시스템 트레이 통합**
  - 트레이 아이콘 더블클릭 또는 우클릭 → **"열기"** : 창 복원 (포커스 + 보이기)
  - 트레이 우클릭 → **"종료"** : 완전 종료 (세션 정리 + 전체 클러스터 disconnect + 프로세스 종료)
  - **단일 인스턴스 강제** — 두 번째 EXE 실행 시 새 창 띄우지 않고 기존 창만 활성화
- **세션 자동 복원** — 클러스터 탭 / 활성 탭 / 활성 페이지 / 네임스페이스 모두 복원
- **명령 팔레트** (Ctrl+K) — 어떤 리소스로도 빠르게 이동
- **Windows Terminal 컬러 스킴** — Polaris 프로파일 자동 주입 (k9s / 파드 셸에서 적용)

#### 설정
- **테마 (배경)** — **6종 컬러 테마 중 선택**, 즉시 적용
  - `polaris` (Polestar Gold · 기본) · `argus` · `aurora` · `forge` · `vault` · `pharos`
- **보안 잠금 방식** — 매번 비밀번호 / 자동 잠금 해제 토글
- **데이터 폴더** — 데이터 저장 위치 변경 (복사 후 재시작 반영)
- **X 버튼 동작** — `tray` (트레이로 숨김) 또는 `exit` (완전 종료) 토글
- **세션 자동 복원** — 다음 실행 시 클러스터 탭/페이지 복원 on/off 토글

### Kubernetes 호환성

| 범위 | 상태 |
|---|---|
| **K8s 1.34, 1.35** |  검증 완료 |
| **K8s 1.30 ~ 1.36** |  권장 |
| **K8s 1.22 ~ 1.29** |  코어 기능만 |
| **K8s ≤ 1.21 / ≥ 1.37** |  미검증 |

Polaris 는 v1 stable API (`CoreV1` / `AppsV1` / `BatchV1` / `NetworkingV1` /
`RbacV1` / `StorageV1` / `AutoscalingV1` / `PolicyV1`) 만 사용해 광범위하게 호환됩니다.
선택적 의존: `metrics.k8s.io` (메트릭 그래프), ArgoCD Application CRD (ArgoCD 페이지).

### 빠른 시작

1. [`polaris.exe`](https://github.com/forestian/polaris/releases/download/v1.2.2-f1/polaris.exe) 다운로드
2. 실행 — 설치 불필요
3. **첫 실행**: 보안 보관함 마스터 비밀번호 설정 (다음 실행부터는 이 비밀번호로 잠금 해제)
4. 타이틀바 `+` → kubeconfig 탐색 → 컨텍스트 선택 → 연결
5. 둘러보기: 대시보드 → 리소스 → 스냅샷 → 보고서

멀티 클러스터: `+` 한 번 더 클릭 후 다른 kubeconfig 추가. 탭으로 전환.

> 마스터 비밀번호는 분실 시 복구할 수 없습니다 (보관된 항목도 함께). 안전하게 보관하세요.

### 트러블슈팅

**SmartScreen 경고가 표시됩니다**  
공식 GitHub Releases 에서 받은 파일인지 확인 후 SHA256 체크섬을 검증하세요.
이상 없으면 **추가 정보 → 실행** 으로 실행 가능합니다.

**보안 보관함 비밀번호를 잊었습니다**  
마스터 비밀번호는 복구할 수 없습니다. 좌하단 **보안 보관함** 박스에서 "마스터 비밀번호 변경"(현재 비밀번호 필요)이 가능하며, 완전히 초기화하려면 `%USERPROFILE%\.polaris\vault.json` 을 삭제 후 재시작하세요 (보관된 항목은 모두 사라집니다).

**클러스터에 연결되지 않습니다**  
- kubeconfig 경로와 선택한 컨텍스트를 확인하세요
- VPN / 네트워크 연결 상태를 확인하세요
- Kubernetes API 서버에 직접 도달 가능한지 확인하세요 (`kubectl cluster-info`)
- 인증서 오류 또는 프록시 설정을 점검하세요

**메트릭(CPU/MEM)이 표시되지 않습니다**  
파드·노드 메트릭은 클러스터에 `metrics.k8s.io` API가 필요합니다.
`metrics-server` 설치 여부를 확인하거나, 클러스터의 메트릭 API 노출 여부를 점검하세요.

**k9s가 열리지 않습니다**  
k9s가 `PATH` 또는 `~/.kube/k9s.exe` 에 없으면, k9s 페이지의 **원클릭 설치** 버튼으로 GitHub 최신 릴리스에서 자동 설치할 수 있습니다 (`~/.kube/k9s.exe` 에 저장).
설치 후에도 열리지 않으면 [k9s 설치 가이드](https://k9scli.io/topics/install/) 를 참고해 수동 설치하세요.

**Helm 릴리스가 보이지 않습니다**  
- `helm` CLI 가 PATH 에 있거나 `~/.kube/helm.exe` 로 설치돼 있는지 확인하세요
- 해당 네임스페이스에 Helm 릴리스 Secret 이 존재하는지 확인하세요

**ArgoCD 페이지가 비어 있습니다**  
ArgoCD 연동은 클러스터에 ArgoCD Application CRD 가 설치돼 있어야 합니다.
ArgoCD가 배포된 클러스터에 연결됐는지 확인하세요.

### 아키텍처 (개발자용)

```
polaris.py            진입점 + 하위호환 re-export
src/
├── tools.py          외부 CLI 탐색 (kubectl/helm/k9s/WT)
├── k8s.py            K8sManager + 도메인 헬퍼
├── reports.py        DOCX/TXT/HTML 보고서 생성
├── snapshot.py       스냅샷 저장/로드/Diff (+ 암호화)
├── vault.py          보안 보관함 (AES-256-GCM + scrypt)
├── paths.py          데이터 디렉터리 위치 해석
├── topology.py       토폴로지 그래프 빌더 헬퍼
├── runtime.py        트레이 + 라이프사이클 + 단일 인스턴스
├── _state.py         공유 백그라운드 작업 dict
└── api/              PolarisAPI mixin 합성 (코어 자동 발견)
    ├── base.py       APIBase: 공유 상태 · 클러스터 · 세션 · 설정 · 연결
    ├── resources.py  리소스 CRUD · 이벤트 · RBAC · CRD · ArgoCD · Helm
    ├── terminal.py   kubectl / k9s / 파드 셸
    ├── port_forward.py
    ├── reports.py
    ├── details.py    파드 메트릭, 리소스 YAML/describe
    ├── logs.py       로그 스트리밍
    ├── topology.py   토폴로지 데이터
    ├── snapshots.py  스냅샷 take/list/diff
    └── vault.py      보안 보관함 (잠금/해제/kubeconfig 보관)
```

> 옵셔널 plugin 아키텍처: 코어가 아닌 `src/api/<name>.py` 는 자동 발견됩니다.
> 이 무료 빌드는 일부 옵셔널 plugin 을 포함하지 않습니다.

기술 스택: **Python 3.13 + kubernetes client + PyWebView + React 18 + Vite + PyInstaller (onefile)**

### 소스에서 빌드

```powershell
# UI
cd ui ; npm install ; npm run build

# Python 의존성
pip install -r requirements.txt

# EXE 빌드 (VERSION/CHANGELOG 동기화 검증, UI 빌드, PyInstaller 실행)
python build.py
# → dist/polaris.exe
```

### 라이선스

**MIT License** — [`LICENSE`](./LICENSE) 파일 참조.
자유롭게 사용·복사·수정·배포·재라이선스·판매 가능. 무보증.

</details>

---
<a id="-english"></a>

<details>
<summary><h2> English</h2></summary>

### What is Polaris?

A **single-EXE desktop application** for managing Kubernetes clusters on Windows.
Built with PyWebView + React, runs without Python installation. Connect to your
clusters via kubeconfig, then browse resources, stream logs, run kubectl/k9s,
**compare cluster snapshots over time**, **analyze RBAC**, generate **DOCX
inspection reports**, and keep sensitive config in an **encrypted vault** —
all from one polished UI.

### Screenshots

<div align="center">

| | |
|:---:|:---:|
| <img src="docs/screenshots/polaris-02-resources.png" width="480" alt="Resource browser"> | <img src="docs/screenshots/polaris-01-dashboard.png" width="480" alt="Dashboard"> |
| **Resource browser** — pod list with detail panel | **Dashboard** — cluster health + node CPU/MEM |
| <img src="docs/screenshots/polaris-04-topology.png" width="480" alt="Topology"> | <img src="docs/screenshots/polaris-03-logs.png" width="480" alt="Log viewer"> |
| **Topology graph** — Ingress → Service → Workload → Config/Storage | **Log viewer** — Deployment / StatefulSet log streaming |

</div>

### Download

| Version | Download | Notes |
|---|---|---|
| **v1.2.2-f1** (latest) | [polaris.exe](https://github.com/forestian/polaris/releases/download/v1.2.2-f1/polaris.exe) | Vault · Snapshot/Diff · RBAC analysis · CRD |
| v1.0.13-e1 | [polaris.exe](https://github.com/forestian/polaris/releases/download/v1.0.13-e1/polaris.exe) | k9s one-click install |

> Single executable. No Python or Node.js required. Requires a valid kubeconfig and access to a Kubernetes API server.

**Integrity verification** (optional):
- [polaris.exe.sha256](https://github.com/forestian/polaris/releases/download/v1.2.2-f1/polaris.exe.sha256) · [polaris.exe.sha512](https://github.com/forestian/polaris/releases/download/v1.2.2-f1/polaris.exe.sha512)
- **PowerShell**: `Get-FileHash polaris.exe -Algorithm SHA256` → compare the printed Hash with the contents of the .sha256 file
- **Bash / Git Bash** (with the .sha256 file next to polaris.exe): `sha256sum -c polaris.exe.sha256` → `polaris.exe: OK`

### ⚠️ Windows SmartScreen Warning

Polaris EXE is currently not signed with a code-signing certificate.
Windows SmartScreen may display a warning on first launch.

If you downloaded from the official [GitHub Releases](https://github.com/forestian/polaris/releases):

1. Click **More info**
2. Click **Run anyway**

> We recommend verifying the SHA256/SHA512 checksum before running.  
> Code signing is planned for a future release.

### Features

#### Core Cluster Management
- **Multi-cluster tabs** — Connect to multiple kubeconfigs simultaneously, switch with tabs
- **Resource browser** — 15 resource types (Pods/Deployments/Services/Ingresses/PVCs/Secrets etc.)
- **CRD auto-discovery** — Discover every CustomResourceDefinition in the cluster + browse custom objects (additionalPrinterColumns honored, object YAML edit/delete)
- **Resource write** — Edit & apply YAML (`kubectl apply`), **Scale** (adjust replicas), **Rollout Restart** — all behind confirm modals
- **Resource detail panel** — Overview · Events · Metrics · Logs · YAML · Describe
- **Secret auto-masking** — base64 tokens / TLS keys never shown in plain text
- **Search & filter** — Real-time search, namespace filter, column sort

#### Operational Inspection *(v1.2~)*
- **Cluster snapshots + diff** — Save full cluster state at a point in time and compare two points:
  resources added(+)/removed(−)/changed(~) with per-field `old → new`, plus new/resolved issue tracking
- **RBAC analysis** — Trace what a ServiceAccount can actually do (binding → role → permissions), with `verbs:*` / cluster-admin warnings
- **DOCX inspection reports** — Cluster overview · nodes · workloads · storage · findings (incl. over-privileged subjects), optional LLM insights

#### Security Vault
- **Startup lock** — Unlock with a master password before the main UI (created on first run)
- **Encrypted at rest** — kubeconfigs and cluster snapshots are encrypted with **AES-256-GCM + scrypt**.
  Snapshots are unreadable as raw files and can only be opened/compared inside the app once unlocked
- **kubeconfig auto-restore** — Once connected, a cluster is restored from the vault on next launch — no original file needed
- **Lock mode choice** — Prompt every launch (default·recommended) or auto-unlock on the current Windows account
- **Relocatable data folder** — Move where all data is stored to any folder you choose

#### Observability
- **Dashboard** — Donut charts (node Ready% · pod Running% · pod capacity%) + KPI cards
- **Pod metrics graphs** — CPU/Memory line charts with request/limit thresholds (5s polling)
- **Topology graph** — 6-column SVG showing Ingress → Service → Workload → Config/Storage → PV
- **Cluster events** — Real-time timeline filtered by resource

#### Operations
- **kubectl terminal** — Built-in terminal with streaming command auto-detection
- **k9s launcher** — Opens k9s in Windows Terminal with Polaris color scheme; **one-click install** when not found
- **Pod shell** — One-click `kubectl exec -it ... -- sh` in a new terminal
- **Port-forwarding GUI** — Visual port-forward management (start/stop/list)
- **CronJob trigger** — Manually run CronJobs without modifying schedules
- **Resource deletion** — Confirm modal prevents accidental deletes

#### Integrations
- **ArgoCD** — Application list / Sync / Rollback / Create / Update / Delete
- **Helm releases** — List releases via Helm CLI or fallback to Kubernetes secrets

#### UI / UX
- **System tray integration**
  - Tray icon double-click or right-click → **"Open"** : restore window (focus + show)
  - Tray right-click → **"Quit"** : full shutdown (clear session + disconnect all clusters + terminate process)
  - **Single-instance enforcement** — launching the EXE again only re-focuses the existing window
- **Session auto-restore** — cluster tabs / active tab / active page / namespace all restored on restart
- **Command palette** (Ctrl+K) — jump to any resource quickly
- **Windows Terminal color scheme** — Polaris profile auto-injected for k9s / pod shell

#### Settings
- **Theme (background)** — **pick from 6 color themes**, applied instantly
  - `polaris` (Polestar Gold · default) · `argus` · `aurora` · `forge` · `vault` · `pharos`
- **Security lock mode** — toggle between prompt-every-launch and auto-unlock
- **Data folder** — relocate where data is stored (copy, applied after restart)
- **X button behavior** — toggle between `tray` (hide to tray) and `exit` (full shutdown)
- **Session auto-restore** — on/off toggle for restoring cluster tabs/page on next launch

### Kubernetes Compatibility

| Range | Status |
|---|---|
| **K8s 1.34, 1.35** |  Verified |
| **K8s 1.30 ~ 1.36** |  Recommended |
| **K8s 1.22 ~ 1.29** |  Supported (core features only) |
| **K8s ≤ 1.21 / ≥ 1.37** |  Unverified |

Polaris uses only stable v1 APIs (`CoreV1` / `AppsV1` / `BatchV1` / `NetworkingV1` /
`RbacV1` / `StorageV1` / `AutoscalingV1` / `PolicyV1`), so the compatibility range
is very wide. Optional dependencies: `metrics.k8s.io` (for metrics graphs),
ArgoCD Application CRD (for ArgoCD page).

### Quick Start

1. Download [`polaris.exe`](https://github.com/forestian/polaris/releases/download/v1.2.2-f1/polaris.exe)
2. Run it — no installation needed
3. **First launch**: set a vault master password (used to unlock on subsequent launches)
4. Title bar `+` → browse your kubeconfig → select a context → Connect
5. Explore: Dashboard → Resources → Snapshots → Reports

For multi-cluster: click `+` again, add another kubeconfig. Switch with tabs.

> The master password cannot be recovered if lost (nor the stored items). Keep it safe.

### Troubleshooting

**SmartScreen warning appears**  
Verify you downloaded from the official GitHub Releases page and check the SHA256 checksum.
If the file is valid, click **More info → Run anyway**.

**I forgot the vault password**  
The master password cannot be recovered. You can change it from the **Vault** box (bottom-left) → "Change master password" (requires the current one). To reset completely, delete `%USERPROFILE%\.polaris\vault.json` and restart (all stored items are lost).

**Cannot connect to cluster**  
- Check the kubeconfig path and selected context
- Check VPN / network connectivity
- Verify the Kubernetes API server is reachable (`kubectl cluster-info`)
- Inspect certificate errors or proxy settings

**Metrics (CPU/MEM) are not showing**  
Pod and node metrics require the `metrics.k8s.io` API.
Check whether `metrics-server` is installed or if your cluster exposes the metrics API.

**k9s does not open**  
If k9s is not in your `PATH` or at `~/.kube/k9s.exe`, use the **one-click install** button on the k9s page to fetch the latest release from GitHub (saved to `~/.kube/k9s.exe`).
If it still does not open after installing, install manually → [k9s installation guide](https://k9scli.io/topics/install/)

**Helm releases are not visible**  
- Ensure `helm` is available in your `PATH` or installed at `~/.kube/helm.exe`
- Check that Helm release Secrets exist in the target namespace

**ArgoCD page is empty**  
The ArgoCD integration requires ArgoCD Application CRDs installed in the cluster.
Make sure you are connected to a cluster where ArgoCD is deployed.

### Architecture (for developers)

```
polaris.py            Entry point + backward-compat re-exports
src/
├── tools.py          External CLI discovery (kubectl/helm/k9s/WT)
├── k8s.py            K8sManager + domain helpers
├── reports.py        DOCX/TXT/HTML report generation
├── snapshot.py       Snapshot save/load/diff (+ encryption)
├── vault.py          Security vault (AES-256-GCM + scrypt)
├── paths.py          Data directory resolution
├── topology.py       Topology graph builder helpers
├── runtime.py        Tray + lifecycle + single-instance
├── _state.py         Shared background-job dicts
└── api/              PolarisAPI mixin composition (core auto-discovery)
    ├── base.py       APIBase: shared state · clusters · session · settings · connect
    ├── resources.py  Resource CRUD · events · RBAC · CRD · ArgoCD · Helm
    ├── terminal.py   kubectl / k9s / pod shell
    ├── port_forward.py
    ├── reports.py
    ├── details.py    Pod metrics, resource YAML/describe
    ├── logs.py       Log streaming
    ├── topology.py   Topology data
    ├── snapshots.py  Snapshot take/list/diff
    └── vault.py      Security vault (lock/unlock/kubeconfig storage)
```

> Optional-plugin architecture: non-core `src/api/<name>.py` modules are auto-discovered.
> This free build does not include some optional plugins.

Tech stack: **Python 3.13 + kubernetes client + PyWebView + React 18 + Vite + PyInstaller (onefile)**

### Build from source

```powershell
# UI
cd ui ; npm install ; npm run build

# Python deps
pip install -r requirements.txt

# Build EXE (validates VERSION/CHANGELOG sync, builds UI, runs PyInstaller)
python build.py
# → dist/polaris.exe
```

### License

Released under the **MIT License** — see [`LICENSE`](./LICENSE).
Free to use, copy, modify, merge, publish, distribute, sublicense, and sell.
No warranty.

</details>

---

<div align="center">

**Polaris** · _North star of your clusters_

Powered by PyWebView + React + kubernetes-client

</div>
