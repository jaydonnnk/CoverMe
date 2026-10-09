# Scripts (Jaydon)

Run in WSL with the root `.env` loaded. Use only test wallets. Kwal credentials stay outside the repository.

| Script | Does | Spends |
|---|---|---|
| `pay_smoke.py` | Quotes (and with `--checkout` pays) the HMX switches from Ana's Kwal vault | `--checkout`: test USDC |
| `write_deployments.py` | Fills `deployments/ink-sepolia.json` `"cover"` from the forge broadcast and `contracts/out` | nothing |

The deploy and the maker's Bond deposit are forge scripts: see `contracts/README.md`.
