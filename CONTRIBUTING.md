# Working together

The shared repo is `jaydonnnk/CoverMe`. Use one base (`main`), personal feature
branches and small PRs. The scaffold is the initial bootstrap; after it lands,
follow the ownership boundaries below. Do not commit feature work directly to main.

## Folder owners

| Area | Owner |
|---|---|
| `contracts/`, excluding the ERC-8004 submodule | Jaydon |
| `contracts/lib/erc-8004-contracts/` | Francesco |
| `service/guard/`, `service/payments/`, `service/fixtures/` | Jaydon |
| Rest of `service/` | Francesco |
| `app/lib/wallet.ts` | Jaydon |
| Rest of `app/` | Francesco |
| `scripts/`, `docs/DEMO_SCRIPT.md` | Jaydon |
| `shared/`, `deployments/`, root config, CI and dependency submodules | Coordinate together |

`.github/CODEOWNERS` requests reviewers once it is on main. Both accounts must
have write access for GitHub to recognize them. CODEOWNERS does **not** itself
protect main: a repository admin should enable a branch rule requiring PRs, a
review and the four CI checks. Requiring one listed owner is not requiring both;
shared interface changes need both people's explicit agreement.

## Start a task

```sh
git switch main
git pull --ff-only origin main
git switch -c francesco/F4-agent-runner  # or jaydon/J2-laeria-ports
# Work, run checks, stage your files, commit.
git push -u origin HEAD
gh pr create --base main
```

Before merging, bring your branch up to date with `origin/main` and rerun checks.
Rebase your own branch only; if you must update a published personal branch after
a rebase, use `--force-with-lease`, never `--force`, and tell anyone using it.
After merging, start the next task from updated main rather than your old branch.

## Keep conflicts small

- No broad formatting sweeps or renaming the other person's files.
- Announce cross-owner edits before starting. Keep them in a separate PR.
- `shared/INTERFACES.md` starts as a **draft**, not a signed-off agreement. Review
  it together for J1/F2; after agreement, interface changes require coordination.
- EIP-712 field types/order live in `shared/purchase-request.json`. Do not create
  independent signing definitions in the app, Python or Solidity.
- Deployment JSON: Francesco changes **only `registries`**; Jaydon changes
  **only `cover`**. Do not regenerate the whole document or reformat the other
  section. Top-level network metadata is shared. Keep `agentId` as a decimal
  string once known, to avoid JavaScript integer precision loss.
- `app/package.json` and `app/package-lock.json` belong to Francesco; keep them
  together in dependency PRs and use npm only. Jaydon coordinates wallet dependency
  additions before porting `wallet.ts`. Service requirements are coordinated if
  the payment port needs additional packages.
- Submodules are pinned commits. Run `git submodule update --init --recursive`
  after pulling and do not use `--remote` unless explicitly upgrading a dependency.
- Prefer mocked payment work in `service/fake_payments.py`, not Jaydon's module.

## Safety

Test wallets only. Put service keys in root `.env`, Kwal credentials outside all
Git repositories, and **public configuration only** in `app/.env.local`. Never
prefix a secret with `NEXT_PUBLIC_`. Sanitize replay fixtures before committing.
Ignore rules are a backup, not a substitute for reviewing `git diff --cached`.

Local validation commands are in [README.md](README.md). Product functionality
must be reviewed by a human; the toolchain smoke tests are not security tests.
