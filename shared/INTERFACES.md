# Cover: shared interfaces

**Status: draft for the J1/F2 read-through.** Transcribed from BUILD_PLAN.md
section 3. Committing this file does not mean Jaydon and Francesco have agreed it.
After that read-through, treat it as fixed; coordinate every subsequent change.

## 3.1 Python: `service/payments` (Jaydon builds, Francesco calls)

```python
from dataclasses import dataclass
from typing import AsyncIterator, Optional

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

def check(request: dict, signature: str, q: Quote) -> list[str]:
    """Calls Checkpoint.check(). Returns every failed rule by name, for the refusal beat."""

async def pay(request: dict, signature: str, q: Quote) -> AsyncIterator["Event"]:
    """release -> wait for vault funding -> checkout -> wait for payment -> confirm.
    One payment at a time. Retries rate limits every 15-30 s for up to 5 minutes.
    Raises NeedsApproval if the agent's score doesn't allow this amount (A5)."""

async def pay_approved(request: dict, signature: str, approval_sig: str, q: Quote) -> AsyncIterator["Event"]:
    """A5 fallback: Ana approved it herself; paid from her account, not covered."""
```

## 3.2 Python: `service/guard` (Jaydon ports from laeria, Francesco calls)

```python
@dataclass
class Limits:                     # read from the Checkpoint by chain.get_limits(shopper)
    per_item_max_cents: int
    monthly_max_cents: int
    shops: list[str]
    address_hash: str
    ends_at: int
    spent_this_month_cents: int

def verify_request(request: dict, signature: str) -> str:
    """Recovers the EIP-712 signer of 3.4 and returns it. Raises BadSignature."""

def check_rules(request: dict, q: Quote, limits: Limits) -> list[str]:
    """laeria's rules check. Returns failed rule names; [] means pass. Unset means deny."""

def spend_ceiling_cents(request: dict, q: Quote, limits: Limits, free_cover_usdc: int) -> int:
    """laeria's ceiling: the smallest of Ana's signed max, the quote, her remaining
    monthly budget and the maker's free cover."""
```

The contract enforces the same rules again at `release`. The guard catches problems before any gas is spent.

## 3.3 TypeScript: `app/lib/wallet.ts` (Jaydon ports from laeria, Francesco's screens call)

```ts
export async function connect(): Promise<`0x${string}`>;
export async function signPurchaseRequest(req: PurchaseRequest): Promise<`0x${string}`>;
export async function sendTx(contract: "Checkpoint" | "Bond" | "USDC",
                             fn: string, args: unknown[]): Promise<`0x${string}`>;
export async function read(contract: "Checkpoint" | "Bond" | "Identity" | "Reputation",
                           fn: string, args: unknown[]): Promise<unknown>;
```

`connect` returns Ana's or the maker's address; `signPurchaseRequest` uses EIP-712
types from `shared/purchase-request.json`; `sendTx` returns the transaction hash.
Addresses and ABIs come from `deployments/ink-sepolia.json`. Until deployment,
`wallet.ts` reads placeholders from the same file.

## 3.4 EIP-712: Ana's signed request (`shared/purchase-request.json`)

Strings, not hashes, so Ana's wallet shows readable fields when she signs. The app
lowercases colour, size, model and shop before signing. Rename fields to match
Mastercard Verifiable Intent once you've read it, but only at the joint read-through.

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

**Known limit:** the contract compares exact labels. "Black" against "White/Dune"
is clear. "Black" against "Midnight" would refund even if Midnight is black. The
demo items have plain labels; in production the shop would sign its attribute data.

The JSON file, not this illustrative block, is the machine-readable source of
truth. Resolve `domain.verifyingContract` from the deployed Checkpoint before
signing; the placeholder is deliberately invalid and must never be signed.

## 3.5 Events (the service streams these; the app renders them)

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

The pipe-delimited strings above describe enum options, not literal values.
`GET /events` (server-sent events) sends every event. The app filters by `purchase_id`.

## 3.6 Solidity: function signatures (Jaydon builds, Francesco's app calls through `wallet.ts`)

```solidity
// ---------- Checkpoint (Ana's account; laeria's rules, onchain) ----------
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
function limitsOf(address shopper) external view returns (/* the Limits fields in 3.2 */);
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

**Fixed at deploy:** the USDC address, Ana's Kwal vault address, the service
address, the judge address, the treasury address, the identity and reputation
registry addresses (from Francesco's F3), the claim window (a few minutes for the
demo), the withdrawal delay (a few minutes for the demo), and the score bands
(90+: per-item cap; 60–89: $50; under 60: $0).

## 3.7 Service routes (Francesco builds, the app calls)

| Route | Does |
|---|---|
| `POST /chat {message}` | The agent replies. When Ana asks to buy, it returns a `request_draft` for the sign card instead of buying |
| `POST /requests {request, signature}` | `guard.verify_request`, then lets the agent find the item and call `covered_purchase` |
| `GET /events` | Server-sent events (3.5) |
| `GET /purchases/{id}` | Purchase with asked and bought fields and both image URLs, for the receipt |
| `POST /claims/vague {purchase_id, complaint}` | A3: runs the judge after Ana's `openVagueClaim` transaction |
| `POST /approvals {purchase_id, approval_sig}` | A5 fallback: Ana's tap to approve an uncovered purchase |

`openClaim`, `setLimits`, `deposit` and `withdraw` are sent from Ana's wallet in
the app through `wallet.ts`, not by the service.

## 3.8 Wallets and `.env.example`

| Wallet | Used for | Needs |
|---|---|---|
| Ana | Owns the Kwal vault and her Checkpoint account; signs requests; opens claims | Test ETH, as much test USDC as possible |
| Maker | Owns the demo agent on ERC-8004; deposits into the Bond | Test ETH, as much test USDC as possible |
| Service | Calls `release`, `confirm`; pays gas | Test ETH |
| Judge (the spare wallet) | Calls `resolveClaim` (A3) | Test ETH |
| Second maker | A4's second agent and deposit | Test ETH, some test USDC |
| Treasury | Receives cover fees | Nothing; any address you control |

Both of you need the maker's key: Francesco registers the agents, Jaydon's
scripts deposit. Share test keys through a private message, never through git.
The complete environment variable template is the root `.env.example`.

## Starter deployment-file convention (review together)

`deployments/ink-sepolia.json` uses `{address, abi}` objects named `Identity`,
`Reputation`, `Checkpoint`, `Bond`, and `USDC`, matching wallet contract names.
Unknown addresses are `null` and ABIs `[]`; consumers must refuse transactions
until both exist. `registries.agentId` starts as `null` and should become a
decimal string. Francesco owns `registries`; Jaydon owns `cover`; neither replaces
the other's section. Top-level chain ID, network and RPC URL are shared.

## Open decisions before J1/F2 sign-off

- **Rule names/bitmask:** agree stable bit positions and the Python/UI names for
  every refusal. `check()` must report all failures, not just the first.
- **Categories:** J2 mentions blocked categories, but neither `Limits` nor `Quote`
  supplies them, and 3.6 has no matching rule. Resolve scope before porting tests.
- **USD cents vs USDC:** define integer conversion and fee headroom in
  `spend_ceiling_cents`; a sandbox quote can charge 1 USDC for a much higher listed
  price. Do not compare 6-decimal USDC units directly with USD cents.
- **Request quantity/address:** the signed request has no quantity or shipping
  fields except `addressHash`. Agree quantity semantics and canonical address
  serialization/hashing; never accept an agent-supplied shipping address.
- **Approval signature:** A5 needs a defined, replay-resistant signed approval
  payload (purchase/request identifier, amount, nonce and expiry), not just an
  `approval_sig` parameter with no agreed meaning.
- **Event IDs:** decide how `checked`, `refused` and `needs_approval` correlate
  before `release()` allocates an onchain `purchaseId`. Also agree SSE framing,
  reconnect/replay behavior and transaction-event ingestion for wallet claims.
- **Receipt/agent payloads:** agree the response schemas for chat/request drafts
  and asked/bought receipt fields before building the screens.
- **Score cap:** `autoPayLimitCents(agentId)` lacks a shopper argument although
  the top band uses Ana's per-item cap. Confirm whether Ana is the fixed demo
  shopper or adjust the interface together before contract implementation.
- **Contract reads:** the maker screen requires deposit/reserved/claims-paid
  views not all explicitly listed in 3.6. Agree getter names and ABIs before deploy.
- **Kwal handover:** record test 1 (approval link), test 4 (contract/second-wallet
  funding and elapsed seconds), test 5 (sandbox pricing) and test 6 (multi-item
  quotes) here when Jaydon has measured results. They are currently unknown.
- **Reference deploy:** the pinned ERC-8004 upstream is Hardhat/upgradeable, not
  a Foundry project. Francesco must verify network/proxy deployment settings;
  reference contracts remain unchanged.
