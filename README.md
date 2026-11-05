# TRAF-MA: SUMO simulation, datasets and Phase 2 learning

TRAF-MA simulates a four-arm signalised intersection with vehicle agents, four roadside units (RSUs), a lossy message path and an edge coordinator. It generates labelled datasets and trains a GRU congestion predictor, centrally and with three-tier hierarchical federated learning (HFL).

Traffic drives on the **left by default** (Indian norm). Right-hand traffic is one setting away.

## 1. Architecture at a glance

```text
vehicle agents (N)  --V2I-->  RSU-N / RSU-E / RSU-S / RSU-W  --I2C-->  edge coordinator
 (own view, 100 m)            (one per road, 150 m zone)               (validate, dedup, fuse)
```

```text
Federated learning (three tiers)

tier 1   vehicle clients + RSU sensor learners      train locally, send model updates
tier 2   RSU edge aggregators (N, E, S, W)          average their own group
tier 3   global coordinator                         averages the four edge models
```

```text
Dataset flow

SUMO run -> agent logs + evaluator labels -> windows (10 steps -> label 30 s ahead)
         -> data/<dataset>/{train,val,test}/<run>/ -> central GRU, FedAvg, baselines -> reports
```

More detail: [docs/ARCHITECTURE_AS_BUILT.md](docs/ARCHITECTURE_AS_BUILT.md).

## 2. Quick start

```bash
python -m venv .venv
source .venv/bin/activate          # Windows PowerShell: .venv\Scripts\activate
pip install -r requirements.txt    # SUMO is installed by the eclipse-sumo wheel
python -m trafma doctor            # starts, steps and closes a minimal SUMO process
python -m pytest                   # 177 tests
```

PyTorch: the CPU build is smaller; the default wheel includes CUDA for NVIDIA GPUs. See [docs/TRAINING_GUIDE.md](docs/TRAINING_GUIDE.md).

## 3. Driving side

`network.drive_side` is `left` (default) or `right`. Layout, signal plan, demand, agents, messages and labels are otherwise identical.

```bash
python -m trafma simulate --vehicles 20 --seed 42                                  # left-hand
python -m trafma simulate --vehicles 20 --seed 42 --set network.drive_side=right   # original behaviour
```

- The network is built with netconvert `--lefthand true`: each lane keeps to the left of its road.
- Turn names are the driver's own. N to E is a left turn for both settings. With left-hand traffic the left turn is the short one and the right turn crosses oncoming traffic. Split phasing means no two approaches are ever green together, so neither conflicts.
- RSUs stand on the kerb side of each road (left of travel for left-hand traffic).
- `netgen.py` checks after building that lanes are on the requested side and the arms are still N, E, S, W, and stops otherwise.
- `drive_side=right` reproduces the previous implementation exactly (trace hash `e2c4145f...` for 20 vehicles, seed 42). Left-hand gives `aa69daee...`.
- Datasets already in `data/phase2_v1`, `phase2_v2_dev` and `phase2_v2` were generated right-hand. Their manifests are kept as legacy records. Do not mix them with left-hand runs.

## 4. Datasets and the train / validation / test split

`python -m trafma collect --config <yaml>` writes each run directly into its split folder.

```text
data/phase2_compact_1500/
  train/<scenario>_s<seed>/
  val/<scenario>_s<seed>/
  test/<scenario>_s<seed>/
  splits.json
  dataset_manifest.json
  dataset_report.txt
  feature_audit.json
  sample_budget.md
```

- The split is by whole run (disjoint seeds), so a window never crosses splits.
- If a collect config has no `splits:` section the default is train seeds 1, 2, 3; val seed 4; test seeds 5, 6.
- Only the names `train`, `val` and `test` are allowed, and a seed may appear in one split only.
- Old datasets that kept runs in `<dataset>/runs/` still load.

| Config | Runs | Scenarios | Seeds train / val / test |
|---|---:|---:|---|
| `configs/data_compact_1500.yaml` | 16 | 4 | 2 / 1 / 1 |
| `configs/data.yaml` (v1) | 24 | 4 | 3 / 1 / 2 |
| `configs/data_v2_dev.yaml` | 48 | 8 | 3 / 1 / 2 |
| `configs/data_v2.yaml` | 160 | 8 | 10 / 5 / 5 |

## 5. The compact 1,500-sample experiment

The current default for quick experiments. Full accounting of vehicles, observations, rounds and windows is in [docs/COMPACT_1500.md](docs/COMPACT_1500.md).

```bash
python -m trafma collect  --config configs/data_compact_1500.yaml
python -m trafma train    --method central --config configs/learning_compact_1500.yaml
python -m trafma fedavg   --hierarchical   --config configs/learning_compact_1500.yaml
python -m trafma baseline --config configs/learning_compact_1500.yaml
```

| Item | Value |
|---|---|
| Simulation | 4 scenarios (60, 220, 380, 260 vehicles), 900 s, 16 runs, 3,680 vehicles scheduled |
| Training / validation / test windows | 1500 / 300 / 300 |
| Central GRU | 104 epochs (minimum 50, early stopped, best at 89) |
| Hierarchical FL | 20 clients x 75 windows, 100 rounds, 5 local epochs |

| Method | Test macro-F1 | Test queue MAE (m) |
|---|---:|---:|
| Central GRU | 0.772 | 20.6 |
| Signal-aware Ridge (matched rows) | 0.562 | 27.1 |
| Hierarchical FedAvg | 0.545 | 36.7 |

These are single-seed results on 300 test windows: descriptive, not a final benchmark.

## 6. Latest 350-client compact comparison (2026-11-05)

The latest compact comparison uses **350 vehicle clients with 20 windows each** (7,000 vehicle windows total), plus a four-RSU self-update ablation. The phrase “7,000 examples per client” would be inaccurate: 7,000 is the aggregate vehicle-window budget. In the RSU self-update-on run, each of the four RSUs contributes 1,750 sensor windows, adding 7,000 RSU windows.

All four model runs use the same held-out cohort of 14,000 windows (7,000 vehicle and 7,000 RSU) for validation and test. The central run trains on 7,000 windows of each type. FL configurations use 100 rounds and five local epochs. Exact configs, run manifests, predictions and reports are saved under `runs/phase2_compact_350_*`; the final RSU self-update-on run is packaged under [artifacts/phase2_compact_350_hfl_rsu_on_7000each](artifacts/phase2_compact_350_hfl_rsu_on_7000each/).

| Method | Train windows | Test macro-F1 | Test balanced accuracy | Test queue MAE (m) | Test queue RMSE (m) |
|---|---:|---:|---:|---:|---:|
| Central GRU | 14,000 | 0.8357 | 0.8292 | 14.905 | 24.578 |
| Flat FedAvg, vehicle only | 7,000 | 0.2669 | 0.2991 | 57.391 | 64.154 |
| Hierarchical FedAvg, RSU self-update off | 7,000 | 0.2524 | 0.2843 | 57.782 | 64.718 |
| Hierarchical FedAvg, RSU self-update on | 14,000 | 0.7078 | 0.6925 | 27.352 | 42.185 |

RSU self-updates strongly affect the result: in the self-update-on run, test macro-F1 / queue MAE are 0.8880 / 6.995 m for RSU rows and 0.5282 / 47.709 m for vehicle rows. The aggregate score therefore hides a substantial gap between sensor types. Flat and hierarchical FedAvg with RSU self-updates off are nearly tied, consistent with the same updates being averaged once; hierarchy alone is not an accuracy gain here.

These are **one-seed descriptive results**, with overlapping one-second windows from four held-out SUMO runs; they are not independent-window confidence estimates or a multi-seed benchmark. The RSU-on comparison also doubles the FL training-window budget relative to the vehicle-only FL runs, so it does not isolate the effect of hierarchy or RSU participation from added training data. See the [latest-run-only matched report](runs/phase2_compact_350_7000_report_latest_only/report.md) and [status evidence](docs/STATUS.md) for per-type breakdowns, plots, manifests and caveats.

## 7. Training: epochs, CPU and GPU

```bash
python -m trafma train --method central --config configs/learning_compact_1500.yaml --device auto
python -m trafma train --method central --config configs/learning_compact_1500.yaml --device cpu --threads 8
```

- At least 50 epochs, at most 150, early stopping with patience 15 after the minimum.
- `--device auto|cpu|cuda`: auto uses a GPU when PyTorch can see one.
- `--threads N`: CPU threads, 0 (default) means every core.
- The GPU path has not been tested yet; see the guide before relying on it.

Details: [docs/TRAINING_GUIDE.md](docs/TRAINING_GUIDE.md).

## 8. Command reference

```bash
python -m trafma simulate --config configs/phase1.yaml --vehicles 20 --seed 42 [--gui] [--duration 180 --online-federation]
python -m trafma gate     --run runs/<run-id> --reproduce --pytest
python -m trafma report   --run runs/<run-id>
python -m trafma replay   --run runs/<run-id> --every 10
python -m trafma inspect  --run runs/<run-id> --vehicle veh_0005
python -m trafma collect  --config configs/data.yaml [--resume] [--jobs 2]
python -m trafma features-audit --dataset data/<dataset>
python -m trafma baseline --config configs/learning.yaml
python -m trafma train    --method central|local --config configs/learning.yaml [--client <id>] [--device auto] [--threads 8]
python -m trafma fedavg   --config configs/learning.yaml [--hierarchical] [--iid-control] [--transient-participation] [--threads 8]
python -m trafma sample-budget --dataset data/<dataset> --experiment <run-dir> [--experiment <run-dir>]
python -m trafma phase2-report --dataset data/<dataset> --baseline <run-dir> --experiment <run-dir>
python -m trafma phase2-stats  --help
python -m trafma phase2-local-eval --help
```

Any config value can be overridden, for example `--set agents.rsu_zone_m=120 --set comms.v2i.loss_prob=0.1`. In `--gui`, vehicles are green inside the RSU zone, red when halted, yellow when approaching and grey in the junction.

## 9. Run artefacts

Each simulation run folder holds:

| File or folder | Contents |
|---|---|
| `manifest.json` | Config, seed, versions, file hashes, counts, status |
| `scenario/` | Network, routes, signal program, SUMO logs, `topology.json` (includes `drive_side`) |
| `agents/rsu_*.jsonl`, `agents/veh_*.jsonl` | Agent-local views only |
| `messages.jsonl` | Send, deliver and reject trace |
| `trace.jsonl` | Per-step vehicle state; its SHA-256 is the reproducibility fingerprint |
| `evaluator/` | Ground truth, never visible to agents or models |
| `labels.jsonl`, `windows.jsonl` | Dataset runs only: label and window index |

A finished left-hand example is in `examples/demo_n20_s42/`.

## 10. Defaults and limits

- 300 m arms, one lane per direction, 150 m RSU zone, 1 s step, signal 25 s green, 3 s yellow, 2 s all-red (120 s cycle).
- Congestion rule: queue / zone below 0.10 is free, below 0.35 moderate, otherwise heavy. History 10 steps, horizon 30 s.
- Sensors are noise-free. Attacks, trust and the dashboard belong to Phase 3.
- The `heavy` and `asymmetric` scenarios are over-saturated on purpose: vehicles still queued at 900 s are reported as unfinished.
- GUI mode was verified under a virtual display only.

## 11. Documentation map

| Document | Purpose |
|---|---|
| [docs/ARCHITECTURE_AS_BUILT.md](docs/ARCHITECTURE_AS_BUILT.md) | What the code does today |
| [docs/COMPACT_1500.md](docs/COMPACT_1500.md) | Sample accounting for the 1,500-window experiment |
| [docs/TRAINING_GUIDE.md](docs/TRAINING_GUIDE.md) | Epochs, early stopping, CPU, GPU, threads |
| [docs/STATUS.md](docs/STATUS.md) | Evidence ledger |
| [docs/DECISIONS.md](docs/DECISIONS.md) | Design decisions |
| [docs/DATA_CONTRACTS.md](docs/DATA_CONTRACTS.md) | Message, label and feature contracts |
| [AGENTS.md](AGENTS.md) | Rules for coding agents |

`docs/ARCHITECTURE.md` is the original plan and still says "camera" where the code says RSU.
