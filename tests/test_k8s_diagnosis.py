import unittest
import ssl
from src.k8s import _diagnose_connect_error

class TestK8sDiagnosis(unittest.TestCase):
    def test_file_not_found(self):
        err = FileNotFoundError()
        msg = _diagnose_connect_error(err, "/path/to/kubeconfig")
        self.assertIn("파일을 찾을 수 없습니다", msg)
        self.assertIn("/path/to/kubeconfig", msg)

    def test_timeout_error(self):
        err = TimeoutError("Connection timed out")
        msg = _diagnose_connect_error(err, "path")
        self.assertIn("연결 시간 초과", msg)

    def test_ssl_error(self):
        err = ssl.SSLError("certificate verify failed")
        msg = _diagnose_connect_error(err, "path")
        self.assertIn("TLS/SSL 인증서 오류", msg)

    def test_connection_refused(self):
        err = Exception("Connection refused")
        msg = _diagnose_connect_error(err, "path")
        self.assertIn("접근할 수 없습니다", msg)

    def test_generic_error(self):
        err = Exception("Some weird error")
        msg = _diagnose_connect_error(err, "path")
        self.assertIn("연결 실패: Some weird error", msg)

if __name__ == "__main__":
    unittest.main()
