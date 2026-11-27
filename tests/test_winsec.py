"""winsec (파일/폴더 권한 하드닝) 테스트 — v1.2.3.

코어 모듈이므로 variant 빌드에서도 유지된다. Windows 에서는 실제로 icacls 가
광범위 그룹(Everyone)을 제거하는지까지 검증한다.
"""
import sys
import shutil
import tempfile
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src import winsec

IS_WIN = sys.platform == 'win32'


class WinsecBasics(unittest.TestCase):
    """플랫폼 무관 — 어떤 경우에도 예외를 던지지 않아야 한다(best-effort)."""

    def test_current_user_nonempty(self):
        self.assertTrue(winsec._current_user())

    def test_chmod_owner_only_no_raise(self):
        d = Path(tempfile.mkdtemp(prefix='polaris-winsec-'))
        try:
            f = d / 'x.txt'
            f.write_text('secret', encoding='utf-8')
            winsec.chmod_owner_only(f)               # 파일
            winsec.chmod_owner_only(d, is_dir=True)  # 폴더
            winsec.chmod_owner_only(d / 'nonexistent')  # 없는 경로도 무탈
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_harden_dir_no_raise_and_marker(self):
        d = Path(tempfile.mkdtemp(prefix='polaris-winsec-'))
        try:
            (d / 'vault.json').write_text('{}', encoding='utf-8')
            winsec.harden_dir(d)        # 예외 없어야 함
            winsec.harden_dir(d)        # 재호출(idempotent) 도 무탈
            if IS_WIN:
                self.assertTrue((d / winsec._HARDEN_MARKER).exists(),
                                '하드닝 표식이 생성되어야 함')
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_harden_file_no_raise(self):
        d = Path(tempfile.mkdtemp(prefix='polaris-winsec-'))
        try:
            f = d / 'servers.json'
            f.write_text('[]', encoding='utf-8')
            winsec.harden_file(f)
            winsec.harden_file(d / 'nope.json')   # 없는 파일도 무탈
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_harden_dir_nonexistent_no_raise(self):
        winsec.harden_dir(Path(tempfile.gettempdir()) / 'polaris-does-not-exist-xyz')


@unittest.skipUnless(IS_WIN, 'Windows ACL 효과 검증')
class WinsecAclEffect(unittest.TestCase):
    """Windows: harden_dir 가 실제로 Everyone 같은 광범위 그룹을 제거하는지."""

    def _icacls(self, *args):
        return subprocess.run(['icacls', *args], capture_output=True, text=True,
                              creationflags=winsec._NO_WINDOW)

    def test_removes_broad_group(self):
        d = Path(tempfile.mkdtemp(prefix='polaris-winsec-acl-'))
        try:
            # 사전조건: Everyone(S-1-1-0) 에 명시적 접근 부여
            r = self._icacls(str(d), '/grant', '*S-1-1-0:(OI)(CI)F')
            if r.returncode != 0:
                self.skipTest('icacls 사용 불가 환경')
            before = self._icacls(str(d)).stdout
            self.assertIn('Everyone', before, '사전조건: Everyone 이 있어야 함')

            winsec.harden_dir(d)   # 하드닝 → Everyone 제거 기대

            after = self._icacls(str(d)).stdout
            self.assertNotIn('Everyone', after,
                             'harden_dir 후 Everyone 접근이 제거되어야 함')
        finally:
            shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    unittest.main()
