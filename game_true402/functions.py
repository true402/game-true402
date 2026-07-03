"""true402 safety stalls as Virtuals Protocol GAME (G.A.M.E) custom Functions.

    from game_true402 import true402_functions
    action_space = true402_functions()   # reads PAYER_PRIVATE_KEY from the env

Each stall is a GAME `Function` whose `executable` pays the stall over x402 (USDC on Base) and
returns the standard `(FunctionResultStatus, message, info)` 3-tuple. The GAME planner passes each
declared `Argument` to the executable BY NAME, so the executables accept keyword args plus `**kwargs`
(the SDK injects extra keys). `token_report` is the primary pre-trade gate.
"""
from __future__ import annotations

import json
from typing import Callable, Optional

from game_sdk.game.custom_types import Argument, Function, FunctionResultStatus

from .x402 import PayOpts, pay_stall


def _summarize(data: object) -> str:
    """Best-effort human/agent-readable one-liner from a stall's JSON, without inventing fields."""
    if not isinstance(data, dict):
        return str(data)[:300]
    parts = []
    for key in ("verdict", "score", "risk", "riskLevel", "reputation", "recommendation"):
        if key in data and data[key] is not None:
            parts.append(f"{key}={data[key]}")
    return ", ".join(parts) if parts else json.dumps(data)[:300]


def _make_executable(path: str, input_key: str, opts_provider: Callable[[], PayOpts]):
    """Build a GAME executable that reads `input_key` from the passed-by-name args and pays the stall."""

    def executable(**kwargs):
        value = kwargs.get(input_key)
        if not value or not isinstance(value, str):
            return (
                FunctionResultStatus.FAILED,
                f"missing required '{input_key}' (a 0x Base address)",
                {},
            )
        try:
            data = pay_stall(path, {input_key: value}, opts_provider())
        except Exception as exc:  # noqa: BLE001 — surface any failure to the planner
            return (
                FunctionResultStatus.FAILED,
                f"{path} check for {value} failed: {exc}",
                {},
            )
        info = data if isinstance(data, dict) else {"result": data}
        return (
            FunctionResultStatus.DONE,
            f"{path} → {_summarize(data)}",
            info,
        )

    return executable


def token_report_function(opts_provider: Callable[[], PayOpts]) -> Function:
    """PRIMARY pre-trade gate — composite avoid/caution/ok verdict for a Base ERC-20."""
    return Function(
        fn_name="check_token_report",
        fn_description=(
            "Pre-trade rug/honeypot gate for a Base ERC-20 token. Runs a real on-chain buy/sell "
            "honeypot simulation (proves sellability, not just a static scan) plus liquidity, "
            "ownership/mint and recent rug activity, and returns a composite avoid/caution/ok "
            "verdict. Call this BEFORE buying any token. Pays ~$0.01 USDC on Base over x402."
        ),
        args=[
            Argument(
                name="token",
                type="string",
                description="The Base ERC-20 token contract address to vet (0x…).",
            ),
        ],
        executable=_make_executable("/v1/base/token-report", "token", opts_provider),
    )


def token_safety_function(opts_provider: Callable[[], PayOpts]) -> Function:
    """Structural safety score 0-100 + flags (lighter than token_report)."""
    return Function(
        fn_name="check_token_safety",
        fn_description=(
            "Structural safety score (0–100) and flags for a Base ERC-20 token: honeypot simulation, "
            "liquidity, mint/ownership/blacklist. Lighter than check_token_report. "
            "Pays ~$0.005 USDC on Base over x402."
        ),
        args=[
            Argument(
                name="token",
                type="string",
                description="The Base ERC-20 token contract address to score (0x…).",
            ),
        ],
        executable=_make_executable("/v1/token-safety", "token", opts_provider),
    )


def address_safety_function(opts_provider: Callable[[], PayOpts]) -> Function:
    """Screen any Base address before send / approve / call."""
    return Function(
        fn_name="check_address_safety",
        fn_description=(
            "Screen any Base address before you send to, approve, or call it: EOA-vs-contract, "
            "ETH+USDC balance, activity, ownership and upgradeable-proxy (EIP-1967) detection. "
            "Pays ~$0.005 USDC on Base over x402."
        ),
        args=[
            Argument(
                name="address",
                type="string",
                description="Any Base address to screen (0x…) — an EOA or a contract.",
            ),
        ],
        executable=_make_executable("/v1/base/address-safety", "address", opts_provider),
    )


def deployer_check_function(opts_provider: Callable[[], PayOpts]) -> Function:
    """Deployer wallet reputation — catches serial ruggers a structural scan can't see."""
    return Function(
        fn_name="check_deployer",
        fn_description=(
            "Deployer reputation for a Base token: resolves who created it and that wallet's track "
            "record (age, contracts shipped, fresh-throwaway flag) to catch serial ruggers a "
            "structural check can't see. Pays ~$0.008 USDC on Base over x402."
        ),
        args=[
            Argument(
                name="token",
                type="string",
                description="The Base ERC-20 token contract address whose deployer to check (0x…).",
            ),
        ],
        executable=_make_executable("/v1/base/deployer-check", "token", opts_provider),
    )


def true402_functions(opts: Optional[PayOpts] = None) -> list[Function]:
    """The four true402 safety Functions, ready to drop into a GAME Worker `action_space`.

    Pass a `PayOpts`, or leave `None` to read PAYER_PRIVATE_KEY / TRUE402_BASE_URL / BASE_RPC_URL from
    the environment. The safety stalls have a free daily trial, so the functions return real results
    even with no wallet configured — until the trial is exhausted, then they require payment.
    `check_token_report` is the primary pre-trade gate.
    """
    resolved = opts or PayOpts.from_env()

    def opts_provider() -> PayOpts:
        return resolved

    return [
        token_report_function(opts_provider),
        token_safety_function(opts_provider),
        address_safety_function(opts_provider),
        deployer_check_function(opts_provider),
    ]
