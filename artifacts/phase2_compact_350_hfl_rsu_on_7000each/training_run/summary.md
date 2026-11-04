# Hierarchical FedAvg experiment: hierarchical_fedavg_phase2_compact_1500_seed20261031_20261104T194135Z

- Dataset: `phase2_compact_1500`; feature schema hash `46196acbcc933a9b60f0a3151cf3a5822350c6988b7894a50f5722ac80f4abe2`.
- Fixed replay cohort: 354 clients, 14000 distinct training windows.
- Rounds: 100; local epochs per client per round: 5.
- Four persistent RSU learners train only on their own sensor histories, capped at 20 sampled windows each; child vehicle updates are aggregated once at their parent RSU.
- The same fixed replay cohort participates in every round.
- This is an offline saved-trajectory replay, not an online networked deployment.
- Serialized byte counts use the federation module's explicit JSON tensor representation; they are not measured network traffic.
- Test data was not used for client selection, local training, or round selection.

| Split | N | Queue MAE (m) | Queue RMSE (m) | Macro-F1 | Balanced accuracy |
|---|---:|---:|---:|---:|---:|
| val | 14000 | 26.140148407372976 | 40.47136699214836 | 0.706772269666958 | 0.6912727842896585 |
| test | 14000 | 27.351940704561652 | 42.18481328613313 | 0.7078371219367021 | 0.6924536041588616 |
