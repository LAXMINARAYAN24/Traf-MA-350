# Central GRU experiment: central_gru_phase2_compact_1500_seed20261031_20261104T093628Z

- Dataset: `phase2_compact_1500`; feature schema hash `46196acbcc933a9b60f0a3151cf3a5822350c6988b7894a50f5722ac80f4abe2`.
- Train/validation/test sampled windows: 1500/300/300.
- Epochs trained: 104 (minimum 50, maximum 150, early-stopping patience 15; stopped early).
- Best checkpoint epoch: 89; parameter count: 5972.
- Device: cuda (requested `auto`); CPU threads: 24.
- Model is a pooled offline reference; it does not preserve client-local training.
- Metrics were recomputed from saved `predictions.csv`; test rows were not used for checkpoint selection.

| Split | N | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| val | 300 | 20.55366339678247 | 30.630859444742082 | 0.7385213834800392 | 0.7249772520473158 |
| test | 300 | 20.587287617007245 | 29.748901636976168 | 0.7510229055162422 | 0.733197979513324 |
