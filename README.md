# Cover

Shared buildathon repository for Jaydon and Francesco: covered agent purchases
on Ink Sepolia (chain ID **763373**).

## What's real / what's not

This is **F1 scaffolding**, not a working purchasing demo. Next.js renders the
workspace and placeholder shopper/maker routes. FastAPI has a real `/health`
liveness route. Foundry builds and runs one toolchain smoke test. ERC-8004 is
pinned unchanged as a submodule.

No wallets, AI, payment guard, Kwal calls, SSE, Checkpoint, Bond, deployments,
claims or refunds are implemented yet. Deployment addresses are `null`; ABIs
are empty. The EIP-712 verifying contract is a deliberate non-address placeholder
that must be replaced from the deployment file before signing.

The planned claim rule compares exact labels: “black” versus “midnight” can
refund even when Midnight is black. Demo items must have plain labels; production
would need shop-signed attributes. See [BUILD_PLAN.md](BUILD_PLAN.md) for the
implementation sequence and [COVER_PLAN.html](COVER_PLAN.html) for the product.

## Fresh clone

Requirements: Node.js 22 (22.13+, see `.nvmrc`), npm 10, Python 3.10+ (3.12 recommended),
Git and Foundry. macOS, Linux and WSL can use the commands below.

```sh
git clone --recurse-submodules https://github.com/jaydonnnk/CoverMe.git
cd CoverMe
# Existing clones: git submodule update --init --recursive
# If you use nvm: nvm use
cp .env.example .env
npm --prefix app ci
cp app/.env.example app/.env.local
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r service/requirements-dev.txt
```

Run the frontend:

```sh
npm --prefix app run dev
```

In a second terminal, from the repo root:

```sh
source .venv/bin/activate
python -m uvicorn service.main:app --reload --env-file .env --port 8000
```

- App: http://localhost:3000
- Service liveness: http://localhost:8000/health
- API docs: http://localhost:8000/docs

The two processes are independent; app pages do not require a running backend
or any secrets. The health route does not imply payment/chain readiness.

## Validate

```sh
npm --prefix app run lint
npm --prefix app run typecheck
npm --prefix app run build
python -m pytest -q
cd contracts
forge fmt --check
forge build
forge test
```

CI runs app lint/types/build, Python health/shared-definition tests, Foundry
checks and ERC-8004 reference compile/tests on PRs and main. It makes no network
transactions and needs no secrets.
The ERC-8004 upstream has its own Hardhat toolchain; see
[contracts/README.md](contracts/README.md) for its separate build procedure.

## Work areas

```text
app/            Francesco: Next.js project (app/app/ contains routes)
  lib/wallet.ts Jaydon: reserved for the laeria port, not implemented yet
service/        Francesco: FastAPI and future agent/runner/judge/MCP
  guard/        Jaydon: signing, rules, spend ceiling and 19 ported tests
  payments/     Jaydon: Kwal + chain integration
  fixtures/     Jaydon: sanitized record/replay data
contracts/      Jaydon: Foundry; except ERC-8004 reference submodule (Francesco)
shared/         Joint: interface draft and EIP-712 definition
deployments/    Joint file: registries (Francesco), cover (Jaydon)
scripts/        Jaydon: future demo reset and payment smoke scripts
docs/           Collaboration and future demo documentation
```

Read [CONTRIBUTING.md](CONTRIBUTING.md) for folder ownership, branches and PRs.
Use `francesco/F*-description` and `jaydon/J*-description` branches from main.
CODEOWNERS and the PR template help coordinate reviews; enabling main branch
protection is a separate repository-admin action.

## Next handovers

1. Review [shared/INTERFACES.md](shared/INTERFACES.md) together (J1/F2), especially
   the open decisions. It is copied from the plan, **not yet jointly agreed**.
2. Jaydon starts J2 in guard/wallet; Francesco starts F3 in ERC-8004 and then F4
   with `fake_payments.py`. Neither has to edit the other's implementation.
3. Keep deployment placeholders until each owner supplies real addresses/ABIs;
   resolve the EIP-712 domain dynamically from the deployed Checkpoint.

No laeria code has been ported in this commit. Prior work planned for J2/J9 is
listed in BUILD_PLAN.md; do not describe it as already implemented.

## Secrets

Root `.env` is backend/scripts-only; `app/.env.local` is public configuration
only. Keep Kwal credentials outside the repo. Never commit test private keys
either, and never use wallets that have held real money.
