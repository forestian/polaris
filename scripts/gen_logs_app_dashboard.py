"""catalog/dashboards/logs-app.json 생성.

폐쇄망 대응: grafana.com 의 Logs App / Loki 대시보드 의존 없이 자체 작성.
패널 구성:
  - 개요: 총 로그/ERROR/WARN/소스 (1h 합계)
  - 수집량: 네임스페이스/컨테이너별 로그 트래픽
  - 분포: 레벨 분포 파이 차트, top 10 시끄러운 파드
  - 탐색: 실시간 로그 스트림 (네임스페이스/파드/검색어 필터)
"""
import json
from pathlib import Path

LOKI = {"type": "loki", "uid": "${datasource_loki}"}


def t(expr: str, legend: str = '', ref: str = 'A',
      query_type: str = 'range') -> dict:
    """Loki target. query_type='range' for timeseries, 'instant' for stat."""
    return {
        "datasource": LOKI,
        "editorMode": "code",
        "expr": expr,
        "legendFormat": legend,
        "queryType": query_type,
        "refId": ref,
    }


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
               color_mode: str = 'value',
               graph_mode: str = 'none') -> dict:
    if thresholds is None:
        thresholds = [{"color": "blue", "value": None}]
    return {
        "datasource": LOKI,
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
            "graphMode": graph_mode,
            "justifyMode": "center",
            "orientation": "auto",
            "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
            "textMode": "auto",
        },
        "targets": [t(expr, '', 'A', 'instant')],
        "title": title,
        "type": "stat",
    }


def panel_timeseries(pid: int, x: int, y: int, w: int, h: int, title: str,
                     targets: list[dict], unit: str = 'logs',
                     stack: bool = False, fill: int = 50) -> dict:
    return {
        "datasource": LOKI,
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {
                    "axisCenteredZero": False,
                    "axisColorMode": "text",
                    "axisLabel": "", "axisPlacement": "auto",
                    "barAlignment": 0,
                    "drawStyle": "bars",
                    "fillOpacity": fill,
                    "gradientMode": "none",
                    "hideFrom": {"legend": False, "tooltip": False, "viz": False},
                    "lineInterpolation": "linear",
                    "lineWidth": 1, "pointSize": 5,
                    "scaleDistribution": {"type": "linear"},
                    "showPoints": "never",
                    "spanNulls": False,
                    "stacking": {"group": "A", "mode": "normal" if stack else "none"},
                    "thresholdsStyle": {"mode": "off"},
                },
                "mappings": [],
                "thresholds": {"mode": "absolute", "steps": [{"color": "green", "value": None}]},
                "unit": unit,
                "min": 0,
            },
            "overrides": [],
        },
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": pid,
        "options": {
            "legend": {"calcs": ["sum"], "displayMode": "table", "placement": "bottom", "showLegend": True},
            "tooltip": {"mode": "multi", "sort": "desc"},
        },
        "targets": targets,
        "title": title,
        "type": "timeseries",
    }


def panel_logs(pid: int, x: int, y: int, w: int, h: int, title: str,
               expr: str) -> dict:
    return {
        "datasource": LOKI,
        "gridPos": {"h": h, "w": w, "x": x, "y": y},
        "id": pid,
        "options": {
            "dedupStrategy": "none",
            "enableLogDetails": True,
            "prettifyLogMessage": False,
            "showCommonLabels": False,
            "showLabels": False,
            "showTime": True,
            "sortOrder": "Descending",
            "wrapLogMessage": True,
        },
        "targets": [t(expr, '', 'A', 'range')],
        "title": title,
        "type": "logs",
    }


def main():
    panels: list[dict] = []
    pid = 1
    y = 0

    # ── 개요 ─────────────────────────────────────────────────
    panels.append(panel_row(pid, y, "개요 (최근 1시간)")); pid += 1; y += 1
    panels.append(panel_stat(
        pid, 0, y, 6, 4, "총 로그 행",
        'sum(count_over_time({namespace=~"$namespace"} [1h]))',
        thresholds=[{"color": "blue", "value": None}],
    )); pid += 1
    panels.append(panel_stat(
        pid, 6, y, 6, 4, "에러 로그",
        'sum(count_over_time({namespace=~"$namespace"} |~ "(?i)(error|fatal|panic|exception)" [1h]))',
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 10},
            {"color": "red", "value": 100},
        ],
        color_mode='background',
    )); pid += 1
    panels.append(panel_stat(
        pid, 12, y, 6, 4, "경고 로그",
        'sum(count_over_time({namespace=~"$namespace"} |~ "(?i)(warn|warning)" [1h]))',
        thresholds=[
            {"color": "green", "value": None},
            {"color": "yellow", "value": 50},
        ],
    )); pid += 1
    panels.append(panel_stat(
        pid, 18, y, 6, 4, "활성 소스 (pod 수)",
        'count(count by (pod) (count_over_time({namespace=~"$namespace"} [1h])))',
        thresholds=[{"color": "blue", "value": None}],
    )); pid += 1
    y += 4

    # ── 수집량 ────────────────────────────────────────────────
    panels.append(panel_row(pid, y, "수집량 추이")); pid += 1; y += 1
    panels.append(panel_timeseries(
        pid, 0, y, 24, 8, "네임스페이스별 로그 수집 (분당)",
        [t('sum by (namespace) (count_over_time({namespace=~"$namespace"} [1m]))',
           '{{namespace}}', 'A')],
        unit='logs', stack=True, fill=70,
    )); pid += 1
    y += 8

    panels.append(panel_timeseries(
        pid, 0, y, 12, 8, "ERROR / WARN 추이 (분당)",
        [t('sum(count_over_time({namespace=~"$namespace"} |~ "(?i)(error|fatal|panic|exception)" [1m]))',
           'error', 'A'),
         t('sum(count_over_time({namespace=~"$namespace"} |~ "(?i)(warn|warning)" [1m]))',
           'warn', 'B')],
        unit='logs', stack=False, fill=50,
    )); pid += 1

    panels.append(panel_timeseries(
        pid, 12, y, 12, 8, "Top 10 시끄러운 파드",
        [t('topk(10, sum by (pod) (count_over_time({namespace=~"$namespace"} [$__range])))',
           '{{pod}}', 'A', 'instant')],
        unit='logs', stack=False, fill=40,
    )); pid += 1
    y += 8

    # ── 컨테이너별 통계 ───────────────────────────────────────
    panels.append(panel_row(pid, y, "컨테이너 / 파드 통계")); pid += 1; y += 1
    panels.append(panel_timeseries(
        pid, 0, y, 24, 8, "컨테이너별 로그 수집 (분당)",
        [t('sum by (container) (count_over_time({namespace=~"$namespace",container!=""} [1m]))',
           '{{container}}', 'A')],
        unit='logs', stack=True, fill=70,
    )); pid += 1
    y += 8

    # ── 실시간 로그 ───────────────────────────────────────────
    panels.append(panel_row(pid, y, "실시간 로그 스트림")); pid += 1; y += 1
    panels.append(panel_logs(
        pid, 0, y, 24, 16,
        "실시간 로그 (네임스페이스/검색어 필터 적용)",
        '{namespace=~"$namespace"} |~ "$search"',
    )); pid += 1
    y += 16

    dashboard = {
        "annotations": {"list": [{
            "builtIn": 1,
            "datasource": {"type": "grafana", "uid": "-- Grafana --"},
            "enable": True, "hide": True,
            "iconColor": "rgba(0, 211, 255, 1)",
            "name": "Annotations & Alerts", "type": "dashboard",
        }]},
        "description": "Logs App — Loki 기반 로그 탐색 (Polaris 내장, grafana.com 불필요)",
        "editable": True,
        "fiscalYearStartMonth": 0,
        "graphTooltip": 1,
        "id": None,
        "links": [],
        "refresh": "30s",
        "schemaVersion": 38,
        "tags": ["polaris", "loki", "logs"],
        "time": {"from": "now-1h", "to": "now"},
        "timepicker": {},
        "timezone": "browser",
        "title": "Logs App — Polaris 내장",
        "uid": "polaris-logs-v1",
        "version": 1,
        "templating": {"list": [
            {
                "current": {}, "hide": 0, "includeAll": False,
                "label": "Loki", "name": "datasource_loki",
                "options": [], "query": "loki",
                "refresh": 1, "type": "datasource",
            },
            {
                "current": {"selected": False, "text": ".+", "value": ".+"},
                "datasource": LOKI,
                "definition": "",
                "hide": 0, "includeAll": False,
                "label": "네임스페이스 (정규식)",
                "multi": False, "name": "namespace",
                "options": [{"selected": True, "text": ".+", "value": ".+"}],
                "query": ".+",
                "refresh": 0, "regex": "", "skipUrlSync": False,
                "type": "textbox",
            },
            {
                "current": {"selected": False, "text": "", "value": ""},
                "hide": 0, "includeAll": False,
                "label": "검색어 (정규식, 비우면 전체)",
                "multi": False, "name": "search",
                "options": [{"selected": True, "text": "", "value": ""}],
                "query": "",
                "refresh": 0, "regex": "", "skipUrlSync": False,
                "type": "textbox",
            },
        ]},
        "panels": panels,
    }

    out = Path(__file__).resolve().parent.parent / 'catalog' / 'dashboards' / 'logs-app.json'
    out.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False), encoding='utf-8')
    print(f'Written {out}')
    print(f'  panels: {len(panels)}')


if __name__ == '__main__':
    main()
