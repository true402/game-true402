"""Pay any true402 stall over x402 and return its JSON.

The whole protocol, in one function: POST → 402 with payment terms → sign an EIP-3009 USDC
authorization → retry with an X-PAYMENT header → 200. No accounts, no API keys; the wallet is the
identity. USDC on Base, gas sponsored by the facilitator (the payer needs only USDC, not ETH).

Safety: the client REFUSES to sign anything that isn't USDC-on-Base within a caller-set cap, so a
rogue/compromised endpoint (or a MITM past TLS) can't make the agent authorize an unexpected
asset/network or an excessive amount.
"""
from __future__ import annotations

import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

import requests
from eth_account import Account
from eth_account.messages import encode_typed_data

BASE_USDC = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"
BASE_NETWORK = "eip155:8453"
BASE_CHAIN_ID = 8453
DEFAULT_BASE_URL = "https://true402.dev/api"
DEFAULT_RPC_URL = "https://mainnet.base.org"
_BALANCE_OF_SELECTOR = "0x70a08231"


@dataclass
class PayOpts:
    """Configuration for paying true402 stalls."""

    payer_private_key: str
    """A Base wallet private key holding a little USDC (the payer)."""
    base_url: str = DEFAULT_BASE_URL
    rpc_url: str = DEFAULT_RPC_URL
    max_amount_usd: float = 0.10
    """Hard ceiling, in USDC, on a single signed payment. The client refuses a 402 demanding more."""
    timeout: float = 30.0

    @classmethod
    def from_env(cls, **overrides: Any) -> "PayOpts":
        """Build from PAYER_PRIVATE_KEY / TRUE402_BASE_URL / BASE_RPC_URL env vars."""
        key = overrides.pop("payer_private_key", None) or os.environ.get("PAYER_PRIVATE_KEY", "")
        return cls(
            payer_private_key=key,
            base_url=overrides.pop("base_url", None) or os.environ.get("TRUE402_BASE_URL", DEFAULT_BASE_URL),
            rpc_url=overrides.pop("rpc_url", None) or os.environ.get("BASE_RPC_URL", DEFAULT_RPC_URL),
            **overrides,
        )


def _usdc_balance(rpc_url: str, holder: str, timeout: float) -> int:
    data = _BALANCE_OF_SELECTOR + holder[2:].rjust(64, "0")
    body = {"jsonrpc": "2.0", "id": 1, "method": "eth_call", "params": [{"to": BASE_USDC, "data": data}, "latest"]}
    r = requests.post(rpc_url, json=body, timeout=timeout, headers={"content-type": "application/json"})
    r.raise_for_status()
    return int(r.json()["result"], 16)


def sign_payment(accept: dict, opts: PayOpts) -> str:
    """Sign an EIP-3009 authorization for the given 402 `accepts[]` entry → base64 X-PAYMENT value."""
    key = opts.payer_private_key
    if not key:
        raise ValueError("no payer_private_key set — cannot pay (set PAYER_PRIVATE_KEY or PayOpts.payer_private_key)")
    if not key.startswith("0x"):
        key = "0x" + key
    account = Account.from_key(key)

    network = accept.get("network")
    if network and network != BASE_NETWORK:
        raise ValueError(f'unexpected payment network "{network}" (expected {BASE_NETWORK}) — refusing to sign')
    asset = accept.get("asset", "")
    if asset.lower() != BASE_USDC.lower():
        raise ValueError(f"unexpected payment asset {asset} (expected Base USDC) — refusing to sign")

    value = int(accept.get("amount") or accept.get("maxAmountRequired") or "0")
    cap_atomic = round(opts.max_amount_usd * 1e6)
    if value > cap_atomic:
        raise ValueError(f"402 demands {value} USDC base units, over the ${opts.max_amount_usd} cap — refusing to sign")

    held = _usdc_balance(opts.rpc_url, account.address, opts.timeout)
    if held < value:
        raise ValueError(f"payer {account.address} holds {held} < {value} USDC base units — fund it")

    now = int(time.time())
    valid_before = now + int(accept.get("maxTimeoutSeconds") or 120)
    nonce = "0x" + secrets.token_hex(32)
    extra = accept.get("extra") or {}
    authorization = {
        "from": account.address,
        "to": accept["payTo"],
        "value": value,
        "validAfter": now - 60,
        "validBefore": valid_before,
        "nonce": bytes.fromhex(nonce[2:]),
    }
    signable = encode_typed_data(
        domain_data={
            "name": extra.get("name", "USD Coin"),
            "version": extra.get("version", "2"),
            "chainId": BASE_CHAIN_ID,
            "verifyingContract": BASE_USDC,
        },
        message_types={
            "TransferWithAuthorization": [
                {"name": "from", "type": "address"},
                {"name": "to", "type": "address"},
                {"name": "value", "type": "uint256"},
                {"name": "validAfter", "type": "uint256"},
                {"name": "validBefore", "type": "uint256"},
                {"name": "nonce", "type": "bytes32"},
            ],
        },
        message_data=authorization,
    )
    signature = Account.sign_message(signable, key).signature.hex()
    if not signature.startswith("0x"):
        signature = "0x" + signature

    payment = {
        "x402Version": 2,
        "scheme": "exact",
        "network": network,
        "payload": {
            "signature": signature,
            "authorization": {
                "from": authorization["from"],
                "to": authorization["to"],
                "value": str(value),
                "validAfter": str(authorization["validAfter"]),
                "validBefore": str(authorization["validBefore"]),
                "nonce": nonce,
            },
        },
    }
    import base64

    return base64.b64encode(json.dumps(payment).encode()).decode()


def pay_stall(path: str, payload: dict, opts: PayOpts) -> Any:
    """POST `payload` to a true402 stall path (e.g. '/v1/base/token-report'), paying over x402 if asked.

    If the first response is 200 (a free-trial call), returns it without paying. If it's 402, signs and
    retries. Raises on any other status or on a refused/insufficient payment.
    """
    url = opts.base_url.rstrip("/") + path
    headers = {"content-type": "application/json"}
    first = requests.post(url, json=payload, headers=headers, timeout=opts.timeout)
    if first.status_code == 200:
        return first.json()  # served free (free trial) — no payment needed
    if first.status_code != 402:
        raise RuntimeError(f"expected HTTP 402 from {path}, got {first.status_code}: {first.text[:200]}")

    challenge = first.json()
    accepts = challenge.get("accepts") or []
    accept = next((a for a in accepts if a.get("scheme") == "exact"), None)
    if not accept:
        raise RuntimeError('no x402 "exact" payment requirement in the 402')

    x_payment = sign_payment(accept, opts)
    paid = requests.post(url, json=payload, headers={**headers, "X-PAYMENT": x_payment}, timeout=opts.timeout)
    if paid.status_code != 200:
        raise RuntimeError(f"paid request to {path} failed (HTTP {paid.status_code}): {paid.text[:200]}")
    return paid.json()
