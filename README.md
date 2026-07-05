# game-true402

[![PyPI version](https://img.shields.io/pypi/v/game-true402)](https://pypi.org/project/game-true402/) &nbsp; **Stable · production-ready** — semver-stable public API (v1.0).

<!-- meta description: Give a Virtuals Protocol GAME agent an on-chain rug, honeypot and address-safety gate — pay per call over x402, USDC on Base, no account and no API key. -->

<p><strong>true402 safety stalls as <a href="https://docs.game.virtuals.io/">Virtuals Protocol GAME</a> functions.</strong> Give a G.A.M.E agent a pay-per-call, on-chain rug/honeypot gate for Base tokens over <a href="https://x402.org">x402</a> — USDC on Base, no account, no API key. The wallet is the identity, and the safety stalls have a free daily trial, so the functions work out of the box with no wallet configured.</p>

## §01 · Install

```bash
pip install game-true402
```

<p>This pulls the canonical Python GAME SDK (<code>game_sdk</code>) plus the x402 payer (<code>requests</code>, <code>eth-account</code>). You also need a GAME API key from <a href="https://console.game.virtuals.io/">console.game.virtuals.io</a>.</p>

## §02 · Use

```python
import os
from game_sdk.game.worker import Worker
from game_true402 import true402_functions

# Reads PAYER_PRIVATE_KEY from the env (a Base wallet holding a little USDC).
# Omit the key to rely on the free daily trial for the safety stalls.
worker = Worker(
    api_key=os.environ["GAME_API_KEY"],
    description="A cautious on-chain trader that vets tokens before buying.",
    instruction="Always run check_token_report before acting on a token.",
    get_state_fn=lambda function_result, current_state: (current_state or {}),
    action_space=true402_functions(),
)

worker.run("Is token 0x… safe to buy on Base?")
```

<p>To compose the functions into a full multi-worker agent instead, register the same list on a <code>WorkerConfig.action_space</code> and pass the worker to an <code>Agent(workers=[…])</code>, then call <code>agent.compile()</code> and <code>agent.run()</code>.</p>

## §03 · The functions

<p>The agent gets four functions. Each pays its stall over x402 and returns the standard GAME <code>(FunctionResultStatus, message, info)</code> tuple; the <code>info</code> dict is the full stall JSON, fed into your <code>get_state_fn</code> on the next step.</p>

<ul>
<li><code>check_token_report</code> — <strong>primary pre-trade gate.</strong> Composite <strong>avoid / caution / ok</strong> verdict from a real on-chain buy/sell honeypot simulation (proves sellability, not just a static scan) plus liquidity, ownership/mint and recent rug activity. Call before buying. ~$0.01.</li>
<li><code>check_token_safety</code> — structural safety score 0–100 and flags (honeypot sim, liquidity, mint/ownership). Lighter than the report. ~$0.005.</li>
<li><code>check_address_safety</code> — screen any address before you send to / approve / call it: EOA-vs-contract, ETH+USDC balance, activity, ownership, upgradeable-proxy (EIP-1967) detection. ~$0.005.</li>
<li><code>check_deployer</code> — deployer wallet reputation (age, contracts shipped, fresh-throwaway flag) to catch serial ruggers a structural scan can't see. ~$0.008.</li>
</ul>

## §04 · Configuration

<p><code>true402_functions()</code> reads the environment, or you can pass an explicit <code>PayOpts</code>:</p>

```python
from game_true402 import true402_functions, PayOpts

action_space = true402_functions(PayOpts(
    payer_private_key="0x…",   # a Base wallet with a little USDC (gas is sponsored; USDC only)
    max_amount_usd=0.10,        # hard per-call ceiling — refuses to sign a 402 demanding more
))
```

<ul>
<li><code>PAYER_PRIVATE_KEY</code> — Base wallet key that signs x402 payments (needs USDC, not ETH). Unset means free-trial only.</li>
<li><code>TRUE402_BASE_URL</code> — defaults to <code>https://true402.dev/api</code>; override to point at a self-hosted instance.</li>
<li><code>BASE_RPC_URL</code> — defaults to <code>https://mainnet.base.org</code>; used only for a balance pre-check.</li>
</ul>

## §05 · Safety

<p>The payer <strong>refuses to sign</strong> anything that isn't USDC-on-Base within <code>max_amount_usd</code> (default $0.10), so a rogue or compromised endpoint can't make your agent authorize an unexpected asset, network, or amount. The private key signs locally and never leaves the process. This is the same verified x402 payer used by the CrewAI and LangChain integrations — signatures recover to the payer address.</p>

## §06 · FAQ

<ol>
<li><p><strong>Do I need a true402 account or API key?</strong> No. Payment is the auth: the agent POSTs, gets an HTTP 402 with payment terms, signs an EIP-3009 USDC authorization, and retries. The wallet is the identity.</p></li>
<li><p><strong>Does it work without a funded wallet?</strong> Yes, up to a point. The safety stalls have a free daily trial, so the functions return real results with no <code>PAYER_PRIVATE_KEY</code> set — until the trial is exhausted, then they require payment.</p></li>
<li><p><strong>Which function should the agent call before trading?</strong> <code>check_token_report</code>. It is the composite avoid/caution/ok gate and folds in the honeypot simulation, liquidity, ownership and deployer signal.</p></li>
<li><p><strong>Why Python and not the Node GAME SDK?</strong> GAME's Python SDK is the canonical reference, and its executables run synchronously — a clean match for the synchronous x402 payer, with no async wrapping. A TypeScript build can wrap the same stalls via the <code>@true402.dev/langchain</code> payer.</p></li>
<li><p><strong>What does the executable return to the planner?</strong> A <code>(FunctionResultStatus.DONE | .FAILED, message, info)</code> tuple. The message is an agent-readable summary; the <code>info</code> dict is the full stall JSON for your <code>get_state_fn</code>.</p></li>
</ol>

## §07 · Links

<ul>
<li>Live check in your browser: <a href="https://true402.dev/check">true402.dev/check</a></li>
<li>API reference: <a href="https://true402.dev/docs/api">true402.dev/docs/api</a> · OpenAPI: <a href="https://true402.dev/openapi.json">true402.dev/openapi.json</a></li>
<li>Also available: <a href="https://www.npmjs.com/package/@true402.dev/langchain">LangChain</a> · <a href="https://pypi.org/project/crewai-true402/">CrewAI</a> · <a href="https://www.npmjs.com/package/@true402.dev/mcp-server">MCP server</a></li>
</ul>

## §08 · License

<p>MIT</p>
