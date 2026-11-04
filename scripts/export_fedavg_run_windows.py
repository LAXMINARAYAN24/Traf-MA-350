"""Export exact selected feature windows for a saved hierarchical FedAvg run."""
from __future__ import annotations

import argparse
import collections
import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from trafma.features import SEQUENCE_LENGTH
from trafma.federated_training import _collect_client_windows, _select_hierarchical_vehicles
from trafma.training import _sample_windows


def digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def export(run_dir: Path, dataset_dir: Path, output_dir: Path) -> None:
    run_manifest_path = run_dir / "manifest.json"
    resolved_path = run_dir / "resolved_config.yaml"
    dataset_manifest_path = dataset_dir / "dataset_manifest.json"
    for path in (run_manifest_path, resolved_path, dataset_manifest_path):
        if not path.is_file():
            raise SystemExit(f"required file not found: {path}")
    run_manifest = json.loads(run_manifest_path.read_text(encoding="utf-8"))
    dataset_manifest = json.loads(dataset_manifest_path.read_text(encoding="utf-8"))
    import yaml
    resolved = yaml.safe_load(resolved_path.read_text(encoding="utf-8"))
    federation = resolved["federation"]
    training = resolved["training"]
    evaluation_seed = int(resolved.get("evaluation_seed", training["seed"]))

    selected_ids = list(run_manifest["selected_client_ids"])
    metadata = dataset_manifest["clients"]
    vehicle_ids = [cid for cid in selected_ids if cid in metadata and metadata[cid].get("type") == "vehicle"]
    rsu_group_ids = [cid for cid in selected_ids if cid in {f"rsu_{a}" for a in ("N", "E", "S", "W")}]
    if len(vehicle_ids) != 350 or len(rsu_group_ids) != 4:
        raise SystemExit(f"unexpected selected cohort: {len(vehicle_ids)} vehicles, {len(rsu_group_ids)} RSU groups")

    source_rsu_ids = [
        cid for cid, item in metadata.items()
        if item.get("split") == "train" and item.get("trainable") and item.get("type") == "rsu"
    ]
    source_ids = vehicle_ids + source_rsu_ids
    source_to_destination = {cid: cid for cid in vehicle_ids}
    for source_id in source_rsu_ids:
        approach = metadata[source_id]["approach"]
        source_to_destination[source_id] = f"rsu_{approach}"
    rsu_cap = federation["max_rsu_windows_per_group"]
    selected_train, available = _collect_client_windows(
        dataset_dir, source_ids, selected_ids, source_to_destination,
        int(federation["max_windows_per_client"]), int(federation["cohort_seed"]),
        maximum_by_client={cid: rsu_cap for cid in rsu_group_ids},
    )
    if sum(map(len, selected_train.values())) != run_manifest["selected_train_windows"]:
        raise SystemExit("reconstructed selected training-window count does not match the saved run manifest")
    expected_class_counts = run_manifest["selected_client_label_counts"]
    for client_id, samples in selected_train.items():
        actual = dict(collections.Counter(str(sample.congestion_class) for sample in samples))
        if actual != expected_class_counts[client_id]:
            raise SystemExit(f"reconstructed class counts differ from manifest for learner {client_id}")

    splits: dict[str, list[tuple[object, str]]] = {
        "train": [(sample, learner) for learner, samples in selected_train.items() for sample in samples]
    }
    per_type = int(resolved["evaluation_windows_by_type"])
    splits["validation"] = [
        (sample, sample.client_id)
        for index, kind in enumerate(("vehicle", "rsu"))
        for sample in _sample_windows(
            dataset_dir, "val", per_type, evaluation_seed + 101 + index, client_type=kind
        )
    ]
    splits["test"] = [
        (sample, sample.client_id)
        for index, kind in enumerate(("vehicle", "rsu"))
        for sample in _sample_windows(
            dataset_dir, "test", per_type, evaluation_seed + 201 + index, client_type=kind
        )
    ]

    prediction_path = run_dir / "predictions.csv"
    with prediction_path.open(newline="", encoding="utf-8") as stream:
        predictions = [row for row in csv.DictReader(stream) if row["split"] == "test"]
    keys_expected = {(row["run_id"], row["client_id"], round(float(row["end_t"]), 6)) for row in predictions}
    keys_exported = {(sample.run_id, sample.client_id, round(sample.end_t, 6))
                     for sample, _ in splits["test"]}
    if keys_exported != keys_expected:
        raise SystemExit("reconstructed test-window identities do not match this run's predictions")

    output_dir.mkdir(parents=True, exist_ok=False)
    npz_payload = {}
    metadata_path = output_dir / "selected_windows.csv"
    metadata_fields = ["split", "learner_id", "client_id", "client_type", "approach",
                       "scenario", "run_id", "end_t", "zone_m", "current_queue_m",
                       "target_queue_m", "congestion_class"]
    counts: dict[str, dict[str, int]] = {}
    with metadata_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=metadata_fields)
        writer.writeheader()
        for split_name, items in splits.items():
            features = np.asarray([sample.features for sample, _ in items], dtype=np.float32)
            if features.shape[1:] != (SEQUENCE_LENGTH, 22):
                raise SystemExit(f"unexpected feature tensor shape for {split_name}: {features.shape}")
            prefix = "val" if split_name == "validation" else split_name
            npz_payload[f"x_{prefix}"] = features
            npz_payload[f"queue_m_{prefix}"] = np.asarray([sample.queue_m for sample, _ in items], dtype=np.float32)
            npz_payload[f"class_{prefix}"] = np.asarray([sample.congestion_class for sample, _ in items], dtype=np.int64)
            npz_payload[f"client_id_{prefix}"] = np.asarray([sample.client_id for sample, _ in items], dtype=str)
            npz_payload[f"learner_id_{prefix}"] = np.asarray([learner for _, learner in items], dtype=str)
            type_counts = collections.Counter(sample.client_type for sample, _ in items)
            counts[split_name] = dict(type_counts)
            for sample, learner in items:
                writer.writerow({
                    "split": split_name,
                    "learner_id": learner,
                    "client_id": sample.client_id,
                    "client_type": sample.client_type,
                    "approach": sample.approach,
                    "scenario": sample.scenario,
                    "run_id": sample.run_id,
                    "end_t": sample.end_t,
                    "zone_m": sample.zone_m,
                    "current_queue_m": "" if sample.current_queue_m is None else sample.current_queue_m,
                    "target_queue_m": sample.queue_m,
                    "congestion_class": sample.congestion_class,
                })
    npz_path = output_dir / "selected_windows.npz"
    np.savez_compressed(npz_path, **npz_payload)
    package_manifest = {
        "created_utc": dt.datetime.now(dt.timezone.utc).isoformat(),
        "run_dir": str(run_dir),
        "dataset_id": dataset_dir.name,
        "run_manifest_sha256": digest(run_manifest_path),
        "resolved_config_sha256": digest(resolved_path),
        "dataset_manifest_sha256": digest(dataset_manifest_path),
        "selected_feature_windows_by_split_and_type": counts,
        "training_learners_by_type": run_manifest["selected_clients_by_type"],
        "training_samples_by_learner": {key: len(value) for key, value in selected_train.items()},
        "available_source_windows_by_learner": available,
        "sequence_length": SEQUENCE_LENGTH,
        "feature_dimension": 22,
        "tensor_file": npz_path.name,
        "tensor_file_sha256": digest(npz_path),
        "metadata_file": metadata_path.name,
        "metadata_file_sha256": digest(metadata_path),
        "test_prediction_rows_verified": len(predictions),
    }
    (output_dir / "manifest.json").write_text(json.dumps(package_manifest, indent=2, sort_keys=True), encoding="utf-8")
    print(f"Exported selected windows: {output_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="saved hierarchical FedAvg run directory")
    parser.add_argument("--dataset", type=Path, required=True, help="dataset directory used by the run")
    parser.add_argument("--output", type=Path, required=True, help="new export directory")
    args = parser.parse_args()
    export(args.run, args.dataset, args.output)


if __name__ == "__main__":
    main()
