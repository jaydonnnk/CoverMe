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
It supports three presentation flows:

- A successful keyboard purchase
- A purchase refused before payment because it breaks the buyer's limits
- A labelled wrong-colour rehearsal that refunds the approved buyer total from
  provider collateral and records merchant recovery as pending

Simulation, replay and live testnet activity are labelled in the interface. Mock
transaction evidence is never presented as an onchain transaction.

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

## Suggested demo sequence

1. Compare Atlas Shopper and Scout Buyer, then hire one.
2. Connect the labelled demo account and save the buyer's limits.
3. Buy the Keychron keyboard and show the successful receipt.
4. Arm the injected-failure rehearsal.
5. Request the black PowerBug and authorize the displayed total.
6. Open the wrong-item claim after the recorded White/Dune purchase.
7. Show the buyer refund, provider loss, reputation update and merchant recovery
   status in the receipt and provider panel.

The full sequence can be reset from the browser without restarting either server.

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
