import unittest
import json
import tempfile
from pathlib import Path
from src.api.base import APIBase

class TestApiSessionMgmt(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.session_path = Path(self.test_dir.name) / "session.json"
        # Monkey patch the session path for the instance
        self.original_path = APIBase._SESSION_PATH
        APIBase._SESSION_PATH = self.session_path
        self.api = APIBase()

    def tearDown(self):
        APIBase._SESSION_PATH = self.original_path
        self.test_dir.cleanup()

    def test_save_and_get_session(self):
        state = {"active_id": "cid-1", "clusters": []}
        res = self.api.save_session(state)
        self.assertTrue(res["ok"])

        loaded = self.api.get_session()
        self.assertEqual(loaded, state)

    def test_get_nonexistent_session(self):
        loaded = self.api.get_session()
        self.assertIsNone(loaded)

    def test_clear_session(self):
        state = {"test": "data"}
        self.api.save_session(state)
        self.assertTrue(self.session_path.exists())

        res = self.api.clear_session()
        self.assertTrue(res["ok"])
        self.assertFalse(self.session_path.exists())

        loaded = self.api.get_session()
        self.assertIsNone(loaded)

    def test_save_blocked(self):
        self.api._disable_session_persistence()
        state = {"should": "not be saved"}
        res = self.api.save_session(state)
        self.assertTrue(res["ok"])
        self.assertTrue(res.get("skipped"))
        self.assertFalse(self.session_path.exists())

if __name__ == "__main__":
    unittest.main()
