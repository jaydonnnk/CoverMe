# Cover: demo script

Ported from laeria's `docs/DEMO_SCRIPT.md` format: pre-flight checklist, timed beats, fallbacks. Under 3 minutes. Beats from `COVER_PLAN.html`.

**Mode for tonight's take: simulation** (`PAYMENTS_MODE=fake`). The app shows a mode badge; say "simulated payments" once on camera. The contracts are live on Ink Sepolia and the full onchain path (release, fee, refund, fair-claim rejection, A5 approval) is proven against the compiled contracts in `service/payments/tests/test_chain_anvil.py`. Show the explorer links below for "verify it yourself".

| Contract | Address (Ink Sepolia, 763373) |
|---|---|
| Checkpoint | [`0xc13A5B8857cE7F4E20A176A03925E2efA68Ef0af`](https://explorer-sepolia.inkonchain.com/address/0xc13A5B8857cE7F4E20A176A03925E2efA68Ef0af) |
| Bond | [`0x872597FF7BF4AA143C21126b50557022BC3ee351`](https://explorer-sepolia.inkonchain.com/address/0x872597FF7BF4AA143C21126b50557022BC3ee351) |
| ERC-8004 Identity | [`0x5fE095dA5C7Bd3E80E28e59F1e43D250D3e7B620`](https://explorer-sepolia.inkonchain.com/address/0x5fE095dA5C7Bd3E80E28e59F1e43D250D3e7B620) |
| ERC-8004 Reputation | [`0x891513a8C901916D57833201bC2720a63E349a60`](https://explorer-sepolia.inkonchain.com/address/0x891513a8C901916D57833201bC2720a63E349a60) |

---

## Pre-flight (5 minutes before the take)

- [ ] **Service** (WSL, repo root): `PAYMENTS_MODE=fake ~/venvs/cover/bin/uvicorn service.main:app --port 8000`. Check `curl localhost:8000/health` says `"mode":"fake"`.
- [ ] **App** (`app/`): `npm run dev`, open `http://localhost:3000` at 1080p. The mode badge says simulation; the ledger says Connected.
- [ ] **Reset**: press the app's reset (or `curl -X POST localhost:8000/demo/reset`). Score shows 100, fees paid 0. Run it before every take.
- [ ] Explorer tab open on the Checkpoint address above.
- [ ] Screen recorder at 1080p, notifications off, stopwatch overlay visible.
- [ ] (Live mode only, not tonight) `scripts/demo_reset.py` printed `READY agentId=<n>` and Ana is logged in with the demo email.

## Beats

| Time | Beat | Do | Say | Ledger should show |
|---|---|---|---|---|
| 0:00–0:20 | Problem | Target's terms on screen, then the 93% / 28% figures | "When the agent gets it wrong, the shopper pays." | nothing yet |
| 0:20–0:45 | Set-up | Maker screen: deposit, score 100, fee 0.5%. Ana sets limits: $100 per item, $150 a month, her shops, her address, ends 31 Oct | "The maker backs its agent with a deposit. Ana sets her limits once." | limits saved |
| 0:45–1:10 | Covered purchase | Chat: **"Get me the Keychron B40."** Sign the card | "She signs what she asked for, not a blank cheque." | checked → released → fee_taken → funded → paid → confirmed, with tx and Kwal payment ID |
| 1:10–1:25 | Refusal | Chat: the fake **"today's deal"** message (GMKtec mini PC, $6,599, new address). Sign | "A prompt injection tries to spend $6,599. The Checkpoint refuses it three ways. No money moves." | **refused: amount, shop, address** |
| 1:25–2:05 | The moment | Chat: **"The black PowerBug 25W, under $60."** Agent takes the default White/Dune. Paid. Tap **Wrong item** | "She asked for black. It sent White/Dune. One tap." Read the stopwatch. | claimed → **refunded** from the maker's deposit → score_written; receipt shows black ≠ white/dune |
| 2:05–2:20 | Fair claim (A2b) | Tap **Wrong item** on the Keychron from 0:45 | "Cover isn't a free refund button. She got exactly what she asked for, so the claim is rejected." | claimed → **rejected**; score stays up |
| 2:20–2:35 | Score has teeth (A5) | Maker screen: score fell, fee rose, auto-pay limit dropped to $50 | "A worse score costs the maker more and lowers what the agent may buy alone. Above that, Ana approves it herself, uncovered." | (onchain: `NeedsApproval`, then `releaseApproved`; proven in tests) |
| 2:35–3:00 | Close | Explorer tab: Checkpoint and Bond | "Limits stop the money. The bond fixes the mistakes. The terms are code and the deposit is public." | |

## Fallbacks

| If | Then |
|---|---|
| Service down / ledger "Disconnected" | Restart uvicorn; the app reconnects by itself. Reset, retake from the last beat. |
| Agent picks the wrong item for the Keychron | Retype exactly "Get me the Keychron B40". |
| PowerBug comes back black (no mismatch) | Use the backups: Satechi Snap Hub (colour) or Gymshark Power T-Shirt (size). |
| Claim button doesn't appear | The purchase isn't `confirmed` yet; wait for the last ledger row. |
| Refusal shows extra reasons | Fine: the beat is "refused, no money moved". Read the first three. |
| Live mode breaks mid-take | Switch to `PAYMENTS_MODE=fake`, say "simulated payments", and point at the explorer for the deployed contracts. |
| OpenAI key missing | The agent runs scripted (`agent_mode: scripted`); the beats above are the scripted lines. |

## What's real and what's simulated tonight

- **Real:** Checkpoint and Bond deployed on Ink Sepolia; ERC-8004 Identity and Reputation deployed; the guard (signature, rules, ceiling: laeria's 19 cases in pytest and forge); a real Kwal checkout earlier today (`pay_de230427f0194287b77669bbf393ef16`, 15.73 USDC, 23 s, no approval link); a contract transfer counting as vault funding (~38 s); `chain.py` driving release, confirm, refund, rejection and the A5 approval against the compiled contracts on anvil.
- **Simulated in the video:** the payment events and the maker's numbers (`PAYMENTS_MODE=fake`), because the demo agent isn't registered and Ana's in-app wallet isn't funded yet.
- **Known limit:** claims compare exact labels. "Black" against "White/Dune" is clear; "Black" against "Midnight" would refund even if Midnight is black.
