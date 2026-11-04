"""Sample accounting: how many vehicles, observations, windows and FL rounds sit behind a training budget.

Everything is read from saved artifacts (dataset manifest, feature audit, experiment manifests); nothing is estimated.
"""
from __future__ import annotations

import json
from collections import defaultdict
from pathlib import Path
from typing import Optional, Union

SPLITS = ("train", "val", "test")


class SampleBudgetError(ValueError):
    """Raised when the dataset or experiment artifacts needed for the accounting are missing."""


def _load(path: Path) -> dict:
    if not path.is_file():
        raise SampleBudgetError(f"missing artifact: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def build_budget(dataset_dir: Union[str, Path], experiments: Optional[list] = None) -> dict:
    root = Path(dataset_dir)
    man = _load(root / "dataset_manifest.json")
    audit_path = root / "feature_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8")) if audit_path.is_file() else None

    runs = man["runs"]
    sim = {s: {"runs": 0, "sim_seconds": 0, "vehicles_scheduled": 0, "vehicles_departed": 0,
               "vehicles_arrived": 0, "vehicles_unfinished": 0} for s in SPLITS}
    scenarios = defaultdict(lambda: {"vehicles_per_run": 0, "runs": defaultdict(int)})
    for run in runs.values():
        row = sim[run["split"]]
        row["runs"] += 1
        row["sim_seconds"] += int(run["steps"])
        row["vehicles_scheduled"] += int(run["vehicles_scheduled"])
        row["vehicles_departed"] += int(run["vehicles_departed"])
        row["vehicles_arrived"] += int(run["vehicles_arrived"])
        row["vehicles_unfinished"] += int(run["vehicles_unfinished"])
        sc = scenarios[run["scenario"]]
        sc["vehicles_per_run"] = int(run["vehicles_scheduled"])
        sc["runs"][run["split"]] += 1

    obs = {s: {"rsu_records": 0, "vehicle_records": 0, "rsu_windows": 0, "vehicle_windows": 0,
               "rsu_clients": 0, "vehicle_clients": 0} for s in SPLITS}
    for client in man["clients"].values():
        row = obs[client["split"]]
        kind = "rsu" if client["type"] == "rsu" else "vehicle"
        row[f"{kind}_records"] += int(client["obs_steps"])
        row[f"{kind}_windows"] += int(client["windows"])
        row[f"{kind}_clients"] += 1

    budget = {
        "dataset_id": man.get("splits") and root.name,
        "history_steps": 10,
        "horizon_s": 30,
        "simulation": sim,
        "scenarios": {k: {"vehicles_per_run": v["vehicles_per_run"], "runs": dict(v["runs"])}
                      for k, v in sorted(scenarios.items())},
        "observations_and_windows": obs,
        "vehicle_records_in_scope": (audit or {}).get("counts", {}).get("incoming_local_vehicle_records"),
        "integrity": man["integrity"],
        "experiments": [],
    }
    for exp in experiments or []:
        d = Path(exp)
        m = _load(d / "manifest.json")
        item = {"experiment_id": m["experiment_id"], "method": m["method"]}
        if "rounds" in m and isinstance(m["rounds"], list):                      # federated
            cfg = _load_yaml(d / "resolved_config.yaml")
            clients = m["selected_clients_by_type"]
            item.update({
                "train_windows": m["selected_train_windows"],
                "validation_windows": m["validation_window_count"],
                "test_windows": m["test_window_count"],
                "clients": m["selected_client_count"],
                "clients_by_type": clients,
                "clients_by_approach": m["selected_clients_by_approach"],
                "windows_per_client": m["max_windows_per_client"],
                "rounds": len(m["rounds"]),
                "local_epochs": cfg["training"]["local_epochs"],
                "client_updates": sum(len(r["accepted_clients"]) for r in m["rounds"]),
                "edge_groups_per_round": len(m["rounds"][0]["groups"]) if m["rounds"] else 0,
                "sample_passes": len(m["rounds"]) * cfg["training"]["local_epochs"] * m["selected_train_windows"],
                "wall_s": m["wall_duration_s"], "cpu_threads": m.get("cpu_threads"),
            })
        else:                                                                        # central / local GRU
            counts = m["selected_window_counts"]
            item.update({
                "train_windows": counts["train"], "validation_windows": counts["validation"],
                "test_windows": counts["test"], "epochs_run": m["epochs_run"], "min_epochs": m["min_epochs"],
                "max_epochs": m["max_epochs"], "best_epoch": m["best_epoch"], "early_stopped": m["early_stopped"],
                "device": m["device"], "cpu_threads": m["cpu_threads"], "wall_s": m["training_wall_time_s"],
                "sample_passes": m["epochs_run"] * counts["train"],
            })
        budget["experiments"].append(item)
    return budget


def _load_yaml(path: Path) -> dict:
    import yaml
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def format_markdown(b: dict) -> str:
    sim, obs = b["simulation"], b["observations_and_windows"]
    L = [f"# Sample budget: `{b['dataset_id']}`", "",
         "Generated by `python -m trafma sample-budget`; every number is read from saved artifacts.", "",
         f"A sample is one window: {b['history_steps']} consecutive 1 s observation steps from one agent, "
         f"labelled with the congestion state {b['horizon_s']} s later.", "",
         "## 1. Simulation", "",
         "| Scenario | Vehicles per run | Train runs | Val runs | Test runs |", "|---|---:|---:|---:|---:|"]
    for name, sc in b["scenarios"].items():
        r = sc["runs"]
        L.append(f"| {name} | {sc['vehicles_per_run']} | {r.get('train', 0)} | {r.get('val', 0)} | {r.get('test', 0)} |")
    L += ["", "| Split | Runs | Simulated seconds | Vehicles scheduled | Departed | Arrived | Still on road at end |",
          "|---|---:|---:|---:|---:|---:|---:|"]
    for s in SPLITS:
        r = sim[s]
        L.append(f"| {s} | {r['runs']} | {r['sim_seconds']} | {r['vehicles_scheduled']} | {r['vehicles_departed']} "
                 f"| {r['vehicles_arrived']} | {r['vehicles_unfinished']} |")
    tot = {k: sum(sim[s][k] for s in SPLITS) for k in sim["train"]}
    L.append(f"| **all** | {tot['runs']} | {tot['sim_seconds']} | {tot['vehicles_scheduled']} | "
             f"{tot['vehicles_departed']} | {tot['vehicles_arrived']} | {tot['vehicles_unfinished']} |")
    L += ["", "## 2. Observations collected and windows available", "",
          "| Split | RSU records | Vehicle records | RSU windows | Vehicle windows | All windows |",
          "|---|---:|---:|---:|---:|---:|"]
    for s in SPLITS:
        o = obs[s]
        L.append(f"| {s} | {o['rsu_records']} | {o['vehicle_records']} | {o['rsu_windows']} | "
                 f"{o['vehicle_windows']} | {o['rsu_windows'] + o['vehicle_windows']} |")
    if b.get("vehicle_records_in_scope") is not None:
        L += ["", f"Of all vehicle records, {b['vehicle_records_in_scope']} were taken while the vehicle was on its "
                  "incoming road (the only records that can form a window)."]
    L += ["", "## 3. What each method trains on", ""]
    for e in b["experiments"]:
        avail = obs["train"]["rsu_windows"] + obs["train"]["vehicle_windows"]
        L += [f"### {e['method']}", "", f"Experiment `{e['experiment_id']}`.", "",
              "| Item | Value |", "|---|---:|",
              f"| Training windows used | {e['train_windows']} of {avail} available "
              f"({100.0 * e['train_windows'] / avail:.2f} %) |",
              f"| Validation / test windows | {e['validation_windows']} / {e['test_windows']} |"]
        if "rounds" in e:
            L += [f"| FL clients | {e['clients']} ({e['clients_by_type'].get('rsu', 0)} RSU + "
                  f"{e['clients_by_type'].get('vehicle', 0)} vehicle) |",
                  f"| Windows per client | {e['windows_per_client']} |",
                  f"| Edge groups (one per RSU) | {e['edge_groups_per_round']} |",
                  f"| Communication rounds | {e['rounds']} |",
                  f"| Local epochs per round | {e['local_epochs']} |",
                  f"| Client updates in total | {e['client_updates']} |",
                  f"| Window passes in total | {e['sample_passes']} |"]
        else:
            L += [f"| Epochs trained | {e['epochs_run']} (min {e['min_epochs']}, max {e['max_epochs']}, "
                  f"best at {e['best_epoch']}, {'early stopped' if e['early_stopped'] else 'ran to max'}) |",
                  f"| Window passes in total | {e['sample_passes']} |",
                  f"| Device / CPU threads | {e['device']} / {e['cpu_threads']} |"]
        L += [f"| Training wall time | {e['wall_s']:.1f} s |", ""]
    i = b["integrity"]
    L += ["## 4. Integrity", "",
          f"Split run overlap: {i['split_run_overlap'] or 'none'}. Windows violating the run/horizon rule: "
          f"{i['windows_violating_run_or_horizon_rule']}. Collisions: {i['total_collisions']}. "
          f"Teleports: {i['total_teleports']}. Evaluator keys in agent logs: "
          f"{i['evaluator_keys_found_in_agent_logs'] or 'none'}.", ""]
    return "\n".join(L)


def run_sample_budget(dataset_dir: Union[str, Path], experiments: Optional[list] = None,
                      output: Optional[Union[str, Path]] = None) -> Path:
    b = build_budget(dataset_dir, experiments)
    out = Path(output) if output else Path(dataset_dir) / "sample_budget.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(format_markdown(b), encoding="utf-8")
    out.with_suffix(".json").write_text(json.dumps(b, indent=2, sort_keys=True), encoding="utf-8")
    return out
