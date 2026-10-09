# Replay fixtures — Jaydon

Recorded Kwal responses (J3/J9). `service/payments/kwal.py` writes every raw
response to `kwal/<YYYYmmdd-HHMMSS>/` as it happens, with Ana's ShipTo values
and the session token replaced by `<redacted>`. `kwal.use_replay(dir)` serves
a run back with no network. Replays must be visibly labelled in the UI.

- `kwal/hmx-quote/`: catalogue reads, variant resolution, one HMX Snowflake
  quote to a fictional US address and one funding read (9 Oct). The unit
  tests replay it. No payment.

Dated runs are live output. Check them before committing; set `KWAL_RECORD=0`
to turn recording off.
