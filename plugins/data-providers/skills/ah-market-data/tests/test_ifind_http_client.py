import argparse
import json
import ssl
import sys
import unittest
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parents[1] / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))

import ifind_http_client as client  # noqa: E402


class TestIFindHTTPClient(unittest.TestCase):
    def test_build_tool_arguments_combines_query_shorthands_and_arg_pairs(self):
        args = argparse.Namespace(
            arguments_json=None,
            query="贵州茅台 2026年第一季度报告",
            arg=["time_start=2026-04-01", "time_end=2026-04-26"],
            size=5,
            keyword=None,
            time_scope=None,
            sensitive=None,
            industry_name=None,
        )

        self.assertEqual(
            client.build_tool_arguments(args),
            {
                "query": "贵州茅台 2026年第一季度报告",
                "time_start": "2026-04-01",
                "time_end": "2026-04-26",
                "size": 5,
            },
        )

    def test_build_tool_arguments_json_rejects_mixed_shortcuts(self):
        args = argparse.Namespace(
            arguments_json='{"query":"贵州茅台"}',
            query="贵州茅台",
            arg=[],
            size=None,
            keyword=None,
            time_scope=None,
            sensitive=None,
            industry_name=None,
        )

        with self.assertRaises(client.IFindAPIError):
            client.build_tool_arguments(args)

    def test_ssl_eof_is_retryable(self):
        exc = ssl.SSLError("EOF occurred in violation of protocol (_ssl.c:997)")

        self.assertTrue(client.is_retryable_error(exc))

    def test_requests_session_ignores_environment_proxy(self):
        session = client._new_requests_session()
        if session is None:
            self.skipTest("requests is not installed")

        self.assertFalse(session.trust_env)

    def test_extract_text_unwraps_ifind_data_answer(self):
        payload = {
            "result": {
                "content": [
                    {
                        "text": json.dumps(
                            {"code": 1, "data": {"answer": "|证券代码|证券简称|"}},
                            ensure_ascii=False,
                        )
                    }
                ]
            }
        }

        self.assertEqual(client.extract_text(payload), "|证券代码|证券简称|")


if __name__ == "__main__":
    unittest.main()
