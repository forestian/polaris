#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Polaris — Kubernetes 클러스터 관리 도구 (진입점).

모든 도메인 로직은 src/ 패키지로 분리되어 있습니다.
이 파일은 단순 진입점 + 하위 호환 re-export 만 담당합니다.

코어 모듈:
  - src.tools     : 외부 CLI 탐색 + subprocess
  - src.k8s       : K8sManager + k8s 도메인 헬퍼
  - src.reports   : DOCX/TXT/HTML 보고서 생성
  - src.topology  : 토폴로지 그래프 헬퍼
  - src._state    : 코어 백그라운드 작업 dict
  - src.api       : PolarisAPI mixin 합성 (옵셔널 plugin 자동 발견)
  - src.runtime   : 트레이 / 단일 인스턴스 / 생명주기 / main

옵셔널 plugin:
  - src.api 의 코어가 아닌 다른 *.py 파일은 자동으로 plugin 으로 등록.
  - 활성 plugin 목록은 src.api.ENABLED_FEATURES 로 확인 가능.
  - variant 빌드에서 plugin 을 제거하려면 해당 *.py + 부속 데이터/UI 만 삭제하면 됨.
"""
import sys
import socket   # 테스트가 polaris.socket.create_connection 을 monkey-patch 함 — 호환용
from pathlib import Path

# 개발 환경 / frozen 모드 양쪽에서 src/ 패키지 import 보장
ROOT = Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

VERSION = '1.5.74-f1'   # 무료판 — 같은 번호 정식판(v1.5.74) 코드에서 무료 범위만 남긴 첫 빌드

# ── 하위 호환 re-export (테스트 + 외부 스크립트가 polaris.X 로 접근 가능) ────
from src.tools import (
    _NO_WINDOW, _KUBECTL_LOCAL, _HELM_LOCAL,
    _probe, _find_kubectl, _find_helm, _find_k9s,
    _find_windows_terminal, _find_wt_settings, _inject_wt_polaris_scheme,
    _WT_SCHEME_NAME, _WT_POLARIS_SCHEME,
    _build_k9s_launch_command, _build_pod_shell_command,
    _run_kubectl, _strip_versioner_noise, _parse_kubectl_command, _extract_host_port,
    _kubectl_subcommand_index, _is_kubectl_streaming_args,
)
from src.k8s import (
    HAS_K8S, K8sManager,
    _age, _parse_cpu, _parse_mem, _pct,
    _build_node_metrics, _apply_node_metric,
    _diagnose_connect_error,
    _is_secret_kind, _redact_secret_yaml, _redact_secret_describe,
    _build_pod_exec_args, _normalize_log_source_type, _build_pod_log_args,
    _is_ingress_controller_pod,
    _normalize_port_forward_kind, _coerce_port, _build_port_forward_spec,
    _clean_argo_sources, _argo_sources_from_spec, _argo_primary_source,
    _build_argocd_spec, _build_argocd_sync_operation,
    _resource_event_field_selector,
    _normalize_kubectl_kind, _build_scale_args, _build_rollout_restart_args,
    _build_rollout_undo_args, _images_from_cr_data,
    _RFC1123_DNS_LABEL, _RFC1123_DNS_SUBDOMAIN,
    _LOG_SOURCE_ALIASES, _WORKLOAD_LOG_TYPES,
    _PORT_FORWARD_KIND_ALIASES, _RESOURCE_EVENT_KIND_MAP,
    _KUBECTL_KIND_ALIASES, _SCALABLE_KINDS, _RESTARTABLE_KINDS,
    _DESCRIBE_SENSITIVE,
)
if HAS_K8S:
    from kubernetes import client as k8s, config as k8s_cfg

from src.reports import (
    _report_required_dataset_keys, _report_finding,
    _report_build_priority_summary,
    _report_collect, _report_evaluate,
    _llm_ask, _set_cell_bg,
    _report_write_docx, _report_write_txt,
    _esc, _table, _build_report_html,
)
from src.topology import (
    _topo_vol_refs, _topo_env_refs, _topo_sel_match,
    _topo_pod_workload_owner, _topo_cronjob_node,
    _topo_job_status, _topo_job_workload_node,
)
from src._state import (
    _report_jobs, _log_jobs, _port_forward_jobs,
)
from src.api import PolarisAPI, ENABLED_FEATURES, OPTIONAL_PLUGIN_ERRORS

from src.runtime import (
    _LIFECYCLE_OPEN, _LIFECYCLE_QUIT,
    _INSTANCE_HOST, _INSTANCE_PORT, _INSTANCE_SIGNAL, _INSTANCE_ACK,
    _make_tray_image, _app_log_event,
    _queue_lifecycle_action, _prepare_full_shutdown,
    _perform_full_quit, _handle_window_closing,
    _notify_existing_instance, _start_instance_signal_server,
    _run_lifecycle_loop,
    main as _runtime_main,
)


def _selfcheck() -> int:
    """GUI 없이 빌드 무결성 점검 (frozen EXE 에서도 동작).

    사용:  polaris.exe --selfcheck
    출력:  버전 / frozen 여부 / 활성 옵셔널 plugin / 핵심 API 메서드 노출 여부.

    옵셔널 plugin 자동 발견이 frozen 빌드에서 깨지는 회귀(v1.0.10)를
    GUI 실행 없이 즉시 검증하기 위한 진단 플래그.
    """
    import json
    # MCP(stdio) 서버 가용성 — frozen 빌드에서 mcp SDK 가 번들되지 않으면 --mcp 가
    # 조용히 죽는다(v1.2.114 plugin 누락과 같은 부류). GUI/클라이언트 없이 즉시 확인.
    mcp_ready, mcp_error = False, None
    try:
        import mcp.server            # noqa: F401
        import mcp.server.stdio      # noqa: F401
        import mcp.types             # noqa: F401
        import anyio                 # noqa: F401
        from src.mcp_server import _tool_defs
        mcp_ready = len(_tool_defs()) > 0
    except Exception as e:
        mcp_error = f'{type(e).__name__}: {e}'

    # Windows Hello 잠금 해제(v1.2.167) — 번들 누락은 GUI 를 열어 잠금화면까지
    # 가야 드러난다. 여기서 임포트 + 실제 조회까지 해 본다.
    #
    # 조회를 넣는 이유: 이 기능은 **PowerShell 을 띄워** WinRT 를 부르는데, 이 코드베이스
    # 에서 PowerShell 호출은 이것이 처음이다 — frozen EXE 에서 되는지 확인할 다른 길이
    # 없다. state 값은 PC 마다 다르지만(Available / NotConfiguredForUser / ...) 그대로
    # 보고한다: "Hello 버튼이 안 보인다" 는 문의를 이 한 줄로 판별할 수 있다.
    # kubernetes 라이브러리(v1.3.73) — 이제 처음 쓸 때 이름으로 불러온다(importlib). 빌드가
    # 그 이름을 못 따라가 빠뜨리면 클러스터를 처음 열 때에야 드러나므로 여기서 실제로 불러 본다.
    k8s_lib, k8s_error = False, None
    try:
        from src.k8s import preload_k8s, k8s as _k8s_mod
        k8s_lib = bool(preload_k8s()) and callable(getattr(_k8s_mod, 'CoreV1Api', None))
    except Exception as e:
        k8s_error = f'{type(e).__name__}: {e}'

    hello_ready, hello_error, hello_state = False, None, None
    try:
        from src import hello as _hello
        hello_ready = callable(_hello.verify) and callable(_hello.availability)
        st = _hello.availability(timeout=6.0)   # 점검이 오래 매달리지 않게 짧게
        hello_state = st.get('state')
        hello_error = st.get('error')
    except Exception as e:
        hello_error = f'{type(e).__name__}: {e}'

    # LGPL 라이브러리(v1.4.19) — 실행 파일 밖의 일반 .py 에서 불러와야 사용자가 바꿔 끼울 수 있다.
    # 파일에서 불러왔는지(__file__ 이 실제 .py) 확인한다 — PYZ 안이면 frozen 에서 파일이 없다.
    import os as _os
    lgpl_libs = {}
    for _name in ('pystray',):
        try:
            _mod = __import__(_name)
            _f = getattr(_mod, '__file__', '') or ''
            lgpl_libs[_name] = bool(_f.endswith('.py') and _os.path.isfile(_f))
        except Exception as e:
            lgpl_libs[_name] = f'{type(e).__name__}: {e}'

    report = {
        'version':          VERSION,
        'lgpl_libs':        lgpl_libs,
        'frozen':           bool(getattr(sys, 'frozen', False)),
        'enabled_features': list(ENABLED_FEATURES),
        'mcp': {'available': mcp_ready, 'error': mcp_error},
        'hello': {'module': hello_ready, 'state': hello_state, 'error': hello_error},
        'k8s_lib': {'loaded': k8s_lib, 'error': k8s_error},
        'api_methods': {
            name: hasattr(PolarisAPI, name)
            for name in (
                'get_status', 'get_dashboard',
                'vault_status',
                'vault_unlock_hello', 'hello_status',
            )
        },
        'optional_plugin_errors': OPTIONAL_PLUGIN_ERRORS,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


def main():
    """진입점. src.runtime.main 에 VERSION 과 PolarisAPI 를 주입해 실행."""
    if '--selfcheck' in sys.argv:
        sys.exit(_selfcheck())
    if '--mcp' in sys.argv:
        # GUI 없이 MCP(stdio) 서버로 실행 — AI 가 크리덴셜 없이 Polaris 로 K8s 조회.
        from src.mcp_server import run as _mcp_run
        sys.exit(_mcp_run())
    _runtime_main(VERSION, PolarisAPI)


if __name__ == '__main__':
    main()
