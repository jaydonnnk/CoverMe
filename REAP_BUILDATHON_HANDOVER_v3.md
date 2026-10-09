# Handover v3: Reap x 65labs Agentic Buildathon — finalise the idea

> Paste everything below into a fresh agent. It is self-contained. The merchant
> list is in the appendix; attaching the spreadsheet is optional.

---

You are picking up a hackathon brainstorm on **the day of the event**. A
previous agent read the event pages, the sponsor docs and code, the merchant
list, this week's news, and the user's last project. **Your job: finalise ONE
idea that passes the user's four rules (section 2), and hand back a
build-ready plan.** The user is setting up the Kwal wallet in parallel and will
feed you test results (section 12).

**Today is Friday 9 October 2026. The event starts at 3:00 pm SGT.** The user
must brief teammates before then, so deliver the final idea within about an
hour. Do not write code or commit anything unless asked.

## 1. How to work with this user

- They delegate judgement calls and expect **a decision plus the reasoning that
  would change it**, not a neutral menu.
- Lead with the human-level problem. Keep explanations plain; they have flagged
  dense writing as hard to follow. Keep code identifiers out of explanations.
- **Separate verified from assumed.** Labels used below:
  **[verified]** = read in the event pages, official docs or source code on
  9 Oct 2026; **[snippet]** = seen only in search-result snippets or
  newsletters; **[memory]** = background knowledge, not checked;
  **[assumption]** = untested inference. Don't upgrade a label without evidence.
- Say plainly which steps are the user's (wallets, signing, venue questions)
  and which are yours.
- The user's laptop runs **Windows**; the Kwal helper scripts need Linux or
  macOS, so they use WSL.

## 2. The four rules the idea must pass (the user's words, then the test)

1. **"Could I build my project without organiser tech? If yes, we're building
   the wrong thing."**
   *Test:* write each idea's "without" version, swapping Reap/Kwal for the best
   ordinary alternative: a company card (Ramp, Brex), a family prepaid card
   (True Link, Greenlight), Stripe, Amazon Business, Splitwise, or **Crossmint's
   new agent checkout toolkit (launched 8 Oct 2026, section 7)**. If the
   "without" version still works, reject the idea or move the organiser tech
   into its core. It passes only when removing Reap/Kwal breaks the core loop,
   not just the payment step. Section 5 lists what is genuinely organiser-only.
2. **"Be early."** Each project changes with current technical progress, what
   has already been done and what is being looked for. What was a limitation a
   month ago may now be mainstream.
   *Test:* the idea relies on something that became possible recently and that
   judges will recognise as the frontier, and it is not what is now table
   stakes. Section 7 has dated signals.
3. **"Align with the track theme as much as possible."**
   *Test:* name one primary and one secondary track and say the pitch in the
   track's own words (section 3). Name the theme it answers.
4. **"Don't be afraid of ambitious ideas. We can build it."**
   *Test:* ambition lives in the concept (who pays, what triggers the spend,
   who holds authority). Protect the build with a **demo spine**: the smallest
   end-to-end loop that must work by 7:00 pm, with ambitious layers on top that
   can be cut without breaking the demo.

## 3. The event [verified — microsite and Luma page, read 9 Oct]

Microsite: https://reap-hackathon-microsite.vercel.app/ ·
Luma: https://luma.com/reap-65labs-hack

| | |
|---|---|
| Event | Reap × 65labs Agentic Buildathon, a Token2049-week side event. 65labs is a Singapore builder community |
| When | Fri 9 Oct, 3:00–10:00 pm SGT |
| Where | SQ Collective x Gen-AI Labs, 65 Mohamed Sultan Rd, Singapore 239003 |
| Schedule | 3:00 registration and team formation · 3:30 kickoff and product/API walkthrough · ~3:45 start building · **4:30 submit team, doors close** · 7:00 dinner · **9:00 submissions close, sharp** · 9–10 optional demos |
| Teams | **2–4 people, mandatory.** Submit the team by 4:30 pm to receive Reap sandbox API access (one key per team). Solo arrivals can find teammates there |
| Judging | After the event; reviews due Mon 12 Oct 5:00 pm SGT. Results date to be confirmed. Submission portal and format shared at the event |
| Prizes | Three tracks, each $500 cash + $500 credits |
| Credits | OpenAI API, Codex and Devin; some sent to the registration email |
| On site | Reap's agentic payments team gives support |

**The microsite's one-line brief:** "Build a working agentic payments demo with
Reap and 65labs. Explore how an AI agent can find products, check out and pay
with a person's permission and spending limits." Luma: "agentic payments must
sit at the core of whatever you make."

**Prize tracks (microsite wording / Luma wording — satisfy both):**
1. **Most Worthwhile Problem** — "A clear, meaningful problem and a product real
   users would want." / "The product real users would download and pay for."
2. **Best Use of Latest Technology** — "New technology that meaningfully
   improves the payment experience." / "The boldest combination of the required
   APIs with other new tech, like agent protocols such as MCP, voice and camera
   inputs, or onchain. It has to be load-bearing."
3. **Best Bridge Between Onchain and Real World** — "A useful link between
   stablecoins and real-world spending or payments." / "The best project
   connecting stablecoins to real-world spending or payments."

**Themes (open spaces, separate from tracks; microsite / Luma):**
- **Business spend** — "Help a team purchase or pay within a budget." / "What
  does a business stop doing by hand when an agent can buy, pay and reconcile
  within budget?"
- **Everyday life** — "Make a recurring or personal purchase easier." / "Which
  everyday spending, for you or someone you care for, should never need a
  human again?"
- **Commerce in chat and apps** — "Bring buying into a chat, community or app."
  / "What if buying and getting paid happened inside the apps people already
  use, like a chat, a browser or a livestream?"
- **Stablecoin money and the agent economy** — "Explore programmable money and
  agents paying for work." / "What can agents do when money is programmable,
  like holding a stablecoin treasury or paying another agent for a real tool
  or API?"

**The hard rule.** Microsite: "Every project must use Reap's Agentic module,
Payward's non-custodial wallet with Agentic, or both. Checkout is simulated: no
real merchant purchases or deliveries. Use test assets for Kwal funding. Don't
bypass Agentic by scraping checkout or handing raw card details to an AI model."
Luma adds: **"Payward's payments endpoints are optional."**

**Steer clear of (Luma, verbatim):** "Generic shopping chatbots that search,
show results and buy. Travel booking. Restricted merchant categories like
gambling and adult content. Workarounds to the Agentic module, like scraping
checkout or handing raw card details to an LLM."
- Shopping-chatbot test: what starts the purchase, and what does the human
  control? A need, event, rule, shared link or onchain signal should start it,
  not a search.
- Also treat alcohol, supplements, pharmacy, tobacco and hacking tools as
  off-limits, even where the merchant sheet lists them.

**Example demos the judges have already seen** (videos, worth skimming; a web
search found nothing else about AGNT Hub, Cashi or Custos):
- AGNT Hub · Pocket agent — https://l8wz6ml09hcmthxx.public.blob.vercel-storage.com/demos/agnt-hub-pocket-agent-demo.mp4
- Animoca Minds · Visa/Reap — https://l8wz6ml09hcmthxx.public.blob.vercel-storage.com/demos/AnimocaMinds_Visareap_video_02.mp4
- Cashi · Agentic checkout — https://l8wz6ml09hcmthxx.public.blob.vercel-storage.com/demos/Cashi-agentic-checkout.mp4
- Custos · Reap demo — https://l8wz6ml09hcmthxx.public.blob.vercel-storage.com/demos/Custos_Reap_Video_v4.mp4
- Payward · Agent payment showcase — https://l8wz6ml09hcmthxx.public.blob.vercel-storage.com/demos/Payward_PWS_Agent_Payment_Showcase_v5_review_1080p.MP4

Minds by Animoca ran a live Visa Intelligent Commerce pilot (8 Jul 2026, Hong
Kong): one person's agent buys within caps that person set [snippet]. **"One
person's shopping agent with caps" is the reference demo, so it's table
stakes.**

## 4. The two build routes, as the docs actually describe them

**Read this before forming ideas. Several assumptions in earlier handovers
were wrong.** The table below is [verified] from `docs.reap.global` and the
Kwal skill's source code (`github.com/payward/kwal-skill`, last updated
5 Oct 2026).

| | **Route A: Reap Agentic API (direct)** | **Route B: Kwal (Payward's non-custodial wallet + Reap)** |
|---|---|---|
| Access | Team key after 4:30 pm. Host `sandbox.api.reap.global`. Every request needs an `Authorization` bearer token and `Reap-Version` header; create calls also need an `Idempotency-Key` | Public, set up now. Gateway `api.sandbox.services.payward.com`, routes under `/kwal/participant/v1/` |
| Who pays | A card the user stores once. Only the **external card** source works; the user types the card on a **Reap-hosted card-entry page**. Reap-card and BIN-sponsor sources are "coming soon". The card must support Visa token service | A **USDC vault on Ink Sepolia** owned by the user's own EVM wallet; Reap issues a sandbox card against it |
| **Human approval per charge** | **Yes.** Each checkout returns a link to a **Reap-hosted approval page** where the user reviews and approves. In sandbox, the header `X-Simulate-Checkout: COMPLETED` (added 24 Sep) completes a checkout instantly | **No approval link in the sandbox.** A sandbox payment is "a simulated card spend against the vault … There is no approval link and no card detail to handle." Kwal approves or declines against vault funds. **You build any permission step yourself** |
| Pre-approved spending ("mandates") | **Not live.** "Mandates are not available yet … the endpoints are not live in sandbox or production." The planned terms: amount ceiling, frequency (weekly/monthly/yearly), max number of charges, merchant scope | Not applicable; spending is bounded by what's in the vault |
| Discovery | Product search (free text, with a `context` of country and currency, price and availability filters, merchant preference) → product details → resolve variant | The same Reap catalogue via Kwal: search → product → variant |
| **Bring your own discovery** | **Since 25 Sep:** a quote can be created from a **merchant checkout URL your app builds** (`externalCheckout`), keeping attribution parameters. Allowlisted merchant domains only; a shipping address is required. **The merchant sheet's "Cart permalink" column is exactly this URL format**, which suggests the hackathon merchants are allowlisted [assumption — ask]. Passing those links to Reap's quote API is the sanctioned flow; opening them in a browser to check out yourself would be the banned workaround | Not exposed by the Kwal helpers |
| Basket | **Several items per quote** (`items` is a list), plus optional offer codes | The helper quotes **one variant per quote** (with a quantity). The service's quote object has a list of lines, so a multi-line request may work [assumption] |
| Currency | Search takes a country and currency context [verified]. **SGD may work** [assumption — ask]; an earlier search snippet mentioned separate Singapore and Mexico API hosts [snippet] | **USD only**: "This sandbox funds only USD quotes with Ink Sepolia USDC." 1 USD = 1 USDC |
| Pricing in sandbox | Merchant prices, shipping and tax itemised | Possibly **1 USDC per item** ("local quote mode", quote IDs start `sandbox_quote_`). Unknown whether it's the default |
| Status updates | Poll the checkout until it's completed, failed or expired. **Agentic webhooks aren't live yet** (FAQ: custom-URL flow "planned shortly after the current webhook work") | Read the payment until completed or declined |
| Concurrency | — | **One payment per card at a time.** Same item + quantity gives the same quote for ~15 min ("quote already used") |
| Money out | — | **Withdrawals need a human operator** (co-signed). No refund-to-wallet flow |
| MCP | **FAQ:** you can build an MCP server or CLI agent on top, but production needs Visa and Reap approval; "MCP client builds remain in sandbox for now." | The Kwal skill is itself an agent skill for Claude Code and Codex |

**Using both routes in one project is allowed ("or both").** But a Kwal card
cannot yet be stored as a payment method on Route A, because Reap-card
enrollment is "coming soon". So each route runs its own checkout.

**What this means for ideas:**
- **Route A is a human-in-the-loop flow.** Every real charge needs the user's
  tap on Reap's hosted page. It suits "the agent prepares, the human
  approves", including links shared in chats (externalCheckout).
- **Route B is the only route where spending can run without a human tapping
  each charge**, bounded by money pre-loaded into an onchain vault. Any idea
  where an agent, a contract or a group spends on its own has to sit on
  Route B, plus a permission layer you build.
- **Reap's mandates are announced but not shipped.** A team that builds the
  equivalent pre-approved, bounded spending authority today (for example an
  Ink contract that releases money into the Kwal vault per approved term) is
  *ahead* of the platform. That is a strong Rule 2 angle, and the Reap judges
  will recognise the schema.

**Other Kwal facts [verified]:**
- **Flow:** register (creates a participant and a 7-day token; **not
  idempotent**, never re-run after a timeout) → set up with an owner wallet
  (deploys the vault, then Reap issuer steps; **vaults deploy one at a time in
  a queue**) → fund the vault with a plain token transfer (no approve step) →
  search → variant → quote → check the quote → checkout → read the payment.
- **Funding:** readiness checks the vault balance, "not receipt of a specific
  transaction". So a top-up from another wallet or a contract probably counts
  [assumption — this is the user's test 4].
- **Several vaults:** a separate participant needs a new credentials file and a
  **new owner wallet** (one owner address per participant). A team can run
  several vaults (one per agent, member or treasury). Register them before the
  4:30 pm rush.
- **Rate limits:** all participants share one provider quota. On a rate-limit
  or "participant unavailable" error, wait 15–30 s and retry, for up to 5
  minutes.
- **No** invoices, payouts or recurring billing; catalogue purchases only.
- **Chain:** Ink Sepolia, chain ID 763373, RPC
  `https://rpc-gel-sepolia.inkonchain.com`. Test ETH: inkonchain.com/faucet;
  test USDC: faucet.circle.com.
- **Running it:** the Python client is importable into a backend. Helpers need
  Python 3.10+ on Linux or macOS. The credentials file must live outside any
  git checkout.

**Payward's optional payments endpoints [verified that they exist; team access
unknown — ask]:** Payward Services (`docs.services.payward.com`) is Kraken's
business API. It covers fiat↔crypto conversions (reusable rules and on-demand),
deposits and withdrawals, transfers between accounts, a hosted fiat-to-crypto
ramp, bank links, swaps (including price-triggered swaps), Auto Earn yield on
eligible balances, and onchain swaps. One guide is titled "Earn between
supplier payments". If teams get credentials, these could make a treasury
earn while idle, convert, or pay out. Don't depend on them until confirmed.

**Related Reap concept [verified, in the main card docs, not the agentic
module]:** in "External" authorization mode, Reap asks *your* endpoint to
approve or decline every card transaction within 1.6 seconds. Kwal appears to
work this way, approving spends against the onchain vault (payments can be
"declined by Kwal" or "declined by Reap") [assumption]. Teams can't configure
this themselves, but it explains why an onchain vault can act as a card's
balance.

## 5. What only the organisers' tech can do (use this for Rule 1)

**The organisers:**
- **Reap:** a stablecoin-native card issuer and licensed Visa issuer
  [snippet].
- **Payward:** Kraken's parent. It completed the Reap acquisition in July 2026
  [snippet], runs the Kwal gateway, and agreed to buy Magic Labs'
  wallet-as-a-service business [snippet].
- **Ink:** Kraken's own Ethereum layer-2 [memory]. Kwal vaults live on its
  test network.
- **65labs:** the host community.

| | Capability | Where | Commodity elsewhere? |
|---|---|---|---|
| A | An agent checks out at 152 merchants through one API; card data never reaches the agent | Reap Agentic | **Increasingly yes.** Crossmint launched a self-serve agent checkout toolkit on 8 Oct 2026 [snippet]. Required here, but not differentiating by itself |
| B | **A payer that isn't a person with a bank account** (a contract, a pooled fund, an agent's own wallet) spends at ordinary card merchants from a **user-owned onchain vault**, with no custodian and no per-charge human tap | Kwal | **Rare.** Agent cards funded by stablecoins exist (MoonPay, Fireblocks, Crossmint) [snippet], but Kwal's non-custodial vault-to-Reap-card is Payward's own and new |
| C | **Bring-your-own-discovery checkout:** any allowlisted merchant link (from a chat, creator post or livestream) becomes a priced, approvable order | Reap Agentic, since 25 Sep | New; check Crossmint's equivalent |
| D | Hosted card entry and a hosted per-charge approval page: the consent and card-security layer you don't build | Reap Agentic | Partly (Stripe, Crossmint) |
| E | Reap's planned mandate model (amount, frequency, max charges, merchant scope), **not live**. You can build its equivalent on B today | Reap roadmap + Kwal | Not shipped by Reap yet |
| F | Ink chain, plus Payward Services (conversions, ramps, earn, swaps), if teams get access | Payward / Kraken | — |
| G | An MCP server or CLI agent on top of Reap, **allowed in sandbox only**; production needs Visa approval | Reap FAQ | Frontier |

**The sharpest Rule 1 pass leans on B, and ideally pairs it with C or E:** an
onchain or non-human payer, or a link shared in a chat, turns into a bounded
real-world purchase. That needs these organisers. **A plain "agent buys for one
person" idea on Route A alone now fails Rule 1, because Crossmint can do it.**

## 6. The merchant list [verified — the organisers' sheet, 152 rows]

The live sheet is on Google Sheets:
https://docs.google.com/spreadsheets/d/1pqb1Jlx1sycembPcjMZ4dxhwzVWXfK7k8RtfNMhb_cs/edit
Its columns are: Category, Market, Merchant, Ships to, Test product, Variant
ID, Item price, Currency, Cart permalink.

- **Currencies:** only **74 merchants price in USD**; all **48 Singapore
  merchants price in SGD**. On Kwal (USD-only), plan on USD merchants unless
  the user's SGD test passes. On Route A, SGD may work (ask).
- **39 USD merchants ship to Singapore**, so a Singapore story can still use
  them.
- **By category:** Computers & Electronics 29 (20 in USD) · Coffee & Tea 17 (10
  SG) · Grocery & Pantry 12 (7 SG) · Fashion 9 · Maker & DIY Electronics 9 ·
  Home & Living 8 · Books & Stationery 8 · Beauty 7 · Audio 7 · Bakery 6 ·
  Office 4 · Drinks & Alcohol 4 (avoid) · Kitchen 4 · Jewellery 3 · Toys 3 ·
  Gifts & Flowers 3 · Health & Wellness 3 (avoid supplements) · Home
  Appliances 3 · Pets 3 · Footwear & Bags 3 · Sports 2 · Department Stores 2 ·
  Household Essentials 2 · Baby & Kids 1.
- **No gift-card merchants.** Any scam-defence demo must use a real catalogue
  item, for example a fake "CEO" or "grandson" asking for a $6,599 GMKtec mini
  PC shipped to a new address.
- The sheet's "Variant ID" may or may not equal the IDs Kwal or Reap return.
  Resolve items through the API.

The full lists are in the appendix.

## 7. "Be early" signals (Rule 2) — dated

Signals from the last ~6 weeks first.

| Date | Signal | Label |
|---|---|---|
| **8 Oct 2026** | **Crossmint launched an Agent Commerce Toolkit**: agents pay with any card and check out online, with card storage, Visa and Mastercard agent credentials and merchant checkout in one self-serve integration. Plain agent checkout is now a commodity | snippet (press release) |
| 6 Oct | Meta is reportedly working with Walmart, Stripe and Sierra on a "personal agent protocol" so companies can tell authorised agent purchases from others | snippet (report) |
| 5 Oct | TikTok launched in-app "Buy Direct" and an AI shopping assistant, the first of several agentic commerce features it plans. Buying inside social and livestream apps is going mainstream | snippet |
| 1 Oct | Cloudflare reportedly put x402 (pay-per-call for agents) into production | snippet (newsletter) |
| 4 Oct | Reap raised its default production rate limits | verified (Reap changelog) |
| **25 Sep** | **Reap: quote from your own checkout URL** (bring your own discovery) and offer codes | **verified** (Reap changelog) |
| 24 Sep | Reap: sandbox can complete a checkout instantly; agentic errors now specific | verified |
| Sep | Mastercard: a score for whether a transaction was started by an AI agent, and "Know Your Agent" checks extended into Agent Pay | snippet |
| Sep | Forbes: giving an agent a wallet is easy; deciding its authority is hard. FinTech Weekly: agentic commerce had its biggest launch month and "nobody wants to own the risk". Checkout.com: only ~3% of transactions involve agents, though 89% of merchants say they're engaging | snippet |
| **Now** | **Reap's mandates (pre-approved, recurring, merchant-scoped spending) are documented but not live.** The industry has announced pre-approved agent spending, but this platform hasn't shipped it | **verified** |
| 5 Oct | Kwal skill repo last updated; Kwal is public and new for this event | verified |
| ~Aug 2026 | OSL launched AgentPay: stablecoin payments between agents (x402, AP2, MPP) | snippet |
| Jul 2026 | Payward completed the Reap acquisition | snippet |
| Jul 2026 | Minds by Animoca and Visa piloted one person's capped agent (now table stakes); a report attributed to Zscaler said fake sites tricked agents into paying for a bogus API licence (4 of 26 models paid) | snippet |
| Jun 2026 | Mastercard Agent Pay for Machines (machine-to-machine payments across cards, accounts and stablecoins); Visa Intelligent Commerce integrated with OpenAI. But Forrester reported OpenAI pulling back Instant Checkout | snippet |
| Apr 2026 | Visa Intelligent Commerce Connect pilot | snippet |
| Mar 2026 | Stripe and Tempo launched MPP, where agents pre-authorise a spending limit and stream payments in stablecoins or fiat | snippet |
| Preview | Amazon Bedrock AgentCore payments, built with Coinbase and Stripe | snippet |

**The previous agent's reading (challenge it if your research disagrees):**
- **Table stakes now:** an agent that checks out at merchants, and one person's
  agent with caps.
- **Frontier:** pre-approved, bounded authority for agents that act on their
  own, which Reap hasn't shipped and you can build on Kwal. Also: payers that
  aren't people (contracts, groups, agents with their own treasury, machines),
  buying from links inside the apps people already use, proving an agent was
  authorised ("Know Your Agent"), and who carries the risk.

## 8. Earlier shortlist, judged against the rules and the corrected facts

Don't inherit these; reuse their useful parts.

- **Day One** — a new hire is added, and the agent buys their kit from a USDC
  treasury within a per-person budget. It has a fraud beat (a fake "CEO" asks
  for 3 × $6,599 mini PCs shipped to a new address; it's refused) and a finance
  ledger. *Buildable* on USD electronics. **Fails Rule 1:** Ramp plus Amazon
  Business, or now Crossmint, does it. *Keep:* the electronics vertical, the
  fraud beat, reconciliation.
- **Guardian** — relatives fund a parent's spending and set rules; the parent
  asks by voice; off-rule requests go to the funder; scams are refused.
  *Strong worthwhile story:* Singapore lost S$913.1M to scams in 2025, and
  over-65s were ~15% of victims with the highest average loss, S$37,053
  [snippet, police figures]. **Mostly fails Rule 1** (True Link-style cards
  exist). Partly rescued if several relatives in different countries fund one
  onchain vault, and the in-rule purchases run without a tap (Route B).
- **Flat Pot** — flatmates or a club top up one shared vault; requests come in
  the group chat; big buys need a group vote. **Passes Rule 1 better** (many
  wallets fund one card), but "out of dish soap" → search → buy is the chatbot
  shape. It improves if requests are *shared merchant links* rather than
  searches (Route A's checkout-URL flow), but then each charge needs a hosted
  approval.
- **Dropped earlier:**
  - Invoice and subscription agents: no invoices or recurring billing, and
    mandates aren't live.
  - x402 rail router: not a sponsor API.
  - Price-drop orders: sandbox prices don't move.
  - Livestream "buy what you see": revisit now via shared links.
  - Photograph the empty bottle: search-and-buy with a camera.
  - Aid vouchers: unclear buyer, privacy, one card for many families.

## 9. Starting directions (seeds, not answers)

Generate your own too. Each puts a non-human, onchain or group payer in front
of a normal merchant, or uses the newest Reap features.

1. **The mandate Reap hasn't shipped, built onchain.** An Ink contract holds
   USDC under the user's own terms, mirroring Reap's planned schema (amount
   ceiling, frequency, max charges, merchant scope). The agent can only spend
   what the contract releases into the Kwal vault for an in-terms purchase.
   Needs a human-facing use case on top (care for a parent, a team's budget, a
   community treasury). Strong for Rules 1 and 2; it depends on the
   contract-deposit test.
2. **Agents with their own treasury.** An agent earns USDC for work, paid
   onchain by a person or another agent, and spends from its own vault on real
   inputs within its owner's terms. Matches the "agents paying for work" theme
   word for word.
3. **Escrowed group commerce in a chat.** Members pledge into your own contract.
   When the target or vote passes, the contract funds the vault and the agent
   buys. If not, pledges return automatically. This avoids Kwal's no-refund
   limit because money only enters the vault on success.
4. **Link-to-purchase inside the apps people use.** A merchant link dropped in a
   group chat, a creator's post or a stream becomes a priced order through
   Route A's checkout-URL flow. A group or onchain pot decides, and the hosted
   page approves. Early (25 Sep feature; TikTok's 5 Oct move shows the
   direction). Check that it isn't a shopping chatbot: the trigger is a shared
   link plus a decision, not a search.
5. **Signal-triggered purchases.** An onchain or real-world signal (sensor,
   device telemetry, an oracle) triggers a bounded purchase, for example
   machines or nodes ordering their own replacement parts from their own
   earnings. Mastercard's "Agent Pay for Machines" shows the direction. The USD
   electronics catalogue fits.
6. **Cross-border family pot** (Guardian upgraded). Several relatives fund one
   vault; the parent's in-rule needs are bought without a tap; off-rule ones go
   to a relative; each relative sees onchain what their money bought.
7. **An MCP server as the load-bearing layer.** Any AI client (Claude, ChatGPT,
   Codex) gets a bounded, vault-funded purchasing tool. Reap says MCP builds
   are sandbox-only today: frontier, and named in Track 2. Better as a layer on
   one of the above than as the product.

Check every seed against section 4: Route A needs a human tap per charge; Route
B allows one payment at a time, no refunds, USD only, and possibly 1-USDC
pricing; contract and shared top-ups are untested.

## 10. Reusable parts from the user's last project, laeria.ai [verified]

Repo `jaydonnnk/laeria-ai` (Python FastAPI backend, Next.js 14 frontend). Built
for the StraitsX Agentic Playground Hackathon (Aug 2026). **Do not resubmit
it** (banned "research → pick → buy" shape, dead Reddit data source,
near-scraping checkout). Disclose any reuse, and ask about the prior-code rule
at kickoff.

- **Spending-rules check:** `backend/services/payment.py:53` and
  `backend/core/models.py:121`. An unset limit means zero allowance, not
  unlimited. Covers a per-transaction cap, a monthly cap, confirm-above
  thresholds, category allowlists and blocked vendors. 19 tests in
  `backend/tests/test_mandate.py`.
- **Spend ceiling:** `backend/api/routes/actions.py:345-361`. The ceiling is the
  minimum of the approved amount plus drift tolerance, the per-transaction cap,
  monthly headroom and wallet backing.
- **Wallet-signed rules:** `backend/services/delegation.py` and
  `frontend/lib/wallet.ts`. The user's wallet signs the exact spending rules
  (EIP-712) and the server recovers the signer. Directly reusable for "terms
  signed by the vault owner".
- **Prompt-injection screening:** `backend/services/bedrock_guardrails.py`
  (needs AWS; otherwise substitute a model check using the event's OpenAI
  credits).
- **Demo craft:** `docs/DEMO_SCRIPT.md` (pre-flight checklist, timed beats,
  fallbacks table) and record/replay fixtures so a flaky upstream can't kill
  the demo.
- **Don't reuse:** the Playwright checkout, Shopify storefront, card issuers,
  x402 rail, Reddit scraping.
- **Lesson from its critique:** purchases worth automating are triggered by a
  need, event or rule, not a search.

## 11. Constraints for the build

- **Build window:** about 5 hours, ~3:45–9:00 pm, with dinner at 7.
- **Team:** 2–4 people, plus OpenAI, Codex and Devin credits.
- **Reap key timing:** it arrives after 4:30 pm, so a Route A spine can't be
  tested before then. Kwal works now.
- **Judging:** the submission is what's judged (video, README, repo), not the
  live demo. Record by ~8:15 pm.

## 12. What the user is doing now, and what to ask them

The user is setting up Kwal: register, vault setup with a fresh wallet, fund
with test USDC, one throwaway purchase. Ask for these results; each one changes
what's buildable:

1. **Did the throwaway purchase complete straight from the vault, or did an
   approval link appear?** This confirms Route B can run without a tap.
2. Did the target products show up? (For example the Keychron B40, Satechi
   Snap Hub, Twelve South PowerBug.)
3. **Does an SGD item quote and check out on Kwal?** (For example Dutch Colony
   coffee or Zenxin cabbage.)
4. **Does a top-up from a second wallet count toward vault funding?** Even
   better: from a contract. This is critical for seeds 1, 3 and 6.
5. Do quote IDs start with `sandbox_quote_`? That means 1-USDC pricing is on.
6. Can one Kwal quote hold several items?
7. How long did vault setup take?

If the final idea needs several vaults, the user must register those extra
participants with new wallets **before 3 pm**.

## 13. Your deliverable

1. **10–15 fresh ideas**, one line each, with their Rule 1 "without" version
   (including "could Crossmint do this?") and a verdict.
2. **A scoring table** for the survivors:
   - Rule 1 (does removing Reap/Kwal break the core loop?)
   - Rule 2 (why now, dated)
   - Rule 3 (primary and secondary track, theme)
   - Rule 4 (ambition versus demo spine)
   - Route (A, B or both) and buildability given section 4
   - The 30-second demo moment
3. **ONE final idea**, with:
   - Name, one-line pitch, who it's for, how often they hit the problem, what
     they do today, and why they'd pay.
   - **Rule 1 proof:** a table mapping each organiser capability (section 5)
     to what breaks without it.
   - **Rule 2 "why now":** dated evidence with labels.
   - **Rule 3:** primary and secondary track, the pitch in the track's own
     words, the theme.
   - **Rule 4:** the ambitious layer versus the demo spine (what must work by
     7:00 pm).
   - **Route choice** (A, B or both) and why, given section 4.
   - **Steer-clear checklist:** all four items, plus "what starts the purchase,
     and what does the human control?"
   - **Vertical and demo items** from the merchant list, with prices and
     currency.
   - **API calls:** use only routes documented in section 4; label anything
     else as an assumption. Don't invent endpoints.
   - **Demo beats** (≤3 minutes) and the 30-second moment.
   - **Risks and mitigations,** especially section 4's realities: hosted
     approval on Route A; on Route B one payment at a time, no refunds, USD,
     1-USDC pricing; the shared rate limit and the 4:30 pm vault queue.
   - **Build plan for 2–4 people:** who does what; milestones at 5:00 pm
     (spine purchase from your own code), 7:00 pm (spine end to end), 7:45 pm
     (feature freeze), 8:15 pm (video recorded), 8:50 pm (submitted).
   - **Video and README outlines.** The README must have an honest "what is
     simulated" section and the reused-code disclosure.
   - **The user's jobs versus the team's jobs.**
   - **What would change your mind.**
4. **Questions for the 3:30 pm kickoff**, at minimum:
   - Which merchant domains are allowlisted for checkout-URL quotes? Are the
     sheet's cart permalinks meant for that?
   - Which test card do we enter on the hosted card-entry page (it must
     support Visa token service)?
   - May demos use the sandbox instant-complete header, or should the hosted
     approval page be shown?
   - Is there any sandbox preview of mandates, or of agentic webhooks?
   - Does SGD work on Route A? On Kwal?
   - Is 1-USDC pricing on for everyone on Kwal? Can a contract or another
     wallet fund a vault? Can one Kwal quote hold several items?
   - Do teams get Payward Services credentials (conversions, ramp, earn)?
   - Is pre-written code allowed (disclose the laeria reuse either way)? What
     are the video length and submission format?

## Sources (read or seen on 9 Oct 2026)

- Microsite: https://reap-hackathon-microsite.vercel.app/ ; Luma: https://luma.com/reap-65labs-hack
- Reap Agentic docs (read in full): https://docs.reap.global/agentic-payments/overview ,
  /how-it-works , /setup , /one-time-purchases , /recurring-purchases , /lifecycle , /faq ;
  changelog https://docs.reap.global/changelog ; authorization mode
  https://docs.reap.global/program-configuration/authorization-mode ; index https://docs.reap.global/llms.txt
- Kwal skill (read in full): https://github.com/payward/kwal-skill
- Payward Services docs index: https://docs.services.payward.com/llms.txt
- Merchant sheet: https://docs.google.com/spreadsheets/d/1pqb1Jlx1sycembPcjMZ4dxhwzVWXfK7k8RtfNMhb_cs/edit
- Crossmint Agent Commerce Toolkit (snippet): https://prnewswire.com/news-releases/crossmint-launches-agent-commerce-toolkit-enabling-ai-agents-to-pay-with-any-card-and-check-out-online-through-one-integration-302901649.html
- TikTok agentic commerce (snippet): https://www.pymnts.com/commerce/social-commerce/2026/tiktok-kicks-off-agentic-commerce-push-with-ai-shopping-assistant/
- Meta agent standards (snippet): https://gizmodo.com/meta-wants-to-write-the-industry-standards-for-safe-agentic-commerce-report-says-2000822526
- FinTech Weekly on liability (snippet): https://www.fintechweekly.com/magazine/articles/agentic-commerce-launch-month-liability-risk-2026
- Mastercard trust services, Sep 2026 (snippet): https://www.mastercard.com/us/en/news-and-trends/press/2026/september/new-trust-and-intelligence-services.html
- Mastercard Agent Pay for Machines, Jun 2026 (snippet): https://www.mastercard.com/us/en/news-and-trends/press/2026/june/mastercard-launches-agent-pay-for-machines.html
- OSL AgentPay (snippet): https://finance.yahoo.com/markets/crypto/articles/osl-debuts-agentpay-enable-stablecoin-071821752.html
- Payward completes Reap acquisition (snippet): https://reap.global/newsroom/payward-completes-acquisition-of-reap
- Singapore Police 2025 scam figures (snippet): https://www.police.gov.sg/media-hub/police-life/2026/02/scams-and-cybercrime-fell-by-almost-a-quarter-in-2025

---

## Appendix: merchant lists by category [verified — organisers' sheet]

Format: merchant (test product, price). `*` = ships to Singapore. Avoid Drinks &
Alcohol, Health & Wellness supplements, Jewellery and the hacking tools in
Maker & DIY (Flipper Zero, Hak5).

USD-priced merchants (Kwal can fund these), grouped by category. * = ships to SG
- **Computers & Electronics** (20): arzopa.com (Arzopa Z1C PLUS 17.3in 1080p Portable, $139.99); auragaminggear.com (SPEED MOUSEPAD - XL, $64.99); baseus.com (Baseus PicoGo AR11 Power Bank 10000mAh, $69.99); computerexchange.com* (Optiplex SFF 7010, $699.99); divinikey.com* (HMX Snowflake Linear Switches - 18 Set, $6.3); dockcase.com* (Dockcase Smart USB-C Hub 7-in-1 with M, $109.99); epomaker.com* (EPOMAKER Stomp Tactile Switch Set - 10, $24.99); gearit.com (1000ft Bulk Cat6 Outdoor Ethernet Cabl, $156.98); gloriousgaming.com* (GMMK PRO Switch Plate Replacement - AN, $29.99); gmktec.com* (GMKtec EVO-X5 Pro Ryzen AI Max+ PRO 49, $6599); hypershop.com (HyperDrive GEN2 15-in-1 USB-C Docking, $299.99); keychron.com* (Keychron B40 Wireless Keyboard - Deep, $49.99); mavigadget.com* (Zero Setup Dual Screen Portable Laptop, $359.95); pixiogaming.com (Pixio PX27 LUMA OLED Glossy, $899.99); plugable.com (Plugable USB-C Triple Monitor Docking, $149.99); satechi.net* (USB-C Snap Hub - Citrus, $44.99); schupantech.com (DELL OPTIPLEX 7010 USFF | Intel Core i, $299.99); techforless.com (Kensington K75406US Pro Fit Ergo Wirel, $59.97); twelvesouth.com* (PowerBug 25W (Qi2.2) - White/Dune, $49.99); uperfect.com* (BE185GF 18.5in 1080P Wireless Touchscr, $299.99)
- **Beauty & Personal Care** (6): beautybakerie.com* (Lip Whip Remover, $11.2); beautyofjoseon.com* (Slow Aging Trio, $38.35); bluemercury.com (Pumpkin Chai Liquid Soap, $28); judydoll.com* (Mini Makeup Palette, $14.99); kbeautymakeup.com (Abib PDRN Collagen Lip Mask 11g, $29.7); kravebeauty.com* (Barrier On-The-Go Mini Kit, $49.5)
- **Coffee & Tea** (5): badasscoffee.com (Pumpkin Pecan Paradise Flavored 12oz C, $18.99); bonescoffee.com (Jacked O' Lantern 12oz - Ground, $17.99); coffeeam.com (Freedom Blend Coffee - 0.5LB / Whole B, $11.95); deathwishcoffee.com* (White Chocolate Pistachio Coffee - 1 b, $13.99); harney.com* (Santa Cruz Peanut Butter - 16 oz Jar /, $10)
- **Audio & Music** (5): eddieselectronicsandgadgets.com* (G1 NEO Gaming Audio Mixer with XLR Mic, $133.3); headphones.com (Lewitt LW6 Wireless Headphones, $699); hifigo.com* (SMSL R3 CS43131 Gaming DAC & Headphone, $159.99); linsoul.com* (SMSL SU-3 Desktop DAC, $189.99); shenzhenaudio.com* (SMSL SU3 AK4496 DAC, $189.99)
- **Books & Stationery** (4): atomicbooks.com (Amazing Venom #4 [PRE-ORDER], $4.99); baronfig.com* (Thinker Tote Bundle, $95); mossery.co* (Far From Above Undated Planner, $13.5); stationerypal.com* (Puppy Notepad - Moon, $1.41)
- **Fashion & Apparel** (4): coinbaseshop.com* (Coinbase Heavy Metal Hat, $30); everlane.com* (W AAP Featherweight Alpaca LS Wrap Top, $148); fashionnova.com (Modern Essential Zip Up Jacket - Navy, $30.99); gymshark.com (Gymshark Power T-Shirt - Chalk Marl -, $36)
- **Kitchen & Dining** (4): fromourplace.com (Walnut Knife Block, $99); greatjonesgoods.com (Big Deal & Saucy, $190); materialkitchen.com (The Forever Peeler - Stainless Steel, $40); misen.com* (9-Piece Dinnerware + Flatware Set (Ser, $139)
- **Home & Living** (3): abchome.com (Amiko End Table, $279); brooklinen.com* (Super-Plush Turkish Cotton Hand Towels, $33); tuftandneedle.com (SNOOZ Go 2 Travel White Noise Machine, $60)
- **Grocery & Pantry** (3): exoticsnacks.com (Lay's Mini Potato Bites Honey Butter F, $4.99); magicspoon.com (Variety 6 - 1 case (6 boxes), $55.5); partakefoods.com (Teeny Tiny Chocolate Chip - 6 boxes, $35)
- **Maker & DIY Electronics** (3): flipper.net (Flipper Zero, $169); nzxt.com (F420 RGB Core - White, $74.99); shop.hak5.org* (LAN Turtle Student Bundle, $150)
- **Bakery & Desserts** (3): jenis.com (Confetti Brownie Batter, $17); levainbakery.com (Fall Bounty Assortment - 4 PK, $32); riverdogbakery.com (Limited Edition Pumpkin Egg Puffs, $12)
- **Jewellery & Watches** (2): atoleajewelry.com* (The Sunshine Bauble, $78.95); evryjewels.com* (Let it Shine Necklace - 14K Gold Plati, $13.99)
- **Health & Wellness** (2): goli.com* (Zero Sugar ACV+ Gummies - 1 Bottle, $17.98); ritual.com (Men's Multivitamin 18+ - 30 servings, $37.5)
- **Drinks & Alcohol** (2): liquiddeath.com* (Pot Head Planter - Red, $34); rabbitwine.com (Leak-Proof Beverage Tumblers - taupe, $30.99)
- **Pets** (2): maxbone.com* (Marc Jacobs x maxbone Daisy Collar - S, $25); wildone.com* (Cat Slow Feeder - Lilac, $12)
- **Household Essentials** (2): packagefreeshop.com (Multi-Purpose Cleaning Spray - Lavende, $14); publicgoods.com* (Silicone Travel Bottles Refill Kit - 5, $19.95)
- **Toys & Games** (1): explodingkittens.com (Berry Cherry Parrot Punch, $9.99)
- **Sports & Outdoors** (1): forzasports.com* (SISU Aero Guard 2.0mm Adult Mouthguard, $19.99)
- **Footwear & Bags** (1): thursdayboots.com* (Highland Sweater - Driftwood - M, $148)
- **Office & Business Supplies** (1): zmdesktop.com* (Modular Space-Saving Laptop Stand (202, $58)

SGD-priced (Singapore market) merchants, by category:
- **Coffee & Tea** (10): alchemist.com.sg (El Borbollon - Espresso / 200g, S$20); bettrcoffee.com (Brazil Mogiana 14/16 - 500g, S$20); commonmancoffeeroasters.com (Yolan Tirta Sulawesi, Indonesi, S$23); dutchcolony.sg (Gatuyaini - 200g / Whole Bean, S$24); forewordcoffee.com (Mini Ondeh Ondeh Tray Cake, S$43.5); gryphontea.com (Premium Asatsuyu Matcha, S$35); huggscoffee.com (Colombia Naranja Salsa (Oporap, S$26.9); parchmen.co (Cindy Li, Thanaka Coffee (Cham, S$8); pppcoffee.com (Hacienda El Obraje - 250g / Wh, S$30); prycetea.com (Mandarin Liu Bao Cha, S$32)
- **Grocery & Pantry** (7): camelnuts.com (Muruku Fine 1kg, S$8); irvinsaltedegg.com (IRVINS Salted Egg Tomato Fish, S$8); sixeleven.xyz (CocoCoast - Chocolate Coconut, S$3.85); supernature.com.sg (Organic Lime Sea Salt Kombucha, S$8.08); thefishwives.com (Yellow Onion (500g) - 500g Pac, S$4); thegoldenduck.co (Signature Snackbox: Sichuan Ma, S$39); zenxin.com.sg ([FRESH] Organic English Cabbag, S$3.3)
- **Home & Living** (4): journeyeast.com (Gangzai Raja Square Trinket Tr, S$75); lux-lumens.sg (Avery - Industrial Linear Ceil, S$99); scanteak.com.sg (Brunja Dining Chair, S$329); thesocialspace.co (The Little Mama Shop (150-piec, S$15)
- **Computers & Electronics** (3): anker.com.sg (Anker Nano USB-C Hub 8-in-1 Du, S$72.9); prismplus.sg (PRISM+ W290U monitor, S$199); ugreen.com.sg (UGREEN Dual Mode Bluetooth + 2, S$32.99)
- **Bakery & Desserts** (3): birdsofparadise.sg (Paradise Set, S$76); janicewong.online (69% Peru Single Origin Pepperm, S$14); plainvanilla.com.sg (Box of 6 Cupcakes - Specials, S$34.5)
- **Office & Business Supplies** (3): boxgreen.co (The Trio Big Bag of Snacks, S$50); ergotune.com (F-Clamp Pegboard Panel - Black, S$59); picketandrail.com (Geometry 12 Custom Table - Can, S$699)
- **Books & Stationery** (3): byndartisan.com (Wabisabi Luggage Tag - Brown/O, S$85); kinokuniya.com.sg (名偵探柯南 (106), S$9.4); popular.com.sg (True Singapore Ghost Stories B, S$10.79)
- **Fashion & Apparel** (2): kydra.co (Axis Linerless Shorts - Navy /, S$58); thetinselrack.com (Tessa Button Top (Linen) - Bla, S$42)
- **Department Stores & Marketplaces** (2): metro.com.sg (Kose Sekkisei Brightening Holi, S$34); shoppy.sg (Ultrasonic Mosquito Repeller, S$22.9)
- **Footwear & Bags** (2): pazzion.com (Cara Woven Bag - Dark Brown -, S$96); worldpolo.sg (Heavy Duty Luggage - Cinnamon, S$45.9)
- **Gifts & Flowers** (2): spectrumstore.sg (Puffy Laptop Sleeve 13/14in -, S$59); windflowerflorist.com (Bonbon - Standard, S$85)
- **Drinks & Alcohol** (1): brewlander.com (SG LAHger - 6 Pack, S$33)
- **Home Appliances & DIY** (1): intertech-hardware.com (WD-40 Bike Degreaser, S$19)
- **Pets** (1): kohepets.com.sg (Absolute Bites Tote Bag, S$9.9)
- **Baby & Kids** (1): motherswork.com.sg (Little Rei Eco-Conscious Tape, S$16.9)
- **Health & Wellness** (1): pupsik.sg (Youha Warming Lactation Massag, S$34.9)
- **Beauty & Personal Care** (1): sg.allies.shop (Peptint Tripeptide & Goji Cell, S$48)
- **Toys & Games** (1): toyster.sg (You Can't Say Umm - Party Game, S$39.9)
