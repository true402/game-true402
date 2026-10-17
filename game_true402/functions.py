"""true402 stalls — on-chain safety and SEO/search data — as Virtuals Protocol GAME (G.A.M.E)
custom Functions.

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


def _optional_int(kwargs: dict, key: str) -> Optional[int]:
    """Best-effort int cast for an optional keyword arg the GAME planner passed as a string."""
    val = kwargs.get(key)
    if val is None or (isinstance(val, str) and not val.strip()):
        return None
    try:
        return int(val)
    except (TypeError, ValueError):
        return None


def _optional_str(kwargs: dict, key: str) -> Optional[str]:
    val = kwargs.get(key)
    return val if isinstance(val, str) and val else None


def _make_executable(path: str, input_key: str, opts_provider: Callable[[], PayOpts], hint: str = "a 0x Base address"):
    """Build a GAME executable that reads `input_key` from the passed-by-name args and pays the stall."""

    def executable(**kwargs):
        value = kwargs.get(input_key)
        if not value or not isinstance(value, str):
            return (
                FunctionResultStatus.FAILED,
                f"missing required '{input_key}' ({hint})",
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


def _make_preflight_executable(opts_provider: Callable[[], PayOpts]):
    """Preflight takes a whole UNSIGNED transaction, not a single address, so it needs its own
    executable. No private key and no signature are ever sent — see the function description."""

    def executable(**kwargs):
        sender = kwargs.get("from") or kwargs.get("from_address")
        to = kwargs.get("to")
        if not isinstance(sender, str) or not isinstance(to, str) or not sender or not to:
            return (FunctionResultStatus.FAILED, "missing required 'from' and 'to' (0x Base addresses)", {})
        body = {"from": sender, "to": to}
        for key in ("data", "value"):
            val = kwargs.get(key)
            if isinstance(val, str) and val:
                body[key] = val
        try:
            data = pay_stall("/v1/base/tx-preflight", body, opts_provider())
        except Exception as exc:  # noqa: BLE001 — surface any failure to the planner
            return (FunctionResultStatus.FAILED, f"tx-preflight failed: {exc}", {})
        info = data if isinstance(data, dict) else {"result": data}
        return (FunctionResultStatus.DONE, f"/v1/base/tx-preflight → {_summarize(data)}", info)

    return executable


def _make_keyword_volume_executable(opts_provider: Callable[[], PayOpts]):
    """Keyword volume takes a LIST of keywords in one call, not a single string — its own executable."""

    def executable(**kwargs):
        raw = kwargs.get("keywords")
        if not isinstance(raw, str) or not raw.strip():
            return (
                FunctionResultStatus.FAILED,
                "missing required 'keywords' (comma-separated, up to 200 — batch them, one call covers all)",
                {},
            )
        keywords = [k.strip() for k in raw.split(",") if k.strip()]
        if not keywords:
            return (FunctionResultStatus.FAILED, "'keywords' contained no usable terms", {})
        body: dict = {"keywords": keywords}
        location = _optional_int(kwargs, "location")
        if location is not None:
            body["location"] = location
        language = _optional_str(kwargs, "language")
        if language is not None:
            body["language"] = language
        try:
            data = pay_stall("/v1/keyword-volume", body, opts_provider())
        except Exception as exc:  # noqa: BLE001 — surface any failure to the planner
            return (
                FunctionResultStatus.FAILED,
                f"/v1/keyword-volume for {len(keywords)} keyword(s) failed: {exc}",
                {},
            )
        info = data if isinstance(data, dict) else {"result": data}
        return (FunctionResultStatus.DONE, f"/v1/keyword-volume → {_summarize(data)}", info)

    return executable


def _make_ranked_keywords_executable(opts_provider: Callable[[], PayOpts]):
    def executable(**kwargs):
        target = kwargs.get("target")
        if not isinstance(target, str) or not target:
            return (FunctionResultStatus.FAILED, "missing required 'target' (a domain)", {})
        body: dict = {"target": target}
        limit = _optional_int(kwargs, "limit")
        if limit is not None:
            body["limit"] = limit
        location = _optional_int(kwargs, "location")
        if location is not None:
            body["location"] = location
        language = _optional_str(kwargs, "language")
        if language is not None:
            body["language"] = language
        try:
            data = pay_stall("/v1/ranked-keywords", body, opts_provider())
        except Exception as exc:  # noqa: BLE001 — surface any failure to the planner
            return (FunctionResultStatus.FAILED, f"/v1/ranked-keywords for {target} failed: {exc}", {})
        info = data if isinstance(data, dict) else {"result": data}
        return (FunctionResultStatus.DONE, f"/v1/ranked-keywords → {_summarize(data)}", info)

    return executable


def _make_keyword_ideas_executable(opts_provider: Callable[[], PayOpts]):
    def executable(**kwargs):
        seed = kwargs.get("seed")
        if not isinstance(seed, str) or not seed:
            return (FunctionResultStatus.FAILED, "missing required 'seed' (a keyword or phrase)", {})
        body: dict = {"seed": seed}
        limit = _optional_int(kwargs, "limit")
        if limit is not None:
            body["limit"] = limit
        location = _optional_int(kwargs, "location")
        if location is not None:
            body["location"] = location
        language = _optional_str(kwargs, "language")
        if language is not None:
            body["language"] = language
        try:
            data = pay_stall("/v1/keyword-ideas", body, opts_provider())
        except Exception as exc:  # noqa: BLE001 — surface any failure to the planner
            return (FunctionResultStatus.FAILED, f"/v1/keyword-ideas for '{seed}' failed: {exc}", {})
        info = data if isinstance(data, dict) else {"result": data}
        return (FunctionResultStatus.DONE, f"/v1/keyword-ideas → {_summarize(data)}", info)

    return executable


def liquidity_history_function(opts_provider: Callable[[], PayOpts]) -> Function:
    """Observed liquidity history — the past, which a live simulation cannot re-derive."""
    return Function(
        fn_name="check_liquidity_history",
        fn_description=(
            "What has ALREADY happened to a Base token's liquidity, from true402's own DEX archive: "
            "every removal event with the amount, block and transaction hash, plus the other tokens "
            "drained in the SAME transaction (one actor, several pools). A live honeypot simulation "
            "cannot see this — a pool drained last month simulates fine today if it was re-seeded. "
            "The answer states the block range the index covers, so 'none observed' is not a claim "
            "of safety. Pays ~$0.005 USDC on Base over x402."
        ),
        args=[
            Argument(
                name="token",
                type="string",
                description="The Base ERC-20 token contract address to look up (0x…).",
            ),
        ],
        executable=_make_executable("/v1/base/liquidity-history", "token", opts_provider),
    )


def tx_preflight_function(opts_provider: Callable[[], PayOpts]) -> Function:
    """The last check before signing. Takes no key and no signature by design."""
    return Function(
        fn_name="preflight_transaction",
        fn_description=(
            "Check a Base transaction BEFORE signing it. Send the UNSIGNED transaction and get three "
            "lenses: a simulation against current state (does it revert?), the decoded intent (is this "
            "an unlimited approval that outlives the trade?), and the counterparty's liquidity-removal "
            "history. Takes NO private key and NO signature, so it cannot broadcast or front-run the "
            "transaction it inspects. Never returns 'safe' — a clean result means these checks found "
            "nothing, and every response states its limits. Call this LAST, immediately before signing. "
            "Pays ~$0.008 USDC on Base over x402."
        ),
        args=[
            Argument(name="from", type="string", description="Sender address (0x…). Asserted, never proven."),
            Argument(name="to", type="string", description="Destination contract or address (0x…)."),
            Argument(name="data", type="string", description="Calldata hex (0x…). Omit for a plain native transfer."),
            Argument(name="value", type="string", description="Native value in wei, decimal string. Default 0."),
        ],
        executable=_make_preflight_executable(opts_provider),
    )


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


def backlinks_function(opts_provider: Callable[[], PayOpts]) -> Function:
    """A domain's backlink profile — the one SEO signal not derivable from a page fetch."""
    return Function(
        fn_name="check_backlinks",
        fn_description=(
            "A domain's backlink profile: referring domains and pages, the dofollow split that "
            "actually carries authority, an authority rank and a spam score. The one SEO signal an "
            "agent cannot compute from a page fetch — it needs a crawled link graph. "
            "Pays ~$0.10 USDC on Base over x402."
        ),
        args=[
            Argument(
                name="target",
                type="string",
                description="A domain, or any URL on it, to look up (e.g. 'example.com').",
            ),
        ],
        executable=_make_executable("/v1/backlinks", "target", opts_provider, hint="a domain or URL"),
    )


def keyword_volume_function(opts_provider: Callable[[], PayOpts]) -> Function:
    """Search volume for up to 200 keywords in ONE priced call — batch or overpay by up to 200x."""
    return Function(
        fn_name="get_keyword_volume",
        fn_description=(
            "Search volume, CPC and competition for up to 200 keywords in a SINGLE call. This is "
            "priced PER CALL, not per keyword: one call with 200 keywords costs the same ~$0.15 as "
            "one call with a single keyword. Calling this once per keyword buys identical data for up "
            "to 200x the money — always batch every keyword you need into one 'keywords' list. "
            "Pays ~$0.15 USDC on Base over x402."
        ),
        args=[
            Argument(
                name="keywords",
                type="string",
                description=(
                    "Comma-separated keywords, up to 200 (e.g. 'best coffee maker, espresso machine "
                    "reviews'). Batch everything you need into this one call — the price is per "
                    "call, not per keyword."
                ),
            ),
            Argument(
                name="location",
                type="string",
                description="Optional Google Ads location code. Default 2840 (United States).",
            ),
            Argument(
                name="language",
                type="string",
                description="Optional two-letter language code. Default 'en'.",
            ),
        ],
        executable=_make_keyword_volume_executable(opts_provider),
    )


def ranked_keywords_function(opts_provider: Callable[[], PayOpts]) -> Function:
    """Keywords a domain already ranks for, with position and the ranking URL."""
    return Function(
        fn_name="get_ranked_keywords",
        fn_description=(
            "Which keywords a domain already ranks for in organic search, with position and the "
            "exact URL that ranks. Works on any domain, so it is competitor research as much as "
            "self-audit. Pays ~$0.05 USDC on Base over x402."
        ),
        args=[
            Argument(name="target", type="string", description="The domain to look up (e.g. 'example.com')."),
            Argument(
                name="limit",
                type="string",
                description="Optional max keywords to return, 1-200. Default 50.",
            ),
            Argument(
                name="location",
                type="string",
                description="Optional Google Ads location code. Defaults server-side.",
            ),
            Argument(
                name="language",
                type="string",
                description="Optional two-letter language code. Defaults server-side.",
            ),
        ],
        executable=_make_ranked_keywords_executable(opts_provider),
    )


def keyword_ideas_function(opts_provider: Callable[[], PayOpts]) -> Function:
    """Related/long-tail keyword ideas for a seed term, with measured volume and intent."""
    return Function(
        fn_name="get_keyword_ideas",
        fn_description=(
            "Related and long-tail keyword ideas for a seed term, each with search volume and search "
            "intent — measured candidates rather than ones a language model invented. "
            "Pays ~$0.05 USDC on Base over x402."
        ),
        args=[
            Argument(name="seed", type="string", description="Seed keyword or phrase, up to 80 characters."),
            Argument(
                name="limit",
                type="string",
                description="Optional max ideas to return, 1-200. Default 50.",
            ),
            Argument(
                name="location",
                type="string",
                description="Optional Google Ads location code. Defaults server-side.",
            ),
            Argument(
                name="language",
                type="string",
                description="Optional two-letter language code. Defaults server-side.",
            ),
        ],
        executable=_make_keyword_ideas_executable(opts_provider),
    )


def true402_functions(opts: Optional[PayOpts] = None) -> list[Function]:
    """The true402 stalls, ready to drop into a GAME Worker `action_space`.

    Pass a `PayOpts`, or leave `None` to read PAYER_PRIVATE_KEY / TRUE402_BASE_URL / BASE_RPC_URL from
    the environment. Most of the on-chain safety stalls have a free daily trial, so those functions
    return real results even with no wallet configured — until the trial is exhausted, then they
    require payment. `check_deployer` and the SEO/search stalls (backlinks, keyword volume, ranked
    keywords, keyword ideas) have NO free trial and are paid from the first call — they need a funded
    `PAYER_PRIVATE_KEY`. `check_token_report` is the primary pre-trade gate.
    """
    resolved = opts or PayOpts.from_env()

    def opts_provider() -> PayOpts:
        return resolved

    return [
        token_report_function(opts_provider),
        token_safety_function(opts_provider),
        address_safety_function(opts_provider),
        liquidity_history_function(opts_provider),
        tx_preflight_function(opts_provider),
        deployer_check_function(opts_provider),
        backlinks_function(opts_provider),
        keyword_volume_function(opts_provider),
        ranked_keywords_function(opts_provider),
        keyword_ideas_function(opts_provider),
    ]
