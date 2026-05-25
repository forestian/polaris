"""백그라운드 작업 (job) 상태의 단일 소유자 모듈.

PolarisAPI 의 여러 메서드가 백그라운드 스레드에서 작업을 시작하고,
별도 메서드에서 그 상태를 폴링합니다. 작업 dict 는 이 모듈에 단 한 번
정의되며 모든 호출자가 같은 객체를 import 해 공유합니다.

Phase 4 (PolarisAPI mixin 분할) 시 각 mixin 파일이 여기서 import 하여
같은 dict 를 참조하게 됩니다.
"""

# job_id → {status, logs, path, error}
_report_jobs: dict = {}

# job_id → {lines, proc, stopped, error}
_log_jobs: dict = {}

# job_id → 활성 kubectl port-forward 세션 메타
_port_forward_jobs: dict = {}

# 추가 plugin (예: 옵셔널 mixin) 이 자기만의 작업 dict 가 필요하면,
# 해당 plugin 모듈 (src/api/<feature>.py) 안에서 모듈 전역으로 정의하세요.
# 코어 _state 는 코어 mixin 들이 공유하는 dict 만 보유.
