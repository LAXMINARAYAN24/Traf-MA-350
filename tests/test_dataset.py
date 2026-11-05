"""Test helpers for test dataset."""

import json

import pytest
import yaml
from conftest import needs_sumo
from trafma.collect import collect, load_collect_config
from trafma.config import ConfigError

pytestmark = needs_sumo


def write(tmp_path, splits):
    """Writes or saves write for the values provided.

    Args:
        tmp_path: Value used by this function.
        splits: Value used by this function.

    Returns:
        The result produced by this function.
    """
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump({"dataset_id": "t", "output_dir": str(tmp_path / "data"),
                                 "base": {"run": {"duration_s": 400}},
                                 "scenarios": [{"name": "moderate", "vehicles": 80}],
                                 "splits": splits}))
    return p


def test_overlapping_split_seeds_rejected(tmp_path):
    """Checks that overlapping split seeds rejected.

    Args:
        tmp_path: Value used by this function.

    Returns:
        None.
    """
    with pytest.raises(ConfigError, match="disjoint"):
        load_collect_config(write(tmp_path, {"train": [1, 2], "test": [2]}))


def test_missing_sections_rejected(tmp_path):
    """Checks that missing sections rejected.

    Args:
        tmp_path: Value used by this function.

    Returns:
        None.
    """
    p = tmp_path / "x.yaml"; p.write_text("dataset_id: a\n")
    with pytest.raises(ConfigError):
        load_collect_config(p)


@pytest.fixture(scope="module")
def man(tmp_path_factory):
    """Handles man for the values provided.

    Args:
        tmp_path_factory: Value used by this function.

    Returns:
        The result produced by this function.
    """
    tp = tmp_path_factory.mktemp("ds")
    return collect(write(tp, {"train": [1], "test": [2]}), out=lambda *a: None), tp / "data" / "t"


def test_integrity_block_clean(man):
    """Checks that integrity block clean.

    Args:
        man: Value used by this function.

    Returns:
        None.
    """
    m, _ = man
    i = m["integrity"]
    assert i["split_run_overlap"] == [] and i["windows_violating_run_or_horizon_rule"] == 0
    assert i["evaluator_keys_found_in_agent_logs"] == [] and i["all_runs_have_complete_rsu_logs"]
    assert i["total_collisions"] == i["total_teleports"] == 0


def test_windows_never_cross_runs_and_labels_are_in_the_future(man):
    """Checks that windows never cross runs and labels are in the future.

    Args:
        man: Value used by this function.

    Returns:
        None.
    """
    m, d = man
    H = m["definitions"]["horizon_s"]
    for run in m["runs"]:
        for l in open(d / m["runs"][run]["split"] / run / "windows.jsonl"):
            w = json.loads(l)
            assert w["client"].startswith(run + "/")
            assert w["label_t"] == pytest.approx(w["end_t"] + H)


def test_vehicle_windows_require_full_incoming_history(man):
    """Checks that vehicle windows require full incoming history.

    Args:
        man: Value used by this function.

    Returns:
        None.
    """
    m, d = man
    hist = m["definitions"]["history_len"]
    run = next(iter(m["runs"]))
    wins = [json.loads(l) for l in open(d / m["runs"][run]["split"] / run / "windows.jsonl")]
    vw = [w for w in wins if w["type"] == "vehicle"]
    assert vw
    by = {}
    for w in vw:
        by.setdefault(w["client"], []).append(w["end_t"])
    for cid, ends in list(by.items())[:15]:
        vid = cid.split("/")[1]
        recs = [json.loads(l) for l in open(d / m["runs"][run]["split"] / run / "agents" / f"{vid}.jsonl")]
        scope = {r["t"]: r["view"]["scope"] for r in recs}
        for e in ends:
            assert all(scope.get(e - k) == "incoming_local" for k in range(hist))


def test_trainable_rule_and_manifest_files(man):
    """Checks that trainable rule and manifest files.

    Args:
        man: Value used by this function.

    Returns:
        None.
    """
    m, d = man
    mw = m["definitions"]["min_windows_trainable"]
    assert all(c["trainable"] == (c["windows"] >= mw) for c in m["clients"].values())
    assert (d / "dataset_manifest.json").is_file() and (d / "dataset_report.txt").is_file()
    assert len([c for c in m["clients"].values() if c["type"] == "rsu"]) == 8     # 4 RSUs x 2 runs


def test_runs_are_physically_separated_by_split(man):
    """Checks that runs are physically separated by split.

    Args:
        man: Value used by this function.

    Returns:
        None.
    """
    m, d = man
    sp = json.loads((d / "splits.json").read_text())
    assert set(sp) == {"train", "test"} and not (d / "runs").exists()
    for split, runs in sp.items():
        on_disk = sorted(p.name for p in (d / split).iterdir() if p.is_dir())
        assert on_disk == runs and runs
    assert not set(sp["train"]) & set(sp["test"])


def test_default_splits_when_config_has_none(tmp_path):
    """Checks that default splits when config has none.

    Args:
        tmp_path: Value used by this function.

    Returns:
        None.
    """
    import yaml
    from trafma.collect import DEFAULT_SPLITS
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump({"scenarios": [{"name": "a", "vehicles": 5}]}))
    assert load_collect_config(p)["splits"] == DEFAULT_SPLITS
    p.write_text(yaml.safe_dump({"scenarios": [{"name": "a", "vehicles": 5}], "splits": {"dev": [1]}}))
    with pytest.raises(Exception):
        load_collect_config(p)
