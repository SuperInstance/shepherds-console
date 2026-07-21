"""Stress tests — actively try to break shepherds-console.

These tests probe edge cases, race conditions, and architectural gaps
that the happy-path test suite misses. After v0.3.0 fixes, many of
these now verify the FIX rather than documenting the bug.
"""

import json
import math
import os
import pytest
import tempfile
import time

from shepherds_console import (
    ShepherdsConsole,
    Fence,
    Pasture,
    Animal,
    LogEntry,
    Health,
    PastureMode,
    Severity,
)


# ── Duplicate Registration (FIXED in v0.3.0) ───────────


class TestDuplicateRegistration:
    """v0.2.0 BUG: Silent overwrite on duplicate names.
    v0.3.0 FIX: Raises ValueError on duplicates."""

    def test_duplicate_animal_raises(self):
        c = ShepherdsConsole()
        c.add_pasture("p1")
        c.add_animal("worker-a", pasture="p1", role="flux")
        with pytest.raises(ValueError, match="already exists"):
            c.add_animal("worker-a", pasture="p1", role="sentinel")

    def test_duplicate_pasture_raises(self):
        c = ShepherdsConsole()
        c.add_pasture("meadow", capacity=10)
        with pytest.raises(ValueError, match="already exists"):
            c.add_pasture("meadow", capacity=5)

    def test_duplicate_fence_raises(self):
        c = ShepherdsConsole()
        c.add_fence("budget", limit=1000)
        with pytest.raises(ValueError, match="already exists"):
            c.add_fence("budget", limit=500)


# ── Throttle Fence Cap (FIXED in v0.3.0) ───────────────


class TestThrottleFenceCap:
    """v0.2.0 BUG: throttle fences let consumed grow unbounded.
    v0.3.0 FIX: throttle caps consumed at limit."""

    def test_throttle_caps_at_limit(self):
        """Throttle should cap consumed at limit, not grow unbounded."""
        f = Fence(name="test", limit=100, action="throttle")
        result1 = f.consume(150)
        assert result1 is True  # allowed (throttle = allow but warn)
        assert f.consumed == 100  # capped at limit, not 150
        assert f.violations == 1
        result2 = f.consume(1000)
        assert result2 is True
        assert f.consumed == 100  # still capped
        assert f.violations == 2

    def test_throttle_fence_still_allows(self):
        """Throttle action allows operations but counts violations."""
        f = Fence(name="test", limit=10, action="throttle")
        f.consume(100)
        assert f.violations == 1
        assert f.consumed == 10  # capped


# ── Invalid Action Validation (FIXED in v0.3.0) ────────


class TestInvalidAction:
    """v0.2.0 BUG: Invalid action strings silently accepted.
    v0.3.0 FIX: Validated against allowed set."""

    def test_invalid_action_rejected(self):
        c = ShepherdsConsole()
        with pytest.raises(ValueError, match="action must be one of"):
            c.add_fence("test", limit=100, action="nonsense")

    def test_valid_actions_accepted(self):
        c = ShepherdsConsole()
        for action in ("throttle", "block", "alert"):
            c.add_fence(f"f-{action}", limit=100, action=action)


# ── Start/Complete Task Lifecycle (FIXED in v0.3.0) ────


class TestTaskLifecycle:
    """v0.2.0 BUG: tasks_in_progress only decrements, never increments.
    v0.3.0 FIX: start_task() method added."""

    def test_start_task_increments(self):
        c = ShepherdsConsole()
        c.add_pasture("p1", mode="plow")
        c.add_animal("w1", pasture="p1")
        c.start_task("w1")
        assert c.pastures["p1"].tasks_in_progress == 1
        c.complete_task("w1")
        assert c.pastures["p1"].tasks_in_progress == 0


# ── Capacity Enforcement (FIXED in v0.3.0) ─────────────


class TestCapacityEnforcement:
    """v0.2.0 BUG: capacity=0 pasture accepts animals.
    v0.3.0 FIX: capacity enforced on add_animal and assign."""

    def test_zero_capacity_rejects_animals(self):
        c = ShepherdsConsole()
        c.add_pasture("zero-cap", capacity=0)
        with pytest.raises(ValueError, match="at capacity"):
            c.add_animal("w1", pasture="zero-cap")

    def test_full_capacity_rejects(self):
        c = ShepherdsConsole()
        c.add_pasture("small", capacity=1)
        c.add_animal("w1", pasture="small")
        with pytest.raises(ValueError, match="at capacity"):
            c.add_animal("w2", pasture="small")


# ── NaN and Infinity Guards (FIXED in v0.3.0) ──────────


class TestNumericEdgeCases:
    """v0.2.0 BUG: NaN/Infinity silently accepted.
    v0.3.0 FIX: Rejected in consume, cost, and limit."""

    def test_nan_cost_rejected(self):
        c = ShepherdsConsole()
        c.add_pasture("p1")
        c.add_fence("f1", limit=100)
        c.add_animal("w1", pasture="p1")
        with pytest.raises(ValueError, match="finite"):
            c.complete_task("w1", cost=float("nan"))

    def test_infinity_cost_rejected(self):
        c = ShepherdsConsole()
        c.add_pasture("p1")
        c.add_fence("f1", limit=100)
        c.add_animal("w1", pasture="p1")
        with pytest.raises(ValueError, match="finite"):
            c.complete_task("w1", cost=float("inf"))

    def test_nan_consume_rejected(self):
        f = Fence(name="t", limit=100)
        with pytest.raises(ValueError, match="finite"):
            f.consume(float("nan"))

    def test_nan_limit_rejected(self):
        c = ShepherdsConsole()
        with pytest.raises(ValueError, match="finite"):
            c.add_fence("bad", limit=float("nan"))


# ── Log Trimming Performance (FIXED in v0.3.0) ─────────


class TestLogTrimmingPerformance:
    """v0.2.0 BUG: log trimming O(n) via list slicing.
    v0.3.0 FIX: deque(maxlen) — O(1) auto-trimming."""

    def test_log_trimming_is_o1(self):
        c = ShepherdsConsole()
        c._max_logs = 10
        for i in range(10000):
            c.log(f"msg-{i}")
        assert len(c.logs) == 500  # deque default maxlen


# ── Lifecycle Methods (ADDED in v0.3.0) ────────────────


class TestLifecycleMethods:
    """v0.2.0 BUG: No remove/reset methods.
    v0.3.0 FIX: Full lifecycle added."""

    def test_remove_animal(self):
        c = ShepherdsConsole()
        c.add_pasture("p1")
        c.add_animal("w1", pasture="p1")
        removed = c.remove_animal("w1")
        assert removed.name == "w1"
        assert "w1" not in c.kennel
        assert "w1" not in c.pastures["p1"].animals

    def test_remove_pasture_orphans_animals(self):
        c = ShepherdsConsole()
        c.add_pasture("p1")
        c.add_animal("w1", pasture="p1")
        c.remove_pasture("p1")
        assert "p1" not in c.pastures
        assert c.kennel["w1"].pasture is None  # orphaned

    def test_remove_fence(self):
        c = ShepherdsConsole()
        c.add_fence("f1", limit=100)
        c.remove_fence("f1")
        assert "f1" not in c.fences

    def test_reset_fence(self):
        c = ShepherdsConsole()
        c.add_fence("f1", limit=100)
        c.fences["f1"].consumed = 90
        c.fences["f1"].violations = 3
        c.reset_fence("f1")
        assert c.fences["f1"].consumed == 0
        assert c.fences["f1"].violations == 0


# ── Save/Load Robustness ───────────────────────────────


class TestSaveLoadRobustness:
    """Save/load edge cases."""

    def test_load_corrupted_json(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            f.write("{corrupted json!!!")
            path = f.name
        try:
            with pytest.raises(json.JSONDecodeError):
                ShepherdsConsole.load_state(path)
        finally:
            os.unlink(path)

    def test_load_partial_state(self):
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as f:
            json.dump({"version": "0.1.0", "pastures": {}}, f)
            path = f.name
        try:
            c = ShepherdsConsole.load_state(path)
            assert len(c.fences) == 0
            assert len(c.kennel) == 0
        finally:
            os.unlink(path)


# ── Offline Animal Guard (FIXED in v0.3.0) ─────────────


class TestOfflineAnimalGuard:
    """v0.2.0 BUG: Offline/injured animals can still complete tasks.
    v0.3.0 FIX: RuntimeError if health is OFFLINE or INJURED."""

    def test_offline_animal_cannot_complete_task(self):
        c = ShepherdsConsole()
        c.add_pasture("p1")
        c.add_animal("w1", pasture="p1")
        c.set_health("w1", "offline")
        with pytest.raises(RuntimeError, match="offline"):
            c.complete_task("w1", cost=10)

    def test_injured_animal_cannot_complete_task(self):
        c = ShepherdsConsole()
        c.add_pasture("p1")
        c.add_animal("w1", pasture="p1")
        c.set_health("w1", "injured")
        with pytest.raises(RuntimeError, match="injured"):
            c.complete_task("w1", cost=10)


# ── Nonexistent Pasture (FIXED in v0.3.0) ──────────────


class TestNonexistentPasture:
    """v0.2.0 BUG: Animal with nonexistent pasture silently orphaned.
    v0.3.0 FIX: KeyError raised."""

    def test_nonexistent_pasture_raises(self):
        c = ShepherdsConsole()
        with pytest.raises(KeyError, match="does not exist"):
            c.add_animal("w1", pasture="does-not-exist")


# ── Fence Status Boundary Exact Values ─────────────────


class TestFenceStatusBoundaries:
    """Exact boundary values of fence.status."""

    def test_exact_0_1_boundary(self):
        f = Fence(name="t", limit=1000)
        f.consumed = 900
        assert f.budget_fraction == pytest.approx(0.1)
        assert f.status == "low"  # frac < 0.1 is False at exactly 0.1

    def test_exact_0_3_boundary(self):
        f = Fence(name="t", limit=1000)
        f.consumed = 700
        assert f.status == "moderate"

    def test_exact_0_7_boundary(self):
        f = Fence(name="t", limit=1000)
        f.consumed = 300
        assert f.status == "moderate"

    def test_consume_exact_limit(self):
        f = Fence(name="t", limit=100, action="block")
        result = f.consume(100)
        assert result is True
        assert f.consumed == 100
        assert f.status == "exhausted"

    def test_consume_one_over_limit_block(self):
        f = Fence(name="t", limit=100, action="block")
        result = f.consume(101)
        assert result is False
        assert f.consumed == 0


# ── Iteration Safety ───────────────────────────────────


class TestIterationSafety:
    """Document iteration safety guarantees."""

    def test_complete_task_iterates_fence_dict(self):
        c = ShepherdsConsole()
        c.add_pasture("p1")
        c.add_animal("w1", pasture="p1")
        for i in range(10):
            c.add_fence(f"f{i}", limit=1000)
        c.complete_task("w1", cost=10)

    def test_render_after_log_trim(self):
        c = ShepherdsConsole()
        for i in range(10):
            c.log(f"msg-{i}")
        output = c.render_terminal()
        assert len(output) > 0


# ── Large Scale Stress ─────────────────────────────────


class TestLargeScale:
    """Stress test with large numbers of entities."""

    def test_1000_animals(self):
        c = ShepherdsConsole()
        c.add_pasture("mega", capacity=10000)
        for i in range(1000):
            c.add_animal(f"worker-{i}", pasture="mega")
        assert len(c.kennel) == 1000
        assert c.pastures["mega"].occupancy == 1000

    def test_1000_fences(self):
        c = ShepherdsConsole()
        for i in range(1000):
            c.add_fence(f"fence-{i}", limit=100)
        c.add_pasture("p1")
        c.add_animal("w1", pasture="p1")
        c.complete_task("w1", cost=1)
        assert all(f.consumed == 1 for f in c.fences.values())

    def test_high_frequency_logging(self):
        """10k logs — should be fast with deque."""
        c = ShepherdsConsole()
        start = time.time()
        for i in range(10000):
            c.log(f"msg-{i}")
        elapsed = time.time() - start
        assert len(c.logs) == 500  # deque maxlen
        print(f"\n10k logs in {elapsed:.3f}s")
        assert elapsed < 1.0

    def test_large_state_save_load(self):
        c = ShepherdsConsole()
        c.add_pasture("mega", capacity=10000)
        for i in range(500):
            c.add_animal(f"worker-{i}", pasture="mega")
        for i in range(100):
            c.add_fence(f"fence-{i}", limit=10000)
            c.fences[f"fence-{i}"].consumed = i * 10
        c.complete_task("worker-0", cost=50)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            c.save_state(path)
            loaded = ShepherdsConsole.load_state(path)
            assert len(loaded.kennel) == 500
            assert len(loaded.fences) == 100
            # complete_task consumed 50 from ALL 100 fences
            assert loaded.fences["fence-0"].consumed == 50
            assert loaded.fences["fence-99"].consumed == 1040
        finally:
            os.unlink(path)
