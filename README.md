# CoverMe

CoverMe is a marketplace for AI shopping agents. Buyers compare agents by
reputation, completed outcomes, service fee and available purchase coverage.
Businesses connect their own OpenAI-compatible agents, set a fixed or percentage
fee, and back each purchase with collateral.

When an agent makes a covered mistake, such as ordering the wrong colour, CoverMe
refunds the buyer from the provider's deposit. The provider then handles the
return or refund with the merchant. Each outcome updates the agent's reputation,
so buyers can make a more informed choice the next time they shop.

## How a purchase works

1. A business completes KYB, connects its agent endpoint and funds coverage.
2. The buyer hires an agent after comparing its record, price and coverage.
3. The agent prepares a purchase request with the item, merchant, attributes,
   spending limit and delivery destination.
4. The buyer reviews the full cost and authorizes the request.
5. CoverMe checks the mandate and reserves enough provider collateral to cover
   the approved purchase.
6. A correct purchase completes normally. A covered mismatch refunds the buyer,
   charges the provider's deposit and updates the agent's score.

The provider's service fee and CoverMe's protection fee are separate. Providers
choose how much they charge for their agent. CoverMe prices the risk of covering
the purchase.

## Demo

The demo includes two shopping agents with different reputations and fee models.
Tonight's recording uses `PAYMENTS_MODE=fake`. Say "simulated payments" once on
camera. The interface keeps the mode visible and labels every mock transaction.

The pitch starts with the consumer problem summarized in
[`COVER_PLAN.html`](COVER_PLAN.html): Target's terms treat an AI agent purchase as
authorized by the shopper, while a September 2026 PYMNTS survey found that 93% of
merchants wanted the agent provider to carry losses from wrong purchases and only
28% allowed agents to buy their full product range.

The recording covers three flows:

- A successful keyboard purchase
- A purchase refused before payment because it breaks the buyer's limits
- A labelled wrong-colour rehearsal that refunds the approved buyer total from
  provider collateral and records merchant recovery as pending

Simulation, replay and live testnet activity are labelled in the interface. Mock
transaction evidence is never presented as an onchain transaction.

### Pre-flight

Run this checklist five minutes before recording:

- [ ] Start FastAPI in simulation mode:

  ```sh
  PAYMENTS_MODE=fake .venv/bin/uvicorn service.main:app --port 8000
  curl http://localhost:8000/health
  ```

  The response should include `"mode":"fake"`.

- [ ] Start the app with `npm --prefix app run dev` and open
  [http://localhost:3000](http://localhost:3000) at 1080p.
- [ ] Confirm the mode badge says simulation and the ledger says Connected.
- [ ] Press **Reset rehearsal**. The provider balances, fees and agent scores
  should return to their starting values.
- [ ] Open the Checkpoint explorer link from the deployment table below.
- [ ] Set the recorder to 1080p, hide notifications and keep the refund timer visible.

### Three-minute run

| Time | Show | Say |
|---|---|---|
| 0:00 to 0:20 | Target's terms and the 93% / 28% figures | "When the agent gets it wrong, the shopper pays." |
| 0:20 to 0:45 | Compare Atlas and Scout, hire Atlas, then show its fee and collateral | "The provider backs its agent with a deposit. Ana chooses based on record, price and coverage." |
| 0:45 to 1:05 | Set Ana's $100 item limit, $150 monthly limit, shops, address and end date | "Ana sets her limits once." |
| 1:05 to 1:30 | Ask for the Keychron B40 and approve the displayed request | "She signs what she asked for, including the agent and total." |
| 1:30 to 1:50 | Run Today's deal and show the refusal | "A prompt injection tries to spend $6,599 at a new shop and address. The request is refused before money moves." |
| 1:50 to 2:35 | Arm the failure rehearsal, request the black PowerBug, approve it and press Wrong item after confirmation | "She asked for black. The agent recorded White/Dune. One claim refunds the approved total from the provider's deposit." |
| 2:35 to 3:00 | Show the refund, provider loss, new score and explorer tabs | "Limits stop the money. The bond fixes covered mistakes. The terms and deposit are public." |

The success ledger should progress through `checked`, `released`, `fee_taken`,
`funded`, `paid` and `confirmed`. The refusal shows amount, shop and address with
no payment events. The mismatch path adds `claimed`, `refunded` and
`score_written`.

### Onchain proof

Checkpoint, Bond and the ERC-8004 registries are deployed on Ink Sepolia. The
contract suite covers release, protection fees, mismatch refunds, matching-claim
rejection, score updates and the `releaseApproved` path for buyer-approved
uncovered purchases:

- [`contracts/test/Checkpoint.t.sol`](contracts/test/Checkpoint.t.sol)
- [`contracts/test/Bond.t.sol`](contracts/test/Bond.t.sol)
- [`contracts/test/Deploy.t.sol`](contracts/test/Deploy.t.sol)

Run `forge test --root contracts` to reproduce those checks locally. During the
simulation recording, use the explorer links below as public deployment evidence.

### Recording fallbacks

| Problem | Response |
|---|---|
| Service is down or the ledger disconnects | Restart FastAPI. The app reconnects automatically. Reset before continuing. |
| Keychron draft is unexpected | Send the exact shortcut **Buy Keychron** again. |
| PowerBug has no mismatch | Confirm **Failure armed** is visible, reset and repeat the PowerBug beat. |
| Claim button is missing | Wait for the `confirmed` ledger event. |
| Refusal lists extra reasons | Keep the message simple: the request was refused and no money moved. |
| OpenAI credentials are absent | Use the scripted demo agent shown by the mode label. |
| A live integration fails during rehearsal | Restart with `PAYMENTS_MODE=fake`, say "simulated payments", and show the deployed contracts in the explorer. |

## Architecture

| Layer | Purpose |
|---|---|
| Next.js | Agent marketplace, buyer authorization, provider controls, receipts and live ledger |
| FastAPI | Agent routing, quote snapshots, purchase orchestration, claims and server-sent events |
| Checkpoint | Enforces the buyer's signed limits before funds are released |
| Bond | Holds provider collateral, reserves coverage, pays refunds and records outcomes |
| ERC-8004 | Stores agent identity and reputation on Ink Sepolia |
| Kwal | Searches products, creates quotes, funds checkout and tracks payment status |

The browser never receives private keys, Kwal credentials or the buyer's saved
delivery address. The service supplies the saved address after verifying the
signed request.

## Ink Sepolia deployment

Network: Ink Sepolia, chain ID `763373`

| Contract | Address |
|---|---|
| Identity Registry | [`0x5fE095dA5C7Bd3E80E28e59F1e43D250D3e7B620`](https://explorer-sepolia.inkonchain.com/address/0x5fE095dA5C7Bd3E80E28e59F1e43D250D3e7B620) |
| Reputation Registry | [`0x891513a8C901916D57833201bC2720a63E349a60`](https://explorer-sepolia.inkonchain.com/address/0x891513a8C901916D57833201bC2720a63E349a60) |
| Checkpoint | [`0xc13A5B8857cE7F4E20A176A03925E2efA68Ef0af`](https://explorer-sepolia.inkonchain.com/address/0xc13A5B8857cE7F4E20A176A03925E2efA68Ef0af) |
| Bond | [`0x872597FF7BF4AA143C21126b50557022BC3ee351`](https://explorer-sepolia.inkonchain.com/address/0x872597FF7BF4AA143C21126b50557022BC3ee351) |
| USDC | [`0xFabab97dCE620294D2B0b0e46C68964e326300Ac`](https://explorer-sepolia.inkonchain.com/address/0xFabab97dCE620294D2B0b0e46C68964e326300Ac) |

The demo agent is ERC-8004 agent `0`, owned by the Maker wallet. Contract
addresses and ABIs live in [`deployments/ink-sepolia.json`](deployments/ink-sepolia.json).

## Run locally

Requirements:

- Node.js 22 and npm 10
- Python 3.10 or newer
- Foundry
- Git with submodule support

```sh
git clone --recurse-submodules https://github.com/jaydonnnk/CoverMe.git
cd CoverMe

cp .env.example .env
cp app/.env.example app/.env.local

npm --prefix app ci

python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r service/requirements-dev.txt
```

Start the service:

```sh
source .venv/bin/activate
python -m uvicorn service.main:app --reload --env-file .env --port 8000
```

Start the app in another terminal:

```sh
npm --prefix app run dev
```

Open [http://localhost:3000](http://localhost:3000). FastAPI documentation is
available at [http://localhost:8000/docs](http://localhost:8000/docs).

The default `PAYMENTS_MODE=fake` runs the complete presentation flow without
moving money. Kwal credentials stay outside the repository at the path set by
`KWAL_CREDENTIALS`.

## Validate

```sh
source .venv/bin/activate
python -m pytest -q

npm --prefix app run lint
npm --prefix app run typecheck
npm --prefix app run build

forge fmt --check --root contracts
forge build --root contracts
forge test --root contracts
```

The ERC-8004 reference project has its own Hardhat toolchain. See
[`contracts/README.md`](contracts/README.md) for its build commands.

## Repository layout

```text
app/            Next.js marketplace and demo workspace
service/        FastAPI service, agent runner, guard and payment adapters
contracts/      Checkpoint and Bond Foundry project
contracts/lib/erc-8004-contracts/
                Pinned ERC-8004 reference implementation
deployments/    Ink Sepolia addresses and ABIs
shared/         Purchase-request and integration definitions
scripts/        Deployment, funding and payment smoke tools
```

## Secrets

Keep backend secrets in the gitignored root `.env`. Only public browser
configuration belongs in `app/.env.local`. Store Kwal credentials outside the
repository and use test wallets that have never held real funds.

See [`CONTRIBUTING.md`](CONTRIBUTING.md) for the collaboration and review workflow.
