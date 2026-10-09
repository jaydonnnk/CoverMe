# Contracts

Jaydon owns `src/`, `test/`, `script/` and Foundry configuration. The starter has
only a toolchain smoke test; Checkpoint, Bond, Sender and deployment logic are not
implemented. `forge-std` is a pinned Git submodule.

From this folder:

```sh
forge build
forge test
forge fmt --check
```

## ERC-8004 — Francesco

`lib/erc-8004-contracts` is pinned as a Git submodule. Keep the reference contracts
unchanged. **Its current upstream uses Hardhat, not Foundry**, so `forge build`
here does not compile the registry implementations. Build them separately:

```sh
cd lib/erc-8004-contracts
npm ci --legacy-peer-deps
SEPOLIA_RPC_URL=http://127.0.0.1:8545 \
MAINNET_RPC_URL=http://127.0.0.1:8545 npx hardhat compile
```

Read upstream `README.md`, `UPGRADEABLE_IMPLEMENTATION.md`, `hardhat.config.ts`
and `scripts/` before F3: the identity/reputation registries are upgradeable.
Ink Sepolia is not preconfigured upstream; agree how to supply network settings
without altering the reference contract source. No deployment is part of F1.
Never reuse registry addresses from another chain.

The pinned upstream lockfile has a Hardhat 2/3 plugin peer conflict, requiring
`--legacy-peer-deps`. Its config also rejects empty Sepolia/mainnet URLs even
when only compiling; the localhost URLs above satisfy validation without
connecting to or deploying on either network. No private key is needed to compile.
Do not run an upstream deploy command with these compile-only settings.

To run upstream's local core and upgradeability tests:

```sh
SEPOLIA_RPC_URL=http://127.0.0.1:8545 \
MAINNET_RPC_URL=http://127.0.0.1:8545 npm test
```

After deployment, Francesco writes `registries` and Jaydon writes `cover` in
`../../deployments/ink-sepolia.json`. These placeholders are not usable addresses.
