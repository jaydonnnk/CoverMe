# Payments — Jaydon

`kwal.py` (J3) wraps the Kwal skill's own Python modules: `search`, `options`,
`variant`, `quote`, `funding`/`wait_for_funding`, `checkout`,
`payment`/`wait_for_payment`, plus `ShipTo` and `Quote` from 3.1. One global
lock, retries every 15-30 s for up to 5 minutes, and every raw response
recorded under `service/fixtures/kwal/`. Runs in WSL/Linux (the skill uses
`fcntl`); set `KWAL_SKILL_DIR` if the skill isn't at
`~/.agents/skills/agent-payment/scripts`.

`chain.py` and `pay()` come in J7; `reap_approval.py` is A5.
Francesco's mock belongs in `service/fake_payments.py`, not this folder.

Kwal facts that shape the API:
- Product and variant ids are aliases: each search or resolution can hand out
  a new id for the same item, and old ids keep working. There is no
  variant -> product route, so `quote()` knows a variant only if `variant()`
  resolved it in this process (or `product_id=` lets it search).
- `shop` is Kwal's merchant name lowercased (`divinikey`, `forza sports`),
  not a domain. Kwal returns no image, so `image_url` is None.
