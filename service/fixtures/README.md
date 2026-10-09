# Replay fixtures — Jaydon

Recorded Kwal responses (J3/J9). `service/payments/kwal.py` writes every raw
response to `kwal/<YYYYmmdd-HHMMSS>/` as it happens, with Ana's ShipTo values
and the session token replaced by `<redacted>`. `kwal.use_replay(dir)` serves
a run back with no network. Replays must be visibly labelled in the UI.

- `kwal/hmx-quote/`: catalogue reads, variant resolution, one HMX Snowflake
  quote to a fictional US address and one funding read (9 Oct). The unit
  tests replay it. No payment.
- `kwal/hmx-checkout/`: the first completed checkout (9 Oct 19:49 SGT),
  HMX to Ana's address, payment `pay_de230427f0194287b77669bbf393ef16`,
  15.73 USDC, no approval link. Includes one live 502 + `retry_after=60s`.
- `kwal/20261009-*`: two HMX quote runs to Ana's address. No payment.

Dated runs are live output. Check them before committing; set `KWAL_RECORD=0`
to turn recording off.
