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

VERSION = '1.0.10-e2'   # build.py 정규식 호환 — 무료 빌드 (카탈로그 plugin 제외)

# ── 하위 호환 re-export (테스트 + 외부 스크립트가 polaris.X 로 접근 가능) ────
from src.tools import (
    _NO_WINDOW, _KUBECTL_LOCAL, _HELM_LOCAL,
    _probe, _find_kubectl, _find_helm, _find_k9s,
    _find_windows_terminal, _find_wt_settings, _inject_wt_polaris_scheme,
    _WT_SCHEME_NAME, _WT_POLARIS_SCHEME,
    _build_k9s_launch_command, _build_pod_shell_command,
    _run_kubectl, _parse_kubectl_command, _extract_host_port,
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
    _RFC1123_DNS_LABEL, _RFC1123_DNS_SUBDOMAIN,
    _LOG_SOURCE_ALIASES, _WORKLOAD_LOG_TYPES,
    _PORT_FORWARD_KIND_ALIASES, _RESOURCE_EVENT_KIND_MAP,
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
from src.api import PolarisAPI, ENABLED_FEATURES, HAS_CATALOG

# ── 옵셔널 plugin 의 helper / state re-export (있을 때만) ─────────────────────
# variant 빌드에서 plugin 이 빠지면 try/except 가 조용히 건너뜀.
# 새 plugin 추가 시 여기에 한 블록 더 추가하면 됨.
if 'catalog' in ENABLED_FEATURES:
    try:
        from src.catalog import (
            _get_catalog_dir, _catalog_load_json, _catalog_fill_placeholders,
            _catalog_helm_chart_args,
            _build_grafana_k8s_manifests, _apply_grafana_k8s_manifests,
        )
        from src.api.catalog import _catalog_install_jobs, _stack_install_jobs
    except ImportError:
        pass
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


def main():
    """진입점. src.runtime.main 에 VERSION 과 PolarisAPI 를 주입해 실행."""
    _runtime_main(VERSION, PolarisAPI)


if __name__ == '__main__':
    main()
