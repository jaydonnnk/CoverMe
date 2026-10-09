# Francesco MVP implementation plan

This is the handoff plan for a new implementation agent working only on
Francesco's part of Cover. The goal is a reliable presentation MVP, not a
production system.

Revision: 9 Oct 2026, following the marketplace/refund clarification and the
supplied wallet/network handover. This is a revision to Francesco's demo scope,
not approval to change Jaydon's contracts or the shared interfaces.

`BUILD_PLAN.md` still controls ownership. `shared/purchase-request.json` and
`shared/INTERFACES.md` control integration shapes until both owners agree changes.
Where this plan adds provider pricing or wider refund coverage, those are product
requirements with explicit simulation/live gates below, not existing contract
capabilities.

## Current state - resume, do not rebuild

Session `ses_edf9ae85affeMQRgBU4PwLFnoX` delivered the single-agent mock foundation
on `francesco/mvp-demo`: https://github.com/jaydonnnk/CoverMe/pull/1, now merged.
It includes chat, request review, guard checks, simulated purchase/refund, maker
metrics, receipts, SSE and reset controls. Its reported validation was 63 Python
tests plus frontend checks and a twice-through browser rehearsal. Revalidate
the current checkout; that report is not proof of live integration.

The presentation simulation now includes agent selection, demo business setup,
configurable flat/percentage service fees, frozen pricing, explicit failure
injection, full approved-total refund, per-provider collateral/reputation and
merchant-recovery status. Remaining live work: funded wallets, Jaydon's covered
payment/chain and browser-wallet adapters, J6 deployments, agreed getters and
claim-event correlation. The Kwal catalogue/quote/checkout client is now present;
do not report all of `service.payments` as missing.
The addresses below do not resolve those blockers by themselves.

### Main synchronized - J3 and J4 scaffold, 9 Oct 2026

The local Francesco branch was fast-forwarded from `af69197` to `1b4028b`
(`origin/main`), preserving this plan file. This includes merged PR #1 and
https://github.com/jaydonnnk/CoverMe/pull/2 (J3 Kwal client/fixtures), plus the
J4 Sender helper commit. No published commits were rewritten.

| Work | Evidence in this checkout | What it does not establish |
|---|---|---|
| J3 Kwal client | `service/payments/kwal.py`, exports in `__init__.py`, tests | No Checkpoint/Bond release, `check`, covered `pay` or chain getters yet |
| J3 smoke command | `scripts/pay_smoke.py` | Direct vault checkout, not an authorized covered purchase through the browser |
| Recorded completed checkout | `service/fixtures/kwal/hmx-checkout/` | No live agent coverage, KYB, physical fulfilment or refund demonstrated |
| J4 funding-test scaffold | `Sender.sol`, `SendToVault.s.sol`, `Sender.t.sol` | Helper source/tests are not a deployment or a measured successful contract-to-vault funding result |

The recorded checkout is HMX Snowflake Linear Switches from **Divinikey**,
size **18 set**, item $6.30 + shipping $8.18 + tax $1.25 = **15.73 USDC**,
payment `pay_de230427f0194287b77669bbf393ef16`. Its final recorded response says
**paid from your vault by a simulated card spend; nothing ships**. Treat this as
recorded test checkout evidence, not proof of real merchant fulfilment. Playback
of those responses is still **Replay**, never a newly executed payment. No
approval link was reported for that run. Recheck current vault/wallet balances;
the earlier 60-USDC vault snapshot predates this recorded spend.

Resolve these concrete F2/F4/F6 integration gaps with Jaydon:

1. `Quote.shop` now uses lowercase merchant names (for example `divinikey`), not
   domain names. Agree one signed/allowlisted merchant representation across
   guard, request, Checkpoint and receipts; do not strip a domain or map an
   unknown name by guesswork. Preserve the existing domain-based simulation.
2. `ShipTo` requires `first_name`, `last_name`, E.164 `phone`, `line1`, `city`,
   ISO-2 `country` and `email`; `line2`, `region` and `postal_code` are optional.
   It rejects the old `name` field. Live `Adapter.shipping()` must consume this
   supplied schema (for example `ShipTo.from_json`) instead of assuming the
   demo address works. Do not invent missing phone/name/address data.
3. `ShipTo.canonical_json()` includes all normalized fields with sorted keys
   and no spaces; `address_hash()` uses keccak256. Use that exact result for
   live `ANA_ADDRESS_HASH`, saved limits and authorization. The mock address
   marker is not a live hash. Agree this now; do not sign the old address shape.
4. Kwal product/variant IDs are dynamic aliases, not the spreadsheet's Shopify
   IDs. Resolve with `search` -> `options` -> `variant` in the same process before
   `quote`. Reuse Jaydon's client, not a new catalogue adapter. Do not pass the
   hardcoded `service/catalogue.py` IDs straight into live `quote`.
5. `listed_usd_cents` is the item subtotal; `charge_usdc` is the Kwal quote total
   including shipping and tax. `read_quote` has the breakdown. Keep those amounts
   distinct and bind the actual payable total before approval. Quotes expire
   after five minutes; used quotes can be reused by the provider for about
   15 minutes and are rejected for another payment. Never replay a spent quote
   as a fresh live checkout or silently reprice after approval.
6. `service.payments.chain`, `check`, covered `pay`, `get_limits` and
   `get_free_cover` are still absent, as is `app/lib/wallet.ts`. The current
   runner deliberately fails closed in live mode. Importing the new Kwal package
   does not make its live adapter ready.
7. Jaydon documents live Kwal use in WSL/Linux with an external skill directory
   (`KWAL_SKILL_DIR`) and credentials. Parser/replay tests skip if the skill is
   missing. Count/report skips rather than presenting them as executed tests;
   coordinate the runtime instead of copying his external skill into the repo.
8. Recorded checkout success is evidence for J3 only. J4 still needs a funding
   read/time measurement after the second-wallet/contract transfer. Do not run
   `--checkout` or `forge ... --broadcast` just to validate this plan; they spend
   test funds and require the owner's preflight/authorization.

Validation after this synchronization: `.venv/bin/python -m pytest -q` reported
**68 passed, 17 skipped** (Kwal external-skill parser/replay cases);
`forge test --root contracts` reported **9 passed** (scaffold + Sender, not
Checkpoint/Bond tests); frontend lint/typecheck/production build passed with
Node 22.16.0 and npm 10.9.2. No live checkout, deployment, transfer or new browser
rehearsal was performed in this documentation/synchronization task.

## 0. Work on a Francesco branch

Use the existing shared repository, but do not implement directly on `main`.
Continue the existing Francesco branch; do not reset the mock implementation.
PR #1 is merged, so subsequent commits need a new follow-up pull request into
`main`, not an attempt to update the merged request.

```bash
cd /Users/franc/Desktop/Trevislabs/CoverMe
git status --short
git switch francesco/mvp-demo
git fetch origin
```

Repository rules:

1. Never implement Francesco's work directly on `main`.
2. Push only `francesco/mvp-demo`.
3. Open a new follow-up PR into `main` after validation; PR #1 is already merged.
   Do not merge the follow-up without coordination.
4. Do not force-push or resolve Jaydon's code by
   overwriting it. Fetch and fast-forward when possible; otherwise coordinate
   a merge. Do not rebase published commits just to synchronize this branch.
5. If an integration commit must edit a shared file, keep it in a separate
   commit so it can be reviewed or cherry-picked independently.
6. Never commit `.env` files or credentials.

## 1. Mission

Product promise:

> Hire a shopping agent you trust. If it makes a covered purchase mistake,
> CoverMe refunds you, and the agent's business bears the cost.

Build the smallest complete demo in which:

1. A pre-onboarded demo business shows its agent connection, chosen service fee
   and prefunded coverage deposit. Demo KYB is explicitly simulated.
2. Ana compares two agents by reputation, completed-outcome count, business,
   service fee and coverage limit, then hires one.
3. Ana sets limits, asks for an item, and reviews the selected agent, requested
   attributes, destination, complete cost breakdown and protection terms.
4. Ana authorizes the purchase; the service uses Jaydon's guard/payment boundaries.
5. One purchase succeeds. A second, explicitly injected demo failure records
   White/Dune after Ana authorized black; known mismatches normally stop checkout.
6. Ana presses **Wrong item**; the receipt shows reimbursement from the provider
   deposit, measured time, provider loss and changed agent reputation.
7. The provider sees **Merchant recovery pending**. Recovery is not a second
   buyer refund and is not automated in this MVP.
8. A compact supporting ledger carries simulation labels or real chain/payment
   evidence. The over-budget/malicious-deal refusal is a secondary presentation
   beat, but its existing tests and safeguards remain.
9. The full main flow runs twice after reset, without a terminal after startup.

Declare **presentation simulation complete** separately from **live integration
complete**. A mock rehearsal must never satisfy the live definition of done.

### Ownership of the revised scope

| Work | Owner | Gate |
|---|---|---|
| Agent marketplace, hire state, reputation/count display | Francesco, F4/F5 | Two demo listings; only genuinely registered/funded agents can execute live |
| Demo business onboarding, simulated KYB, endpoint configuration/adapter | Francesco, F4/F5 | One real endpoint connection is enough; no real automated KYB |
| Flat/percentage service-fee settings, cost breakdown and frozen receipt | Francesco, F4/F5 | Simulated settlement until Jaydon supplies payment authorization/settlement |
| ERC-8004 registry deployment and agent registration | Francesco, F3 | Funded maker, correct network and verified deployment/owner |
| Buyer screens, wallet integration and claim evidence display | Francesco, F5-F7 | Calls Jaydon's wallet/payment APIs; does not implement them |
| Wallet/Privy adapter, fee transfers, reserves, refund amounts and contracts | Jaydon, J2/J5-J7 | Coordinate before changing pricing, ABI or signing payloads |
| Shopper identity, quote/fee authorization, getters and claim correlation | Both, F2/J1 | Explicit agreement before live execution |

### Fees and coverage - keep these distinct

- **Agent service fee:** business-selected flat USD amount or basis-point
  percentage of the item subtotal, excluding shipping, tax and other fees. Convert
  using integer cents with round-half-up; show the basis and amount. Higher
  reputation may support a premium, but never forces a higher price.
- **CoverMe protection fee:** separate risk/platform fee. The existing Bond
  `feeBps` formula rises as reputation falls and charges the maker's deposit to
  Treasury. It is not provider revenue or a buyer charge. Keep that payer in the
  live UI unless Jaydon explicitly changes the contract design.
- Snapshot selected agent/provider, fee model/rate, item amount, shipping, tax,
  buyer-paid fees, buyer total and refundable total before authorization. Later
  provider fee changes affect only new purchases. Do not silently add fees to
  the existing EIP-712 request or charge unbound fees in live mode.
- **Target full refund:** actual item charge, shipping, tax and all buyer-paid
  service/protection fees for a covered agent error, capped at the approved total.
  The current draft Bond reserves/refunds `chargeUsdc` only; J3 defines that as
  item + shipping + tax, not extra agent/platform fees. Until Jaydon confirms
  that it covers the whole buyer-paid total, label the supported live amount
  precisely; do not promise broader coverage. Nonzero provider-fee settlement and
  all-in refunds are simulated until agreed and implemented. An interim live
  demo may use a zero service fee and supported refund scope with disclosure.
- Reserve the full supported refund exposure from prefunded provider collateral,
  plus separate maker-paid protection-fee headroom, before purchase. Refuse if
  coverage is insufficient; do not rely on collecting a debt after the mistake.
- A successful checkout is not a final positive score: finalize once after the
  claim window closes or the claim resolves, then release the reserve. Block
  withdrawal of reserved funds. Display zero-history agents as **Unrated**, even
  if the contract's technical default score is 100.
- Covered MVP errors are objective differences in recorded colour, size or
  model against the approved order. Recorded merchant differences may also be
  displayed where the agreed claim interface supports them. Physical delivery
  defects, courier delays, dissatisfaction and global-cheapest claims are out
  of scope. Exact-label comparison remains a disclosed limitation.
- Known wrong variants should stop before payment. Only an explicit, visibly
  labelled injected-failure rehearsal may exercise the wrong-item refund path.
  Never weaken signature, budget, shop, destination or collateral checks.
- Obtain legal assessment before launching real purchase protection; changing
  the marketing label from insurance to guarantee does not decide regulation.

### Wallet/network handover - supplied snapshot, not verified deployment

Network: **Ink Sepolia**, chain **763373**.
RPC: `https://rpc-gel-sepolia.inkonchain.com`.
Explorer: `https://explorer-sepolia.inkonchain.com`.

| Role | Public address | Purpose / credential reference |
|---|---|---|
| Ana, Kwal owner | `0x3aDe6336e45c37a41193aEcb9b02315eA59268d0` | Existing Kwal account/vault owner; user's own wallet |
| Ana, Privy shopper | **Not created yet** | Checkpoint depositor/shopper, purchase signer and claimant; `ANA_PRIVATE_KEY` only if later exported for local test tooling |
| Maker | `0x5DaF7ba2C06d5c9511a67e158F590c11ed3B1794` | Intended ERC-8004 owner, Bond depositor, J4 deployer; `MAKER_PRIVATE_KEY` |
| Service | `0x0A971d41E186D266f78551e319716d5a815a3cAa` | Calls release/confirm; `SERVICE_PRIVATE_KEY` |
| Judge | `0x0E295F2e243Ad7c5b0749B891aaC811a9F17f078` | Optional A3 resolveClaim role; `JUDGE_PRIVATE_KEY` |
| Maker2 | `0x9774e64e62BB9922Dc3Ce2fCAfD14bD46b6f41b9` | Optional second live provider; `MAKER2_PRIVATE_KEY` |
| Treasury | `0xfd9d8EDdA04a7BB04017aCB8EF55Af1aF4bC9B07` | Receives CoverMe protection fees; supplied `TREASURY_PRIVATE_KEY` is not needed just to receive |

| Contract / token | Supplied address or status | Next action |
|---|---|---|
| Ana's Kwal vault | `0x2dF401bA23216Bc593D052697893554B55Eda0fb` | Existing destination; Jaydon verifies funding/ownership behaviour |
| Circle USDC, 6 decimals | `0xFabab97dCE620294D2B0b0e46C68964e326300Ac` | Supplied token address; verify code/decimals and Kwal match before use |
| Checkpoint | **Not deployed** | Jaydon J6 |
| Bond | **Not deployed** | Jaydon J6 |
| Identity registry proxy | `0x5fE095dA5C7Bd3E80E28e59F1e43D250D3e7B620` | Deployed; version 2.0.0, ABI recorded |
| Reputation registry proxy | `0x891513a8C901916D57833201bC2720a63E349a60` | Deployed; version 2.0.0, ABI recorded |

The registries were deployed on Ink Sepolia as ordinary UUPS proxies from the
pinned upstream contracts, not at the upstream vanity addresses. The supplied
funded Ana/Kwal-owner test signer is upgrade admin for both proxies. Identity
implementation: `0x889a495F911c509Fe1a163073Fa4Dc6C7BAe57b7`;
Reputation implementation: `0xbBCc07cbd9BE6d7a33DD212B5113721fba44AA1C`.
Reputation points to the Identity proxy. Seven deployment/upgrade transactions
all succeeded, and the deployment file records proxy addresses only. This is
acceptable for the presentation testnet; production ownership needs a multisig
or governance decision. Agent `0` was registered at the public main-branch
metadata URL by the funded deployer and immediately transferred to Maker because
its signer was unavailable locally. `ownerOf(0)` now returns
`0x5DaF7ba2C06d5c9511a67e158F590c11ed3B1794`. Transfer correctly cleared the
optional `agentWallet` metadata, which remains unset until Maker proves control.

Reported balances at the last check (stale until rechecked): Kwal owner
0.01 ETH / 0 USDC; vault 60 USDC; Maker empty with 20 faucet USDC expected;
all other listed wallets empty. Faucet arrival is not guaranteed. A 20-USDC
maker deposit cannot cover a real $49.99 charge plus fees; sandbox charges may
differ. The vault's 60 USDC is neither maker collateral nor a Checkpoint deposit.

**Two Ana identities are a new F2/J1 blocker.** `ANA_ADDRESS` must be the actual
Checkpoint shopper/signing wallet, not automatically the Kwal owner's address.
`ANA_KWAL_OWNER_ADDRESS` denotes the existing Kwal identity; `ANA_VAULT_ADDRESS`
denotes its vault. Agree whether the service can fund that vault on behalf of the
Privy shopper, where refunds go (the authorized shopper), and how purchase IDs
map to the same beneficiary. Jaydon must verify the J4 funding handover before
deploying contracts with fixed addresses. Do not invent the Privy address or
export keys merely to make browser signing work. If Privy integration is not
ready, use the existing browser wallet only after both owners agree the simpler
single-shopper configuration.

Keep keys and credentials outside git and browser bundles. Public addresses may
appear here. Update `deployments/ink-sepolia.json` only after verification and
within ownership: Francesco writes `registries`; Jaydon writes `cover`, including
USDC/address/ABI. Leave undeployed addresses null. This document does not itself
update environment files, deploy contracts or transfer funds.

## 2. Scope and ownership

### Francesco may edit

- `contracts/lib/erc-8004-contracts/`
- The `registries` section of `deployments/ink-sepolia.json`
- `service/main.py`
- `service/agent.py`
- `service/runner.py`
- `service/fake_payments.py`
- Other new files directly under `service/`, such as models and an in-memory
  store
- All of `app/` except `app/lib/wallet.ts`
- Francesco-owned tests
- `service/requirements.txt` only for Francesco's backend dependencies such as
  the OpenAI SDK

### Do not edit

- `contracts/src/`, `contracts/test/`, or `contracts/script/`
- `service/guard/`
- `service/payments/`
- `service/fixtures/`
- `app/lib/wallet.ts`
- `scripts/`
- `docs/DEMO_SCRIPT.md`
- The `cover` section of `deployments/ink-sepolia.json`
- Existing files inside the ERC-8004 submodule unless a deployment-only config
  change is strictly required; do not change reference contract source

If an interface supplied by Jaydon is missing, keep a local fake with the same
public shape. Do not rewrite his module.

To avoid dependency-lock conflicts, do not add frontend packages for the MVP.
Use React, Next.js, Tailwind and browser APIs already installed in `app/`.

## 3. Keep the architecture simple

Use:

- Next.js 16 App Router, React 19 and TypeScript in `app/`
- Tailwind CSS v4 and project CSS tokens for styling
- FastAPI in `service/`
- Server-sent events for the live ledger
- OpenAI Python SDK for the shopping agent
- Jaydon's `app/lib/wallet.ts` as the only browser wallet/contract adapter
- Jaydon's `service.guard` and `service.payments` as integration boundaries
- A small in-memory Python store for purchases and events
- A small server-owned provider/agent catalogue with per-provider endpoint and
  fee settings; no marketplace service or generalized plugin framework

Do **not** add:

- Authentication
- An ORM
- Redux, Zustand or another global state package
- WebSockets
- A queue system
- Microservices
- A second API layer in Next.js
- A custom component library
- Supabase before the core demo works
- Automated KYB, live Amazon checkout, broad web search or vendor-return APIs
- Privy SDK/authentication as an uncoordinated addition: Jaydon owns the wallet
  adapter; agree its requirements before introducing a new dependency

### Supabase decision

Supabase is not required for the presentation MVP. The demo uses one service
process and can keep purchases/events in memory.

Only add Supabase after the main flow works twice, and only if the deployed
FastAPI service must preserve receipts across restarts. If added, use it only
for `purchases` and `events`, access it from FastAPI with server-only secrets,
and keep the same store interface. Do not add Supabase Auth, Realtime, Storage,
Edge Functions or browser-side database access.

## 4. Rules for the implementation agent

1. Revalidate the existing mock foundation, then work through the remaining
   changes in order. Record a live blocker explicitly and continue simulation
   work without pretending the blocked phase is complete.
2. Before editing Next.js code, read `app/AGENTS.md` and the relevant guides in
   `app/node_modules/next/dist/docs/`.
3. Load and apply the `design-taste-frontend` skill before building the UI.
4. Keep pages as Server Components unless they need state, event handlers,
   wallet APIs or `EventSource`; isolate those parts in small Client Components.
5. Use Node 22 and npm 10. The app records `npm@10.9.9`.
6. Do not change an agreed interface to make local code easier.
7. Never place private keys, OpenAI keys or Supabase secret keys in `app/` or a
   `NEXT_PUBLIC_*` variable.
8. Make mock, replay and live modes visibly different. Never show fake data as
   a real transaction.
9. Prefer deterministic demo behavior over generality.
10. After each phase, run the listed validation before moving on.
11. Keep mock-only setup/reset/failure/claim controls behind `/demo` and disabled
    in live mode. Do not expose unauthenticated provider administration in live
    mode; one preconfigured trusted provider is sufficient.

## 5. MVP modes

The same UI must support two modes.

### Mock mode

- Enabled explicitly with `PAYMENTS_MODE=fake` (the local demo default). An
  explicit live request must never silently fall back to fake mode.
- Uses `service/fake_payments.py`.
- Emits the exact event schema from `shared/INTERFACES.md`.
- Shows a persistent **Demo simulation** badge.
- Used to build and test the UI without waiting for Jaydon.
- Simulated KYB, scores/history, collateral, provider earnings and refunds are
  each labelled. A real agent endpoint does not make simulated payments live.
- Provide browser setup/claim/reset controls, plus an explicit injected-failure
  control. Run the ordinary matching-purchase path with injection off.

### Live mode

- Enabled with `PAYMENTS_MODE=live`.
- Imports `service.payments` and `service.guard`.
- Uses real transaction hashes and Kwal payment IDs.
- Shows **Ink Sepolia live**.
- Fails clearly if deployments or required environment values are missing.
- Requires confirmed shopper identity/funding and verified reserve/refund scope.
- Only genuinely registered and funded agents can execute; demo comparison
  listings cannot borrow the live agent's ID, deposit or score.
- Agent service-fee transfer and wider coverage remain unavailable unless the
  agreed authorization/settlement interface has been implemented and validated.

Do not fork the UI by mode. Only the service adapter and visible mode label
should differ.

## 6. Shared data shapes

Create Python Pydantic models and matching TypeScript types for these shapes.
Keep names in `snake_case` over the API.

### Provider, agent listing and authorized pricing snapshot

Add only Francesco-owned models; these do not modify the shared signing schema.

- Provider: internal ID, business name, `kyb_status` (`demo_verified` or
  `not_verified`), agent configuration, flat fee in cents or percentage in bps.
- Server-only connection: trusted `base_url`, model and API-key environment
  reference. Never return a stored key in a listing or receipt.
- Agent listing: internal listing ID, provider ID/name, optional real ERC-8004
  ID, score and finalized-outcome count, fee model/rate, coverage limit,
  connection status, and independent simulation labels for identity/history,
  KYB and money. **Unrated** when count is zero.
- Draft/quote metadata: opaque server-issued `quote_id`, selected listing ID,
  frozen requested attributes, fee basis/rate, item/shipping/tax charges, buyer-paid
  fee amounts, buyer total and supported refundable total. No browser authority
  over provider fees, score, funding destination or coverage capacity.
- Purchase/receipt: retain existing fields and add the frozen provider/pricing
  snapshot plus supported `refund_amount_usdc`, simulation status and merchant
  recovery status. Use actual 6-decimal charges for money movement, not listed
  USD prices when sandbox pricing differs.

Use the existing signed `agentId` for live identity binding. Changing the selected
agent invalidates an unsigned draft; never silently replace an agent after
approval. Agree binding of `quote_id` and nonzero service fees in F2 before live
use. A quote ID alone is not buyer authorization: reject tampered/mismatched
quote/request pairs, and do not charge a fee that the signed payload does not
authorize. Simulation may demonstrate the proposed approval with a clear
non-cryptographic marker. The existing live request stays unchanged meanwhile.
The proposed opaque draft `quote_id` is distinct from Kwal's external quote ID;
store their association explicitly. A live approved snapshot must reuse its
actual unexpired Kwal quote, or require a new review/authorization if repriced.

### Event

Use the exact event shape from `shared/INTERFACES.md`:

```json
{
  "purchase_id": 3,
  "step": "checked",
  "status": "ok",
  "tx_hash": null,
  "kwal_payment_id": null,
  "detail": "Request passed all limits",
  "ts": "2026-10-09T19:12:03.120Z"
}
```

Allowed steps:

`checked`, `refused`, `needs_approval`, `released`, `fee_taken`, `funded`,
`paid`, `confirmed`, `claimed`, `refunded`, `rejected`, `needs_review`,
`score_written`.

### Request draft

```json
{
  "shopper": "0x...",
  "agentId": "1",
  "shop": "twelvesouth.com",
  "item": "PowerBug 25W (Qi2.2)",
  "colour": "black",
  "size": "",
  "model": "",
  "maxUsdCents": 6000,
  "addressHash": "0x...",
  "nonce": "1",
  "deadline": "1760000000"
}
```

The frontend must normalize `shop`, `colour`, `size` and `model` to lowercase
before asking `wallet.ts` to sign.

### Purchase

The service may use a simple purchase object:

```json
{
  "id": 3,
  "agent_id": "1",
  "status": "confirmed",
  "asked": {
    "shop": "twelvesouth.com",
    "item": "PowerBug 25W (Qi2.2)",
    "colour": "black",
    "size": "",
    "model": "",
    "image_url": null
  },
  "bought": {
    "shop": "twelvesouth.com",
    "item": "PowerBug 25W (Qi2.2)",
    "colour": "white/dune",
    "size": "",
    "model": "",
    "image_url": null
  },
  "listed_usd_cents": 4999,
  "charge_usdc": 49990000,
  "sandbox_pricing": false,
  "tx_hash": "0x...",
  "kwal_payment_id": "..."
}
```

For sandbox pricing, display both the listed amount and actual USDC charge.

### Verified merchants from the supplied Reap spreadsheet

These entries were checked directly in
`Reap - List of Supported Merchant.xlsx`:

| Spreadsheet row | Merchant | Test product | Price | Ships to SG? | MVP use |
|---:|---|---|---:|:---:|---|
| 75 | `keychron.com` | Keychron B40 Wireless Keyboard - Deep Black | $49.99 USD | Yes | Correct purchase |
| 144 | `twelvesouth.com` | PowerBug 25W (Qi2.2) - White/Dune | $49.99 USD | Yes | Wrong-item purchase |
| 55 | `gmktec.com` | GMKtec EVO-X5 Pro, 192GB + 2TB / US | $6,599 USD | Yes | Refusal beat |
| 118 | `satechi.net` | USB-C Snap Hub - Citrus | $44.99 USD | Yes | Optional/rehearsal only |
| 153 | `zmdesktop.com` | Modular Space-Saving Laptop Stand - Black Walnut | $58 USD | Yes | Optional score-limit beat |
| 59 | `gymshark.com` | Gymshark Power T-Shirt - Chalk Marl - Medium | $36 USD | **No, US only** | Do not use with Ana's SG address |

Important limitations:

- The spreadsheet verifies the White/Dune PowerBug product, not a black
  PowerBug variant. Asking for black must normally return unavailable/refuse
  rather than quietly ordering White/Dune. The mismatch purchase exists only
  in the explicitly injected-failure rehearsal.
- Do not depend on Gymshark for a Singapore rehearsal or presentation purchase.
- Use the spreadsheet variant IDs in deterministic fake mode. In live mode,
  let Jaydon's Kwal catalogue adapter confirm the current product/variant.

Do not add Amazon purchasing for this presentation. Keep the supported products
for simulation; for live success prefer the recorded HMX/Divinikey route after
Jaydon confirms current availability and the actual saved address. Keychron and
PowerBug remain the existing simulation fixtures, not proven live catalogue
matches. A black-umbrella catalogue is an optional simulation-only
reskin after the core flow works, not another merchant integration.
If shown, say **lowest total price among eligible results**, not globally
cheapest. Tomorrow-delivery promises are out of this live MVP; a future mandate
needs destination, timezone, absolute delivery deadline, shipping cost and quote
evidence before it can support that promise.

## 7. Phase F1 - acknowledge the existing scaffold

F1 is already complete. Do not recreate the projects.

Resume the existing F4-F7 mock implementation as well; do not overwrite it.
Confirm the baseline and record pre-existing failures:

```bash
python -m pytest -q
npm --prefix app run lint
npm --prefix app run typecheck
npm --prefix app run build
forge build --root contracts
```

Do not replace package managers, regenerate the app or restructure the repo.

## 8. Phase F2 - freeze integration interfaces

Read:

- `shared/INTERFACES.md`
- `shared/purchase-request.json`
- `deployments/ink-sepolia.json`

Agree with Jaydon on only the values required by the UI:

- Stable refusal names for amount, monthly limit, shop and address
- Whether pre-release events have a temporary purchase ID
- Exact purchase response fields
- Exact Bond getter names needed by the maker panel
- Exact `wallet.ts` call signatures
- J3 merchant-name representation, new ShipTo fields/canonical keccak hash,
  same-process variant resolution and actual quote subtotal/shipping/tax total
- Privy shopper address versus Kwal owner/vault, refund beneficiary and the J4
  second-wallet/contract funding result; decide the wallet route before deployment
- Supported live refundable total, shipping/fee treatment, maker-paid protection
  fee and full-reserve headroom; do not assume `chargeUsdc` includes extra fees
- Provider-fee recipient, flat/percentage basis (excluding shipping/tax), rounding
  and snapshot expiry;
  how selected agent, quote and fees are authorized and settled (or explicitly
  disabled with zero fee for the interim live demo)
- How to exercise an injected wrong-item failure without disabling existing
  controls; simulation-only unless both owners approve a supported live test
- Local purchase ID to onchain purchase ID mapping, wallet-claim event ingestion,
  final outcome/claim-window timing and exactly one reputation write

Do not redesign the interfaces unilaterally. Keep proposed marketplace/pricing
metadata in Francesco's code until live signing/settlement changes are agreed.
Record unresolved items as blockers, not defaults inferred from a demo.

**Done when:** both branches use the same request/event/purchase shapes and the
live identity, refund and fee gates above have explicit decisions. Simulation
can continue while these decisions are pending.

## 9. Phase F3 - ERC-8004 registry and agent

Files:

- `contracts/lib/erc-8004-contracts/`
- `deployments/ink-sepolia.json`
- `app/public/agent.json` for the public registration metadata

Current deployment status: registry deployment, metadata, agent registration,
Maker ownership and deployment-registry recording are complete. The optional
agent-wallet metadata proof remains follow-up work.

Steps:

1. Registry deployment and initial registration used the funded Ana/Kwal-owner
   test signer. Maker ownership was established by ERC-721 transfer. Before any
   Maker-only follow-up, verify its signer and test ETH. Never print or commit keys.
2. Reuse the existing reference project's Hardhat toolchain and compile result;
   install/compile if needed. Keep the reference source unchanged.
3. Deploy only the Identity and Reputation registries to Ink Sepolia using the
   simplest existing upstream deployment route. **Complete:** ordinary UUPS
   proxies were used because the vanity bootstrap hardcodes an owner unavailable
   to this project; pinned implementation source remained unchanged.
4. Record the deployed proxy addresses immediately. **Complete** in
   `deployments/ink-sepolia.json`; never replace them with implementation addresses.
5. Update the existing `app/public/agent.json` containing:
   - name: the connected demo provider's agent name
   - description: `An agent backed by Cover`
   - network: `Ink Sepolia`
   - Bond address if it is already known, otherwise omit it for the MVP
6. Intended route: Maker calls `register(agentURI)`. **Completed with a documented
   deviation:** the funded deployer registered agent `0` and transferred it to
   Maker because the Maker signer was unavailable. Ownership is correct;
   `agentWallet` metadata was cleared by transfer and is not presented as set.
7. Read the `Registered` event and record the agent ID.
8. Update only `deployments/ink-sepolia.json -> registries`:
   - Identity `{ address, abi }`
   - Reputation `{ address, abi }`
   - `agentId` as a decimal string. **Complete:** `agentId` is `"0"`.
9. Push that change so Jaydon can deploy Bond and Checkpoint against it.

One live registered agent is enough for this demo. The second comparison listing
may remain simulated and non-executable in live mode. Register/fund Maker2 only
if time remains and Jaydon agrees; two onchain providers are not a prerequisite
for the marketplace UI.

Use proxy addresses if the selected upstream deployment uses proxies. Do not
copy implementation addresses into the deployment registry.

Do not commit build artifacts, deployment caches or source edits from inside
the ERC-8004 submodule. The expected repository changes from F3 are the
`registries` JSON section and `app/public/agent.json` only.

Validation:

```bash
cast code <IDENTITY_ADDRESS> --rpc-url "$INK_RPC"
cast code <REPUTATION_ADDRESS> --rpc-url "$INK_RPC"
cast call <IDENTITY_ADDRESS> "owner()(address)" --rpc-url "$INK_RPC"
cast call <REPUTATION_ADDRESS> "getIdentityRegistry()(address)" --rpc-url "$INK_RPC"
cast call <IDENTITY_ADDRESS> "ownerOf(uint256)(address)" <AGENT_ID> --rpc-url "$INK_RPC"
```

**Done when:** `ownerOf(agentId)` returns the maker address and Jaydon has the
registry addresses and agent ID.

## 10. Phase F4A - service foundation and fake payment stream

Extend the existing files rather than recreating them:

- `service/models.py`
- `service/store.py`
- `service/fake_payments.py`
- `service/providers.py` (small trusted demo provider/listing configuration)
- Tests under `service/tests/`

### `service/models.py`

Define only the API models needed for:

- Event
- RequestDraft
- ChatRequest and ChatResponse
- SignedPurchaseRequest
- AskedItem and BoughtItem
- Purchase
- Provider / AgentListing
- PricingSnapshot / draft quote metadata

Use Pydantic validation. Keep the enum values equal to the interface strings.

### `service/store.py`

Implement a small process-local store:

- `purchases: dict[int, Purchase]`
- `events: list[Event]`
- Monotonic purchase ID counter
- `asyncio.Queue` per connected SSE subscriber
- `add_purchase()`
- `get_purchase()`
- `append_event()` that stores and broadcasts
- `subscribe()` / `unsubscribe()`
- Frozen draft/quote snapshots keyed by opaque quote ID, bound to the selected
  agent, shopper and approved request; an in-memory implementation is sufficient
- Per-demo-agent collateral, reserved amounts, fees/earnings and finalized scores;
  never debit one provider's deposit or score a different agent for this purchase

Keep at most the latest 200 events. No database abstraction beyond one small
class is needed.

### `service/fake_payments.py`

Implement the public payment shapes expected by the runner. For a normal fake
purchase, emit on short timers:

1. `checked`
2. `released`
3. `fee_taken`
4. `funded`
5. `paid`
6. `confirmed`

Use deterministic IDs such as `0xmock...` and `kwal_mock_...`, but set a flag or
label so the UI cannot mistake them for live values.

Add deterministic demo catalogue results:

- `Keychron B40` -> correct item, $49.99
- `PowerBug 25W`, requested black -> unavailable/refused by default; an explicit
  injected-failure setting chooses `white/dune`, $49.99, to exercise the claim
- `GMKtec` -> refused with amount, shop and address failures

Simulate full buyer-total refunds and provider service-fee earnings separately
from the maker-paid CoverMe protection fee. Keep reserve/fee headroom checks,
prevent duplicate refunds and release successful reserves only after the claim
window/final outcome. Reuse existing browser-only demo limits/claims/reset
endpoints and extend reset to restore provider settings, pricing snapshots and
per-agent balances. Do not emit a real-looking live fee transfer for a quote.

**Done when:** tests prove event order, purchase lookup, multi-subscriber SSE,
per-agent financial isolation, fee math and the normal-versus-injected-failure
distinction. The existing mock flow still passes.

## 11. Phase F4B - shopping agent

Files: `service/agent.py`, `service/providers.py`.

First configure one pre-onboarded business and two comparison listings. The
provider setup screen shows business identity, **Demo KYB - simulated**, agent
name, endpoint/model connection status, flat/percentage fee setting and collateral.
No real KYB checks, automated business verification or production onboarding API.

Connect one real trusted endpoint if credentials are supplied. Use a server-owned
endpoint/model/key reference; buyers cannot submit arbitrary endpoints or keys.
Use the installed OpenAI Python SDK with a configured `base_url` and the supported
Chat Completions API (`chat.completions.create`). Do not assume an
OpenAI-compatible endpoint implements Responses API, `responses.parse`, strict
JSON schemas or tool calling. For this demo, document a minimum contract:
stateless messages in, one structured product selection/draft out, validated by
Pydantic against the supported catalogue. Check any optional JSON/tool support
with the selected endpoint before relying on it. A timeout, invalid selection or
connection failure stops drafting; there is no silent substitution of another
agent. Reference: https://github.com/openai/openai-python#usage and its custom
client/base-URL configuration.

Reuse the small agent with two conceptual tools, routing to the hired listing:

1. `find_item(query)`
2. `covered_purchase(variant_id)`

For the MVP, `POST /chat` must stop before purchase and return a request draft.
The signed request is submitted separately through `POST /requests`.

Required behavior:

- `Get me the Keychron B40` returns a draft for the Keychron B40.
- `Buy the black PowerBug 25W, under $60` returns a draft asking for black with
  `maxUsdCents = 6000`.
- Preserve the requested black. Normally the absence of a black PowerBug variant
  prevents payment. Only the explicit injected-failure rehearsal later selects
  White/Dune; show that status before the demonstration starts. Do not bake
  always-buy-the-wrong-variant behaviour into a provider's normal system prompt.
- Non-purchase chat gets a short normal reply and no draft.
- Drafts retain the hired listing's provider/agent identity; the buyer cannot
  change providers or pricing after authorization.

Keep the agent stateless. Send only the current user message and a compact
system prompt. Do not build conversation memory, retrieval or an agent
framework.

If the selected demo provider has no endpoint/key in fake mode, reuse the
deterministic parser for only the three demo cases above. The UI must show
**Scripted demo agent**. Distinguish **Endpoint connected** from KYB, reputation
and payment verification; an OpenAI-compatible endpoint proves none of those.

**Done when:** tests cover the two shopping prompts, non-purchase chat, hired
agent routing, connection/validation failures and scripted fallback labels
without making a live OpenAI call. Demonstrate one connection test separately
when credentials are available.

## 12. Phase F4C - runner

File: `service/runner.py`

Implement one orchestration function for a signed request:

0. Resolve the server-issued quote/draft and selected agent; verify request/agent
   binding and frozen pricing. Apply the agreed F2 fee authorization gate.
1. Verify the request with `guard.verify_request`.
2. Fill shipping data only from `ANA_SHIP_TO_JSON`.
3. In live mode resolve the selected product/options/variant through the J3
   client and use the actual unexpired quote bound to approval. In fake mode
   retain the deterministic catalogue. Do not blindly call live `quote` with a
   spreadsheet variant ID or reprice a frozen approval.
4. Read limits and run `guard.check_rules`.
5. Run `guard.spend_ceiling_cents`.
6. Run `payments.check` for the onchain preflight.
7. If failures exist, emit one `refused` event listing all failure names and
   stop before payment.
8. Otherwise consume `payments.pay(...)` and forward every event to the store.
9. Update the purchase after each meaningful event.

Before payment, verify available coverage against the entire supported refundable
exposure and maker-paid protection-fee headroom. Reject known variant mismatch
with injection off. Injection is a separate demo setting, never a buyer-supplied
override and never a bypass for existing guard rules. Bind refund/reputation
updates to the same provider/agent and the actual onchain purchase ID. Route the
funding to the configured Kwal vault without treating its owner as the shopper.

Select the adapter once from `PAYMENTS_MODE`; do not scatter mode checks through
the function.

The request route should start the runner with `asyncio.create_task` and return
the allocated purchase ID immediately. The UI then follows progress over SSE.

**Done when:** both fake successful purchases and the three-rule refusal run
through this single function.

## 13. Phase F4D - FastAPI routes

File: `service/main.py`

Keep the existing health/chat/request/purchase/SSE and mock rehearsal routes.
Add only small Francesco-owned catalogue/draft extensions:

- `GET /agents`: public comparison data, no keys or server connection secrets.
- `POST /chat`: selected internal listing ID plus message; return draft, opaque
  quote ID and frozen cost/coverage metadata. The service resolves any ERC-8004
  ID; buyer selection never supplies authoritative provider funding/pricing.
- `POST /requests`: proposed additive quote ID plus existing request/signature;
  agree this extension and live fee authorization at F2. Existing signed fields
  stay unchanged until coordinated. Reject unknown/expired/mismatched snapshots.
- `/demo/providers` and `/demo/failure-mode`: mock-only configuration controls for
  simulated KYB, fee settings and injected-failure rehearsal. Credentials come
  from server environment/config, not browser responses. In live mode providers
  are preconfigured; mutating demo routes return unavailable.

### `POST /chat`

Input:

```json
{ "agent_listing_id": "demo-provider-agent-1", "message": "Buy the black PowerBug 25W, under $60" }
```

Output:

```json
{
  "message": "I found the PowerBug and prepared a request for you to review.",
  "quote_id": "opaque-server-issued-draft-id",
  "agent_listing_id": "demo-provider-agent-1",
  "pricing": { "...": "frozen cost breakdown and supported refundable total" },
  "request_draft": { "...": "..." },
  "mode": "openai"
}
```

### `POST /requests`

Accept the existing `{ request, signature }` plus the proposed `quote_id`
extension after F2 agreement. Validate the snapshot, allocate a purchase, start
the runner and return `{ purchase_id }`. Nonzero live service fees remain
disabled until separately bound to buyer authorization and settled by Jaydon.

### `GET /events`

Return `text/event-stream`. Each message uses:

```text
event: purchase
data: {json event}

```

Send a comment heartbeat every 15 seconds. Unsubscribe the queue when the
client disconnects.

### `GET /purchases/{id}`

Return the receipt object or 404.

Do not implement `/claims/vague` or `/approvals` in the main MVP.

Tests:

- Health returns 200.
- Chat returns a request draft for both demo products.
- Signed request returns a purchase ID.
- Unknown purchase returns 404.
- Refused request emits all three failures.
- Agent listings expose reputation/count, fee and coverage labels without keys.
- Selected agent and quote match the authorized request; tampering is rejected.
- Changed provider fees leave existing purchase/quote snapshots unchanged.
- Demo provider/reset/failure/claim routes cannot execute in live mode.

**Done when:** the complete fake flow can be driven with HTTP requests only.

## 14. Phase F5A - frontend design system

Before writing UI code, load `design-taste-frontend`.

Use this design read:

> A trust-first shopping-agent marketplace: compare the business, track record,
> fee and coverage, hire an agent, then see an accountable refund when it fails.
> Keep the provider view and evidence ledger secondary to the buyer's journey.

Recommended dials:

- `DESIGN_VARIANCE: 4`
- `MOTION_INTENSITY: 4`
- `VISUAL_DENSITY: 6`

Use the visual language already present in `COVER_PLAN.html`:

- Off-white / dark green neutral base
- One green accent
- Amber for waiting/warnings
- Red only for refusal or mismatch
- Archivo for display text
- Atkinson Hyperlegible for body text
- IBM Plex Mono for hashes, IDs and amounts

Use `next/font`; do not load Google Fonts with `<link>` tags.

Design rules:

- Build one 1080p-friendly demo workspace.
- Agent comparison and **Hire agent** are the entry point, not the maker metrics.
- Ana is the primary panel on the left.
- Provider setup/cover status is a secondary panel or dedicated maker view.
- The compact ledger spans the bottom and can be expanded for technical evidence.
- Use borders and spacing for hierarchy, not a wall of floating cards.
- Keep one radius system.
- Every button needs hover, focus, active, disabled and loading states.
- Every async section needs loading, empty and error states.
- Use only short transform/opacity transitions.
- Respect `prefers-reduced-motion`.
- No gradients, glassmorphism, neon glow, giant hero, decorative dashboard chart
  or fake precision.
- The receipt must remain understandable with the sound off.

## 15. Phase F5B - frontend file structure

Suggested structure:

```text
app/
  app/
    page.tsx                 # agent selection -> combined recording workspace
    ana/page.tsx             # shopper-only view, reuses AnaPanel
    maker/page.tsx           # maker-only view, reuses MakerPanel
  components/
    demo-workspace.tsx       # client coordinator
    agent-marketplace.tsx
    provider-setup.tsx        # demo KYB, endpoint status and service-fee settings
    cost-breakdown.tsx
    ana-panel.tsx
    limits-form.tsx
    chat-panel.tsx
    request-sign-card.tsx
    purchase-progress.tsx
    receipt.tsx
    maker-panel.tsx
    ledger.tsx
    mode-badge.tsx
  lib/
    api.ts
    types.ts
    format.ts
    wallet.ts                # Jaydon-owned; import, do not replace
```

Do not introduce a component package. Use semantic HTML and Tailwind/CSS.

State can live in `demo-workspace.tsx` using `useState` and `useReducer`:

- Connected account
- Selected agent listing/provider
- Draft quote ID and frozen pricing/coverage snapshot
- Explicit injected-failure demo state
- Limits transaction state
- Chat messages
- Current request draft
- Current purchase ID
- Purchases by ID
- Event list
- Maker metrics
- Claim stopwatch state

No global state library is needed.

## 16. Phase F5C - API and SSE client

In `app/lib/api.ts`:

- Read `NEXT_PUBLIC_SERVICE_URL`.
- Implement typed helpers for `/agents`, `/chat`, `/requests`, `/purchases/{id}`
  and the existing mock controls; keep the proposed quote extension gated by F2.
- Throw readable errors for non-2xx responses.
- Never put secrets in this module.

In the client workspace:

1. Create one `EventSource` for `/events` in `useEffect`.
2. Parse `purchase` events.
3. Deduplicate by a stable event key made from purchase ID, step, timestamp and
   transaction hash.
4. Append ledger rows.
5. Update the current purchase progress.
6. Fetch the receipt after `confirmed`, `refunded` or `rejected`.
7. Close `EventSource` during cleanup.
8. Show disconnected/reconnecting state without clearing prior events.

## 17. Phase F5D - Ana panel

Implement these blocks in order.

### Agent marketplace and hire state

- Show two comparison listings with provider name, reputation + finalized
  purchase count, flat/percentage service fee, supported coverage limit and
  separate verification/simulation labels. Zero history reads **Unrated**.
- **Hire agent** selects the listing before chat; show its identity in chat,
  request review, progress and receipt. Changing selection clears unsigned drafts.
- Two simulated listings are enough initially. In live mode allow checkout only
  for registered, connected, funded agents; a demo listing is comparison-only.
- Hide setup complexity from the buyer. Provider onboarding lives in the maker
  view, with a brief business/connection/fee/deposit summary available for recording.

### Wallet and limits

- Connect wallet button.
- Show the shortened actual shopper address and Ink Sepolia network. For the
  two-wallet route, distinguish it from Kwal owner and vault in technical details.
  Until Privy exists and Jaydon's adapter is ready, live signing is unavailable.
- Inputs with visible labels:
  - Monthly maximum: `$150`
  - Per-item maximum: `$100`
  - Allowed shops: Keychron, Twelve South, Satechi, ZM Desktop, Gymshark
  - Shipping address summary
  - End date: `31 Oct 2026`
- **Set limits** calls `wallet.sendTx("Checkpoint", "setLimits", args)`.
- Buyer-funded Checkpoint deposit is separate from both the existing Kwal vault
  balance and the maker's Bond collateral. Never imply the vault's reported
  60 USDC completes buyer setup.
- USDC approval and deposit may be separate buttons if required by
  `wallet.ts`, but keep them next to limits setup.
- Show pending, confirmed and failed transaction states.

The default merchant/domain choices above are for the existing simulation.
For live HMX use the agreed J3 merchant identifier (currently `divinikey`) and
the real saved address rather than this panel's Singapore demonstration summary.

### Chat

- A simple message list and text input.
- Add three presentation shortcuts:
  - `Get me the Keychron B40`
  - `Buy the black PowerBug 25W, under $60`
  - `Show me today's deal` (secondary refusal beat)
- Shortcuts fill/send normal chat messages; they are not separate backend
  endpoints.

### Request sign card

- Show readable shop, item, colour, max amount and destination summary.
- Show hired agent/provider, item/shipping/tax, buyer-paid service/protection fees,
  buyer total and supported refundable amount. The current maker-paid protection
  fee is disclosed separately and not added to the buyer total.
- State which fees are simulated or unavailable for live settlement. Display
  **Full approved total protected** only if the supported reserve/refund actually
  covers it; otherwise disclose the narrower supported charge.
- Allow Ana to review but not silently edit generated values.
- **Sign request** calls `wallet.signPurchaseRequest(draft)`.
- Submit the agreed request/signature/quote metadata to `/requests`; do not alter
  the shared EIP-712 types or claim that displayed fees are already signed.
- Clear the draft only after the service returns a purchase ID.

### Purchase progress

- Show the sequence `checked -> released -> funded -> paid -> confirmed`.
- Waiting state should be visually distinct from completed state.
- Show transaction hash and Kwal payment ID when present.
- Do not invent either value client-side.

**Done when:** Ana can set limits and sign a request on Ink Sepolia using the
real wallet adapter.

## 18. Phase F5E - maker panel

Poll every 4-5 seconds through `wallet.read`.

Add a compact demo provider setup block before the existing cover metrics:

- Business name and **Demo KYB - simulated** status; no real identity verification.
- Connected agent name, masked endpoint/model summary and connection test state.
- Flat/percentage service-fee controls with a preview of the basis/rounding.
- Changes apply to future drafts only. Credentials remain server-configured.
- Prefunded deposit and supported coverage limit; insufficient-funds state.

Show the required per-agent metrics:

- ERC-8004 agent ID
- Maker deposit
- Reserved cover
- Free cover
- Score average and count
- Agent service-fee rate/model and earnings (simulated until real settlement)
- Separate maker-paid CoverMe protection-fee rate
- Auto-pay limit
- Fees paid to Cover
- Refund loss and **Merchant recovery pending** after a covered failure; neither
  claims a vendor return or recovery transfer has occurred

Requirements:

- Use the registry/deployment JSON for IDs and addresses.
- Show count-zero agents as **Unrated** even if the contract returns 100; never
  reuse one agent's history/collateral for another listing.
- Display skeleton rows while loading.
- Display `Not deployed` if an address or ABI is absent.
- Keep the previous value during a temporary read failure and mark it stale.
- Briefly highlight a number when it changes after a claim.
- Do not calculate authoritative balances in the browser if a contract getter
  exists.
- A confirmed order retains reserved collateral until its claim window closes
  or a final claim outcome. Display provider loss independently of refunded
  buyer-paid fees to avoid double-counting the maker's protection fee.

**Done when:** maker values refresh without reloading the page.

## 19. Phase F6 - swap fake payments for Jaydon's implementation

Do not rewrite the runner. Change only the adapter selected by
`PAYMENTS_MODE=live`.

Integration checklist:

- `service.guard` imports succeed.
- `service.payments` imports succeed.
- Saved shipping address is valid.
- Registry, Bond, Checkpoint and USDC deployments are present.
- Verify USDC is the supplied `0xFabab97dCE620294D2B0b0e46C68964e326300Ac`, has
  6 decimals, and matches Kwal funding; Jaydon owns the `cover` JSON update.
- The request signer equals the agreed Checkpoint shopper (`ANA_ADDRESS`), not
  necessarily the Kwal owner. Privy identity and J4 funding handover are resolved.
- Maker and Service have gas; shopper has required gas/funds or an explicitly
  agreed sponsored-wallet route. Maker collateral covers the actual charged
  refundable exposure plus fees. Funding a vault alone does not satisfy this.
- Maker owns the registered live agent; the hired listing resolves to that ID.
- Service-fee authorization/settlement and supported refund scope are agreed;
  otherwise nonzero service fees remain simulated/unavailable, not live charges.
- Event fields from Jaydon are normalized to the shared Event model.
- Actual `tx_hash` and `kwal_payment_id` reach the UI.
- Payment exceptions become an `error` event and readable UI message.
- Getter reads, local/onchain purchase IDs and wallet-claim event ingestion are
  agreed and implemented. Client simulation cannot synthesize live score/refund.

Run one currently supported purchase from the UI with Jaydon present. Prefer
HMX Snowflake / Divinikey / size 18 set, matching the recorded J3 smoke route,
after resolving current IDs and pricing/address; Keychron is not yet proven live.

**Done when:** one covered purchase completes from chat to confirmation without
using a terminal after startup.

## 20. Phase F7 - the money moment

This phase is mandatory and has priority over every add-on.

### Wrong item claim

For a confirmed PowerBug purchase:

1. Show **Wrong item**.
2. On click, start a visible stopwatch immediately.
3. In live mode call `wallet.sendTx("Bond", "openClaim", [onchainPurchaseId])`
   only after mapping the local receipt to the actual contract purchase ID.
   In fake mode use the existing mock-only claim route, never a wallet transaction.
4. Keep listening to SSE and polling the maker panel.
5. Stop the timer on the `refunded` event.
6. Fetch the final purchase receipt.

Never fake the elapsed value in live mode.

Use the wrong-colour purchase only with the explicit injected-failure rehearsal
label. The normal path refuses a known mismatch. Keep failure injection in mock
mode unless both owners agree a supported live test; this doc does not grant a
guard bypass. A live recording can show live successful payment and a separate
clearly labelled simulated failure/refund if the live failure path is not ready.

### Receipt

Show:

- Asked item on the left
- Bought item on the right
- Product images if present
- Colour swatches and names if images are missing
- A prominent mismatch line: `black != white/dune`
- Listed price
- Actual USDC charge if sandbox pricing differs
- Selected agent/provider, frozen fee breakdown and supported refundable total
- Refund transaction hash
- Actual refunded amount, `Refunded from the provider's deposit in ... s` using
  measured time, and **simulated** when appropriate. Do not display the $49.99
  listed price as an actual refund when a sandbox charge/refund was 1 USDC.
- Provider loss, changed reputation/count and **Merchant recovery pending**
- Covered order-attribute mismatch, not proof that a physical parcel arrived

Animate only the refund state change, not a fake coin flying across the screen.
A short directional transform/fill animation is enough.

### Ledger

Each row shows:

- Time
- Step
- Plain-language detail
- Status
- Short transaction hash when available
- Kwal payment ID when available

Keep the ledger readable at 1080p. New rows may auto-scroll only when the user
is already near the bottom.

### Refusal beat

The `Show me today's deal` message produces the GMKtec attempt. The UI must show
one refusal containing all three reasons:

- Amount
- Shop
- Address

Show `No money moved`. Do not show release/funding/payment events after refusal.

**Done when:** compare/hire, authorized Keychron success and the labelled
injected PowerBug refund all work twice after reset, with per-agent financial
and reputation updates. The secondary GMKtec refusal still passes its tests.
Report simulation and live results separately.

## 21. Phase F8 - optional work only after MVP passes twice

Stop optional work at the agreed feature-freeze time.

Order:

1. **A1 explorer links** - the only recommended presentation add-on. Add an
   Ink explorer link to every real transaction hash and a **Verify it yourself**
   link on the refund receipt.
2. **A3 OpenAI judge** - only if vague claims are still required and the main
   demo is stable.
3. **A3b injection check**.
4. **A2 public terms page**.
5. **A4 MCP server**.
6. **A6 mock shop page**.

For the quick MVP, do not implement A3, A3b, A2, A4 or A6.
Also defer real automated KYB, a second funded live provider, Amazon checkout,
tomorrow-delivery guarantees, arbitrary endpoint onboarding and automated merchant
returns. A second comparison listing and simulated KYB are core UI, not A4.

## 22. Phase F9 - presentation preparation

Use Jaydon's `docs/DEMO_SCRIPT.md` once it exists. Share the revised sequence with
him; do not edit his script without agreement. The sequence below is Francesco's
UI handoff, not a unilateral change to the team deployment/demo commitments.

Before recording:

1. For simulation use the existing browser demo reset. For live rehearsal use
   Jaydon's reset script only after the funding/deployment preflight passes.
2. Start FastAPI in the explicitly chosen mode; do not require live mode for a
   simulated presentation or silently downgrade a failed live startup.
3. Start Next.js.
4. Open the combined workspace at 1920x1080.
5. Connect Ana's agreed shopper wallet for live mode; use labelled simulated
   authorization otherwise.
6. Confirm provider settings, agent listings, scores/counts and available cover
   are consistent and show their real/simulated provenance.
7. Confirm the SSE connection is live.
8. Keep the browser zoom at a level where the ledger is readable.
9. Close unrelated tabs, notifications and wallet history.
10. Perform the full sequence once, reset, then record.

The recording sequence is:

1. Briefly show a pre-onboarded business, demo KYB, endpoint connection, configured
   service fee and coverage deposit (about 20 seconds).
2. Compare two agents by business, reputation/count, price and coverage; hire one.
3. Show the buyer's limits and complete purchase/fee/protection approval.
4. Buy Keychron correctly in simulation, or the confirmed HMX/Divinikey item in
   live mode. Show success; explain collateral remains reserved
   until the final outcome rather than awarding instant reputation.
5. Turn on the labelled injected-failure rehearsal; ask for black PowerBug and
   demonstrate the recorded White/Dune order.
6. Press **Wrong item**. Show refund amount/time/evidence, provider deposit loss,
   changed reputation and **Merchant recovery pending**.
7. If time remains, show the three-rule GMKtec refusal with **No money moved**.

Target under three minutes. If live components are incomplete, record a coherent
labelled simulation rather than mixing mock hashes/balances into an **Ink Sepolia
live** panel. A real endpoint connection may still be shown with simulated money.

## 23. Environment variables

Backend `.env` additions:

```dotenv
PAYMENTS_MODE=fake
INK_RPC=https://rpc-gel-sepolia.inkonchain.com
CHAIN_ID=763373
USDC_ADDRESS=0xFabab97dCE620294D2B0b0e46C68964e326300Ac
ANA_KWAL_OWNER_ADDRESS=0x3aDe6336e45c37a41193aEcb9b02315eA59268d0
ANA_VAULT_ADDRESS=0x2dF401bA23216Bc593D052697893554B55Eda0fb
ANA_ADDRESS=                    # Agreed Checkpoint shopper; Privy not created yet
ANA_ADDRESS_HASH=               # Agreed canonical saved shipping-address hash
ANA_SHIP_TO_JSON=               # J3 ShipTo schema; never agent-supplied
SERVICE_ADDRESS=0x0A971d41E186D266f78551e319716d5a815a3cAa
JUDGE_ADDRESS=0x0E295F2e243Ad7c5b0749B891aaC811a9F17f078
MAKER_ADDRESS=0x5DaF7ba2C06d5c9511a67e158F590c11ed3B1794
MAKER2_ADDRESS=0x9774e64e62BB9922Dc3Ce2fCAfD14bD46b6f41b9
TREASURY_ADDRESS=0xfd9d8EDdA04a7BB04017aCB8EF55Af1aF4bC9B07
DEPLOYMENTS_FILE=deployments/ink-sepolia.json
KWAL_CREDENTIALS=               # Absolute path outside the repo; Jaydon configures
KWAL_SKILL_DIR=                 # External Kwal scripts directory on the live host
OPENAI_API_KEY=
OPENAI_AGENT_MODEL=
PROVIDER_AGENT_BASE_URL=        # Optional trusted Chat Completions base URL
PROVIDER_AGENT_MODEL=
PROVIDER_AGENT_API_KEY=         # Server-only credential, never a browser value
SUPABASE_URL=
SUPABASE_SECRET_KEY=
```

`SUPABASE_*` stays empty unless optional persistence is added.
`PROVIDER_AGENT_*`, `ANA_KWAL_OWNER_ADDRESS` and the public role-address variables
are proposed configuration names for implementation; documenting them does not
mean the current service consumes them. Keep existing `OPENAI_*` configuration
working while adding the selected-provider adapter. Coordinate shared `.env.example`
updates instead of changing it in this documentation-only task.
`KWAL_SKILL_DIR` is already consumed by J3. Its documented default is
`~/.agents/skills/agent-payment/scripts`. The actual `ANA_SHIP_TO_JSON` must use
the J3 first/last name + phone schema and the supplied saved destination; the
existing mock `name`/Singapore object is not a valid live substitute. Do not
copy personal shipping data or Kwal session credentials into this plan.

Existing private-key names in the handover are `MAKER_PRIVATE_KEY`,
`SERVICE_PRIVATE_KEY`, `JUDGE_PRIVATE_KEY`, `MAKER2_PRIVATE_KEY` and
`TREASURY_PRIVATE_KEY`. `ANA_PRIVATE_KEY` may be exported later for optional
test tooling. Do not add values to this document or require the Treasury key
for receipt of fees. Use keys only in the authorized local deployment/service
tools; browser purchase signing remains in Jaydon's wallet adapter.

Frontend `app/.env.local`:

```dotenv
NEXT_PUBLIC_SERVICE_URL=http://localhost:8000
```

No private key belongs in `app/.env.local`.

## 24. Minimum test plan

### Python

- Health route
- Chat creates Keychron draft
- Chat creates black PowerBug draft with a $60 maximum
- Non-purchase chat has no draft
- Fake payment emits events in order
- Refusal emits all three reasons and no payment events
- Purchase route returns asked/bought fields
- Event store broadcasts to two subscribers
- Agent comparison includes count-zero **Unrated**, provenance, service fee and
  supported coverage; one agent cannot inherit another's history/deposit
- Hired listing routes to its configured endpoint; endpoint errors/invalid drafts
  stop the flow without silently swapping agents
- Flat and percentage fee arithmetic, round-half-up cents, complete cost display
  and frozen fee/agent snapshots; invalid/expired/tampered quotes are rejected
- Normal wrong-colour selection is refused; injected demo failure is explicit
  and does not bypass amount/shop/address/signature/collateral checks
- Reserve covers supported refundable exposure plus maker-paid fee headroom;
  insufficient cover refuses before payment
- Full simulated buyer-total refund, per-agent deposit loss, exactly one refund
  and final reputation write, and merchant recovery remaining pending
- Successful reserves release only on final outcome after the claim window;
  provider withdrawals cannot remove reserved collateral
- Demo-only setup/claims/reset/failure routes are disabled in live mode, missing
  live dependencies fail closed, and real endpoint + fake money retains labels
- Live catalogue resolution uses J3 merchant identifiers, dynamic variant IDs,
  new ShipTo/canonical hash and item/shipping/tax totals; parser/replay tests run
  on a configured host, or report the explicit external-skill skips

Run:

```bash
python -m pytest -q
```

### Next.js

- Type-check all API models and component props
- Lint passes with no warnings
- Production build passes

Run with Node 22/npm 10:

```bash
npm --prefix app run lint
npm --prefix app run typecheck
npm --prefix app run build
```

### Browser smoke test

At desktop and mobile widths verify:

- Keyboard navigation and visible focus
- Form labels and error messages
- Chat loading/error state
- Request signing state
- Compare/hire state, changing agent clearing an unsigned draft, and the same
  selected provider appearing through draft, purchase and receipt
- Demo provider setup, masked connection status and fee controls applying only
  to future approvals; no secret returned to the browser
- Complete buyer total versus separate maker-paid protection fee; fee/refund
  simulation labels and zero service-fee live fallback disclosure
- SSE reconnect state
- Ledger readability
- Receipt mismatch without product images
- Reduced-motion behavior
- No horizontal overflow

## 25. Commit sequence

Use small commits so integration problems are easy to isolate:

The previous session's service/app/demo commits already exist; do not recreate
them. Suggested remaining logical commits:

1. `docs: revise Francesco marketplace demo and wallet handover plan`
2. `feat(service): add provider listings and frozen pricing drafts`
3. `feat(service): route drafts through selected provider endpoint`
4. `feat(app): add agent hire and demo provider setup`
5. `feat(demo): distinguish injected failure and full simulated refund`
6. `feat(registries): deploy ERC-8004 identity and reputation` when F3 is funded
7. `feat(app): connect live shopper wallet reads and claim evidence` when F2/J2/J6/J7
   blockers are resolved
8. `feat(demo): link transaction evidence` only if A1 is completed

Commit numbering is not permission to skip phase validation; blocked deployment
work can wait while the presentation simulation is implemented. No deployment
or commit/push is performed just by updating this document.

Do not mix changes from Jaydon-owned folders into these commits.

Before every push, audit the branch:

```bash
git fetch origin
git diff --name-only origin/main...HEAD
git diff --check origin/main...HEAD
```

The changed-file list must not contain:

```text
contracts/src/
contracts/test/
contracts/script/
service/guard/
service/payments/
service/fixtures/
app/lib/wallet.ts
scripts/
docs/DEMO_SCRIPT.md
```

`deployments/ink-sepolia.json` is allowed only when the diff changes the
`registries` object and leaves the `cover` object untouched. Changes to
`shared/INTERFACES.md` or `shared/purchase-request.json` require a separate,
explicitly coordinated commit; the normal implementation branch treats both
as read-only.

## 26. Final definition of done

### Presentation simulation complete

- [x] Two agent listings show provider, reputation/count, flat/percentage service
      fee, coverage limit and provenance; no-history agents are **Unrated**.
- [x] Buyer hires an agent before drafting; identity and fee snapshot persist
      through authorization, payment and receipt.
- [x] Demo business setup shows simulated KYB, endpoint status, chosen fee and
      collateral. Real endpoint connection is demonstrated only if supplied;
      otherwise **Scripted demo agent** remains explicit.
- [x] Item/shipping/tax/buyer-paid fees/total/refundable total are reviewed before
      authorization; maker-paid protection fee is separate.
- [x] Buyer limits and labelled simulated authorization work in the browser.
- [x] Keychron completes; a normal known PowerBug mismatch is refused.
- [x] Explicit injected-failure PowerBug records black requested/White-Dune bought.
- [x] Wrong-item claim refunds the full simulated approved buyer total once,
      updates the correct provider deposit and final reputation/count, and shows
      **Merchant recovery pending** without claiming vendor recovery.
- [x] Reserve/headroom refusal and the existing three-rule GMKtec refusal pass.
- [x] Receipt shows actual simulated refund amount and measured time; no fake
      hashes are linked to an explorer or labelled as onchain.
- [x] Simulation provenance is visible for KYB, identity/history, signing and money.
- [x] Python tests and app lint/typecheck/build pass; browser smoke passes.
- [x] Full revised main sequence passes twice after reset.
- [x] No Jaydon-owned file is edited by Francesco; synced upstream work is kept
      intact. Validated new work is submitted as a follow-up PR from the Francesco
      branch (PR #1 is already merged).

### Live integration complete - separate gate, currently blocked

- [ ] F2 decisions cover two Ana identities, fee authorization/settlement,
      refundable amount, getters, claim correlation and failure-rehearsal scope.
- [x] Registry addresses/ABIs and real agent ID are in `registries`; ownerOf
      returns the supplied Maker, with nonempty code on the intended network.
- [ ] Jaydon's Checkpoint/Bond/USDC addresses/ABIs are verified in `cover`.
- [ ] Wallets have required gas, buyer funds and adequate maker collateral;
      stale balance reports/faucet promises are not treated as funding proof.
- [ ] Agreed shopper connects, deposits, sets limits, signs and claims through
      Jaydon's adapter; Kwal owner/vault are not confused with the signer.
- [ ] A registered/funded hired agent completes an actual covered purchase.
- [ ] Real claim/refund and exactly one final reputation update are observed for
      the mapped onchain purchase ID; measured time and actual charge/refund match.
- [ ] Provider fee transfer and all-in refund are implemented/tested by Jaydon
      if advertised. Otherwise explicitly report a limited live demo with zero
      service fee/narrower supported protection, not the full product completion.
- [ ] Maker metrics are real getter reads; receipt/ledger carry actual hashes and
      payment IDs. Any separate simulated failure remains visibly separate.
- [ ] Live sequence passes twice with Jaydon's reset/preflight and validation.

If time runs short, cut optional features and the secondary refusal recording,
not its safeguards/tests. Preserve compare/hire, cost/coverage approval, limits,
authorized purchase, accountable refund and evidence. Ship a clearly labelled
simulation rather than declaring incomplete live integration finished.
