# Compact 1,500-sample experiment

This document explains the small training budget used for the Phase 2 central GRU and three-tier hierarchical federated learning (HFL) runs: how many vehicles were simulated, how many observations were collected, how many windows exist, and how 1,500 of them are used.

The tables in section 2 are copied from the output of `python -m trafma sample-budget`, which reads the saved dataset manifest. The values in sections 3 and 4 come from the saved experiment manifests and metrics (`runs/phase2_compact/`). Nothing is estimated by hand.

## 1. What "1,500 samples" means

- A **sample** is one window: 10 consecutive 1 s observation steps from one agent, labelled with the congestion state 30 s later.
- **1,500 is the training set.** Validation and test are separate and smaller: 300 windows each.
- The training windows are drawn only from the `train` runs. Validation and test windows come from different simulation runs (different seeds), so nothing leaks between splits.

| Split | Windows used | Why |
|---|---:|---|
| Train | 1500 | The requested budget |
| Validation | 300 | 4 runs x 75 windows, used for early stopping and for choosing the number of FL rounds |
| Test | 300 | 4 runs x 75 windows, never used to choose anything |

## 2. Simulation and observations

| Scenario | Vehicles per run | Train runs | Val runs | Test runs |
|---|---:|---:|---:|---:|
| asymmetric | 260 | 2 | 1 | 1 |
| free | 60 | 2 | 1 | 1 |
| heavy | 380 | 2 | 1 | 1 |
| moderate | 220 | 2 | 1 | 1 |

| Split | Runs | Simulated seconds | Vehicles scheduled | Departed | Arrived | Still on road at end |
|---|---:|---:|---:|---:|---:|---:|
| train | 8 | 7200 | 1840 | 1835 | 1579 | 256 |
| val | 4 | 3600 | 920 | 920 | 796 | 124 |
| test | 4 | 3600 | 920 | 920 | 788 | 132 |
| **all** | 16 | 14400 | 3680 | 3675 | 3163 | 512 |

### Observations collected and windows available

| Split | RSU records | Vehicle records | RSU windows | Vehicle windows | All windows |
|---|---:|---:|---:|---:|---:|
| train | 28800 | 271026 | 27552 | 205929 | 233481 |
| val | 14400 | 139430 | 13776 | 106786 | 120562 |
| test | 14400 | 143462 | 13776 | 111067 | 124843 |

Of all vehicle records, 471466 were taken while the vehicle was on its incoming road (the only records that can form a window).

Reading the tables: the simulator is deterministic, so the same seed always reproduces the same traffic. The 1,500 training windows are a tiny slice (0.64 percent) of the 233,481 windows that the 8 training runs contain.

## 3. How the 1,500 windows are used

### Central GRU

| Item | Value |
|---|---:|
| Training windows | 1500 (random but seeded sample of the train split) |
| Validation / test windows | 300 / 300 |
| Maximum epochs | 150 |
| Minimum epochs | 50 (early stopping cannot fire earlier) |
| Early-stopping patience | 15 epochs without validation improvement |
| Epochs actually trained | 104 (stopped early; best checkpoint at epoch 89) |
| Batch size | 64 (24 updates per epoch) |
| Training time | about 6 s on 1 CPU core |

### Three-tier hierarchical FL

The three tiers are the vehicle clients, the four RSU edge aggregators and the global coordinator.

```text
tier 1  vehicle clients (16) + RSU sensor learners (4)      75 windows each = 1,500
           |  each trains locally for 5 epochs per round
tier 2  RSU edge aggregators: rsu_N, rsu_E, rsu_S, rsu_W    5 clients each, mass 375 each
           |  one edge aggregate per RSU per round
tier 3  global coordinator                                  weighted average, mass 1,500
```

| Item | Value |
|---|---:|
| Clients | 20 (4 RSU learners + 16 vehicle clients, 5 per approach) |
| Windows per client | 75, enforced by `federation.require_full_client_budget` |
| Training windows in total | 20 x 75 = 1500 |
| Communication rounds | 100 |
| Local epochs per round | 5 |
| Client updates in total | 2000 |
| Window passes in total | 750000 |
| Training time | about 59 s on 1 CPU core |

Every vehicle client must own at least 75 windows. A window needs 10 consecutive steps on the incoming road, so such a vehicle spent at least 84 s on its approach. These clients therefore come mostly from the moderate, heavy and asymmetric runs. The `free` scenario provides RSU windows and at most a few vehicle clients.

### Why 100 rounds

The number of rounds was chosen on validation results only. Test results were not used.

| Rounds | Local epochs | Learning rate | Validation macro-F1 |
|---:|---:|---:|---:|
| 30 | 2 | 0.001 | 0.235 |
| 100 | 5 | 0.001 | 0.553 |
| 100 | 5 | 0.003 | 0.512 |
| 60 | 5 | 0.005 | 0.531 |
| 150 | 5 | 0.002 | 0.530 |
| 200 | 5 | 0.001 | 0.565 |

30 rounds is under-trained. 200 rounds gives a small further gain for twice the time, so 100 rounds is the default. Set `federation.rounds: 200` in `configs/learning_compact_1500.yaml` to use it.

## 4. Results

All methods are scored on the same 300 held-out test windows.

| Method | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|---:|
| Central GRU (1,500 windows) | 20.58 | 29.87 | 0.772 | 0.754 |
| Matched signal-aware Ridge (all train windows) | 27.07 | 36.97 | 0.562 | 0.620 |
| Hierarchical FedAvg (1,500 windows) | 36.67 | 45.14 | 0.545 | 0.555 |
| Majority-class diagnostic | n/a | n/a | 0.159 | 0.333 |

How to read this honestly:

- The central GRU is clearly best here and beats Ridge even though Ridge uses far more training windows.
- Hierarchical FedAvg is about level with Ridge on macro-F1 and worse on queue error. With only 75 windows per client and non-IID clients, it does not match the pooled model. This is a real result, not a tuning accident.
- The test set has only 300 windows from 4 runs, and each result is a single training seed. Treat differences of a few points as noise. These numbers are descriptive, not a final benchmark.
- Central and hierarchical results are not from identical windows: both use 1,500, but the hierarchical windows are fixed per client while the central windows are a random sample.

## 5. Reproduce

```bash
python -m trafma collect  --config configs/data_compact_1500.yaml
python -m trafma features-audit --dataset data/phase2_compact_1500
python -m trafma train    --method central --config configs/learning_compact_1500.yaml
python -m trafma fedavg   --hierarchical   --config configs/learning_compact_1500.yaml
python -m trafma baseline --config configs/learning_compact_1500.yaml
python -m trafma sample-budget --dataset data/phase2_compact_1500 --experiment runs/phase2_compact/<central-run> --experiment runs/phase2_compact/<hierarchical-run>
```

Data generation takes about 70 s and about 470 MB. Central training takes seconds and hierarchical FL about a minute on one CPU core.

## 6. Changing the budget

| To change | Edit |
|---|---|
| Training samples for the central GRU | `training.max_train_windows` |
| Training samples for HFL | `federation.max_clients` x `federation.max_windows_per_client` (keep `max_clients` at least 6) |
| Validation and test size | `evaluation_windows_per_run` x number of runs in the split |
| Rounds and local work | `federation.rounds`, `training.local_epochs` |
| Number of vehicles or scenarios | `configs/data_compact_1500.yaml` |
| Which seeds are train, val and test | `splits` in `configs/data_compact_1500.yaml` |
