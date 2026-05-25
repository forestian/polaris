"""catalog/dashboards/traces-app.json 생성.

폐쇄망 대응: grafana.com 의존 없이 자체 작성. Tempo 단독 대시보드.
패널 구성:
  - 트레이스 검색 (table, 최근 N건, traceQL)
  - 서비스 맵 (nodeGraph)
  - 서비스별 트레이스 (timeseries, traceQL metrics)
  - 평균 지연 / 에러율 / 트레이스 수 (stat)
"""
import json
from pathlib import Path

TEMPO = {"type": "tempo", "uid": "${datasource_tempo}"}


def panel_row(pid: int, y: int, title: str) -> dict:
    return {
        "collapsed": False,
        "gridPos": {"h": 1, "w": 24, "x": 0, "y": y},
        "id": pid,
        "title": title,
        "type": "row",
    }


def panel_stat(pid: int, x: int, y: int, w: int, h: int, title: str,
               query_type: str, query: str = '', unit: str = 'short',
               thresholds: list | None = None) -> dict:
    if thresholds is None:
        thresholds = [{"color": "blue", "value": None}]
    return {
        "datasource": TEMPO,
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
            "colorMode": "value",
            "graphMode": "area",
            "justifyMode": "center",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        "targets": [{
            "datasource": TEMPO,
            "queryType": query_type,
            "query": query,
            "refId": "A",
            "limit": 100,
            "tableType": "traces",
        }],
        "title": title,
        "type": "stat",
    }


def panel_traces_table(pid: int, x: int, y: int, w: int, h: int, title: str,
                       traceql: str, limit: int = 50) -> dict:
    return {
        "datasource": TEMPO,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": pid,
        "options": {
            "query": {"limit": limit, "queryType": "traceql", "tableType": "traces"},
        },
        "targets": [{
            "datasource": TEMPO,
            "queryType": "traceql",
            "query": traceql,
            "limit": limit,
            "refId": "A",
            "tableType": "traces",
        }],
        "title": title,
        "type": "traces",
    }


def panel_node_graph(pid: int, x: int, y: int, w: int, h: int, title: str) -> dict:
    return {
        "datasource": TEMPO,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": pid,
        "options": {},
        "targets": [{
            "datasource": TEMPO,
            "queryType": "serviceMap",
            "refId": "A",
        }],
        "title": title,
        "type": "nodeGraph",
    }


def panel_timeseries(pid: int, x: int, y: int, w: int, h: int, title: str,
                     query: str, query_type: str = 'traceqlMetrics',
                     unit: str = 'short') -> dict:
    return {
        "datasource": TEMPO,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "axisCenteredZero": False, "axisColorMode": "text",
                    "axisLabel": "", "axisPlacement": "auto",
                    "barAlignment": 0, "drawStyle": "line",
                    "fillOpacity": 30, "gradientMode": "none",
                    "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                    "lineInterpolation": "linear", "lineWidth": 1,
                    "pointSize": 5, "scaleDistribution": {"type": "linear"},
                    "showPoints": "never", "spanNulls": False,
                    "stacking": {"group": "A", "mode": "none"},
                    "thresholdsStyle": {"mode": "off"},
                },
                "mappings": [],
                "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
                "unit": unit,
            },
            "overrides": [],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": pid,
        "options": {
            "legend": {"calcs": ["mean", "max"], "displayMode": "table",
                       "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        "targets": [{
            "datasource": TEMPO,
            "queryType": query_type,
            "query": query,
            "refId": "A",
        }],
        "title": title,
        "type": "timeseries",
    }


def main():
    panels: list[dict] = []
    pid, y = 1, 0

    # ── 개요 ─────────────────────────────────────────────────
    panels.append(panel_row(pid, y, "트레이스 개요")); pid += 1; y += 1
    panels.append(panel_traces_table(
        pid, 0, y, 24, 4, "최근 트레이스 (최근 1시간)",
        '{}',
        limit=20,
    )); pid += 1
    y += 4

    # ── 서비스 맵 ────────────────────────────────────────────
    panels.append(panel_row(pid, y, "서비스 맵 (Service Graph)")); pid += 1; y += 1
    panels.append(panel_node_graph(
        pid, 0, y, 24, 12,
        "서비스 간 호출 관계 (자동 생성)",
    )); pid += 1
    y += 12

    # ── 트레이스 검색 ────────────────────────────────────────
    panels.append(panel_row(pid, y, "트레이스 검색")); pid += 1; y += 1
    panels.append(panel_traces_table(
        pid, 0, y, 24, 10,
        '느린 트레이스 (duration > 100ms)',
        '{ duration > 100ms }',
        limit=50,
    )); pid += 1
    y += 10

    panels.append(panel_traces_table(
        pid, 0, y, 24, 10,
        '에러 트레이스 (status = error)',
        '{ status = error }',
        limit=50,
    )); pid += 1
    y += 10

    # ── 트레이스 통계 (TraceQL Metrics — Tempo 2.5+) ────────
    panels.append(panel_row(pid, y, "트레이스 통계 (TraceQL Metrics)")); pid += 1; y += 1
    panels.append(panel_timeseries(
        pid, 0, y, 12, 8,
        "서비스별 트레이스 카운트 (분당)",
        '{} | rate() by (resource.service.name)',
        unit='cps',
    )); pid += 1

    panels.append(panel_timeseries(
        pid, 12, y, 12, 8,
        "서비스별 평균 지연 (p95)",
        '{} | quantile_over_time(duration, .95) by (resource.service.name)',
        unit='ms',
    )); pid += 1
    y += 8

    dashboard = {
        "annotations": {"list": [{
            "builtIn": 1,
            "datasource": {"type": "grafana", "uid": "-- Grafana --"},
            "enable": True, "hide": True,
            "iconColor": "rgba(0, 211, 255, 1)",
            "name": "Annotations & Alerts", "type": "dashboard",
        }]},
        "description": "Traces App — Tempo 기반 트레이스 탐색 (Polaris 내장, grafana.com 불필요)",
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": [],
        "refresh": "30s",
        "schemaVersion": 38,
        "tags": ["polaris", "tempo", "traces"],
        "time": {"from": "now-1h", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Traces App — Polaris 내장",
        "uid": "polaris-traces-v1",
        "version": 1,
        "templating": {"list": [{
            "current": {}, "hide": 0, "includeAll": False,
            "label": "Tempo", "name": "datasource_tempo",
            "options": [], "query": "tempo",
            "refresh": 1, "type": "datasource",
        }]},
        "panels": panels,
    }

    out = Path(__file__).resolve().parent.parent / 'catalog' / 'dashboards' / 'traces-app.json'
    out.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Written {out}')
    print(f'  panels: {len(panels)}')


if __name__ == '__main__':
    main()
