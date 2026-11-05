"""Test helpers for test sample budget."""

import json

import pytest

from trafma.sample_budget import SampleBudgetError, build_budget, format_markdown, run_sample_budget


def _manifest(tmp_path):
    """Handles  manifest for the values provided.

    Args:
        tmp_path: Value used by this function.

    Returns:
        None.
    """
    runs = {
        "a_s1": {"split": "train", "scenario": "a", "steps": 900, "vehicles_scheduled": 50, "vehicles_departed": 50,
                 "vehicles_arrived": 40, "vehicles_unfinished": 10},
        "a_s2": {"split": "val", "scenario": "a", "steps": 900, "vehicles_scheduled": 50, "vehicles_departed": 50,
                 "vehicles_arrived": 50, "vehicles_unfinished": 0},
    }
    clients = {
        "a_s1/rsu_N": {"split": "train", "type": "rsu", "obs_steps": 900, "windows": 860},
        "a_s1/veh_0000": {"split": "train", "type": "vehicle", "obs_steps": 100, "windows": 80},
        "a_s2/rsu_N": {"split": "val", "type": "rsu", "obs_steps": 900, "windows": 860},
    }
    integrity = {"split_run_overlap": [], "windows_violating_run_or_horizon_rule": 0, "total_collisions": 0,
                 "total_teleports": 0, "evaluator_keys_found_in_agent_logs": []}
    (tmp_path / "dataset_manifest.json").write_text(json.dumps(
        {"runs": runs, "clients": clients, "integrity": integrity, "splits": {"train": ["a_s1"], "val": ["a_s2"]}}))


def test_budget_counts_come_from_the_manifest(tmp_path):
    """Checks that budget counts come from the manifest.

    Args:
        tmp_path: Value used by this function.

    Returns:
        None.
    """
    _manifest(tmp_path)
    b = build_budget(tmp_path)
    assert b["simulation"]["train"]["vehicles_scheduled"] == 50 and b["simulation"]["test"]["runs"] == 0
    assert b["observations_and_windows"]["train"] == {
        "rsu_records": 900, "vehicle_records": 100, "rsu_windows": 860, "vehicle_windows": 80,
        "rsu_clients": 1, "vehicle_clients": 1}
    assert b["scenarios"]["a"]["vehicles_per_run"] == 50


def test_markdown_tables_are_well_formed(tmp_path):
    """Checks that markdown tables are well formed.

    Args:
        tmp_path: Value used by this function.

    Returns:
        None.
    """
    _manifest(tmp_path)
    text = format_markdown(build_budget(tmp_path))
    lines = text.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("|"):                       # a table must be preceded by a blank line (preview-safe)
            assert i == 0 or lines[i - 1].startswith("|") or lines[i - 1] == ""
    assert text.count("```") % 2 == 0


def test_writes_markdown_and_json_and_rejects_missing_dataset(tmp_path):
    """Checks that writes markdown and json and rejects missing dataset.

    Args:
        tmp_path: Value used by this function.

    Returns:
        None.
    """
    _manifest(tmp_path)
    out = run_sample_budget(tmp_path)
    assert out.is_file() and out.with_suffix(".json").is_file()
    with pytest.raises(SampleBudgetError):
        build_budget(tmp_path / "nope")
