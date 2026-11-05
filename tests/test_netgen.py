"""Test helpers for test netgen."""

import math

from conftest import needs_sumo
from trafma import APPROACHES
from trafma.sensors import approach_signal_char, time_to_state_change

pytestmark = needs_sumo


def test_twelve_links_three_per_approach(topo):
    """Checks that twelve links three per approach.

    Args:
        topo: Value used by this function.

    Returns:
        None.
    """
    assert topo.n_links == 12
    all_links = sorted(i for a in APPROACHES for i in topo.approaches[a].link_indices)
    assert all_links == list(range(12))
    assert all(len(topo.approaches[a].link_indices) == 3 for a in APPROACHES)


def test_signal_never_gives_two_approaches_green(topo):
    """Checks that signal never gives two approaches green.

    Args:
        topo: Value used by this function.

    Returns:
        None.
    """
    for ph in topo.signal_phases:
        live = [a for a in APPROACHES if approach_signal_char(ph["state"], topo.approaches[a].link_indices) != "r"]
        assert len(live) <= 1, ph


def test_every_approach_gets_green_and_cycle(topo):
    """Checks that every approach gets green and cycle.

    Args:
        topo: Value used by this function.

    Returns:
        None.
    """
    greens = {a: sum(p["duration"] for p in topo.signal_phases
                     if approach_signal_char(p["state"], topo.approaches[a].link_indices) == "G") for a in APPROACHES}
    assert set(greens.values()) == {25.0}
    assert topo.cycle_s == 120.0


def test_one_rsu_per_road_beside_its_own_stop_line(topo):
    """Checks that one rsu per road beside its own stop line.

    Args:
        topo: Value used by this function.

    Returns:
        None.
    """
    pos = {a: topo.approaches[a].rsu_xy for a in APPROACHES}
    assert len(set(pos.values())) == 4
    for a, g in topo.approaches.items():
        d = math.dist(g.rsu_xy, g.stop_xy)
        assert 7.9 < d < 8.1
        others = [math.dist(g.rsu_xy, o.stop_xy) for b, o in topo.approaches.items() if b != a]
        assert min(others) > d            # nearest stop line is its own


def test_lane_fits_zone(topo):
    """Checks that lane fits zone.

    Args:
        topo: Value used by this function.

    Returns:
        None.
    """
    assert all(g.in_len >= 150 and g.out_len >= 100 for g in topo.approaches.values())


def test_time_to_state_change(topo):
    # phase 0 = N green with 24 s left: N changes in 24 s; E stays red through N's yellow+allred (24+3+2)
    """Checks that time to state change.

    Args:
        topo: Value used by this function.

    Returns:
        None.
    """
    assert time_to_state_change(topo, "N", 0, 24.0) == 24.0
    assert time_to_state_change(topo, "E", 0, 24.0) == 29.0


# ---------------------------------------------------------------- drive side (left-hand traffic, Indian norm)
def _lateral(g):
    """Signed lateral offset of the RSU from its lane at the stop line: + = left of travel, - = right."""
    ux, uy = g.dir_xy
    return (-uy * (g.rsu_xy[0] - g.stop_xy[0]) + ux * (g.rsu_xy[1] - g.stop_xy[1]))


def _build(tmp_path, side):
    """Handles  build for the values provided.

    Args:
        tmp_path: Value used by this function.
        side: Value used by this function.

    Returns:
        The result produced by this function.
    """
    from trafma.config import load_config
    from trafma.netgen import build_network, Topology
    _, tp, _, _ = build_network(load_config(overrides={"network": {"drive_side": side}}), tmp_path / side)
    return Topology.load(tp)


def test_default_is_left_hand_traffic(topo):
    """Checks that default is left hand traffic.

    Args:
        topo: Value used by this function.

    Returns:
        None.
    """
    assert topo.drive_side == "left"


def test_left_hand_rsu_on_left_kerb_and_right_hand_on_right(tmp_path):
    """Checks that left hand rsu on left kerb and right hand on right.

    Args:
        tmp_path: Value used by this function.

    Returns:
        None.
    """
    left, right = _build(tmp_path, "left"), _build(tmp_path, "right")
    assert all(_lateral(g) > 7.9 for g in left.approaches.values())      # + = left of travel
    assert all(_lateral(g) < -7.9 for g in right.approaches.values())    # - = right of travel


def test_compass_layout_and_signal_identical_for_both_sides(tmp_path):
    """Checks that compass layout and signal identical for both sides.

    Args:
        tmp_path: Value used by this function.

    Returns:
        None.
    """
    left, right = _build(tmp_path, "left"), _build(tmp_path, "right")
    # link numbering inside the state string may differ between SUMO builds; the schedule must not
    sched = lambda t: [(ph["label"], ph["duration"]) for ph in t.signal_phases]
    assert sched(left) == sched(right) and left.cycle_s == right.cycle_s
    from trafma.sensors import approach_signal_char
    for t in (left, right):
        for ph in t.signal_phases:
            if ph["label"].endswith("_green"):
                a = ph["label"][0]
                assert approach_signal_char(ph["state"], t.approaches[a].link_indices) == "G"
                assert all(approach_signal_char(ph["state"], t.approaches[b].link_indices) == "r"
                           for b in APPROACHES if b != a)
    for a in APPROACHES:
        assert left.approaches[a].dir_xy == right.approaches[a].dir_xy      # N still heads south, etc.
        assert left.approaches[a].link_indices and len(left.approaches[a].link_indices) == 3


def test_left_hand_lane_is_left_of_road_axis(tmp_path):
    """Checks that left hand lane is left of road axis.

    Args:
        tmp_path: Value used by this function.

    Returns:
        None.
    """
    import sumolib
    from trafma.config import load_config
    from trafma.netgen import build_network
    build_network(load_config(), tmp_path / "chk")
    net = sumolib.net.readNet(str(tmp_path / "chk" / "net.net.xml"))
    # N arm: vehicles head south; the driver's left is east (+x). Lane must be east of the arm-end node.
    n_lane = net.getEdge("N_in").getLanes()[0].getShape()[0]
    assert n_lane[0] > net.getNode("N").getCoord()[0]
    # turn labels are unchanged: N->E is a LEFT turn, N->W a RIGHT turn
    e = net.getEdge("N_in")
    dirs = {o.getID(): e.getConnections(o)[0].getDirection() for o in e.getOutgoing()}
    assert dirs == {"E_out": "l", "S_out": "s", "W_out": "r"}


def test_invalid_drive_side_rejected():
    """Checks that invalid drive side rejected.

    Returns:
        None.
    """
    import pytest
    from trafma.config import load_config, ConfigError
    with pytest.raises(ConfigError):
        load_config(overrides={"network": {"drive_side": "middle"}})


def test_old_topology_without_drive_side_loads_as_right_hand(topo):
    """Checks that old topology without drive side loads as right hand.

    Args:
        topo: Value used by this function.

    Returns:
        None.
    """
    import json
    from trafma.netgen import Topology
    d = json.loads(topo.to_json()); d.pop("drive_side")
    assert Topology.from_json(json.dumps(d)).drive_side == "right"
