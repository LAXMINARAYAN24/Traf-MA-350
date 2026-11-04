# Baseline experiment: baseline_phase2_compact_1500_20261104T071004Z

- Dataset: `phase2_compact_1500` (manifest SHA-256 `2e54f245f7f96d31f50b6d1e0c56b28df830a30fe448fd2d2f7d1d18002d0e98`)
- Feature schema: `trafma.features/1` (SHA-256 `46196acbcc933a9b60f0a3151cf3a5822350c6988b7894a50f5722ac80f4abe2`)
- Train-only Ridge windows: 232584 from 1796 eligible clients.
- Persistence uses each RSU's observed current queue; vehicle persistence is unavailable.
- Ridge predictions use only local features from the final input timestep; predicted class uses the frozen 0.10/0.35 queue-to-zone thresholds.
- Windows overlap; overall window metrics are descriptive. Run-level MAE mean and standard deviation are also saved.

| Split | Method | N | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---|---:|---:|---:|---:|---:|
| val | persistence | 13776 | 29.51855487804827 | 49.3562836038482 | 0.5249476384323807 | 0.5230510858501646 |
| val | signal_aware_ridge | 120562 | 36.42817378670524 | 44.86142727092408 | 0.47962531182146023 | 0.5370488722714108 |
| val | majority_class | 120562 | n/a | n/a | 0.20807990901448845 | 0.3333333333333333 |
| test | persistence | 13776 | 30.83334051974349 | 51.61871080242052 | 0.5207234188511108 | 0.519075637392436 |
| test | signal_aware_ridge | 124843 | 37.283126584002375 | 45.45267037182294 | 0.47009715436402644 | 0.5314362093643489 |
| test | majority_class | 124843 | n/a | n/a | 0.2161341893389053 | 0.3333333333333333 |

## Matched RSU-only comparison

Both methods below use the same held-out RSU windows. Persistence is not available on vehicle rows.

| Split | Method | N | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---|---:|---:|---:|---:|---:|
| val | persistence | 13776 | 29.51855487804827 | 49.3562836038482 | 0.5249476384323807 | 0.5230510858501646 |
| val | signal_aware_ridge | 13776 | 20.600878809448258 | 28.656575031513864 | 0.570517980910967 | 0.6425504376326264 |
| val | majority_class | 13776 | n/a | n/a | 0.12217149858698444 | 0.3333333333333333 |
| test | persistence | 13776 | 30.83334051974349 | 51.61871080242052 | 0.5207234188511108 | 0.519075637392436 |
| test | signal_aware_ridge | 13776 | 20.8705488521148 | 29.240516417514353 | 0.5659631295458795 | 0.6425565776133544 |
| test | majority_class | 13776 | n/a | n/a | 0.12918202922299607 | 0.3333333333333333 |
