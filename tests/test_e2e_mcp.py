"""
E2E test for the deployed Lovable Bridge MCP Server.

Tests the full pipeline against the live Databricks App:
  health → MCP connect → initialize → list tools
  → lovable_import → lovable_convert → lovable_deploy → lovable_status

Usage:
  # Default: uses the pre-configured app URL and a sample GitHub project
  python tests/test_e2e_mcp.py

  # With custom GitHub URL (e.g. Trainline Travel Hub):
  GITHUB_URL=https://github.com/your-org/your-repo python tests/test_e2e_mcp.py

  # With custom app URL:
  APP_URL=https://your-app.databricksapps.com GITHUB_URL=... python tests/test_e2e_mcp.py
"""

import asyncio
import json
import os
import subprocess
import sys
import time
from typing import Any

import httpx

# ── Config ──────────────────────────────────────────────────────────────────
APP_URL = os.getenv(
    "APP_URL",
    "https://lovable-bridge-mcp-dev-7474655448180618.aws.databricksapps.com",
)
GITHUB_URL = os.getenv(
    "GITHUB_URL",
    # ZIP URL avoids git credential issues in headless containers.
    # Replace with the Trainline Travel Hub ZIP, or any Lovable-exported project.
    "https://github.com/supabase/realtime/archive/refs/heads/main.zip",
)
DATABRICKS_HOST = "https://fevm-ismailmakhlouf-demo-ws.cloud.databricks.com"

# ── Helpers ─────────────────────────────────────────────────────────────────
_failures: list[str] = []


def check(condition: bool, label: str) -> None:
    status = "  ✓" if condition else "  ✗"
    print(f"{status} {label}")
    if not condition:
        _failures.append(label)
        raise AssertionError(f"FAILED: {label}")


def get_auth_token() -> str:
    result = subprocess.run(
        ["databricks", "auth", "token", "--host", DATABRICKS_HOST],
        capture_output=True, text=True, timeout=15,
    )
    if result.returncode != 0:
        raise RuntimeError(f"databricks auth token failed: {result.stderr.strip()}")
    return json.loads(result.stdout)["access_token"]


# ── Phase 1: Health ──────────────────────────────────────────────────────────
async def test_health(token: str) -> None:
    print("\n[Phase 1] Health check")
    async with httpx.AsyncClient(follow_redirects=False, timeout=15) as client:
        resp = await client.get(
            f"{APP_URL}/health",
            headers={"Authorization": f"Bearer {token}"},
        )
    check(resp.status_code == 200, f"HTTP 200 (got {resp.status_code})")
    data = resp.json()
    check(data.get("status") == "healthy", f"status == healthy (got {data.get('status')})")
    db_ok = data.get("databricks_connected", False)
    print(f"  databricks_connected: {db_ok}")


# ── Phase 2: MCP session ─────────────────────────────────────────────────────
async def run_mcp_session(token: str, github_url: str) -> dict[str, Any]:
    """
    Open an MCP SSE session, run the full tool chain, return results dict.

    MCP SSE protocol:
      1. GET /mcp/sse  → SSE stream; server sends  event: endpoint / data: /mcp/messages/?session_id=xxx
      2. POST to messages URL with JSON-RPC 2.0 requests
      3. Responses arrive as  event: message / data: {...}  on the SSE stream
    """
    results: dict[str, Any] = {}
    responses: dict[int, Any] = {}
    messages_url: str | None = None
    endpoint_ready = asyncio.Event()
    msg_id = 0

    auth_headers = {"Authorization": f"Bearer {token}"}

    # ── SSE reader (background task) ─────────────────────────────────────────
    sse_client = httpx.AsyncClient(follow_redirects=False, timeout=300)

    async def sse_reader() -> None:
        nonlocal messages_url
        async with sse_client.stream(
            "GET", f"{APP_URL}/mcp/sse",
            headers={**auth_headers, "Accept": "text/event-stream"},
        ) as resp:
            check(resp.status_code == 200, f"SSE connect 200 (got {resp.status_code})")
            print("  ✓ SSE stream opened")
            current_event: str | None = None
            async for line in resp.aiter_lines():
                if line.startswith("event:"):
                    current_event = line.split(":", 1)[1].strip()
                elif line.startswith("data:"):
                    payload = line[5:].strip()
                    if current_event == "endpoint":
                        path = payload
                        messages_url = (
                            f"{APP_URL}{path}" if path.startswith("/") else path
                        )
                        print(f"  ✓ Messages endpoint: {path}")
                        endpoint_ready.set()
                    elif current_event == "message":
                        try:
                            msg = json.loads(payload)
                            if "id" in msg:
                                responses[msg["id"]] = msg
                        except json.JSONDecodeError:
                            pass
                    current_event = None  # reset after data

    sse_task = asyncio.create_task(sse_reader())

    try:
        # Wait for endpoint URL from server
        await asyncio.wait_for(endpoint_ready.wait(), timeout=20)
        assert messages_url is not None

        post_headers = {**auth_headers, "Content-Type": "application/json"}

        async def rpc(method: str, params: dict) -> dict:
            """Send JSON-RPC request; wait for response via SSE."""
            nonlocal msg_id
            msg_id += 1
            mid = msg_id
            body = {"jsonrpc": "2.0", "id": mid, "method": method, "params": params}
            async with httpx.AsyncClient(follow_redirects=False, timeout=60) as c:
                r = await c.post(messages_url, json=body, headers=post_headers)
            check(
                r.status_code in (200, 202, 204),
                f"POST {method} accepted (got {r.status_code})",
            )
            deadline = time.time() + 60
            while time.time() < deadline:
                if mid in responses:
                    return responses.pop(mid)
                await asyncio.sleep(0.1)
            raise TimeoutError(f"No SSE response for {method} id={mid} after 60s")

        async def notify(method: str, params: dict | None = None) -> None:
            """Send JSON-RPC notification (no id, no response expected)."""
            body: dict[str, Any] = {"jsonrpc": "2.0", "method": method}
            if params:
                body["params"] = params
            async with httpx.AsyncClient(follow_redirects=False, timeout=15) as c:
                await c.post(messages_url, json=body, headers=post_headers)

        # ── initialize ───────────────────────────────────────────────────────
        print("\n[Phase 2] MCP handshake")
        print("  → initialize")
        init = await rpc("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "lovable-bridge-e2e", "version": "1.0"},
        })
        check("result" in init, "initialize → result present")
        server_info = init["result"].get("serverInfo", {})
        print(f"  ✓ Server: {server_info.get('name')} v{server_info.get('version')}")
        results["server_info"] = server_info

        await notify("notifications/initialized")

        # ── tools/list ───────────────────────────────────────────────────────
        print("  → tools/list")
        tl = await rpc("tools/list", {})
        check("result" in tl, "tools/list → result present")
        tool_names = {t["name"] for t in tl["result"].get("tools", [])}
        expected = {"lovable_import", "lovable_convert", "lovable_deploy", "lovable_status"}
        check(expected.issubset(tool_names), f"all 4 tools listed (got {sorted(tool_names)})")
        results["tools"] = sorted(tool_names)

        # ── tool call helper ─────────────────────────────────────────────────
        async def call_tool(name: str, arguments: dict) -> Any:
            resp = await rpc("tools/call", {"name": name, "arguments": arguments})
            check("result" in resp, f"{name} → result present (error: {resp.get('error')})")
            content = resp["result"].get("content", [])
            check(len(content) > 0, f"{name} → content non-empty")
            data = json.loads(content[0]["text"])
            check("error" not in data, f"{name} no error (got: {data.get('error')})")
            return data

        # ── lovable_import ───────────────────────────────────────────────────
        print(f"\n[Phase 3] lovable_import  url={github_url}")
        import_data = await call_tool("lovable_import", {"url": github_url})
        project_id = import_data.get("project_id", "")
        check(bool(project_id), f"project_id returned: {project_id!r}")
        analysis = import_data.get("analysis", {})
        print(f"  project_id:  {project_id}")
        print(f"  components:  {analysis.get('components', 0)}")
        print(f"  tables:      {analysis.get('database_tables', 0)}")
        print(f"  endpoints:   {analysis.get('api_endpoints', 0)}")
        results["import"] = import_data

        # ── lovable_convert ──────────────────────────────────────────────────
        print(f"\n[Phase 4] lovable_convert  project_id={project_id}")
        convert_data = await call_tool("lovable_convert", {
            "project_id": project_id,
            "catalog": "main",
            "schema": "lovable_e2e",
        })
        files_total = convert_data.get("generated_files", {}).get("total", 0)
        check(files_total > 0, f"files generated: {files_total}")
        print(f"  files generated: {files_total}")
        print(f"  catalog/schema:  {convert_data.get('catalog')}.{convert_data.get('schema')}")
        results["convert"] = convert_data

        # ── lovable_deploy ───────────────────────────────────────────────────
        print(f"\n[Phase 5] lovable_deploy  project_id={project_id}")
        deploy_data = await call_tool("lovable_deploy", {
            "project_id": project_id,
            "app_name": "lovable-e2e-test",
            "target": "dev",
        })
        deployment_id = deploy_data.get("deployment_id", "")
        check(bool(deployment_id), f"deployment_id returned: {deployment_id!r}")
        app_url = deploy_data.get("app_url", "")
        print(f"  deployment_id: {deployment_id}")
        print(f"  app_url:       {app_url}")
        results["deploy"] = deploy_data

        # ── lovable_status ───────────────────────────────────────────────────
        print(f"\n[Phase 6] lovable_status  deployment_id={deployment_id}")
        status_data = await call_tool("lovable_status", {"deployment_id": deployment_id})
        print(f"  status:  {status_data.get('status')}")
        print(f"  app_url: {status_data.get('app_url')}")
        results["status"] = status_data

    finally:
        sse_task.cancel()
        try:
            await sse_task
        except (asyncio.CancelledError, Exception):
            pass
        await sse_client.aclose()

    return results


# ── Main ─────────────────────────────────────────────────────────────────────
async def main() -> int:
    print("=" * 65)
    print("  Lovable Bridge MCP Server — End-to-End Test")
    print(f"  App:    {APP_URL}")
    print(f"  Source: {GITHUB_URL}")
    print("=" * 65)

    try:
        print("\n[Auth] Getting Databricks token…")
        token = get_auth_token()
        print("  ✓ Token obtained")

        await test_health(token)
        results = await run_mcp_session(token, GITHUB_URL)

        print("\n" + "=" * 65)
        print("  E2E PASSED")
        if results.get("deploy", {}).get("app_url"):
            print(f"  Deployed app URL: {results['deploy']['app_url']}")
        print("=" * 65)
        return 0

    except (AssertionError, TimeoutError) as e:
        print(f"\n  FAILED: {e}")
    except Exception as e:
        import traceback
        print(f"\n  ERROR: {e}")
        traceback.print_exc()

    print("\n" + "=" * 65)
    print(f"  E2E FAILED  ({len(_failures)} assertion(s) failed)")
    for f in _failures:
        print(f"    ✗ {f}")
    print("=" * 65)
    return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
