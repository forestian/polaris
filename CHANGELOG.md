# POLARIS Changelog

이 문서는 POLARIS (Windows Kubernetes 클러스터 관리 GUI) 의 모든 변경/패치 내역을 기록합니다.

버전 표기 규칙 (v1.0.3 이후):
- `vX.0` — 메이저 (전면 개편)
- `vX.Y` — 마이너 (기능 추가)
- `vX.Y.Z` — 패치 (버그 수정 / 작은 개선)
- `vX.Y.Z-eN` — variant 빌드 (옵셔널 plugin 일부 제외, 예: 무료 = `-e1`)
- 향후 다른 알파벳 (`-fN`, `-sN` 등) — 제외 plugin 조합별 별도 식별자

빌드 구분:
- **풀패키지** (`vX.Y.Z`): 모든 옵셔널 plugin 포함 — 사내/유료
- **variant 빌드** (`vX.Y.Z-e1` 등): 일부 옵셔널 plugin 제거 — GitHub 공개 등

플러그인별 Changelog 분리 (v1.0.10~):
- 코어 변경 → 이 파일 (`CHANGELOG.md`)
- 앱 카탈로그 plugin 변경 → [`CHANGELOG-CATALOG.md`](./CHANGELOG-CATALOG.md)
- 새 plugin 추가 시 별도 `CHANGELOG-<plugin>.md` 운영 권장

> **v1.0.2 이전 표기 규칙** (`-rN` = 실험적): 옛 안정 트랙은 `v3-v1` 브랜치에 아카이브.

---

## v1.0.12-e1 — 2026-05-27  ·  UX 개선 — 로그/이벤트 저장·복사, 터미널 drag-copy

### 추가
- **로그 뷰어** (`LogPage`): 저장 버튼 — 현재 필터 결과를 `.log` 파일로 내보내기
- **이벤트 타임라인** (`EventsPage`): 복사(TSV) · 저장 버튼 — 필터된 이벤트 목록
- **kubectl 터미널** (`TerminalPage`):
  - 전체 출력 복사 버튼 추가
  - 출력 영역 드래그 텍스트 선택 시 포커스 이동 차단 (drag-copy 버그 수정)
- **리소스 패널** (`ResourcePanel`): YAML/Describe 복사 버튼을 스크롤바 겹침 없이 좌측 이동
- **진단 플래그** `--selfcheck`: 버전 / frozen 여부 / 활성 plugin 확인 (EXE 빌드 무결성 점검)

### 참고
- 앱 카탈로그 plugin 은 이 variant 에 포함되지 않습니다.

---

## v1.0.10-e2 — 2026-05-26  ·  보고서 '작성 조직' 행 제거

무료 빌드용 패치 — DOCX 운영 점검 보고서에서 표지 페이지와 1.3 점검 정보 표의
'작성 조직: Nimbus Networks' 행을 제거. 외부 사용자에게 부적절한 사내 조직명이
보고서에 박혀있던 문제 해결.

### 변경
- `src/reports.py`: `Nimbus Networks` 하드코딩 2곳 제거
  - 표지 페이지 (line 693 일대) — 점검 일시 / 클러스터 / 노드 만 표시
  - 1.3 점검 정보 표 (line 743 일대) — '작성 조직' 행 자체 제거

### 영향
- DOCX 보고서: '작성 조직' 행 사라짐
- 다른 항목 (클러스터 버전 / 점검 일시 / 노드 수 등) 그대로
- 기능 / 코드 동작 변화 없음
- master 풀패키지는 영향 없음 (이 변경은 polaris-free 브랜치 전용)

### 산출물
- `dist/polaris.exe` (재빌드)
- GitHub release v1.0.10-e2 + SHA-256/512 체크섬

---

## v1.0.10-e1 — 2026-05-26  ·  무료 빌드 (plugin 아키텍처 활용 첫 분리)

v1.0.10 의 plugin 아키텍처를 활용한 첫 번째 mechanical 분리 결과.
master 의 코어 코드를 **한 줄도 수정하지 않고** 디렉터리/파일 삭제만으로 빌드.

### 제거된 plugin 자산
- `catalog/` 디렉터리 (catalog.json + 6개 앱 + dashboards/*.json)
- `src/catalog.py` (loader / Grafana ConfigMap 빌더)
- `src/api/catalog.py` (CatalogMixin — 11 메서드 + catalog state dict)
- `tests/test_catalog.py` (카탈로그 7개 테스트)
- `CHANGELOG-CATALOG.md` (카탈로그 전용 changelog)
- `ui/src/pages/CatalogPage.jsx` + `catalogValues.js` + `catalogFilters.js`

### UI 수동 편집 (3 파일)
- `ui/src/api.js` : 카탈로그 / 스택 메서드 13개 제거
- `ui/src/App.jsx` : `CatalogPage` import / route 제거
- `ui/src/components/Sidebar.jsx` : "앱 카탈로그" 메뉴 + `AppWindow` icon 제거

### 코어 수정 0줄 — plugin 아키텍처 효과
- ✅ `src/api/__init__.py` : 자동 발견이 `ENABLED_FEATURES = ()` 로 처리
- ✅ `src/k8s.py` : `get_helm_releases_by_label` 은 generic 이라 그대로
- ✅ `src/_state.py` : 카탈로그 dict 가 mixin 안에 있어 자동 제거
- ✅ `polaris.py` : 조건부 import (`if 'catalog' in ENABLED_FEATURES`) 가 자동 skip
- ✅ `packaging/specs/Polaris.spec` : 디렉터리 자동 감지가 알아서 catalog/ 제외

### 검증
- python -m unittest discover tests: **46/46 PASS** (코어만; 옛 카탈로그 7개는 파일 자체 부재)
- `from src.api import ENABLED_FEATURES`: `()` (빈 튜플 = plugin 0)
- `HAS_CATALOG`: False (하위 호환 alias)
- PolarisAPI public methods: 63 → **52** (-11 카탈로그)

### 향후 — UI plugin 화
현재 UI 측 3 파일 수동 편집이 남음. v1.0.11 에서 UI 도 plugin manifest 기반으로
바꾸면 UI 측도 코어 수정 0 줄로 분리 가능. 그때까지는 매 e-build 시 이 3 라인 수정 수동 처리.

---

## v1.0.10 — 2026-05-25  ·  옵셔널 plugin 아키텍처 도입

향후 어떤 기능이든 카테고리 단위로 self-contained plugin 으로 격리하여,
variant 빌드 (예: 무료 = 일부 plugin 제거) 가 **mechanical 하게 자동 분리** 되도록 코어를 개편.
master 의 모든 기능 동작은 변화 없음 — 순수 아키텍처 정리.

### 핵심 변경
- **`src/api/__init__.py`** : 옵셔널 mixin 자동 발견
  - `src/api/` 디렉터리에서 코어가 아닌 `*.py` 파일을 스캔해 `*Mixin` 클래스 자동 등록
  - 코어에서 plugin 이름 (예: 'catalog') 을 hardcode 안 함
  - `ENABLED_FEATURES` 튜플로 활성 plugin 조회 가능 (예: `('catalog',)`)
  - `HAS_CATALOG` 는 하위 호환 alias 로만 유지

- **`src/k8s.py`** : `K8sManager` 에서 catalog 특화 메서드 제거
  - `get_catalog_label_releases()` → `get_helm_releases_by_label(key, value, extra_meta_key)` 일반화
  - K8sManager 가 plugin 의 라벨 이름 (`polaris-catalog`) 을 모름
  - catalog mixin 이 generic helper 를 호출해 자기 메타 가져옴

- **`src/_state.py`** : 카탈로그 작업 dict 제거
  - `_catalog_install_jobs` / `_stack_install_jobs` → `src/api/catalog.py` 모듈 전역으로 이동
  - 코어 state 는 plugin 마다 dict 가 늘어나지 않음 (각 plugin 이 자기 dict 보유)

- **`polaris.py`** : catalog re-export 를 조건부로
  - `if 'catalog' in ENABLED_FEATURES: try/except import` 로 감쌈
  - 코어 docstring 에서 catalog 언급 제거 ("옵셔널 plugin 은 자동 발견" 일반 설명으로)

- **`packaging/specs/Polaris.spec`** : `datas` 자동 분기
  - 옵셔널 데이터 디렉터리 목록을 루프로 검사 → 디렉터리 존재할 때만 datas 에 추가
  - `catalog/` 가 삭제된 variant 빌드에서도 spec 수정 불필요

- **테스트 분리**
  - `tests/test_catalog.py` (신규) : 카탈로그 plugin 전용 테스트 7개
    `@skipUnless('catalog' in ENABLED_FEATURES)` 로 미활성 빌드에서 자동 스킵
  - `tests/test_common_foundation.py` : 코어 테스트만 (46개)

- **Changelog 분리** (v1.0.10~)
  - 카탈로그 변경 → [`CHANGELOG-CATALOG.md`](./CHANGELOG-CATALOG.md) (신규)
  - 코어 변경 → 이 파일

### variant 빌드 만들기 — 개선 결과
**개선 전** (v1.0.9):
```
src/api/__init__.py 의 try/except CatalogMixin 수정
src/k8s.py 의 get_catalog_label_releases 제거
src/_state.py 의 catalog dict 제거
polaris.py docstring 정리
tests/test_common_foundation.py 의 catalog 테스트 7개 수정
CHANGELOG.md 의 catalog 줄 25+ 개 정리
README.md 의 catalog 섹션 정리
packaging/specs/Polaris.spec 의 datas 항목 제거
```

**개선 후** (v1.0.10):
```
rm -rf catalog/                       # 데이터
rm src/catalog.py src/api/catalog.py  # plugin
rm tests/test_catalog.py              # 테스트
rm CHANGELOG-CATALOG.md               # changelog
rm ui/src/pages/CatalogPage.jsx + 부속 4개   # UI
# 그 외 코어 파일 한 줄도 수정 안 함
```
→ 코어 코드 변경 0줄. 자동으로 plugin 비활성화.

### 검증
- `python -m unittest discover tests`: **53/53 PASS** (이전과 동일)
- `from src.api import ENABLED_FEATURES`: `('catalog',)` 그대로
- `polaris.HAS_CATALOG`: True (하위 호환)
- PolarisAPI 63 public methods 그대로
- master 기능 변화 0

### 향후 plugin 추가 패턴
1. `src/api/<plugin>.py` 작성 — `*Mixin` 클래스 + 자기 작업 dict + helper
2. (선택) `src/<plugin>.py` 추가 헬퍼
3. (선택) `<plugin>/` 데이터 디렉터리 — `packaging/specs/Polaris.spec` 의 자동 분기 리스트에 한 줄 추가
4. (선택) `tests/test_<plugin>.py` 작성
5. (선택) `CHANGELOG-<plugin>.md` 작성
6. UI 측: `ui/src/pages/<Plugin>Page.jsx` + Sidebar/App.jsx 의 menu/route 추가
→ 이게 끝. PolarisAPI 자동으로 plugin mixin 등록함.

---

## v1.0.9 — 2026-05-22  ·  앱 카탈로그 단일 앱 설치 확장

세션 공유 WAS를 스택 묶음 설치로 이동하고, Nginx와 Tomcat을 각각 별도 앱으로 설치할 수 있게 했습니다.

### 추가
- 앱 카탈로그 단일 앱 2종
  - **Nginx**: 공식 nginx 이미지, ConfigMap 기반 `default.conf` / `index.html`
  - **Tomcat**: 공식 tomcat 이미지, ConfigMap 기반 `server.xml` / `index.jsp`
- 공용 로컬 Helm chart `configurable-web`
  - Deployment / StatefulSet 전환 지원
  - StatefulSet 선택 시 headless service 자동 생성
  - Helm repo 의존 없이 EXE에 포함된 chart/values 로 설치
- 설치 모달 워크로드 유형 옵션
  - Nginx 기본 권장: Deployment
  - Tomcat 기본 권장: StatefulSet

### 변경
- **세션 공유 WAS**는 단일 앱 카드에서 숨기고 `스택 묶음 설치` 영역으로 이동
- 앱 카탈로그 설명을 운영 스택 + 단일 애플리케이션 구조로 정리

### 검증
- 카탈로그 계약 테스트 추가
- React 카탈로그 필터 / values.yaml 워크로드 옵션 단위 테스트 추가
- Nginx/Tomcat values 로 Helm lint 및 Deployment/StatefulSet 렌더링 검증
- Rancher Desktop K8s `v1.34.6+k3s1` 에 Nginx/Tomcat 실제 설치 후 HTTP 응답 확인, 테스트 네임스페이스 삭제 완료

---

## v1.0.8 — 2026-05-22  ·  설정 화면 테마 선택 추가

설정 버튼에서 종료 옵션과 배경 테마를 탭으로 나누고, Polaris 브랜드는 유지한 채 색감만 바꿀 수 있게 했습니다.

### 추가
- 설정 화면 2탭 구성
  - `종료 옵션`: 기존 트레이 최소화 / 완전 종료 / 자동 복원 설정
  - `배경 테마`: Polaris 기본값 + Argus / Aurora / Forge / Vault / Pharos 선택
- `themeId` 설정 저장
  - `%USERPROFILE%\.polaris\settings.json` 에 선택 테마 저장
  - 알 수 없는 theme id 는 안전하게 `polaris` 로 fallback
- React 테마 레지스트리
  - 디자인 자료의 `makeTheme(brand)` 토큰을 기반으로 CSS 변수 세트화
  - 앱 이름과 Polaris 아이콘은 유지하고 배경·텍스트·액센트 색상만 변경

### 검증
- `themeId` 저장/로드 단위 테스트 추가
- React 테마 레지스트리 단위 테스트 추가

---

## v1.0.7 — 2026-05-22  ·  세션 공유 WAS Rancher Desktop 실배포 검증

v1.0.6 의 세션 공유 WAS 카탈로그 항목을 로컬 Rancher Desktop 클러스터에 실제 배포해 검증했습니다.

### 검증
- Rancher Desktop `rancher-desktop` context, K8s `v1.34.6+k3s1` 에서 Helm 설치 성공
- `session-was-test-tomcat` Tomcat 2 replicas, `session-was-test-redis` Redis 1 replica 모두 Running 확인
- `/?value=polaris-...` 로 저장한 세션 값을 Tomcat Pod 삭제 후 다른 Pod에서 같은 `JSESSIONID` 로 복원 확인
- Redis에 `polaris-session-was:*` 세션 키 생성 확인
- 테스트 네임스페이스 `polaris-session-test` 삭제 완료

### 변경
- 기능 코드는 v1.0.6 과 동일합니다.
- 버전, README 최신 다운로드 링크, 릴리스 메타데이터만 v1.0.7 로 갱신했습니다.

---

## v1.0.6 — 2026-05-22  ·  세션 공유 WAS 카탈로그 추가

Tomcat 복제본 2개 이상이 Redis를 HTTP 세션 저장소로 공유하는 샘플 WAS 배포 항목을 앱 카탈로그에 추가했습니다.
Bitnami 차트 없이 Polaris에 포함된 로컬 Helm chart로 설치되며, 공식 Tomcat/Redis 이미지를 사용합니다.

### 추가
- 앱 카탈로그: **세션 공유 WAS**
  - Tomcat `11.0.22-jdk25-temurin` 복제본 2개 이상
  - Redis `8.6.3-alpine` 단일 인스턴스
  - Redisson Tomcat 11 Session Manager `4.3.1`
  - 세션 공유 검증용 JSP 샘플 페이지 포함
- Polaris 로컬 Helm chart 설치 지원
  - `catalog/.../chart` 를 EXE에 포함하고 Helm repo add/update 없이 설치
  - 기존 원격 Helm chart 설치 흐름은 유지

### 검증 포인트
- `/?value=polaris` 로 세션 값을 저장한 뒤 Tomcat 파드가 바뀌어도 같은 `JSESSIONID` 값이 Redis에서 복원되는지 확인 가능
- 기본 small 프리셋도 Tomcat 2 replicas 로 배포되어 세션 공유 검증이 가능

---

## v1.0.5 — 2026-05-22  ·  dist/ 단일 EXE 정책 + 빌드 산출물 정리

릴리스마다 dist/ 에 `polaris-vX.Y.Z.exe` 사본을 매번 만들지 않습니다.
이제 dist/ 에는 항상 `polaris.exe` 하나만 존재. 옛 버전이 필요하면
GitLab 태그 (`raw/vX.Y.Z/dist/polaris.exe`) 로 접근 가능 — 기록은 그대로.

### 변경
- `packaging/specs/Polaris.spec`: `name='Polaris'` → `name='polaris'` (소문자)
- `build.py`:
  - `EXE = dist/polaris.exe` (소문자)
  - `copy_versioned_exe()` 함수 제거 — 더 이상 버전별 사본 생성 안 함
  - 산출물은 매 빌드마다 dist/polaris.exe 하나로 덮어씀
- README: 다운로드 표 모든 행이 `dist/polaris.exe` 사용
- `dist/` 정리: 옛 versioned EXE 4개 (`polaris-v1.0.1-r1.exe`, `polaris-v1.0.2-r1.exe`,
  `polaris-v1.0.3.exe`, `polaris-v1.0.4.exe`) 및 옛 `Polaris.exe` 삭제

### 의도
- **저장공간**: 새 릴리스마다 +27MB 누적되던 패턴 정지 → 매번 같은 파일 덮어쓰기로 전환
- **옛 버전 접근**: 태그가 그 시점의 polaris.exe 를 보존 → README 의 "이전 버전" 행도 그대로 작동
- **명명 일관성**: 윈도우 explorer / 다운로드 폴더에서 소문자 `polaris.exe` 로 통일

### 영향 없음
- 사용자 경험 / API 시그니처 / 코드 구조: 모두 동일
- v1.0.4 의 mixin import 핫픽스 그대로 유지

---

## v1.0.4 — 2026-05-22  ·  mixin import 누락 4건 수정 (패치)

Phase 4 (PolarisAPI 78 메서드 → mixin 9개 분할) 시 누락된 `import` 4건을 수정한 핫픽스.
모두 try/except 안에서 동적으로 참조되는 이름이라 구체 증상은 다양했으나,
파드 상세 / 이벤트 / 포트포워드 / 카탈로그 일부 기능이 silent 실패 / NameError 로 빠지는 회귀.

### 수정
- `src/api/base.py` — `VERSION` (지연 import 로 변경)
- `src/api/catalog.py` — `_HELM_LOCAL` (from `src.tools` import 누락)
- `src/api/details.py` — `_age`, `datetime`, `timezone` (from `src.k8s` / `datetime` import 누락)
  - 영향: `get_pod_detail` 의 age 필드, `get_resource_events` 의 정렬 키 fallback
- `src/api/port_forward.py` — `timezone` (`datetime.now(timezone.utc)` 호출 실패)

### 검출 방법
AST 기반 정적 분석 — 모든 `src/api/*.py` 의 사용 이름과 import 이름을 비교해 누락 식별.
이번 패치 이후 모든 mixin 파일에서 미정의 이름 0건 확인.

### 변경 없음
- 코드 구조 / API 시그니처 / EXE 빌드 패턴: 모두 동일
- v1.0.3 의 새 명명 규칙 / 카탈로그 / 리팩토링 결과 그대로 유지

---

## v1.0.3 — 2026-05-22  ·  새 버전 표기 규칙 + 단일 master 브랜치 운영

v1.0.2-r1 의 모든 코드 (앱 카탈로그 + Phase 1~5 리팩토링) 를 그대로 풀패키지로 정착시키고,
버전 표기 규칙을 정리한 마일스톤.

### 변경 요약
- **버전 표기 규칙 변경**: `-rN` (실험적) → `-eN` (일부 기능 제외 빌드). 풀패키지는 접미사 없음.
- **단일 master 브랜치 운영**: 옛 `experimental` 브랜치를 master 로 통합. 향후 모든 작업은 master 에서.
- **옛 안정 트랙 아카이브**: 옛 master (v1.0.1 라인) 를 `v3-v1` 브랜치로 백업 → 기록 손실 0.
- 코드 변경 없음 (v1.0.2-r1 과 동일한 트리). 명명 / 문서 / 빌드 산출물 이름만 변경.

### 빌드 산출물
- `dist/polaris-v1.0.3.exe` — 풀패키지 (모든 기능)
- 향후: `dist/polaris-v1.0.3-e1.exe` — 무료 빌드 (앱 카탈로그 제외, spec 별도)

### 향후 계획
- `Polaris-Free.spec` 작성 → `polaris-v1.0.3-e1.exe` 빌드 활성화 (`src/api/__init__.py` 의 `try/except CatalogMixin` 로 이미 인프라 준비됨)
- GitHub 공개 — 무료 빌드만

---

## v1.0.2-r1 — 2026-05-22  ·  대형 리팩토링: 단일 파일 → src/ 패키지 분리 [구 실험적]

`polaris.py` 단일 파일 (6,482줄) 을 기능별 `src/` 패키지 19개 모듈로 분리.
**사용자 경험 / API 계약 / 빌드 산출물 변화 없음** — 순수 코드 구조 개선 + 향후
듀얼 빌드 (유료 카탈로그 포함 / 무료 카탈로그 제외) 의 기반 구축.

### 분리 결과
- `polaris.py`: **6,482줄 → 98줄 (-98.5%)** — 진입점 + 하위 호환 re-export 만
- `src/` 도메인 모듈 (7개): tools, k8s, reports, topology, catalog, runtime, _state
- `src/api/` mixin 패키지 (9개): base / resources / terminal / port_forward / reports / details / logs / topology / catalog
- 평균 파일 크기 ~365줄 (큰 파일도 1,608줄 = k8s.py)

### Phase 1~5 점진 마이그레이션 (5 커밋)
1. **Phase 1**: `src/tools.py` (361줄) + `src/k8s.py` (1,608줄) — 외부 CLI 헬퍼 + K8sManager
2. **Phase 2**: `src/reports.py` (1,442줄) + `src/topology.py` (105줄) — 보고서 + 토폴로지 헬퍼
3. **Phase 3**: `src/catalog.py` (273줄) + `src/_state.py` (24줄) — 카탈로그 격리 + 공유 dict 단일화
4. **Phase 4**: `src/api/*` 9개 mixin — PolarisAPI 78 메서드 분할 (다중상속 합성)
5. **Phase 5**: `src/runtime.py` (336줄) — 트레이 / 단일 인스턴스 / 생명주기 + main()

### 설계 원칙
- **UX 보존**: `__file__` 기반 경로 모두 보정 (catalog, tray icon, ui/dist) → frozen 모드 동일 동작
- **Mixin __init__ 금지**: APIBase 만 `__init__` 정의 → 초기화 순서 100% 보존
- **공유 상태 단일화**: 백그라운드 작업 dict 5개를 `src/_state.py` 한 곳에서 import 공유
- **하위 호환**: 모든 helper / 상수가 `polaris.X` 로 그대로 접근 가능 (테스트 / 외부 스크립트 호환)
- **카탈로그 격리**: `src/catalog.py` 와 `src/api/catalog.py` 를 `try/except` 로 선택적 로드 →
  spec 파일에서 두 파일 + `catalog/` 데이터 디렉터리만 제외하면 무료 빌드 자동 구성

### 검증
- `python -m unittest tests.test_common_foundation`: **44/44 PASS**
- `python build.py --check`: 버전/CHANGELOG 동기화 확인
- PolarisAPI: 76 메서드 (63 public + 13 private) 변동 없음
- `HAS_CATALOG=True`, `get_catalog()` 정상 응답 (apps=5, stacks=3)
- MRO: PolarisAPI → 8 mixins → APIBase → object (11 클래스)

### 향후 (이번 릴리스 범위 밖)
- 무료 빌드용 `Polaris-Free.spec` (카탈로그 제외) 활성화
- GitHub 공개 (무료 빌드만)

---

## v1.0.1-r1 — 2026-05-21  ·  Polaris 명칭 정리 + 앱 카탈로그 API 복구 [실험적]

- 안정 라인 `v1.0.1` 변경사항을 반영했습니다.
- `experimental` 브랜치에서 누락됐던 앱 카탈로그 backend API를 복구했습니다.
  UI가 호출하는 `get_catalog`, `catalog_preflight`, `start_catalog_install`, `start_stack_install`,
  `get_installed_catalog_apps` 등 카탈로그 설치/조회 계약을 다시 제공합니다.
- Helm 릴리스 label, Grafana ConfigMap 이름, dashboard UID/tag, Alloy cluster label을 `polaris-*` 체계로 정리했습니다.
- 보고서 생성, 세션/설정 경로, single-instance signal, pywebview event bridge, 빌드 진입점을 Polaris 기준으로 정리했습니다.

## v1.0.1 — 2026-05-21  ·  Polaris 런타임 명칭 정리 [안정]

- Python 진입점을 `polaris.py`, PyInstaller spec을 `Polaris.spec`, 산출물을 `polaris-v1.0.1.exe`로 정리했습니다.
- 사용자 데이터 경로를 `~/.polaris`로 전환해 완전 종료 후 재실행 상태와 Polaris 런타임 명칭을 일치시켰습니다.
- 보고서 기본 파일명과 HTML 타이틀을 Polaris 기준으로 변경했습니다.
- UI/runtime event bridge와 single-instance signal을 Polaris 기준으로 변경했습니다.

---

## v1.0.0-r1 — 2026-05-18  ·  POLARIS 출범 + 앱 카탈로그 트랙 [실험적]

Bastion v3.8.0-r1 (experimental) 코드베이스 그대로 + 전면 리브랜딩.

### 리브랜딩
- **이름**: `Bastion` → **`POLARIS`** (북극성)
- **로고**: 8각 컴퍼스 별 + Polestar Gold 그라데이션 + 후광/광선 (`ui/src/components/PolarisMark.jsx`)
- **타이틀바 텍스트**: gradient text — `linear-gradient(90deg, #ffe9b8, var(--nimbus) 55%, var(--blue))`
- **부제**: "NIMBUS NETWORKS"

### 디자인 토큰 (Polaris Design System v1)
- **베이스 배경**: 미드나잇 인디고 (`#060914` ~ `#2e3360`) · 이전 Nimbus 다크 블루(`#060e1c` ~ `#263e65`)에서 인디고/보라 톤으로 이동
- **텍스트**: 라일락-크림 (`#c8c4dc` ~ `#f0e8f5`)
- **메인 액센트**: **Polestar Gold** (`#f3c969` / dark `#c89a3e`) · 이전 민트 그린(`#34d399`)에서 골드로 이동
- **상태 컬러**: 시그널 시안 (running, `#7dd3fc`) · 옐로우 (warning) · 레드 (error) · 라일락 (info, `#b9b3df`)
- **`--nimbus` 변수명은 유지** — 기존 컴포넌트 코드 호환 (값만 골드로 재매핑)

### 변경 파일
- `ui/src/index.css` — CSS variables 전면 교체 (15 색 토큰)
- `ui/src/components/PolarisMark.jsx` — 신규 (SVG 별 + 후광/광선 컴포넌트)
- `ui/src/App.jsx` — 타이틀바: `NimbusMark` 컴포넌트 제거 → `PolarisMark` + "POLARIS" gradient text + "NIMBUS NETWORKS" 부제
- `ui/src/components/StatusBar.jsx` — `Bastion v...` → `Polaris v...`
- `ui/index.html` — `<title>Bastion</title>` → `<title>Polaris</title>`
- `bastion.py` — `VERSION = '1.0.0-r1'`, webview create_window title, pystray icon name+title
- `build.py` — `dist/Polaris.exe`, 산출물 이름 `polaris-v{VERSION}.exe`, 빌드 헤더/완료 텍스트
- `packaging/specs/Bastion.spec` — PyInstaller `name='Polaris'`
- `ui/package.json` — `name: "polaris-ui"`, `version: "1.0.0-r1"`

### 유지 (호환성)
- `bastion.py` 파일명 그대로 — 진입점 식별자 안정
- `~/.bastion/session.json` 등 사용자 데이터 디렉터리 그대로 — 기존 세션 유지
- `bastion-catalog=true` Helm 라벨 그대로 — 기존 클러스터의 카탈로그 설치 릴리스 식별 호환

### 포함된 기능 (Bastion v3.8.0-r1 그대로)
- 멀티클러스터 탭 / 대시보드 / 리소스 브라우저 / 토폴로지 / 로그 뷰어 / 보고서(DOCX)
- 파드 메트릭 그래프 (5초 폴링) / 이벤트 타임라인 / 명령 팔레트(⌘K) / CronJob 즉시 실행
- kubectl 터미널 (streaming 자동 감지) / k9s 런처 / 포트포워딩 GUI / ArgoCD / Helm
- **앱 카탈로그** — 스택 묶음 3종 (lgtm-full / log-trace / metrics-only) + 자체 대시보드 4종 (LGTM 통합 / Node Exporter Full / Logs App / Traces App)
- 시스템 트레이 + 자동 복원 + 단일 인스턴스
- 보안 패치 4건 (RFC1123 검증 / Secret 마스킹 / LLM 외부 URL 경고 / ArgoCD Sync 확인)
- PyInstaller numpy 제외 빌드 (EXE 약 28 MB)

---
