# Final 350-vehicle / RSU self-update-on run

This package contains only the final hierarchical FedAvg run with RSU self-update enabled, its selected feature-window data, its config, and its individual HTML report.

## Run summary

- 350 vehicle learners x 20 selected windows = 7,000 vehicle training windows.
- Four persistent RSU groups x 1,750 selected windows = 7,000 RSU training windows.
- Total training: 14,000 windows; validation and test: 7,000 vehicle + 7,000 RSU windows each.
- 100 hierarchical FedAvg rounds; 40.3 minutes wall time; one training seed.
- Test metrics: queue MAE 27.352 m, RMSE 42.185 m, macro-F1 0.7078, balanced accuracy 0.6925.
- The held-out set contains overlapping one-second windows from four SUMO simulation runs. These results are descriptive, not independent-run confidence estimates.

## Contents

- `config.yaml`: exact run configuration.
- `training_run/`: saved manifest, resolved config, all round checkpoints, round/client logs, predictions and metrics.
- `selected_data/selected_windows.npz`: exact reconstructed feature tensors and target arrays for the selected train, validation and test cohorts. Each input is shaped as 10 timesteps x 22 features.
- `selected_data/selected_windows.csv`: per-window split, learner/client identity, type, approach, scenario, run, time, queue target and class.
- `selected_data/manifest.json`: per-split/type counts, schema dimensions, data hashes and source-run provenance. The export process verified training class counts and that exported test identities match the saved predictions.
- `report/report.html` and `report/report.md`: the report for this run; `report/plots/` contains the report graphs.

The complete `data/phase2_compact_1500` raw dataset is not copied here. Its manifest hash is recorded in the saved run manifest; the exact selected feature windows needed to inspect this experiment are included in `selected_data/`.

## Original saved run

The run was created at `runs/phase2_compact_350_vehicle_rsu_7000each/hierarchical_fedavg_phase2_compact_1500_seed20261031_20261104T194135Z/` with `configs/learning_compact_350vehicles_7000rsu.yaml`.
