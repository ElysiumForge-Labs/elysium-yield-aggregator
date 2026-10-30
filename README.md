# elysium-yield-aggregator

ERC-4626 vault that routes HYPE across several yield sources on Elysium, plus the off-chain tools used to design and test it.

Part of [ElysiumForge Labs](https://github.com/ElysiumForge-Labs).

> **Independent research repository.** Not affiliated with, endorsed by, or sponsored by Kinetiq or Hyperliquid. This is a reference implementation and backtester, not an audited production system. Simulation numbers are not a projection of live vault performance.

Allocation is regime-driven: staking, kHYPE, perp funding, basis, and an optional xHYPE leg.

Two on-chain dependencies are not available on testnet. They are scheduled for an ArbOS upgrade about four weeks after Elysium mainnet:

- HyperCore market-data precompile
- `ElysiumCoreWriter` predeploy

Until those addresses exist, legs talk to mock-friendly interfaces and the keeper runs against a mock venue.

## Layout

```
solidity/          vault, legs, RegimeDetector, TradeOnlyAgent
hypeback/          Python backtester and aggregator simulator (stdlib only)
keeper-runtime/    TypeScript keeper: EIP-712 sign + submit
dev-harness/       Foundry mocks for HyperCore precompiles
elix-kit/          small Foundry + TypeScript starter
dashboard/         static DeFiLlama snapshot page
docs/              specs, design notes, roadmap
check_repo.py      independent docs + Solidity drift check
```

## Requirements

- Python 3.10 or newer (backtester has no third-party packages)
- Foundry for `forge test`
- Node.js 20 or newer for `keeper-runtime` and `elix-kit`
- Optional for Python compile/deploy: `py-solc-x`, `web3`, `eth-abi`, `eth-utils`

## Backtester

Data is bundled: `data/hype_funding_full.json` (15,750 hourly HyperCore funding records, 2024-12-05 to 2026-09-22 UTC).

```bash
python -m hypeback sanity
python -m hypeback run --hr 1.0 --lev 3 --vol 0.70 --staking 0.0189 --seed 42
python -m hypeback mc --hr 1.0 --lev 3 --paths 500
python -m hypeback sweep --hrs 1.0 1.5 2.0 --levs 2 3 5 --rebals 6 12 24
python -m hypeback gate --hr 1.0 --lev 3
python -m hypeback agg
python -m hypeback fetch --coin HYPE --hours 8760
python -m hypeback serve --port 8760
```

The local UI binds to `127.0.0.1` only.

| Flag | Default | Meaning |
| --- | --- | --- |
| `--hr` | 1.5 | Hedge ratio (perp notional / spot value) |
| `--lev` | 3.0 | Perp leverage |
| `--vol` | 0.70 | HYPE annualized volatility |
| `--staking` | 0.0189 | Staking APY |
| `--capital` | 100000 | Initial capital, USD |
| `--rebal` | 12 | Rebalance interval, hours |
| `--seed` | 42 | Price-path seed |
| `--window` | all | Last N hours of funding history |

Kill gate (exit 0 pass, 1 fail): net APY above 4% annualized, max drawdown below 15%, no liquidation.

`python -m hypeback agg` compares the regime-driven allocator to a static benchmark. On 15 seeds over that funding window the median alpha was about +2.1% APY (aggregator ~11.96% vs static ~9.85%). That is a sweep result on a synthetic price path, not a live vault.

## Solidity

Contracts compile with solc 0.8.26. Independent check: `python check_repo.py .`

| Contract | Role |
| --- | --- |
| `YieldAggregator` | ERC-4626 vault; keeper-gated, timelocked rebalance |
| `RegimeDetector` | On-chain observer of funding / vol regime |
| `TradeOnlyAgent` | EIP-712 scoped, revocable trade delegation |
| `KHYPELeg` | kHYPE liquid staking |
| `SpotStakingLeg` | Direct HYPE staking |
| `PerpFundingLeg` | Long spot / short perp for funding |
| `BasisHedgeLeg` | Same shape at hedge ratio 1.0, targeting basis |
| `LiminalXHYPELeg` | Wrapper for an xHYPE ERC-4626 vault |

```bash
cd solidity
python scripts/compile.py
python scripts/verify.py
python scripts/deploy.py --dry-run \
  --leg-addr 0x1111111111111111111111111111111111111111 \
  --leg-addr 0x2222222222222222222222222222222222222222 \
  --leg-addr 0x3333333333333333333333333333333333333333 \
  --leg-addr 0x4444444444444444444444444444444444444444
```

Live deploy:

```bash
export RPC_URL=<rpc>
export DEPLOYER_PK=0x...
python scripts/deploy.py \
  --leg-addr <leg1> --leg-addr <leg2> --leg-addr <leg3> --leg-addr <leg4>
```

The script refuses unknown chain IDs unless both `--yes-i-mean-it` and `--chain-id` are set. It always refuses chain ID 999 (HyperEVM mainnet, not Elysium). Elysium mainnet and testnet IDs must be taken from Kinetiq at launch. Manifests write to `solidity/output/deployments/`.

Owner and keeper keys can pause, retarget legs, and move vault funds. `devFallbackEnabled` defaults to on in perp legs; turn it off for any production deploy. See `solidity/README.md`.

## Keeper, harness, kit, dashboard

```bash
cd keeper-runtime && npm ci && npm test
cd elix-kit/ts && npm ci && npm test
cd solidity && forge test
```

| Path | Role |
| --- | --- |
| `keeper-runtime/` | Signs Stream-A delegations; never logs the private key. Read `keeper-runtime/SECURITY.md` before setting `KEEPER_PK`. |
| `dev-harness/` | CREATE2 HyperCore precompile mocks for Foundry tests. |
| `elix-kit/` | Copy-out starter: `HelloElysium` and a minimal vault. |
| `dashboard/` | Static page over `dashboard/data.json`. Refresh with `dashboard/refresh.py`. |

## Docs

| File | Contents |
| --- | --- |
| `docs/AGGREGATOR_SPEC.md` | Vault architecture |
| `docs/DELEGATION_SPEC.md` | Trade-Only-Agent protocol |
| `docs/ROADMAP.md` | Built vs deferred, milestones |
| `docs/AUDIT_SUMMARY.md` | Scope and known gaps |
| `docs/TEST_COVERAGE_GAP.md` | Test inventory |

## License

Apache-2.0. Not investment advice.
