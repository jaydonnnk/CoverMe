# App integrations

Francesco owns this folder **except `wallet.ts`**, which Jaydon will port from laeria.
Do not select a different wallet library or create a competing wallet implementation.
The four wallet functions are drafted in `shared/INTERFACES.md` section 3.3.
Read the EIP-712 types from `shared/purchase-request.json` and addresses/ABIs from
`deployments/ink-sepolia.json`; refuse signing/sending when addresses are placeholders.

`NEXT_PUBLIC_SERVICE_URL` is the browser-facing FastAPI URL. Private keys and API
keys must never be imported by the app or added to a `NEXT_PUBLIC_*` variable.
