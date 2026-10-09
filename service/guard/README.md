# Guard — Jaydon

laeria's signed-request check, rules check and spend ceiling (3.2), run before
any gas is spent. The Checkpoint enforces the same rules again at `release`.

| File | Ported from | Does |
|---|---|---|
| `signing.py` | laeria `services/delegation.py` | `verify_request(request, signature)` recovers the EIP-712 signer from `shared/purchase-request.json` and the deployed Checkpoint; raises `BadSignature` unless it is `request.shopper`. `sign_request` signs from Python (tests, `demo_reset.py`). |
| `rules.py` | laeria `services/payment.py:53`, `core/models.py:121` | `check_rules(request, q, limits)` returns every failed rule; `[]` passes. Unset means deny. `needs_approval(q, auto_pay_limit_cents)` decides A5 parking. `RULES` fixes the bit positions of `Checkpoint.check()`. |
| `ceiling.py` | laeria `api/routes/actions.py:345-361` | `spend_ceiling_cents(...)`: one `min()` over the signed max, the quote, the per-item cap, the monthly headroom and the maker's free cover net of the fee. |
| `tests/test_mandate.py` | laeria `tests/test_mandate.py` | The 19 laeria cases, each naming its origin and any deliberate difference. |

Use from the service:

```python
from service.guard import BadSignature, Limits, check_rules, needs_approval, \
    purchase_cents, spend_ceiling_cents, verify_request

signer = verify_request(request, signature)           # BadSignature -> 400
failed = check_rules(request, q, limits)              # non-empty -> "refused"
if purchase_cents(q) > spend_ceiling_cents(request, q, limits, free_cover, fee_bps=fee):
    failed.append("not_enough_cover")
if not failed and needs_approval(q, auto_pay_limit):  # -> "needs_approval"
    ...
```

All amounts are integer cents. `purchase_cents(q)` is the larger of the listed
price and the quote total; that choice is pending agreement at J1.

Run: `python -m pytest service/guard` (needs `eth-account`, in `service/requirements.txt`).
