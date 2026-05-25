"""catalog/dashboards/node-exporter-full.json 생성.

폐쇄망 대응: grafana.com 의 gnetId 1860 (Node Exporter Full) 의존 없이 자체 작성.
패널 구성:
  - 노드 개요 (Uptime, CPU 코어, 메모리, 부트 시간)
  - CPU 모드별 사용률, 로드 평균
  - 메모리 (사용/사용가능/캐시/버퍼/Swap)
  - 디스크 I/O bytes·IOPS·지연, 파일시스템 사용률
  - 네트워크 RX/TX·에러/드롭
  - 시스템 (컨텍스트 스위치·인터럽트)
"""
import json
from pathlib import Path

PROM = {"type": "prometheus", "uid": "${datasource_prom}"}


def target(expr: str, legend: str = '', ref: str = 'A') -> dict:
    return {"datasource": PROM, "expr": expr, "legendFormat": legend, "refId": ref}


def panel_row(pid: int, y: int, title: str) -> dict:
    return {
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
        "id": pid,
        "title": title,
        "type": "row",
    }


def panel_stat(pid: int, x: int, y: int, w: int, h: int, title: str,
               expr: str, unit: str = 'short',
               thresholds: list | None = None,
               color_mode: str = 'value') -> dict:
    if thresholds is None:
        thresholds = [{"color": "blue", "value": None}]
    return {
        "datasource": PROM,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "thresholds"},
                "mappings": [],
                "thresholds": {"mode": "absolute", "steps": thresholds},
                "unit": unit,
            },
            "overrides": [],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": pid,
        "options": {
            "colorMode": color_mode,
            "graphMode": "none",
            "justifyMode": "center",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        "targets": [target(expr)],
        "title": title,
        "type": "stat",
    }


def panel_timeseries(pid: int, x: int, y: int, w: int, h: int, title: str,
                     targets: list[dict], unit: str = 'short',
                     stack: bool = False, fill: int = 10,
                     min_v: float | None = None,
                     max_v: float | None = None) -> dict:
    defaults = {
        "color": {"mode": "palette-classic"},
        "custom": {
            "axisCenteredZero": False,
            "axisColorMode": "text",
            "axisLabel": "",
            "axisPlacement": "auto",
            "barAlignment": 0,
            "drawStyle": "line",
            "fillOpacity": fill,
            "gradientMode": "none",
            "hideFrom": {"legend": False, "tooltip": False, "viz": False},
            "lineInterpolation": "smooth",
            "lineWidth": 1,
            "pointSize": 5,
            "scaleDistribution": {"type": "linear"},
            "showPoints": "never",
            "spanNulls": False,
            "stacking": {"group": "A", "mode": "normal" if stack else "none"},
            "thresholdsStyle": {"mode": "off"},
        },
        "mappings": [],
        "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
        "unit": unit,
    }
    if min_v is not None:
        defaults["min"] = min_v
    if max_v is not None:
        defaults["max"] = max_v
    return {
        "datasource": PROM,
        "fieldConfig": {"defaults": defaults, "overrides": []},
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": pid,
        "options": {
            "legend": {"calcs": ["mean", "max"], "displayMode": "table", "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        "targets": targets,
        "title": title,
        "type": "timeseries",
    }


def main():
    panels: list[dict] = []
    pid = 1
    y = 0

    # ── 노드 개요 ──────────────────────────────────────────────
    panels.append(panel_row(pid, y, "노드 개요")); pid += 1; y += 1
    panels.append(panel_stat(
        pid, 0, y, 4, 4, "Uptime",
        '(node_time_seconds{instance=~"$node"} - node_boot_time_seconds{instance=~"$node"})',
        unit='s', thresholds=[{"color": "blue", "value": None}],
    )); pid += 1
    panels.append(panel_stat(
        pid, 4, y, 4, 4, "CPU 코어 수",
        'count(count(node_cpu_seconds_total{instance=~"$node"}) by (cpu))',
        unit='short', thresholds=[{"color": "green", "value": None}],
    )); pid += 1
    panels.append(panel_stat(
        pid, 8, y, 4, 4, "총 메모리",
        'node_memory_MemTotal_bytes{instance=~"$node"}',
        unit='bytes', thresholds=[{"color": "blue", "value": None}],
    )); pid += 1
    panels.append(panel_stat(
        pid, 12, y, 4, 4, "메모리 사용률",
        '(1 - node_memory_MemAvailable_bytes{instance=~"$node"} / node_memory_MemTotal_bytes{instance=~"$node"}) * 100',
        unit='percent',
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 70},
            {"color": "red", "value": 90},
        ],
        color_mode='background',
    )); pid += 1
    panels.append(panel_stat(
        pid, 16, y, 4, 4, "루트 디스크 사용률",
        '(1 - node_filesystem_avail_bytes{instance=~"$node",mountpoint="/"} / node_filesystem_size_bytes{instance=~"$node",mountpoint="/"}) * 100',
        unit='percent',
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 70},
            {"color": "red", "value": 90},
        ],
        color_mode='background',
    )); pid += 1
    panels.append(panel_stat(
        pid, 20, y, 4, 4, "Load 1m",
        'node_load1{instance=~"$node"}',
        unit='short', thresholds=[{"color": "green", "value": None}],
    )); pid += 1
    y += 4

    # ── CPU ───────────────────────────────────────────────────
    panels.append(panel_row(pid, y, "CPU")); pid += 1; y += 1
    cpu_modes = ['user', 'system', 'iowait', 'idle', 'irq', 'softirq', 'steal', 'nice']
    panels.append(panel_timeseries(
        pid, 0, y, 12, 8, "CPU 사용률 (모드별)",
        [target(
            f'avg by (mode) (irate(node_cpu_seconds_total{{instance=~"$node",mode="{m}"}}[5m])) * 100',
            m, chr(ord('A') + i),
        ) for i, m in enumerate(cpu_modes)],
        unit='percent', stack=True, fill=50, min_v=0,
    )); pid += 1
    panels.append(panel_timeseries(
        pid, 12, y, 12, 8, "로드 평균",
        [target('node_load1{instance=~"$node"}', '1m', 'A'),
         target('node_load5{instance=~"$node"}', '5m', 'B'),
         target('node_load15{instance=~"$node"}', '15m', 'C')],
        unit='short', fill=10,
    )); pid += 1
    y += 8

    # ── 메모리 ────────────────────────────────────────────────
    panels.append(panel_row(pid, y, "메모리")); pid += 1; y += 1
    panels.append(panel_timeseries(
        pid, 0, y, 12, 8, "메모리 분포",
        [target('node_memory_MemTotal_bytes{instance=~"$node"} - node_memory_MemFree_bytes{instance=~"$node"} - node_memory_Buffers_bytes{instance=~"$node"} - node_memory_Cached_bytes{instance=~"$node"}', 'used', 'A'),
         target('node_memory_Buffers_bytes{instance=~"$node"}', 'buffers', 'B'),
         target('node_memory_Cached_bytes{instance=~"$node"}', 'cached', 'C'),
         target('node_memory_MemFree_bytes{instance=~"$node"}', 'free', 'D')],
        unit='bytes', stack=True, fill=50, min_v=0,
    )); pid += 1
    panels.append(panel_timeseries(
        pid, 12, y, 12, 8, "Swap 사용",
        [target('node_memory_SwapTotal_bytes{instance=~"$node"} - node_memory_SwapFree_bytes{instance=~"$node"}', 'used', 'A'),
         target('node_memory_SwapFree_bytes{instance=~"$node"}', 'free', 'B')],
        unit='bytes', stack=True, fill=50, min_v=0,
    )); pid += 1
    y += 8

    # ── 디스크 ────────────────────────────────────────────────
    panels.append(panel_row(pid, y, "디스크")); pid += 1; y += 1
    panels.append(panel_timeseries(
        pid, 0, y, 12, 8, "디스크 I/O (Bytes/sec)",
        [target('irate(node_disk_read_bytes_total{instance=~"$node"}[5m])',  'read {{device}}',  'A'),
         target('-irate(node_disk_written_bytes_total{instance=~"$node"}[5m])', 'write {{device}}', 'B')],
        unit='Bps', fill=10,
    )); pid += 1
    panels.append(panel_timeseries(
        pid, 12, y, 12, 8, "디스크 IOPS",
        [target('irate(node_disk_reads_completed_total{instance=~"$node"}[5m])',  'read {{device}}',  'A'),
         target('-irate(node_disk_writes_completed_total{instance=~"$node"}[5m])', 'write {{device}}', 'B')],
        unit='iops', fill=10,
    )); pid += 1
    panels.append(panel_timeseries(
        pid, 0, y + 8, 24, 8, "파일시스템 사용률 (마운트포인트별)",
        [target('(1 - node_filesystem_avail_bytes{instance=~"$node",fstype!~"tmpfs|fuse.lxcfs|nsfs|overlay|squashfs"} / node_filesystem_size_bytes{instance=~"$node",fstype!~"tmpfs|fuse.lxcfs|nsfs|overlay|squashfs"}) * 100',
                '{{mountpoint}}', 'A')],
        unit='percent', fill=10, min_v=0, max_v=100,
    )); pid += 1
    y += 16

    # ── 네트워크 ──────────────────────────────────────────────
    panels.append(panel_row(pid, y, "네트워크")); pid += 1; y += 1
    panels.append(panel_timeseries(
        pid, 0, y, 12, 8, "네트워크 트래픽",
        [target('irate(node_network_receive_bytes_total{instance=~"$node",device!~"lo|veth.*|docker.*|cali.*"}[5m]) * 8',
                'rx {{device}}', 'A'),
         target('-irate(node_network_transmit_bytes_total{instance=~"$node",device!~"lo|veth.*|docker.*|cali.*"}[5m]) * 8',
                'tx {{device}}', 'B')],
        unit='bps', fill=10,
    )); pid += 1
    panels.append(panel_timeseries(
        pid, 12, y, 12, 8, "네트워크 에러 + 드롭",
        [target('irate(node_network_receive_errs_total{instance=~"$node",device!~"lo|veth.*"}[5m])',
                'rx err {{device}}', 'A'),
         target('irate(node_network_transmit_errs_total{instance=~"$node",device!~"lo|veth.*"}[5m])',
                'tx err {{device}}', 'B'),
         target('irate(node_network_receive_drop_total{instance=~"$node",device!~"lo|veth.*"}[5m])',
                'rx drop {{device}}', 'C'),
         target('irate(node_network_transmit_drop_total{instance=~"$node",device!~"lo|veth.*"}[5m])',
                'tx drop {{device}}', 'D')],
        unit='pps', fill=10,
    )); pid += 1
    y += 8

    # ── 시스템 ────────────────────────────────────────────────
    panels.append(panel_row(pid, y, "시스템")); pid += 1; y += 1
    panels.append(panel_timeseries(
        pid, 0, y, 12, 8, "컨텍스트 스위치 / 초",
        [target('irate(node_context_switches_total{instance=~"$node"}[5m])', 'ctx switches', 'A')],
        unit='short', fill=10,
    )); pid += 1
    panels.append(panel_timeseries(
        pid, 12, y, 12, 8, "인터럽트 / 초",
        [target('irate(node_intr_total{instance=~"$node"}[5m])', 'intr', 'A')],
        unit='short', fill=10,
    )); pid += 1

    dashboard = {
        "annotations": {"list": [{
            "builtIn": 1,
            "datasource": {"type": "grafana", "uid": "-- Grafana --"},
            "enable": True, "hide": True,
            "iconColor": "rgba(0, 211, 255, 1)",
            "name": "Annotations & Alerts", "type": "dashboard",
        }]},
        "description": "Node Exporter Full — 노드 단위 시스템 메트릭 (Polaris 내장, grafana.com 불필요)",
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": [],
        "refresh": "30s",
        "schemaVersion": 38,
        "tags": ["polaris", "node-exporter", "kubernetes"],
        "time": {"from": "now-1h", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Node Exporter Full — Polaris 내장",
        "uid": "polaris-node-exporter-v1",
        "version": 1,
        "templating": {"list": [
            {
                "current": {}, "hide": 0, "includeAll": False,
                "label": "Prometheus", "name": "datasource_prom",
                "options": [], "query": "prometheus",
                "refresh": 1, "type": "datasource",
            },
            {
                "current": {"selected": False, "text": "All", "value": "$__all"},
                "datasource": {"type": "prometheus", "uid": "${datasource_prom}"},
                "definition": "label_values(node_uname_info,instance)",
                "hide": 0, "includeAll": True,
                "label": "노드", "multi": True, "name": "node",
                "options": [],
                "query": {"query": "label_values(node_uname_info,instance)",
                          "refId": "StandardVariableQuery"},
                "refresh": 2, "regex": "", "sort": 1, "type": "query",
            },
        ]},
        "panels": panels,
    }

    out = Path(__file__).resolve().parent.parent / 'catalog' / 'dashboards' / 'node-exporter-full.json'
    out.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Written {out}')
    print(f'  panels: {len(panels)}')


if __name__ == '__main__':
    main()
