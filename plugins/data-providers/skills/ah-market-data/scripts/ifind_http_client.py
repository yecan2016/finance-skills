from __future__ import annotations

import argparse
import json
import os
import socket
import ssl
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


DEFAULT_BASE_URL = "https://api-mcp.51ifind.com:8643/ds-mcp-servers"
SERVERS = {
    "stock": "hexin-ifind-ds-stock-mcp",
    "fund": "hexin-ifind-ds-fund-mcp",
    "edb": "hexin-ifind-ds-edb-mcp",
    "news": "hexin-ifind-ds-news-mcp",
}


class IFindAPIError(RuntimeError):
    """Raised when the iFinD HTTP API returns an unusable response."""


class IFindHTTPClient:
    """Small direct HTTP client for iFinD's JSON-RPC data endpoints.

    This bypasses agent-side MCP tool registration. The remote service still speaks
    MCP-over-HTTP JSON-RPC, so the client performs initialize -> tools/list|tools/call.
    """

    def __init__(
        self,
        token: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: int = 60,
        verify_tls: Optional[bool] = None,
        max_retries: Optional[int] = None,
        retry_base_delay: Optional[float] = None,
    ) -> None:
        self.token = token or load_auth_token()
        if not self.token:
            raise IFindAPIError(
                "Missing iFinD auth token. Set IFIND_AUTH_TOKEN or provide mcp_config.json."
            )

        self.base_url = (base_url or os.getenv("IFIND_BASE_URL") or DEFAULT_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.verify_tls = (
            _env_enabled("IFIND_VERIFY_TLS", default=False)
            if verify_tls is None
            else verify_tls
        )
        self.max_retries = max_retries or int(os.getenv("IFIND_MAX_RETRIES", "3"))
        self.retry_base_delay = retry_base_delay or float(os.getenv("IFIND_RETRY_BASE_DELAY", "0.8"))
        self._requests_session = _new_requests_session()
        self._session_ids: Dict[str, str] = {}
        self._request_ids: Dict[str, int] = {}

    def list_tools(self, server_type: str) -> Dict[str, Any]:
        self._ensure_initialized(server_type)
        return self._rpc(server_type, "tools/list", {})

    def call_tool(self, server_type: str, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        self._ensure_initialized(server_type)
        return self._rpc(
            server_type,
            "tools/call",
            {"name": tool_name, "arguments": arguments},
        )

    def _ensure_initialized(self, server_type: str) -> None:
        if server_type in self._session_ids:
            return

        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(server_type),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {},
                "clientInfo": {"name": "ifind-http-client", "version": "1.0.0"},
            },
        }
        _status, headers, data = self._post(server_type, payload, timeout=min(self.timeout, 30))
        session_id = headers.get("Mcp-Session-Id") or headers.get("mcp-session-id")
        if not session_id:
            raise IFindAPIError(f"initialize succeeded but no Mcp-Session-Id was returned: {data}")
        self._session_ids[server_type] = session_id

        notify = {"jsonrpc": "2.0", "method": "notifications/initialized"}
        self._post(server_type, notify, timeout=min(self.timeout, 10))

    def _rpc(self, server_type: str, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        payload = {
            "jsonrpc": "2.0",
            "id": self._next_id(server_type),
            "method": method,
            "params": params,
        }
        _status, _headers, data = self._post(server_type, payload)
        if isinstance(data, dict) and data.get("error"):
            raise IFindAPIError(json.dumps(data["error"], ensure_ascii=False))
        if not isinstance(data, dict):
            raise IFindAPIError(f"Expected JSON object response, got: {str(data)[:300]}")
        return data

    def _post(
        self, server_type: str, payload: Dict[str, Any], timeout: Optional[int] = None
    ) -> Tuple[int, Dict[str, str], Any]:
        if server_type not in SERVERS:
            raise IFindAPIError(f"Unknown server_type: {server_type}")

        effective_timeout = timeout or self.timeout
        last_error: Optional[BaseException] = None
        for attempt in range(1, max(self.max_retries, 1) + 1):
            try:
                if self._requests_session is not None:
                    return self._post_requests(server_type, payload, effective_timeout)
                return self._post_urllib(server_type, payload, effective_timeout)
            except BaseException as exc:
                last_error = exc
                if attempt >= max(self.max_retries, 1) or not is_retryable_error(exc):
                    if isinstance(exc, IFindAPIError):
                        raise
                    raise IFindAPIError(str(exc)) from exc
                time.sleep(self.retry_base_delay * (2 ** (attempt - 1)))

        raise IFindAPIError(str(last_error) if last_error else "iFinD request failed")

    def _post_requests(
        self, server_type: str, payload: Dict[str, Any], timeout: int
    ) -> Tuple[int, Dict[str, str], Any]:
        if self._requests_session is None:
            raise IFindAPIError("requests transport is not available")

        response = self._requests_session.post(
            f"{self.base_url}/{SERVERS[server_type]}",
            json=payload,
            headers=self._headers(server_type),
            verify=self.verify_tls,
            timeout=timeout,
        )
        text = response.text
        if response.status_code >= 400:
            raise IFindAPIError(f"HTTP {response.status_code}: {text[:500]}")
        return response.status_code, dict(response.headers.items()), _parse_json_or_text(text)

    def _post_urllib(
        self, server_type: str, payload: Dict[str, Any], timeout: int
    ) -> Tuple[int, Dict[str, str], Any]:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(
            f"{self.base_url}/{SERVERS[server_type]}",
            data=body,
            method="POST",
            headers=self._headers(server_type),
        )
        context = None if self.verify_tls else ssl._create_unverified_context()

        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout,
                context=context,
            ) as response:
                text = response.read().decode("utf-8", errors="replace")
                return response.status, dict(response.headers.items()), _parse_json_or_text(text)
        except urllib.error.HTTPError as exc:
            text = exc.read().decode("utf-8", errors="replace")
            raise IFindAPIError(f"HTTP {exc.code}: {text[:500]}") from exc
        except urllib.error.URLError as exc:
            raise IFindAPIError(str(exc.reason)) from exc

    def _headers(self, server_type: str) -> Dict[str, str]:
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": self.token,
        }
        session_id = self._session_ids.get(server_type)
        if session_id:
            headers["Mcp-Session-Id"] = session_id
        return headers

    def _next_id(self, server_type: str) -> int:
        self._request_ids[server_type] = self._request_ids.get(server_type, 0) + 1
        return self._request_ids[server_type]


def load_auth_token(config_path: Optional[str] = None) -> str:
    for env_name in ("IFIND_AUTH_TOKEN", "IFIND_API_TOKEN"):
        token = os.getenv(env_name)
        if token:
            return token.strip()

    for candidate in _config_candidates(config_path):
        if candidate.exists():
            data = json.loads(candidate.read_text(encoding="utf-8"))
            token = str(data.get("auth_token") or data.get("authorization") or "").strip()
            if token:
                return token
    return ""


def _config_candidates(config_path: Optional[str] = None) -> List[Path]:
    candidates: List[Path] = []

    # 1. Skill directory config (highest priority)
    script_dir = Path(__file__).resolve().parent
    candidates.append(script_dir / "mcp_config.json")

    # 2. Explicit config path
    explicit = config_path or os.getenv("IFIND_MCP_CONFIG_PATH")
    if explicit:
        candidates.append(Path(os.path.expanduser(os.path.expandvars(explicit))))

    # 3. Current working directory and parents
    cwd = Path.cwd()
    candidates.append(cwd / "mcp_config.json")
    candidates.extend(parent / "mcp_config.json" for parent in cwd.parents)

    # 4. Script directory parents (if different from cwd hierarchy)
    script_path = Path(__file__).resolve()
    candidates.extend(parent / "mcp_config.json" for parent in script_path.parents)

    unique: List[Path] = []
    seen = set()
    for candidate in candidates:
        key = str(candidate)
        if key not in seen:
            unique.append(candidate)
            seen.add(key)
    return unique


def _parse_json_or_text(text: str) -> Any:
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return text


def extract_text(payload: Dict[str, Any]) -> str:
    content = payload.get("result", {}).get("content", [])
    parts = []
    for item in content:
        if not isinstance(item, dict):
            continue
        text = item.get("text")
        if not text:
            continue
        parts.append(_unwrap_text_payload(str(text)))
    return "\n".join(part for part in parts if part).strip()


def _unwrap_text_payload(text: str) -> str:
    stripped = text.strip()
    if not stripped.startswith(("{", "[")):
        return stripped
    try:
        data = json.loads(stripped)
    except json.JSONDecodeError:
        return stripped
    if isinstance(data, dict):
        nested = data.get("data", {})
        if isinstance(nested, dict):
            for key in ("text", "answer", "data"):
                if nested.get(key):
                    return str(nested[key]).strip()
        if data.get("text"):
            return str(data["text"]).strip()
        if data.get("answer"):
            return str(data["answer"]).strip()
    return stripped


def _new_requests_session() -> Any:
    try:
        import requests
    except Exception:
        return None

    session = requests.Session()
    session.trust_env = False
    try:
        requests.packages.urllib3.disable_warnings()
    except Exception:
        pass
    return session


def is_retryable_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    if isinstance(exc, IFindAPIError) and any(marker in text for marker in ("http 400", "http 401", "http 403", "tool not allowed", "invalid arguments")):
        return False
    return any(
        marker in text
        for marker in (
            "eof occurred",
            "timed out",
            "timeout",
            "connection reset",
            "remote end closed",
            "temporarily unavailable",
            "ssl",
            "http 500",
            "http 502",
            "http 503",
            "http 504",
        )
    ) or isinstance(exc, (TimeoutError, socket.timeout, ssl.SSLError, urllib.error.URLError))


def build_tool_arguments(args: argparse.Namespace) -> Dict[str, Any]:
    shortcut_values = [
        getattr(args, "query", None),
        getattr(args, "arg", None),
        getattr(args, "size", None),
        getattr(args, "keyword", None),
        getattr(args, "time_start", None),
        getattr(args, "time_end", None),
        getattr(args, "time_scope", None),
        getattr(args, "sensitive", None),
        getattr(args, "industry_name", None),
    ]
    has_shortcuts = any(bool(value) for value in shortcut_values)
    if getattr(args, "arguments_json", None):
        if has_shortcuts:
            raise IFindAPIError("Use either --arguments-json or shortcut arguments, not both.")
        arguments = json.loads(args.arguments_json)
        if not isinstance(arguments, dict):
            raise IFindAPIError("--arguments-json must be a JSON object.")
        return arguments

    arguments: Dict[str, Any] = {}
    if getattr(args, "query", None):
        arguments["query"] = args.query

    for item in getattr(args, "arg", None) or []:
        key, value = _parse_arg_pair(item)
        arguments[key] = value

    for cli_name, arg_name in (
        ("time_start", "time_start"),
        ("time_end", "time_end"),
        ("size", "size"),
        ("keyword", "keyword"),
        ("time_scope", "time_scope"),
        ("sensitive", "sensitive"),
        ("industry_name", "industry_name"),
    ):
        value = getattr(args, cli_name, None)
        if value is not None:
            arguments[arg_name] = value

    if not arguments:
        raise IFindAPIError("Provide --query, --arguments-json, or shortcut arguments.")
    return arguments


def _parse_arg_pair(item: str) -> Tuple[str, Any]:
    if "=" not in item:
        raise IFindAPIError(f"--arg must use KEY=VALUE format: {item}")
    key, value = item.split("=", 1)
    key = key.strip()
    if not key:
        raise IFindAPIError(f"--arg key cannot be empty: {item}")
    return key, _coerce_cli_value(value)


def _coerce_cli_value(value: str) -> Any:
    stripped = value.strip()
    if stripped == "":
        return ""
    try:
        return json.loads(stripped)
    except json.JSONDecodeError:
        return stripped


def _env_enabled(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() not in {"0", "false", "no", "off"}


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Direct HTTP client for iFinD data tools.")
    parser.add_argument("--base-url", default=None, help="Override IFIND_BASE_URL.")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--max-retries", type=int, default=None)
    parser.add_argument("--text", action="store_true", help="Print extracted text content when present.")
    parser.add_argument(
        "--verify-tls",
        action="store_true",
        help="Verify TLS certificates. By default the client matches iFinD's sample bridge and skips verification.",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    list_parser = subparsers.add_parser("list", help="List tools for a server type.")
    list_parser.add_argument("server_type", choices=sorted(SERVERS))

    call_parser = subparsers.add_parser("call", help="Call a tool.")
    call_parser.add_argument("server_type", choices=sorted(SERVERS))
    call_parser.add_argument("tool_name")
    call_parser.add_argument("--query", help="Shortcut for arguments JSON: {\"query\": ...}.")
    call_parser.add_argument("--arguments-json", help="Full JSON object for tool arguments.")
    call_parser.add_argument("--arg", action="append", default=[], metavar="KEY=VALUE", help="Add one tool argument without writing JSON. May be repeated.")
    call_parser.add_argument("--time-start", dest="time_start", help="Shortcut for news/search time_start.")
    call_parser.add_argument("--time-end", dest="time_end", help="Shortcut for news/search time_end.")
    call_parser.add_argument("--size", type=int, help="Shortcut for news/search size.")
    call_parser.add_argument("--keyword", help="Shortcut for search_trending_news keyword.")
    call_parser.add_argument("--time-scope", dest="time_scope", help="Shortcut for search_trending_news time_scope.")
    call_parser.add_argument("--sensitive", help="Shortcut for search_trending_news sensitive.")
    call_parser.add_argument("--industry-name", dest="industry_name", help="Shortcut for search_trending_news industry_name.")

    return parser


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    client = IFindHTTPClient(
        base_url=args.base_url,
        timeout=args.timeout,
        verify_tls=True if args.verify_tls else None,
        max_retries=args.max_retries,
    )

    if args.command == "list":
        result = client.list_tools(args.server_type)
    else:
        arguments = build_tool_arguments(args)
        result = client.call_tool(args.server_type, args.tool_name, arguments)

    if args.text:
        text = extract_text(result)
        print(text if text else json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except IFindAPIError as exc:
        print(f"iFinD API error: {exc}", file=sys.stderr)
        raise SystemExit(1)
