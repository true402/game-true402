"""Who this client is, for the true402 update notice.

Kept OUT of the shared payment code (x402.py), which is byte-identical across packages; this is the
one file that differs per package. `src/clients/registry.test.ts` in the true402 repo holds it equal
to pyproject.toml.
"""

CLIENT_ID = "game"
VERSION = "1.4.4"
PACKAGE = "game-true402"
INSTALL = "pip install -U game-true402"
