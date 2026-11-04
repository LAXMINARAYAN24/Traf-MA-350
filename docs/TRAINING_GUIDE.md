# Training guide: epochs, early stopping, CPU and GPU

This guide covers the central GRU and the federated runs. It reflects the code in `trafma/training.py` and `trafma/federated_training.py`.

## 1. What trains where

| Run | Command | Runs on | Why |
|---|---|---|---|
| Central GRU | `python -m trafma train --method central` | CPU or GPU | One model, one pooled training set |
| Local GRU | `python -m trafma train --method local --client <id>` | CPU or GPU | One client's windows |
| Flat or hierarchical FedAvg | `python -m trafma fedavg ...` | CPU, multi-threaded | Each client has only tens of windows, so a GPU transfer costs more than it saves |

The model has 5,972 parameters. It is small enough that a CPU is a perfectly good choice for the 1,500-sample runs (central training took about 6 s and hierarchical FL about 59 s on a single CPU core).

## 2. Epochs and early stopping

Settings live under `training:` in `configs/learning.yaml` and `configs/learning_compact_1500.yaml`.

| Key | Value | Meaning |
|---|---:|---|
| `epochs` | 150 | Maximum number of epochs |
| `min_epochs` | 50 | Always train at least this many epochs. Early stopping cannot fire before it |
| `early_stopping_patience` | 15 | After `min_epochs`, stop when validation loss has not improved for 15 epochs |

How it behaves:

1. Validation loss is measured after every epoch.
2. The best checkpoint (lowest validation loss) is always kept, even if later epochs are worse.
3. From epoch 50 onward, 15 epochs in a row without a new best stops the run.
4. If that never happens, training runs to 150 epochs.
5. The saved model is the best checkpoint, not the last epoch.

The run manifest records `epochs_run`, `best_epoch`, `early_stopped`, `min_epochs` and `max_epochs`. `training_history.csv` has the loss for every epoch.

In the compact run the model trained 104 epochs and the best checkpoint was epoch 89.

## 3. Install PyTorch for your machine

`requirements.txt` lists `torch`. Pick the build that matches your hardware.

CPU only (smaller download):

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

NVIDIA GPU (the default Linux and Windows wheel includes CUDA):

```bash
pip install torch
```

Check what PyTorch sees:

```bash
python -c "import torch; print(torch.__version__, 'cuda:', torch.cuda.is_available(), 'threads:', torch.get_num_threads())"
```

If `cuda: False` on a machine with an NVIDIA GPU, you have the CPU build or an old driver. Reinstall the default wheel and update the driver.

## 4. Choosing the device

Set `training.device` in the YAML or pass `--device` on the command line.

| Value | Behaviour |
|---|---|
| `cpu` | Always the CPU |
| `cuda` | The first NVIDIA GPU. Stops with a clear error if none is available |
| `auto` | The GPU if PyTorch can see one, otherwise the CPU |

```bash
python -m trafma train --method central --config configs/learning_compact_1500.yaml --device auto
python -m trafma train --method central --config configs/learning_compact_1500.yaml --device cuda
python -m trafma train --method central --config configs/learning_compact_1500.yaml --device cpu
```

The device that was actually used is written to the run's `manifest.json` (`device`, `device_requested`) and to `summary.md`.

GPU status: the GPU path is implemented but was **not tested** in the environment where this was developed (no GPU available). Run it once on your own machine and check `summary.md` before relying on it. For a model this small, do not expect a GPU to be faster than a multi-core CPU.

## 5. CPU multi-threading

On the CPU, PyTorch spreads the matrix work over several threads. This project sets the thread count explicitly.

| Setting | Behaviour |
|---|---|
| `training.num_threads: 0` (default) | Use every logical core |
| `training.num_threads: 8` | Use exactly 8 threads |
| `--threads 8` | Same, from the command line (works for `train` and `fedavg`) |

```bash
python -m trafma train  --method central --config configs/learning_compact_1500.yaml --device cpu --threads 8
python -m trafma fedavg --hierarchical   --config configs/learning_compact_1500.yaml --threads 8
```

The thread count in use is recorded as `cpu_threads` in the run manifest. On a GPU the setting is ignored.

Note: the development sandbox had one core, so multi-threading was confirmed to be applied but its speed-up was not measured. Using all cores while SUMO is running at the same time slows both down, so run training after data collection finishes.

## 6. Reproducibility

- `training.deterministic: true` (default) asks PyTorch for deterministic algorithms and fixes all random seeds. Two runs on the same machine with the same settings gave identical metrics.
- Results can still differ slightly between machines, between CPU and GPU, and between different thread counts. Compare runs made with the same settings.
- If a GPU run stops with an error about a non-deterministic operation, set `training.deterministic: false` and record that in your notes.
- Training seeds 400 to 404 are reserved and rejected.

## 7. Troubleshooting

| Message or symptom | Fix |
|---|---|
| `training.device=cuda was requested, but this PyTorch installation has no available CUDA device` | Use `--device auto` or `--device cpu`, or install the CUDA build of PyTorch |
| `training.min_epochs must be an integer in [1, training.epochs]` | Make `min_epochs` no larger than `epochs` |
| `training.num_threads must be an integer >= 0` | Use 0 for all cores or a positive count |
| `only N vehicle clients have >= 75 windows` | Lower `federation.max_clients` or `federation.max_windows_per_client`, or generate more training runs |
| `dataset manifest not found` | Run `python -m trafma collect --config configs/data_compact_1500.yaml` first |
