"""Cover's guard (3.2): laeria's signed-request check, rules check and spend
ceiling, run before any gas is spent. The Checkpoint enforces the same rules
again at `release`."""
from .ceiling import spend_ceiling_cents
from .rules import (
    RULES,
    WORDS,
    Limits,
    check_rules,
    from_bitmask,
    needs_approval,
    purchase_cents,
    to_bitmask,
)
from .signing import (
    BadSignature,
    SigningConfigError,
    make_approval,
    request_digest,
    sign_approval,
    sign_request,
    verify_approval,
    verify_request,
)

__all__ = [
    "RULES",
    "WORDS",
    "BadSignature",
    "Limits",
    "SigningConfigError",
    "check_rules",
    "from_bitmask",
    "make_approval",
    "needs_approval",
    "purchase_cents",
    "request_digest",
    "sign_approval",
    "sign_request",
    "spend_ceiling_cents",
    "to_bitmask",
    "verify_approval",
    "verify_request",
]
