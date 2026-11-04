# TRAF-MA Phase 2 saved-artifact report

- Dataset: `data\phase2_compact_1500` (phase2_compact_1500).
- Baseline artifact: `runs\phase2_compact\baseline_phase2_compact_1500_20261104T071004Z`; method `non-neural baselines`.
- Matched global-model test rows: 300; run-level split; overlapping windows are not independent replicates.
- Flat/HFL/IID are offline trajectory replays. Synthetic IID pooling is diagnostic and not a local deployment.
- Scores below are descriptive development results; no test-set tuning was performed.

| Method | N | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| Matched signal-aware Ridge | 300 | 27.069628413314362 | 36.97307658473256 | 0.5624 | 0.6201 |
| Matched majority-class diagnostic | 300 | n/a | n/a | 0.1591 | 0.3333 |
| Matched RSU persistence | 70 | 13.802114285714286 | 28.99099173930708 | 0.5568 | 0.5364 |
| Central GRU | 300 | 20.587287617007245 | 29.748901636976168 | 0.7510 | 0.7332 |
| Hierarchical FedAvg (RSU self-update on) | 300 | 36.66233018385349 | 45.13233730898981 | 0.5366 | 0.5486 |

## Local-only stratum results

## Central GRU breakdown

### Scenario

| Group | N | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| asymmetric | 75 | 21.6993 | 29.7480 | 0.7523 | 0.7401 |
| free | 75 | 8.8732 | 13.4957 | 0.5508 | 0.5280 |
| heavy | 75 | 31.9608 | 42.9106 | 0.7842 | 0.8108 |
| moderate | 75 | 19.8157 | 25.1316 | 0.5659 | 0.5527 |

### Approach

| Group | N | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| E | 60 | 20.4169 | 31.8161 | 0.7539 | 0.7391 |
| N | 100 | 18.7217 | 27.2007 | 0.7785 | 0.7637 |
| S | 79 | 21.7053 | 30.2352 | 0.7943 | 0.7751 |
| W | 61 | 22.3652 | 30.9829 | 0.5816 | 0.5669 |

### Client type

| Group | N | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| rsu | 70 | 7.3740 | 12.5462 | 0.7506 | 0.7353 |
| vehicle | 230 | 24.6087 | 33.2632 | 0.7278 | 0.7114 |

## Hierarchical FedAvg (RSU self-update on) breakdown

### Scenario

| Group | N | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| asymmetric | 75 | 39.6596 | 48.3595 | 0.5274 | 0.5343 |
| free | 75 | 25.0445 | 32.3299 | 0.5279 | 0.6190 |
| heavy | 75 | 42.3460 | 51.0347 | 0.4855 | 0.5198 |
| moderate | 75 | 39.5992 | 46.4684 | 0.3179 | 0.4084 |

### Approach

| Group | N | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| E | 60 | 38.2760 | 45.9231 | 0.5322 | 0.5455 |
| N | 100 | 35.9064 | 44.1447 | 0.5446 | 0.5535 |
| S | 79 | 37.9464 | 46.3701 | 0.6175 | 0.6076 |
| W | 61 | 34.6514 | 44.3167 | 0.4172 | 0.4792 |

### Client type

| Group | N | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| rsu | 70 | 18.2242 | 26.6668 | 0.5091 | 0.4906 |
| vehicle | 230 | 42.2739 | 49.4008 | 0.4880 | 0.5010 |

## Interpretation limits

- Central, flat, IID and hierarchical metrics use identical sampled test rows; their training cohort sizes differ and the federated participant cohorts are not matched across methods.
- Local-only results use held-out rows matched on the selected client's type and approach, not the global-model test cohort; do not compare the local aggregate as if rows were identical.
- Moderate-class recall, class support, and confusion matrices are retained in each `metrics.json`; a zero moderate recall is a material negative result, not an omitted metric.
- Communication bytes are the implementation's JSON model-payload sizes, not measured network traffic. Wall-clock times are from the recorded CPU environment.
- The optional live online federation path is smoke-tested separately; this offline report does not measure live learning performance, radio/network behavior, a formal privacy guarantee, or attack/trust behavior.

## Generated figures

## Training label-distribution divergence

Jensen-Shannon divergence (base 2, bits) compares each training subgroup's pooled class distribution to all training clients. It is descriptive and uses overlapping-window histograms.

### Approach

| Group | Clients | Windows by class [free, moderate, heavy] | JS divergence (bits) |
|---|---:|---|---:|
| E | 427 | [22265, 7563, 22987] | 0.000413 |
| N | 503 | [24658, 9404, 26935] | 0.000269 |
| S | 539 | [25218, 9013, 36709] | 0.002591 |
| W | 398 | [21162, 7364, 20203] | 0.001368 |

### Type

| Group | Clients | Windows by class [free, moderate, heavy] | JS divergence (bits) |
|---|---:|---|---:|
| rsu | 32 | [16253, 5162, 6137] | 0.045300 |
| vehicle | 1835 | [77050, 28182, 100697] | 0.000724 |

### Scenario

| Group | Clients | Windows by class [free, moderate, heavy] | JS divergence (bits) |
|---|---:|---|---:|
| asymmetric | 523 | [26571, 9191, 36056] | 0.001449 |
| free | 128 | [11489, 1723, 0] | 0.293274 |
| heavy | 768 | [35633, 11549, 64580] | 0.010626 |
| moderate | 448 | [19610, 10881, 6198] | 0.076694 |

## Per-client label and sample distributions

Per-client records for all 1796 eligible natural training clients are saved in `client_label_distributions.json`. The declared divergence is base-2 Jensen-Shannon divergence in bits from the applicable pooled class distribution. `p90` is the worst-decile threshold, not a maximum.

### Natural clients by client type

| Group | Clients | Windows | Median windows (IQR; p90) | Median JSD (IQR; p90), bits | Label histogram [free, moderate, heavy] |
|---|---:|---:|---|---|---|
| rsu | 32 | 27552 | 861.0 (0.0; 861.0) | 0.165672 (0.277857; 0.315086) | [16253, 5162, 6137] |
| vehicle | 1764 | 205032 | 100.0 (95.0; 223.0) | 0.039555 (0.275802; 0.397873) | [76252, 28123, 100657] |

### Natural clients by approach

| Group | Clients | Windows | Median windows (IQR; p90) | Median JSD (IQR; p90), bits | Label histogram [free, moderate, heavy] |
|---|---:|---:|---|---|---|
| E | 408 | 52549 | 98.0 (83.0; 238.0) | 0.037001 (0.280317; 0.397873) | [22002, 7560, 22987] |
| N | 491 | 60828 | 98.0 (99.0; 211.0) | 0.034023 (0.276742; 0.397873) | [24501, 9392, 26935] |
| S | 519 | 70676 | 110.0 (108.0; 246.0) | 0.041119 (0.269113; 0.397873) | [25012, 8992, 36672] |
| W | 378 | 48531 | 91.5 (104.2; 246.5) | 0.078744 (0.279380; 0.397873) | [20990, 7341, 20200] |

### Natural clients by scenario

| Group | Clients | Windows | Median windows (IQR; p90) | Median JSD (IQR; p90), bits | Label histogram [free, moderate, heavy] |
|---|---:|---:|---|---|---|
| asymmetric | 504 | 71571 | 109.0 (122.8; 259.7) | 0.036583 (0.263785; 0.397873) | [26361, 9191, 36019] |
| free | 114 | 13011 | 61.5 (49.5; 102.7) | 0.397873 (0.096724; 0.397873) | [11288, 1723, 0] |
| heavy | 754 | 111647 | 132.0 (92.0; 240.0) | 0.026308 (0.031236; 0.230456) | [35554, 11516, 64577] |
| moderate | 424 | 36355 | 73.0 (55.2; 112.7) | 0.285309 (0.308441; 0.397873) | [19302, 10855, 6198] |

No matched natural/IID training-cohort artifacts were supplied, so no IID divergence comparison is reported.

- `plots/matched_metrics.png`
- `plots/label_skew_js.png`
- `plots/confusion_matrices.png`
- `plots/validation_curves.png`
- `plots/federation_costs.png`
- `plots/label_distributions.png`
- `plots/feature_availability.png`
- `plots/central_queue_scatter.png`
- `plots/approach_breakdown.png`
- `plots/client_sample_counts.png`

## Input experiment artifacts

- `runs\phase2_compact\central_gru_phase2_compact_1500_seed20261031_20261104T093628Z` — `central_gru_phase2_compact_1500_seed20261031_20261104T093628Z`; 1500 selected training windows.
- `runs\phase2_compact\hierarchical_fedavg_phase2_compact_1500_seed20261031_20261104T094318Z` — `hierarchical_fedavg_phase2_compact_1500_seed20261031_20261104T094318Z`; 1500 selected training windows.
