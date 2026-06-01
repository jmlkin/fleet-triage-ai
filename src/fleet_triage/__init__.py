"""Fleet Triage AI — a policy-driven endpoint fleet-health engine.

Three layers, strictly dependency-ordered:
  1. Core engine (this package, minus mcp_server/ai) — deterministic, no network, no key.
  2. MCP server (mcp_server.py)            — exposes the engine to a Claude client. No key.
  3. Optional BYOK AI (ai.py)              — Anthropic SDK, only if ANTHROPIC_API_KEY is set.

The core never imports `mcp` or `anthropic`; both higher layers consume `engine.analyze`.
"""

__version__ = "0.3.0"

from .engine import analyze  # noqa: E402,F401
