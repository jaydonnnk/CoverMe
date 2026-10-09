# Scaffold scope and plan review

This bootstrap implements the F1 foundation and prepares the J1/F2 documents.
It does not mark any product milestone complete or claim joint interface sign-off.

## Included

- Next.js App Router project under `app/`: TypeScript, Tailwind, ESLint, npm lock,
  three static scaffold routes. Product screens and wallet integration remain F5.
- FastAPI `service/main.py` with `/health`, local CORS and health/CORS tests.
- Foundry configuration, pinned `forge-std`, a toolchain test, empty source/script
  areas and the unchanged pinned ERC-8004 reference submodule.
- Machine-readable EIP-712 request fields, deployment placeholders and shared
  interface draft. JSON checks enforce the signed field names/types/order.
- Ownership rules, branch/PR guidance, CODEOWNERS, a PR template and four CI jobs.
- Secret/build ignore rules, LF conventions for WSL/macOS and separate server vs
  browser environment templates. No API key or test key is needed to build.

## Deliberately left to the owners

Jaydon implements the contracts, laeria guard/wallet ports, Kwal and chain calls,
fixtures, demo/reset scripts and `docs/DEMO_SCRIPT.md`. Francesco implements
registry deployment, registration, agent/runner, fake payments, SSE, judge, MCP
and actual screens. File placeholders are not permission to overwrite the other
owner's work after the bootstrap.

## Integration risks found in the plan

Resolve the open decisions at the end of `shared/INTERFACES.md` before parallel
implementation. In particular, fee headroom/sandbox pricing and the undefined
approval signature cannot be filled in independently by app and contract authors.
The shared deployment JSON is still a single-file conflict hotspot: section-only
edits and small coordinated PRs are the least disruptive approach that preserves
the layout in the supplied plan.

ERC-8004's upstream is now Hardhat and upgradeable. Treat its build/deployment
as a separate toolchain; a successful root Foundry build does not validate it.
Keep upstream source unchanged and verify its deployment procedure before F3.

Add-on estimates in F8 exceed its 30-minute slot even individually. Follow the
plan's main-product gate and cut order rather than putting add-ons in the scaffold.

## Repository settings still needed

A repo admin must enable main branch protection/rulesets and required CI/review
checks after this scaffold is pushed. CODEOWNERS routes review requests but does
not enforce them. This task makes no remote repository settings changes.

## Dependency caveats at bootstrap

`npm audit --omit=dev` reports no app runtime vulnerabilities. The generated
Next.js ESLint dependency tree currently reports five high-severity development
findings through `braces` (GHSA-vfj7-8cjw-p6xm); no patched `braces` release is
available at bootstrap. Do not blindly use `npm audit fix --force`, which proposes
an incompatible ESLint-config/Next.js downgrade. Recheck when patched tooling ships.

The unchanged pinned ERC-8004 upstream reports 36 npm findings (including ten
high). Its install also requires `--legacy-peer-deps` for an existing Hardhat 2/3
plugin mismatch. Compilation and all 79 upstream tests pass with compile-only
localhost URL settings; review dependencies and deployment tooling before F3.
These external dependency warnings are not payment/security-test coverage.
