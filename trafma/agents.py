"""**SUMO/** This file is part of the SUMO related functionality. It defines the software agents that report SUMO traffic.

P1.4/P1.5 - Agent registry (4 RSUs + N vehicles) and the vehicle -> RSU relay logic."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from . import APPROACHES
from .config import Config
from .messages import (Envelope, make_msg_id, build_payload, validate, VEHICLE_REPORT, RSU_SUMMARY,
                       RELAY_BUNDLE, EVIDENCE_DIRECT, EVIDENCE_RELAYED_CHILD, EVIDENCE_RELAY)

COORDINATOR_ID = "coordinator"


def rsu_id(approach: str) -> str:
    """Finds or calculates rsu id for the values provided.

    Args:
        approach: Value used by this function.

    Returns:
        The result produced by this function.
    """
    return f"rsu_{approach}"


class VehicleAgent:
    def __init__(self, vid: str, origin: str, depart_time: float):
        """Sets up this object using the values provided.

        Args:
            vid: Value used by this function.
            origin: Value used by this function.
            depart_time: Value used by this function.

        Returns:
            None.
        """
        self.vid, self.origin, self.parent = vid, origin, rsu_id(origin)
        self.depart_time = depart_time
        self.arrive_time: Optional[float] = None
        self._seq = 0
        self.n_reports = 0

    def report(self, view: dict, now: float) -> Envelope:
        """Formats or summarizes report for the values provided.

        Args:
            view: Value used by this function.
            now: Value used by this function.

        Returns:
            The result produced by this function.
        """
        env = Envelope(make_msg_id(self.vid, self._seq), VEHICLE_REPORT, self.vid, self.vid, self.parent,
                       self._seq, now, [self.vid], EVIDENCE_RELAYED_CHILD, build_payload(VEHICLE_REPORT, view))
        self._seq += 1
        self.n_reports += 1
        return env


class RsuAgent:
    """Roadside unit for ONE road. Exists for the whole run. Senses its own approach and relays its children."""

    def __init__(self, approach: str, cfg: Config):
        """Sets up this object using the values provided.

        Args:
            approach: Value used by this function.
            cfg: Value used by this function.

        Returns:
            None.
        """
        self.approach, self.id, self.cfg = approach, rsu_id(approach), cfg
        self._seq = 0
        self._bundle_seq = 0
        self.children: set = set()
        self._last_seq: dict = {}
        self._seen: set = set()
        self._relay_buf: list = []
        self.stats = {"accepted": 0, "duplicate": 0, "stale": 0, "out_of_order": 0, "invalid": 0,
                      "not_my_child": 0}

    def summarise(self, view: dict, now: float) -> Envelope:
        """Formats or summarizes summarise for the values provided.

        Args:
            view: Value used by this function.
            now: Value used by this function.

        Returns:
            The result produced by this function.
        """
        env = Envelope(make_msg_id(self.id, self._seq), RSU_SUMMARY, self.id, self.id, COORDINATOR_ID,
                       self._seq, now, [self.id], EVIDENCE_DIRECT, build_payload(RSU_SUMMARY, view))
        self._seq += 1
        return env

    def receive_from_child(self, d: dict, now: float):
        """-> (accepted: bool, reason: str)"""
        probs = validate(d)
        if probs:
            self.stats["invalid"] += 1
            return False, "invalid:" + probs[0]
        if d["msg_type"] != VEHICLE_REPORT:
            self.stats["invalid"] += 1
            return False, "invalid:not a vehicle_report"
        if d["origin_id"] not in self.children:
            self.stats["not_my_child"] += 1
            return False, "not_my_child"
        if d["msg_id"] in self._seen:
            self.stats["duplicate"] += 1
            return False, "duplicate"
        if d["seq"] <= self._last_seq.get(d["origin_id"], -1):
            self.stats["out_of_order"] += 1
            return False, "out_of_order"
        if d["sim_time"] < now - self.cfg.comms.stale_after_s:
            self.stats["stale"] += 1
            return False, "stale"
        self._seen.add(d["msg_id"])
        self._last_seq[d["origin_id"]] = d["seq"]
        d = dict(d)
        d["hops"] = list(d["hops"]) + [self.id]
        self._relay_buf.append(d)
        self.stats["accepted"] += 1
        return True, "accepted"

    def flush_relay(self, now: float) -> Optional[Envelope]:
        """Finishes or delivers flush relay for the values provided.

        Args:
            now: Value used by this function.

        Returns:
            The result produced by this function.
        """
        if not self._relay_buf:
            return None
        rep, self._relay_buf = self._relay_buf, []
        env = Envelope(make_msg_id(self.id + ":relay", self._bundle_seq), RELAY_BUNDLE, self.id + ":relay",
                       self.id, COORDINATOR_ID, self._bundle_seq, now, [self.id], EVIDENCE_RELAY,
                       {"rsu_id": self.id, "reports": rep})
        self._bundle_seq += 1
        return env


class AgentRegistry:
    """Single source of truth for which agents exist. Four RSUs from t=0 to the end; vehicles from
    SUMO's departure event to its arrival event (ownership by origin road persists until arrival)."""

    def __init__(self, cfg: Config):
        """Sets up this object using the values provided.

        Args:
            cfg: Value used by this function.

        Returns:
            None.
        """
        self.cfg = cfg
        self.rsus = {a: RsuAgent(a, cfg) for a in APPROACHES}
        self.vehicles: dict = {}          # active
        self.retired: dict = {}
        self.events: list = []

    def on_depart(self, vid: str, origin: str, now: float) -> VehicleAgent:
        """Handles depart event and updates the related state.

        Args:
            vid: Value used by this function.
            origin: Value used by this function.
            now: Value used by this function.

        Returns:
            The result produced by this function.
        """
        if vid in self.vehicles or vid in self.retired:
            raise RuntimeError(f"vehicle {vid} departed twice")
        v = VehicleAgent(vid, origin, now)
        self.vehicles[vid] = v
        self.rsus[origin].children.add(vid)
        self.events.append((now, "depart", vid))
        return v

    def on_arrive(self, vid: str, now: float):
        """Handles arrive event and updates the related state.

        Args:
            vid: Value used by this function.
            now: Value used by this function.

        Returns:
            None.
        """
        v = self.vehicles.pop(vid, None)
        if v is None:
            raise RuntimeError(f"vehicle {vid} arrived but was never registered")
        v.arrive_time = now
        self.retired[vid] = v
        self.events.append((now, "arrive", vid))   # RSU child set is kept: late duplicates stay attributable

    def parent_of(self, vid: str) -> Optional[str]:
        """Finds or calculates parent of for the values provided.

        Args:
            vid: Value used by this function.

        Returns:
            The result produced by this function.
        """
        v = self.vehicles.get(vid) or self.retired.get(vid)
        return v.parent if v else None
