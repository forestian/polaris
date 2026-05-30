"""PolarisAPI — pywebview 에 노출되는 JSON API 퍼사드.

PolarisAPI 는 기능별 mixin 의 다중상속으로 합성됩니다.
각 mixin 은 자기 영역의 메서드만 가지며, 공유 상태/__init__ 는 APIBase 에 있습니다.
MRO 종착점이 APIBase 가 되도록 mixin 순서의 맨 마지막에 APIBase 를 배치합니다.

────────────────────────────────────────────────────────────────────────
플러그인 아키텍처 (v1.0.10~)
────────────────────────────────────────────────────────────────────────
mixin 은 두 부류로 나뉩니다:

  1. 코어 mixin (CORE_MIXIN_MODULES) — 모든 빌드에 항상 포함되는 기본 기능.
     resources / terminal / port_forward / reports / details / logs / topology

  2. 옵셔널 mixin (자동 발견) — src/api/ 의 위 목록에 없는 *.py 파일.
     해당 파일이 있으면 자동으로 PolarisAPI 에 등록됨.
     파일이 없으면 (= 변형 빌드에서 삭제됨) 조용히 건너뜀.

variant 빌드 (예: 일부 기능 제거) 만들기:
  • src/api/<feature>.py 파일을 삭제하면 끝.
  • 코어 코드는 한 줄도 안 건드림.
  • ENABLED_FEATURES (모듈 전역) 으로 활성 플러그인 ID 확인 가능.
"""
import importlib
import pkgutil
from pathlib import Path

from .base         import APIBase
from .resources    import ResourcesMixin
from .terminal     import TerminalMixin
from .port_forward import PortForwardMixin
from .reports      import ReportsMixin
from .details      import DetailsMixin
from .logs         import LogsMixin
from .topology     import TopologyMixin
from .snapshots    import SnapshotsMixin
from .vault        import VaultMixin

# ── 코어 mixin 목록 (항상 포함) ─────────────────────────────────────────────
_CORE_MIXINS = [
    ResourcesMixin, TerminalMixin, PortForwardMixin,
    ReportsMixin, DetailsMixin, LogsMixin, TopologyMixin,
    SnapshotsMixin, VaultMixin,
]

# 자동 발견에서 제외할 모듈 (코어 + 내부 헬퍼)
_CORE_MODULE_NAMES = {
    '__init__', 'base', 'resources', 'terminal', 'port_forward',
    'reports', 'details', 'logs', 'topology', 'snapshots', 'vault',
}


def _discover_optional_mixins():
    """src/api/ 패키지에서 코어가 아닌 *Mixin 클래스를 자동 등록.

    반환: [(feature_id, MixinClass), ...]
        feature_id 는 모듈명 (예: 'catalog').

    ▸ 개발 환경: 파일시스템의 *.py 를 pkgutil.iter_modules 로 열거.
    ▸ PyInstaller frozen EXE: glob('*.py') 는 PYZ 아카이브 안의 파일을 찾지
      못하므로 pkgutil.iter_modules(__path__) 를 사용한다. PyInstaller 4+ 의
      pyi_rth_pkgutil 런타임 훅이 이 호출을 frozen 아카이브 목록으로 리다이렉트.
      폴백으로 파일시스템 glob 을 추가로 시도해 어느 환경에서도 동작을 보장.

    파일이 없으면 (variant 빌드) 빈 리스트. import 에러도 조용히 무시.
    """
    found = []

    # ① pkgutil.iter_modules — 개발/frozen 양쪽 지원 (권장 경로)
    stems: set[str] = set()
    try:
        for mi in pkgutil.iter_modules(__path__):
            if mi.name not in _CORE_MODULE_NAMES and not mi.name.startswith('_'):
                stems.add(mi.name)
    except Exception:
        pass

    # ② 파일시스템 glob — 개발 환경 폴백 (frozen 에서는 아무것도 추가 안 됨)
    try:
        pkg_dir = Path(__file__).resolve().parent
        for f in pkg_dir.glob('*.py'):
            if f.stem not in _CORE_MODULE_NAMES and not f.stem.startswith('_'):
                stems.add(f.stem)
    except Exception:
        pass

    for stem in sorted(stems):
        try:
            mod = importlib.import_module(f'.{stem}', package=__package__)
            # 해당 파일에서 직접 정의된 첫 번째 *Mixin 클래스 사용
            mixin_cls = next(
                (obj for name, obj in vars(mod).items()
                 if name.endswith('Mixin') and isinstance(obj, type)
                 and obj.__module__ == mod.__name__),
                None,
            )
            if mixin_cls is not None:
                found.append((stem, mixin_cls))
        except Exception as e:
            OPTIONAL_PLUGIN_ERRORS[stem] = f'{type(e).__name__}: {e}'
            # 변형 빌드에서 파일이 없거나 의존성이 없는 경우 — 조용히 무시
            continue
    return found


OPTIONAL_PLUGIN_ERRORS = {}


_optional = _discover_optional_mixins()

# 활성 옵셔널 플러그인의 ID 목록 (모듈 전역, 외부에서 조회 가능)
ENABLED_FEATURES = tuple(fid for fid, _ in _optional)

# 최종 mixin 체인: 코어 + 자동 발견된 옵셔널
_MIXINS = _CORE_MIXINS + [cls for _, cls in _optional]


class PolarisAPI(*_MIXINS, APIBase):
    """pywebview JS API 퍼사드.

    mixin 합성 결과로 모든 메서드가 인스턴스의 dir() 에 노출되며,
    pywebview 가 자동으로 window.pywebview.api.xxx() 로 바인딩합니다.

    활성 옵셔널 플러그인 목록은 ENABLED_FEATURES 로 확인.
    """
    pass


# ── 하위 호환 alias ───────────────────────────────────────────────────────────
# v1.0.9 까지 HAS_CATALOG 를 사용한 외부 코드 (UI / 테스트) 를 위한 별칭.
# 새 코드는 'catalog' in ENABLED_FEATURES 형태를 사용 권장.
HAS_CATALOG = 'catalog' in ENABLED_FEATURES
