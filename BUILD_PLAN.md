# Cover: build plan

Reap × 65labs Agentic Buildathon, Fri 9 Oct 2026, build 3:45 pm to 9:00 pm.

- **Jaydon: payments.** Everything that moves money: Kwal, the Checkpoint and Bond contracts, the ERC-8004 deployment, the chain calls, the demo reset script.
- **Francesco: backend and app.** Everything the agent and Ana touch: the FastAPI service, the rules check, the OpenAI agent and judge, MCP, the Next.js app.

`COVER_PLAN.html` says **what** Cover does and why. This file says **how** to build it, in order. Each task has its files, its steps and a "done when" check. Tick the boxes as you go.

---

## 0. Rules for the night

1. **Everything an add-on needs onchain goes into the contracts before the 5:30 deploy.** Redeploying later means new addresses and an empty history. That covers the vague-claim functions, the judge role, the approval route, score bands, the fee and the treasury.
2. **Nobody waits on anybody.** Francesco builds against a fake `pay()` until the real one lands at 6:00. The app is built against the contract signatures in section 3 before the contracts are deployed.
3. **Folders have owners.** `contracts/`, `service/payments/` and `scripts/` are Jaydon's. The rest of `service/` and all of `app/` are Francesco's. Say so before editing the other person's folder.
4. **No secrets in git.** Private keys, the Kwal credentials file and API keys live in `.env` (gitignored) or outside the repo. Commit `.env.example` only.
5. **Codex and Devin write boilerplate** (app screens, test scaffolding, FastAPI routes). People write the contracts' rule logic.
6. **Main product first.** No add-on starts until the full demo runs twice in a row (7:45).

---

## 1. Tech stack

| Layer | Tech | Owner |
|---|---|---|
| Chain | Ink Sepolia, chain ID 763373, RPC `https://rpc-gel-sepolia.inkonchain.com` | Jaydon |
| Money | Test USDC (6 decimals; take the token address from Kwal's funding output, never from memory) | Jaydon |
| Contracts | Solidity and Foundry: `Checkpoint.sol`, `Bond.sol` | Jaydon |
| Agent identity and score | ERC-8004 reference contracts (github.com/erc-8004/erc-8004-contracts), deployed by us | Jaydon |
| Payment | Kwal Python client (github.com/payward/kwal-skill, `scripts/` on the Python path) | Jaydon |
| Chain calls from Python | web3.py | Jaydon |
| Uncovered purchases (A5) | Reap Agentic API, direct (team key after 4:30) | Jaydon |
| Service | Python 3.10+, FastAPI, server-sent events, in WSL | Francesco |
| Rules and signing | Ported from laeria: `backend/services/payment.py`, `backend/core/models.py`, `backend/services/delegation.py`, 19 tests in `backend/tests/test_mandate.py` | Francesco |
| AI | OpenAI Python SDK: the agent (tools), the judge and the injection check (logprobs) | Francesco |
| Any agent can plug in (A4) | MCP Python SDK | Francesco |
| App | Next.js, laeria's `frontend/lib/wallet.ts` for wallet connect and EIP-712 signing | Francesco |

---

## 2. Repo layout

```
contracts/                 Jaydon. Foundry project
  src/Checkpoint.sol
  src/Bond.sol
  src/test-helpers/Sender.sol    10-line contract for Kwal test 4
  test/Checkpoint.t.sol
  test/Bond.t.sol
  script/Deploy.s.sol
  lib/erc-8004-contracts/        reference registries, unchanged
deployments/
  ink-sepolia.json         Jaydon. Written by the deploy; read by everyone
shared/
  INTERFACES.md            Both. Section 3 of this file, agreed at 3:45
  purchase-request.json    Both. The EIP-712 types, the one source for app and contract
service/
  main.py                  Francesco. FastAPI app and routes
  signing.py               Francesco. Verifies Ana's signature (from laeria delegation.py)
  rules.py                 Francesco. Rules check (from laeria payment.py and models.py)
  runner.py                Francesco. quote, rules check, pay
  agent.py                 Francesco. OpenAI agent, two tools
  judge.py                 Francesco. A3 and A3b
  mcp_server.py            Francesco. A4
  fake_payments.py         Francesco. Fake pay() until 6:00
  tests/                   Francesco. Ported laeria tests
  payments/                Jaydon
    __init__.py            quote(), pay(), the types in section 3.1
    kwal.py                thin wrapper over the Kwal client
    chain.py               web3.py calls to Checkpoint and Bond
    reap_approval.py       A5 only
  fixtures/                Jaydon. Recorded Kwal runs for replay
scripts/
  demo_reset.py            Jaydon. Run before every full take
  pay_smoke.py             Jaydon. One payment from the command line
app/                       Francesco. Next.js
.env.example
README.md
```

---

## 3. The interfaces, drafted now so 3:45 is a 10-minute read-through

Copy this section into `shared/INTERFACES.md` at 3:45, change what you disagree with, and treat it as fixed after that.

### 3.1 Python: `service/payments` (Jaydon builds, Francesco calls)

```python
from dataclasses import dataclass
from typing import AsyncIterator, Literal, Optional

@dataclass
class ShipTo:            # filled from Ana's saved limits, never from the agent
    name: str
    line1: str
    city: str
    postal_code: str
    country: str         # "SG"
    email: str

@dataclass
class Quote:
    quote_id: str
    product_id: str
    variant_id: str
    shop: str                     # merchant domain, lowercase, e.g. "twelvesouth.com"
    title: str                    # e.g. "PowerBug 25W (Qi2.2)"
    colour: str                   # lowercase variant label, "" if none
    size: str
    model: str
    image_url: Optional[str]      # for the receipt; None if Kwal doesn't return one
    listed_usd_cents: int         # what the shop lists; limits use this
    charge_usdc: int              # 6-decimal units actually charged; refunds use this
    sandbox_pricing: bool         # True if quote_id starts with "sandbox_quote_"

def quote(variant_id: str, quantity: int, ship_to: ShipTo) -> Quote: ...

async def pay(request: dict, signature: str, q: Quote) -> AsyncIterator["Event"]:
    """release -> wait for vault funding -> checkout -> wait for payment -> confirm.
    One payment at a time. Retries rate limits every 15-30 s for up to 5 minutes.
    Raises NeedsApproval if the agent's score doesn't allow this amount (A5)."""

def check(request: dict, signature: str, q: Quote) -> list[str]:
    """Calls Checkpoint.check(). Returns every failed rule by name, for the refusal beat."""

async def pay_approved(request: dict, signature: str, approval_sig: str, q: Quote) -> AsyncIterator["Event"]:
    """A5 fallback: Ana approved it herself; paid from her account, not covered."""
```

### 3.2 Events (the service streams these; the app renders them)

```json
{
  "purchase_id": 3,
  "step": "checked | refused | needs_approval | released | fee_taken | funded | paid | confirmed | claimed | refunded | rejected | needs_review | score_written",
  "status": "ok | waiting | error",
  "tx_hash": "0x... or null",
  "kwal_payment_id": "... or null",
  "detail": "Plain words for the ledger, e.g. 'Refused: amount, shop, address'",
  "ts": "2026-10-09T19:12:03.120Z"
}
```

`GET /events` (server-sent events) sends every event. The app filters by `purchase_id`.

### 3.3 EIP-712: Ana's signed request (`shared/purchase-request.json`)

Strings, not hashes, so Ana's wallet shows readable fields when she signs. The app lowercases colour, size, model and shop before signing. Rename fields to match Mastercard Verifiable Intent once you've read it, but only at 3:45.

```json
{
  "domain": { "name": "Cover", "version": "1", "chainId": 763373, "verifyingContract": "<Checkpoint address>" },
  "primaryType": "PurchaseRequest",
  "types": {
    "PurchaseRequest": [
      { "name": "shopper",     "type": "address" },
      { "name": "agentId",     "type": "uint256" },
      { "name": "shop",        "type": "string"  },
      { "name": "item",        "type": "string"  },
      { "name": "colour",      "type": "string"  },
      { "name": "size",        "type": "string"  },
      { "name": "model",       "type": "string"  },
      { "name": "maxUsdCents", "type": "uint256" },
      { "name": "addressHash", "type": "bytes32" },
      { "name": "nonce",       "type": "uint256" },
      { "name": "deadline",    "type": "uint256" }
    ]
  }
}
```

An empty string means "any". The claim only compares fields Ana filled in.

**Known limit, for the README:** the contract compares exact labels. "Black" against "White/Dune" is clear. "Black" against "Midnight" would refund even if Midnight is black. The demo items have plain labels; in production the shop would sign its attribute data.

### 3.4 Solidity: function signatures (Jaydon builds, Francesco's app calls)

```solidity
// ---------- Checkpoint (Ana's account) ----------
struct Bought {
    bytes32 quoteIdHash;
    string  shop;  string colour;  string size;  string model;   // lowercase
    uint256 listedUsdCents;   // limits, bands and the monthly total use this
    uint256 chargeUsdc;       // what moves, 6 decimals
}

function setLimits(uint256 perItemMaxCents, uint256 monthlyMaxCents, string[] calldata shops,
                   bytes32 addressHash, uint64 endsAt) external;              // Ana
function deposit(uint256 usdc) external;                                     // Ana (approve USDC first)
function withdraw(uint256 usdc) external;                                    // Ana, any time
function check(PurchaseRequest calldata r, bytes calldata sig, Bought calldata b)
    external view returns (uint256 failedRules);                             // bitmask, for the refusal beat
function release(PurchaseRequest calldata r, bytes calldata sig, Bought calldata b)
    external returns (uint256 purchaseId);                                   // service only
function releaseApproved(PurchaseRequest calldata r, bytes calldata sig, bytes calldata approvalSig,
                         Bought calldata b) external returns (uint256);      // service only, A5 fallback, not covered
function confirm(uint256 purchaseId, bytes32 paymentIdHash, uint8 status) external;  // service only
function autoPayLimitCents(uint256 agentId) external view returns (uint256);

event PurchaseRecorded(uint256 indexed purchaseId, address indexed shopper, uint256 indexed agentId,
    string askedColour, string askedSize, string askedModel,
    string boughtColour, string boughtSize, string boughtModel,
    uint256 listedUsdCents, uint256 chargeUsdc, bool covered);

error OverRequestMax(); error OverPerItem(); error OverMonthly(); error ShopNotAllowed();
error WrongAddress(); error Expired(); error BadSignature(); error NotEnoughCover();
error NeedsApproval();   // amount is above the agent's score band; the service routes it to Ana (A5)

// ---------- Bond (maker's deposit, claims, fee, score) ----------
function deposit(uint256 agentId, uint256 usdc) external;          // only the agent's ERC-8004 owner
function requestWithdraw(uint256 agentId, uint256 usdc) external;  // waits withdrawDelay; never touches reserved cover
function withdraw(uint256 agentId) external;
function reserve(uint256 purchaseId, uint256 agentId, address shopper, uint256 chargeUsdc,
                 bytes32 askedHash, bytes32 boughtHash) external;  // Checkpoint only; takes the fee to treasury
function releaseReserve(uint256 purchaseId) external;              // anyone after the window; writes score 100
function openClaim(uint256 purchaseId) external;                   // shopper only; mismatch -> refund + score 0, match -> reject + score 100
function openVagueClaim(uint256 purchaseId, string calldata complaint) external;  // shopper only (A3)
function resolveClaim(uint256 purchaseId, uint8 verdict, bytes32 evidenceHash) external; // judge only: 1 refund, 2 reject, 3 needs review
function makerResolve(uint256 purchaseId, bool refund) external;   // agent owner, for needs-review claims
function score(uint256 agentId) external view returns (uint256 avg, uint64 count);  // no history yet = 100
function feeBps(uint256 agentId) external view returns (uint256);  // 50 + 5 * (100 - avg)
function freeCover(uint256 agentId) external view returns (uint256);
function feesPaid(uint256 agentId) external view returns (uint256);
```

**Fixed at deploy:** the USDC address, Ana's Kwal vault address, the service address, the judge address, the treasury address, the identity and reputation registry addresses, the claim window (a few minutes for the demo), the withdrawal delay (a few minutes for the demo), and the score bands (90+: per-item cap; 60–89: $50; under 60: $0).

### 3.5 Service routes (Francesco builds, the app calls)

| Route | Does |
|---|---|
| `POST /chat {message}` | The agent replies. When Ana asks to buy, it returns a `request_draft` for the sign card instead of buying |
| `POST /requests {request, signature}` | Verifies the signature, then lets the agent find the item and call `covered_purchase` |
| `GET /events` | Server-sent events (3.2) |
| `GET /purchases/{id}` | Purchase with asked and bought fields and both image URLs, for the receipt |
| `POST /claims/vague {purchase_id, complaint}` | A3: runs the judge after Ana's `openVagueClaim` transaction |
| `POST /approvals {purchase_id, approval_sig}` | A5 fallback: Ana's tap to approve an uncovered purchase |

`openClaim`, `setLimits`, `deposit` and `withdraw` are sent from Ana's wallet in the app, not by the service.

### 3.6 Wallets and `.env.example`

| Wallet | Used for | Needs |
|---|---|---|
| Ana | Owns the Kwal vault and her Checkpoint account; signs requests; opens claims | Test ETH, as much test USDC as possible |
| Maker | Owns the demo agent on ERC-8004; deposits into the Bond | Test ETH, as much test USDC as possible |
| Service | Calls `release`, `confirm`; pays gas | Test ETH |
| Judge (the spare wallet) | Calls `resolveClaim` (A3) | Test ETH |
| Second maker | A4's second agent and deposit | Test ETH, some test USDC |
| Treasury | Receives cover fees | Nothing; any address you control |

```
INK_RPC=https://rpc-gel-sepolia.inkonchain.com
CHAIN_ID=763373
USDC_ADDRESS=            # from Kwal's funding output
KWAL_CREDENTIALS=        # absolute path OUTSIDE the repo
ANA_ADDRESS=
ANA_VAULT_ADDRESS=       # from Kwal setup
ANA_SHIP_TO_JSON=        # {"name":...,"country":"SG",...}
SERVICE_PRIVATE_KEY=
JUDGE_PRIVATE_KEY=
MAKER_PRIVATE_KEY=       # scripts only
MAKER2_PRIVATE_KEY=      # A4
TREASURY_ADDRESS=
OPENAI_API_KEY=
OPENAI_AGENT_MODEL=
OPENAI_JUDGE_MODEL=      # must return logprobs
REAP_API_KEY=            # after 4:30, A5 only
DEPLOYMENTS_FILE=deployments/ink-sepolia.json
```

---

## 4. Before 3:00 pm (Jaydon)

- [ ] Finish Kwal setup with a fresh wallet that plays Ana. Credentials file outside every git folder. Never re-run registration after a timeout.
- [ ] Run the handover tests and write the answers into `shared/INTERFACES.md`: test 1 (no approval link?), test 4 (does a second wallet's transfer count as funding, and how many seconds?), test 5 (`sandbox_quote_`, meaning 1-USDC pricing?), test 6 (several items in one quote?).
- [ ] Check the PowerBug 25W has a black option next to White/Dune through Kwal's product lookup. If not, switch to a backup from `COVER_PLAN.html`.
- [ ] Faucets for all wallets in 3.6: test ETH from inkonchain.com/faucet, test USDC from faucet.circle.com. Most USDC to Ana and the maker.
- [ ] Clone the ERC-8004 reference repo and get `forge build` passing. Note how its own deploy script works (plain contracts or proxies) and copy that.
- [ ] Send `COVER_PLAN.html` and this file to Francesco.

**Francesco, before 3:00:** pick the OpenAI judge model and confirm a test call returns `logprobs`. Clone laeria (`jaydonnnk/laeria-ai`) so the files in section 1 are at hand.

---

## 5. Jaydon's tasks (payments)

### J1 · 3:45–3:55 · Interfaces, with Francesco
- [ ] Read section 3 together, adjust, commit `shared/INTERFACES.md` and `shared/purchase-request.json`.

**Done when** both of you have pulled the commit.

### J2 · 3:55–4:30 · Kwal module
Files: `service/payments/kwal.py`, `service/payments/__init__.py`, `scripts/pay_smoke.py`
- [ ] Wrap the Kwal client: `catalog.search_products`, `read_product`, `resolve_variant`, `quotes.create_quote(lines, email, shipping_address)`, `read_quote`, `select_shipping`, `vault.read_funding(quote_id=…)`, `poll_funding`, `checkout.create_checkout(payment_id, quote_id)`, `read_payment`, `poll_payment`.
- [ ] Build `quote()` returning the `Quote` type from 3.1. Set `sandbox_pricing` from the quote ID prefix.
- [ ] Add retries (15–30 s, up to 5 minutes) on rate-limit and "participant unavailable" errors, and one global lock so only one payment runs at a time.
- [ ] Save every raw Kwal response to `service/fixtures/` as you go (it becomes the replay data).

**Done when** `python scripts/pay_smoke.py` buys a rehearsal item (vault funded by hand) and prints a completed payment ID.

### J3 · 3:55–5:00 · Contracts and tests (in parallel with J2; let Codex scaffold)
Files: `contracts/src/*.sol`, `contracts/test/*.t.sol`
- [ ] **Tests first.** Turn laeria's 19 rule cases into Checkpoint tests. Rule from laeria: an unset limit means zero, never unlimited.
- [ ] Checkpoint: `setLimits`, `deposit`, `withdraw`, EIP-712 verification of 3.3, every rule in 3.4 with its custom error, `check()` returning all failures as a bitmask, `release` (sends `chargeUsdc` to Ana's vault and calls `Bond.reserve`), `releaseApproved` (skips the band and the Bond; `covered = false`), `confirm`, `autoPayLimitCents` from `Bond.score`.
- [ ] Bond: deposit (owner check via the Identity Registry's `ownerOf(agentId)`), withdrawals with a delay that can't touch reserved cover, `reserve` (refuses unless free cover ≥ charge + fee; sends the fee to treasury), `releaseReserve`, `openClaim`, `openVagueClaim`, `resolveClaim`, `makerResolve`, `score`, `feeBps`, plain counters.
- [ ] Score writes: exactly one per purchase, at the final outcome, inside `try/catch`:
  `reputation.giveFeedback(agentId, int128(value), 0, "cover", outcome, "", "", recordHash)` with value 100 and outcome `"ok"`, or value 0 and outcome `"wrong-item"`.
- [ ] `score()`: `getSummary(agentId, [address(this)], "cover", "")`, falling back to the counters if the call fails. **Check in the reference code** that `summaryValue` is an average and how its decimals work, before trusting it.
- [ ] Never make the Bond an operator of any agent (the registry blocks owners and operators from scoring their own agent).

**Done when** `forge test` passes with at least: every Checkpoint rule and refusal; `check()` reporting amount, shop and address together; mismatch refund; match rejection; over-reserve refusal; withdrawal blocked by reserved cover; fee reaching treasury and rising as the score falls; one score per purchase, never two; refund still paid when the registry reverts; `NeedsApproval` when the score drops from 100 to 67 and the amount is $58.

### J4 · 4:30–4:45 · Test 4, live
Files: `contracts/src/test-helpers/Sender.sol`
- [ ] Deploy `Sender` (one function: transfer USDC to an address). Get a quote, send the exact amount from `Sender` to Ana's vault, and time `poll_funding` until ready.
- [ ] Write the seconds into `shared/INTERFACES.md`.

**Done when** you know whether a contract transfer counts and how long it takes. If it doesn't count, switch to the forwarding fallback in `COVER_PLAN.html` and tell Francesco.

### J5 · 5:00–5:30 · Deploy
Files: `contracts/script/Deploy.s.sol`, `deployments/ink-sepolia.json`
- [ ] Deploy the ERC-8004 Identity and Reputation registries the way their repo does it, unchanged.
- [ ] Deploy Bond, then Checkpoint, with the fixed values from 3.4; point the Bond at the Checkpoint.
- [ ] From the maker wallet: `register(agentURI)` (a small JSON naming Cover and the Bond; a GitHub raw URL is fine), then `approve` and `Bond.deposit`.
- [ ] Write addresses, ABIs (from `contracts/out/`) and the agent ID to `deployments/ink-sepolia.json` and push.

```bash
forge script script/Deploy.s.sol --rpc-url $INK_RPC --broadcast
```

**Done when** the JSON is pushed, the contracts show on the Ink Sepolia explorer, and `cast call <Bond> "score(uint256)" <agentId>` returns 100 with a count of 0.

### J6 · 5:30–6:00 · The real `pay()`
Files: `service/payments/chain.py`, `service/payments/__init__.py`
- [ ] `chain.py`: load `deployments/ink-sepolia.json`; `check`, `release`, `confirm`, `release_approved`; decode custom errors into rule names.
- [ ] `pay()`: `release` → events `released` and `fee_taken` → `poll_funding` → `funded` → `create_checkout` → `poll_payment` → `paid` → `confirm` → `confirmed`. `NeedsApproval` raises instead of emitting `refused`.

**Done when** `python scripts/pay_smoke.py --real` prints every event and the release and confirm transactions are on the explorer. Tell Francesco to swap out the fake.

### J7 · 6:00–6:45 · First end-to-end run, together
- [ ] Sit with Francesco while the app drives one covered purchase. Fix whatever breaks on your side first.

**Done when** the 6:45 milestone passes: one covered purchase from the app, no terminal.

### J8 · 7:00–7:45 · Demo reset and replay
Files: `scripts/demo_reset.py`, `service/fixtures/`
- [ ] `demo_reset.py`: register a fresh agent ID, deposit, make exactly two good covered purchases with items not used on camera, wait out the window, call `releaseReserve` on both, then check score 100 over 2, fee 50 bps, auto-pay limit equal to Ana's per-item cap, and enough free cover. Print `READY agentId=<n>` or stop with what's wrong. Write the new agent ID where the app reads it.
- [ ] Record a real run of every Kwal call used in the demo into `service/fixtures/`; add a `REPLAY=1` switch that serves them. Replays are labelled as replays in the UI.
- [ ] Help Francesco wire `openClaim` and the receipt data.

**Done when** two full demo runs pass, each after `demo_reset.py` printed READY.

### J9 · 7:50–8:20 · Add-ons, in this order, stop at 8:20
- [ ] **A2b** (10 min): on camera, claim on the Keychron B40 bought at 0:45; check the contract rejects it.
- [ ] **A5 fallback** (20 min): on `NeedsApproval`, emit `needs_approval`; Francesco's app shows Ana an approve button; `pay_approved()` calls `releaseApproved`. Then, only if time remains, the real Reap hosted approval page (`reap_approval.py`, about 60 min, copy exact paths from docs.reap.global).
- [ ] **A2** (35 min): public terms page in `app/terms`, reading the contracts: deposit, reserved, claims paid, fee formula, judge prompt.
- [ ] **A7**: only if kickoff confirmed Payward Services credentials.

### J10 · 8:20–8:45 · README
- [ ] Write it from the outline in `COVER_PLAN.html`. Contract addresses from `deployments/ink-sepolia.json`. The "what's real and what's simulated" section near the top, including the exact-label limit from 3.3.

---

## 6. Francesco's tasks (backend and app)

### F1 · 3:00–3:45 · Scaffolding
- [ ] Repo folders from section 2, `.gitignore` (`.env`, `out/`, `node_modules/`, any credentials), `.env.example` from 3.6.
- [ ] FastAPI app with a `/health` route; Next.js app (`npx create-next-app@latest app`).

**Done when** both start locally from a fresh clone.

### F2 · 3:45–3:55 · Interfaces, with Jaydon
Same as J1.

### F3 · 3:55–4:45 · Signing, rules, fake payments
Files: `service/signing.py`, `service/rules.py`, `service/fake_payments.py`, `service/tests/`
- [ ] Port laeria's `delegation.py` to verify the `PurchaseRequest` in 3.3 and recover the signer.
- [ ] Port laeria's rules check and its 19 tests: per-item cap, monthly cap, shop allowlist, blocked categories. Unset means deny.
- [ ] Spend ceiling (from laeria `actions.py:345-361`): the smallest of Ana's signed max, the quote, her remaining monthly budget and the maker's free cover.
- [ ] `fake_payments.py` with the same functions as 3.1, emitting the 3.2 events with fake hashes on a timer.

**Done when** `pytest` passes and a fake `pay()` streams events.

### F4 · 4:30–5:30 · Agent, runner and events
Files: `service/agent.py`, `service/runner.py`, `service/main.py`
- [ ] Agent with two tools: `find_item(query)` (Kwal catalogue: search, product, variant) and `covered_purchase(variant_id)`. When Ana asks to buy, the agent first returns a `request_draft` (shop, item, colour, size, model, max) for her to sign. For the demo, the system prompt says to take the shop's default variant when unsure; the README says so.
- [ ] Runner: `quote()` with Ana's saved address → rules check → `check()` → `pay()`, streaming events.
- [ ] Routes from 3.5, with `GET /events` as server-sent events.

**Done when** "Buy the black PowerBug 25W, under $60" ends with the White/Dune variant chosen, and "Get me the Keychron B40" ends with the right one, both through the fake `pay()`.

### F5 · 4:30–5:30 · App shell (in parallel with F4; let Codex scaffold)
Files: `app/`
- [ ] Wallet connect and EIP-712 signing using laeria's `wallet.ts` and `shared/purchase-request.json`.
- [ ] Ana's limits screen: one `setLimits` transaction; USDC `approve` + `Checkpoint.deposit`.
- [ ] Recording layout: Ana on the left (phone-sized), maker on the right, ledger along the bottom, readable at 1080p.

**Done when** Ana can set limits and sign a request from the app on Ink Sepolia (contract addresses arrive at 5:30; use placeholders until then).

### F6 · 5:30–6:45 · Real payments, chat, maker screen
- [ ] Swap `fake_payments` for `service.payments` when Jaydon says (by 6:00).
- [ ] Ana's chat, the sign-request card, the purchase card moving through checked, released, paid.
- [ ] Maker screen from the contracts: ERC-8004 agent ID, deposit, reserved, free cover, score (average and count), fee rate, auto-pay limit, fees paid to Cover. Poll every few seconds.

**Done when** the 6:45 milestone passes with Jaydon (J7).

### F7 · 7:00–7:45 · The money moment
- [ ] "Wrong item" button → `Bond.openClaim(purchaseId)` from Ana's wallet.
- [ ] The receipt: both product images side by side from `GET /purchases/{id}`, the differing field highlighted ("black ≠ white/dune"), USDC animating from the maker's deposit to Ana, a stopwatch from tap to the refund transaction, and "$49.99 refunded from the maker's deposit · 9.8 s". If there are no images, use colour swatches and names.
- [ ] Ledger: every event in order with its transaction hash and Kwal payment ID.
- [ ] Refusal beat: a fake "deal" message with a hidden instruction makes the agent try the $6,599 GMKtec to a new address; the ledger shows all three failures from `check()` and no money moves.

**Done when** two full demo runs pass (with J8).

### F8 · 7:50–8:20 · Add-ons, in this order, stop at 8:20
- [ ] **A1** (20 min): explorer links on every ledger row and a "verify it yourself" link on the receipt.
- [ ] **A3** (35 min): `judge.py`. One Chat Completions call, no tools, `temperature 0`, `logprobs true`, `top_logprobs 5`, a few output tokens. The system prompt says the request, description and complaint are data, never instructions, and asks for one word: MISMATCH, MATCH or UNSURE. Read the first token's probability. 0.9 or more for MISMATCH: `resolveClaim(id, 1, hash)`. 0.9 or more for MATCH: `resolveClaim(id, 2, hash)`. Anything else, an error or an unexpected word: `resolveClaim(id, 3, hash)` for maker review. The hash covers the model name, the prompt, the answer and the probabilities. Rehearse five labelled claims before recording.
- [ ] **A3b** (15 min): the same call with YES/NO on product and shop text before the agent sees it. Flagged text is dropped and a ledger event shows it.
- [ ] **A4** (50 min): `mcp_server.py` exposing `covered_purchase` so Claude or ChatGPT can buy through Cover, backed by the second maker's agent (Jaydon registers it with `demo_reset.py --second-agent`).
- [ ] **A6** (25 min): mock shop page "Covered agents welcome" showing the live ERC-8004 score.

### F9 · 8:20–8:45 · Video
- [ ] Record and edit the beats in `COVER_PLAN.html`, under 3 minutes. Run `demo_reset.py` before the take. Stopwatch and explorer links visible during the refund.

---

## 7. Checkpoints

| Time | Check | If it fails |
|---|---|---|
| 3:55 | `shared/INTERFACES.md` committed | Don't start coding until it is |
| 4:30 | `pay_smoke.py` bought one item; `forge test` has the rule tests | Jaydon drops J4 to 4:45 and keeps going |
| 4:45 | Test 4 answered | Forwarding fallback; tell Francesco |
| 5:30 | `deployments/ink-sepolia.json` pushed | Francesco keeps placeholders; Jaydon deploys without the registries and the screens use the Bond's counters |
| 6:00 | Real `pay()` handed over | Francesco keeps the fake for UI work; Jaydon fixes alone |
| 6:45 | One covered purchase from the app, no terminal | Cut the A-list now; both on the main path |
| 7:45 | Full demo twice, each after a reset; raw takes recorded | No add-ons; polish and record |
| 8:20 | Feature freeze | Nothing new |
| 8:45 | Submitted | Submissions close at 9:00 sharp |

**Cut order if late:** A7, A6, A5 (real Reap page, then the fallback), A4, A3b, A3, A2b, A2, A1. **Never cut:** Ana's limits, the signed request, the checkpoint release, the Kwal payment, the claim refund, the ledger.
