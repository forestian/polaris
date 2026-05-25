"""Polaris 런타임 — 트레이 / 단일 인스턴스 / 생명주기 / main 진입점.

이 모듈은 PyWebView 창 + 시스템 트레이 + 단일 인스턴스 시그널 서버를 통합합니다.
polaris.py 는 이 모듈의 main() 을 호출하는 얇은 진입점으로만 동작합니다.
"""
import os
import sys
import json
import queue
import socket
import threading
from datetime import datetime
from pathlib import Path

_LIFECYCLE_OPEN = 'open'
_LIFECYCLE_QUIT = 'quit'
_INSTANCE_HOST = '127.0.0.1'
_INSTANCE_PORT = 43711
_INSTANCE_SIGNAL = b'NIMBUS_POLARIS_OPEN_V1\n'
_INSTANCE_ACK = b'OK\n'

# ─────────────────────────────────────────────────────────────────────────────
# 진입점
# ─────────────────────────────────────────────────────────────────────────────

def _make_tray_image():
    """트레이 아이콘 이미지 (PIL Image).

    POLARIS 8각 별 — 미리 생성된 polaris-tray.png 를 로드 (scripts/gen_polaris_icon.py).
    PyInstaller 번들 / 개발 환경 모두 지원: _MEIPASS 우선 → 소스 디렉터리 폴백.
    파일 못 찾으면 인디고 배경 + 골드 별 단순 폴리곤으로 즉석 생성.
    """
    from PIL import Image, ImageDraw

    # 1) 번들된 PNG 우선
    candidates = []
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        candidates.append(Path(meipass) / 'packaging' / 'icons' / 'polaris-tray.png')
    candidates.append(Path(__file__).resolve().parent.parent / 'packaging' / 'icons' / 'polaris-tray.png')
    for p in candidates:
        try:
            if p.is_file():
                return Image.open(p).convert('RGBA')
        except Exception:
            continue

    # 2) 폴백 — 즉석 polaris 별 (배경 + 8각 별)
    img = Image.new('RGBA', (64, 64), (0, 0, 0, 0))
    d   = ImageDraw.Draw(img)
    d.rounded_rectangle((4, 4, 60, 60), radius=14, fill='#131734')
    s = 64 / 40.0
    def _pts(c): return [(x * s, y * s) for x, y in c]
    d.polygon(_pts([(20,3),(23,17),(37,20),(23,23),(20,37),(17,23),(3,20),(17,17)]), fill='#a87830')
    d.polygon(_pts([(20,6),(22.4,17.6),(34,20),(22.4,22.4),(20,34),(17.6,22.4),(6,20),(17.6,17.6)]), fill='#f3c969')
    d.polygon(_pts([(20,10),(21.4,18.6),(30,20),(21.4,21.4),(20,30),(18.6,21.4),(10,20),(18.6,18.6)]), fill='#fff5d6')
    return img


def _app_log_event(message):
    try:
        log_dir = Path.home() / '.polaris' / 'logs'
        log_dir.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        with (log_dir / 'app.log').open('a', encoding='utf-8') as f:
            f.write(f'[{stamp}] {message}\n')
    except Exception:
        pass


def _queue_lifecycle_action(action_queue, action):
    try:
        action_queue.put_nowait(action)
        _app_log_event(f'lifecycle queued: {action}')
        return True
    except Exception as e:
        _app_log_event(f'lifecycle queue failed: {action}: {e}')
        return False


def _prepare_full_shutdown(api):
    try:
        api._disable_session_persistence()
    except AttributeError:
        pass
    except Exception as e:
        _app_log_event(f'session persistence block failed: {e}')
    try:
        api.clear_session()
        _app_log_event('saved session cleared for full shutdown')
    except Exception as e:
        _app_log_event(f'session cleanup failed: {e}')
    try:
        api._disconnect_all_clusters()
    except Exception as e:
        _app_log_event(f'disconnect on full shutdown failed: {e}')


def _perform_full_quit(api, window, tray_state):
    tray_state['force_quit'] = True
    _prepare_full_shutdown(api)
    try:
        window.destroy()
    except Exception as e:
        _app_log_event(f'window destroy failed: {e}')


def _handle_window_closing(api, window, tray_state):
    if tray_state.get('force_quit'):
        _app_log_event('window closing: force quit')
        return True

    try:
        behavior = api._load_settings_raw().get('closeBehavior', 'tray')
    except Exception:
        behavior = 'tray'

    if behavior == 'exit':
        _app_log_event('window closing: exit')
        _prepare_full_shutdown(api)
        return True

    _app_log_event('window closing: hide to tray')
    try:
        window.hide()
    except Exception as e:
        _app_log_event(f'window hide failed: {e}')
    return False


def _notify_existing_instance(timeout=0.35):
    try:
        with socket.create_connection((_INSTANCE_HOST, _INSTANCE_PORT), timeout=timeout) as s:
            s.settimeout(timeout)
            s.sendall(_INSTANCE_SIGNAL)
            acknowledged = s.recv(16) == _INSTANCE_ACK
        if acknowledged:
            _app_log_event('existing instance notified')
        return acknowledged
    except OSError:
        return False


def _start_instance_signal_server(action_queue, stop_event):
    ready = threading.Event()
    state = {'error': None}

    def _run():
        server = None
        try:
            server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server.bind((_INSTANCE_HOST, _INSTANCE_PORT))
            server.listen(4)
            server.settimeout(0.25)
            ready.set()
            _app_log_event(f'instance signal server listening: {_INSTANCE_PORT}')

            while not stop_event.is_set():
                try:
                    conn, _addr = server.accept()
                except socket.timeout:
                    continue
                except OSError:
                    break
                with conn:
                    try:
                        data = conn.recv(128)
                    except OSError:
                        data = b''
                    if data.strip() == _INSTANCE_SIGNAL.strip():
                        _queue_lifecycle_action(action_queue, _LIFECYCLE_OPEN)
                        try:
                            conn.sendall(_INSTANCE_ACK)
                        except OSError:
                            pass
        except OSError as e:
            state['error'] = e
            ready.set()
            _app_log_event(f'instance signal server failed: {e}')
        finally:
            if server is not None:
                try:
                    server.close()
                except Exception:
                    pass
            _app_log_event('instance signal server stopped')

    thread = threading.Thread(target=_run, daemon=True, name='PolarisInstanceSignal')
    thread.start()
    ready.wait(0.5)
    return None if state['error'] else thread


def _run_lifecycle_loop(action_queue, stop_event, handlers):
    while not stop_event.is_set():
        try:
            action = action_queue.get(timeout=0.2)
        except queue.Empty:
            continue
        handler = handlers.get(action)
        if not handler:
            _app_log_event(f'unknown lifecycle action: {action}')
            continue
        try:
            _app_log_event(f'lifecycle handling: {action}')
            handler()
        except Exception as e:
            _app_log_event(f'lifecycle handler failed: {action}: {e}')


def main(version: str, api_cls):
    """PyWebView 메인 진입점.

    version: 'X.Y.Z' 형식의 버전 문자열 (창 타이틀, 트레이 툴팁에 사용)
    api_cls: PolarisAPI 클래스 (또는 호환 API 클래스)
    """
    try:
        import webview
    except ImportError:
        print('[ERROR] pywebview가 설치되지 않았습니다.')
        print('  pip install pywebview 를 실행하세요.')
        sys.exit(1)

    # React 빌드 dist 경로
    dist = Path(__file__).resolve().parent.parent / 'ui' / 'dist' / 'index.html'
    if not dist.exists():
        print(f'[ERROR] UI 빌드 파일이 없습니다: {dist}')
        print('  ui/ 폴더에서 npm install && npm run build 를 먼저 실행하세요.')
        sys.exit(1)

    action_queue = queue.Queue()
    lifecycle_stop = threading.Event()
    if _notify_existing_instance():
        return
    _start_instance_signal_server(action_queue, lifecycle_stop)

    api = api_cls()

    window = webview.create_window(
        title=f'Polaris v{version}',
        url=dist.as_uri(),
        js_api=api,
        width=1400,
        height=900,
        min_size=(960, 640),
        resizable=True,
        frameless=False,
        easy_drag=False,
    )
    api._window = window

    # ── 트레이 통합 (v3.7.11) ────────────────────────────────────────────
    # X 버튼 = 설정에 따라 트레이 hide 또는 완전 종료
    # 트레이 메뉴: "열기" (default = 더블클릭), "종료"
    tray_state = {'icon': None, 'force_quit': False}

    def _on_tray_open(icon=None, item=None):
        """트레이 → 윈도우 표시 요청."""
        _queue_lifecycle_action(action_queue, _LIFECYCLE_OPEN)

    def _on_tray_quit(icon=None, item=None):
        """트레이 → 완전 종료 요청."""
        _queue_lifecycle_action(action_queue, _LIFECYCLE_QUIT)

    def _handle_lifecycle_open():
        try:
            window.show()
        except Exception as e:
            _app_log_event(f'window show failed: {e}')
        try:
            window.restore()
        except Exception:
            pass

    def _handle_lifecycle_quit():
        _perform_full_quit(api, window, tray_state)

    def _on_window_closing():
        """X 버튼 / Alt+F4 가로채기.
        설정 closeBehavior가 'tray'면 hide, 'exit'이면 종료 진행.
        """
        return _handle_window_closing(api, window, tray_state)

    # 이벤트 핸들러 등록 (일부는 환경에 따라 없을 수 있어 보호)
    try:
        window.events.closing += _on_window_closing
    except Exception:
        pass

    # 트레이 아이콘 별도 스레드 시작
    def _start_tray():
        try:
            import pystray
            menu = pystray.Menu(
                pystray.MenuItem('열기', _on_tray_open, default=True),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem('종료', _on_tray_quit),
            )
            icon = pystray.Icon(
                'polaris',
                _make_tray_image(),
                f'Polaris v{version}',
                menu,
            )
            tray_state['icon'] = icon
            icon.run()   # 블로킹 — 스레드 안에서
        except Exception as e:
            # 트레이 실패해도 앱 자체는 계속 실행되어야 함
            print(f'[WARN] 트레이 시작 실패: {e}')

    tray_thread = threading.Thread(target=_start_tray, daemon=True)
    tray_thread.start()

    lifecycle_handlers = {
        _LIFECYCLE_OPEN: _handle_lifecycle_open,
        _LIFECYCLE_QUIT: _handle_lifecycle_quit,
    }

    # ── pywebview 메인 루프 ─────────────────────────────────────────────
    try:
        webview.start(
            _run_lifecycle_loop,
            args=(action_queue, lifecycle_stop, lifecycle_handlers),
            debug='--debug' in sys.argv,
        )
    finally:
        lifecycle_stop.set()
        # 메인 루프 종료 후 트레이도 정리
        try:
            if tray_state['icon']:
                tray_state['icon'].stop()
        except Exception:
            pass


