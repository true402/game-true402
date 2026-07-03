"""true402 safety stalls as Virtuals Protocol GAME (G.A.M.E) custom Functions.

Give a GAME agent a pay-per-call, on-chain rug/honeypot gate for Base tokens over x402 (USDC on Base,
no account, no API key — the wallet is the identity).

    from game_true402 import true402_functions
    from game_sdk.game.worker import Worker

    worker = Worker(
        api_key=GAME_API_KEY,
        description="Vets tokens before trading.",
        instruction="Always vet a token with check_token_report before acting.",
        get_state_fn=lambda function_result, current_state: (current_state or {}),
        action_space=true402_functions(),   # reads PAYER_PRIVATE_KEY from the env
    )
"""
from .functions import (
    address_safety_function,
    deployer_check_function,
    token_report_function,
    token_safety_function,
    true402_functions,
)
from .x402 import PayOpts, pay_stall, sign_payment

__version__ = "0.1.0"
__all__ = [
    "true402_functions",
    "token_report_function",
    "token_safety_function",
    "address_safety_function",
    "deployer_check_function",
    "PayOpts",
    "pay_stall",
    "sign_payment",
]
