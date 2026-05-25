"""Polaris 소스 패키지.

polaris.py 진입점에서 이 패키지의 모듈들을 import 합니다.

코어 모듈 (모든 빌드에 항상 포함):
  - src.tools     : 외부 CLI(kubectl/helm/k9s/Windows Terminal) 탐색 + subprocess
  - src.k8s       : K8sManager 클래스 + k8s 도메인 헬퍼
  - src.reports   : DOCX/TXT/HTML 보고서 생성
  - src.topology  : 토폴로지 그래프 빌더
  - src.runtime   : 트레이 / 라이프사이클 / 단일 인스턴스
  - src.api       : PolarisAPI mixin 합성 (pywebview 노출)
  - src._state    : 코어 백그라운드 작업 dict

옵셔널 plugin 모듈 (variant 빌드에서 제거 가능):
  - src/api/ 하위의 비-코어 *.py 파일이 자동으로 plugin 으로 등록됨.
  - 추가 helper 가 필요하면 같은 이름의 src/<feature>.py 모듈을 만들 수 있음
    (예: 외부 데이터 디렉터리, 매니페스트 빌더 등).
  - 코어는 plugin 의 이름을 알지 않음. plugin 추가/제거 시 코어 코드 수정 불필요.
"""
