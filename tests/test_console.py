"""Tests for The Shepherd's Console."""

import json
import pytest
import time

from shepherds_console import (
    ShepherdsConsole,
    Health,
    PastureMode,
    Severity,
    Fence,
    Pasture,
    Animal,
    LogEntry,
)


@pytest.fixture
def console():
    """A console with some test data."""
    c = ShepherdsConsole()
    c.add_pasture("meadow-1", mode="plow", capacity=10)
    c.add_pasture("grove-2", mode="fallow", capacity=5)
    c.add_fence("token-budget", limit=1000, action="throttle")
    c.add_fence("hard-limit", limit=100, action="block")
    c.add_animal("worker-a", pasture="meadow-1", role="flux")
    c.add_animal("worker-b", pasture="meadow-1", role="sentinel")
    c.add_animal("worker-c", pasture="grove-2", role="scout")
    return c


class TestPasture:
    def test_defaults(self):
        p = Pasture(name="test")
        assert p.mode == PastureMode.FALLOW
        assert p.capacity == 10
        assert p.occupancy == 0
        assert p.utilization == 0.0

    def test_occupancy(self):
        p = Pasture(name="test", capacity=5)
        p.animals = ["a", "b", "c"]
        assert p.occupancy == 3
        assert p.utilization == pytest.approx(0.6)

    def test_utilization_zero_capacity(self):
        p = Pasture(name="test", capacity=0)
        assert p.utilization == 0.0


class TestFence:
    def test_budget_remaining(self):
        f = Fence(name="test", limit=1000)
        assert f.remaining == 1000
        assert f.budget_fraction == pytest.approx(1.0)
        assert f.status == "healthy"

    def test_consume(self):
        f = Fence(name="test", limit=1000)
        assert f.consume(350) is True
        assert f.remaining == pytest.approx(650)
        assert f.status == "moderate"

    def test_consume_low_budget(self):
        f = Fence(name="test", limit=1000)
        f.consume(750)
        assert f.status == "low"

    def test_consume_critical(self):
        f = Fence(name="test", limit=1000)
        f.consume(950)
        assert f.status == "critical"

    def test_consume_throttle(self):
        f = Fence(name="test", limit=100, action="throttle")
        # Over-consume with throttle → allowed but violation counted
        result = f.consume(150)
        assert result is True
        assert f.violations == 1

    def test_consume_block(self):
        f = Fence(name="test", limit=100, action="block")
        result = f.consume(150)
        assert result is False
        assert f.violations == 1
        # Budget not consumed on block
        assert f.consumed == 0.0

    def test_disabled_fence(self):
        f = Fence(name="test", limit=100, action="block")
        f.enabled = False
        # Disabled fence always allows
        assert f.consume(99999) is True
        assert f.status == "disabled"


class TestShepherdsConsole:
    def test_add_pasture(self, console):
        assert "meadow-1" in console.pastures
        assert console.pastures["meadow-1"].mode == PastureMode.PLOW

    def test_add_fence(self, console):
        assert "token-budget" in console.fences
        assert console.fences["token-budget"].limit == 1000

    def test_add_animal(self, console):
        assert "worker-a" in console.kennel
        assert console.kennel["worker-a"].pasture == "meadow-1"
        # Animal should appear in pasture's animal list
        assert "worker-a" in console.pastures["meadow-1"].animals

    def test_assign(self, console):
        console.assign("worker-a", "grove-2")
        assert console.kennel["worker-a"].pasture == "grove-2"
        assert "worker-a" in console.pastures["grove-2"].animals
        assert "worker-a" not in console.pastures["meadow-1"].animals

    def test_assign_unknown_animal(self, console):
        with pytest.raises(KeyError):
            console.assign("nobody", "meadow-1")

    def test_assign_unknown_pasture(self, console):
        with pytest.raises(KeyError):
            console.assign("worker-a", "nowhere")

    def test_complete_task(self, console):
        console.complete_task("worker-a", cost=50)
        assert console.kennel["worker-a"].tasks_completed == 1
        assert console.pastures["meadow-1"].tasks_completed == 1

    def test_complete_task_with_fence_block(self, console):
        # hard-limit is block action, limit=100
        # worker-c is in grove-2
        console.complete_task("worker-c", cost=150)
        # Task still completes even if fence blocks consumption
        assert console.kennel["worker-c"].tasks_completed == 1
        # Fence should have a violation
        assert console.fences["hard-limit"].violations >= 1

    def test_set_health(self, console):
        console.set_health("worker-a", "injured")
        assert console.kennel["worker-a"].health == Health.INJURED

    def test_log(self, console):
        initial = len(console.logs)
        console.log("test message", severity=Severity.WARN)
        assert len(console.logs) == initial + 1
        assert console.logs[-1].message == "test message"
        assert console.logs[-1].severity == Severity.WARN

    def test_log_trimming(self):
        c = ShepherdsConsole()
        c._max_logs = 10
        for i in range(20):
            c.log(f"msg-{i}")
        assert len(c.logs) == 10
        assert c.logs[0].message == "msg-10"
        assert c.logs[-1].message == "msg-19"

    def test_status(self, console):
        s = console.status()
        assert "pastures" in s
        assert "fences" in s
        assert "kennel" in s
        assert "logs" in s
        assert "summary" in s
        assert len(s["pastures"]) == 2
        assert len(s["fences"]) == 2
        assert len(s["kennel"]) == 3

    def test_summary_counts(self, console):
        s = console._summary()
        assert s["total_animals"] == 3
        assert s["total_pastures"] == 2
        assert s["total_fences"] == 2

    def test_render_terminal(self, console):
        output = console.render_terminal()
        assert isinstance(output, str)
        assert len(output) > 0
        # Should mention key sections
        assert "PASTURES" in output.upper() or "Pasture" in output
        assert "FENCES" in output.upper() or "Fence" in output

    def test_render_html(self, console):
        output = console.render_html()
        assert "<html" in output
        assert "Shepherd" in output
        assert "meadow-1" in output
        assert "worker-a" in output
        assert "token-budget" in output

    def test_render_html_escaping(self):
        c = ShepherdsConsole()
        c.add_pasture("<script>alert(1)</script>")
        html_out = c.render_html()
        assert "<script>alert(1)</script>" not in html_out
        assert "&lt;script&gt;" in html_out


class TestSerialization:
    def test_pasture_to_dict(self, console):
        d = console.pastures["meadow-1"].to_dict()
        assert d["name"] == "meadow-1"
        assert d["mode"] == "plow"
        assert isinstance(d["animals"], list)

    def test_fence_to_dict(self, console):
        d = console.fences["token-budget"].to_dict()
        assert d["name"] == "token-budget"
        assert d["limit"] == 1000
        assert "remaining" in d
        assert "status" in d

    def test_animal_to_dict(self, console):
        d = console.kennel["worker-a"].to_dict()
        assert d["name"] == "worker-a"
        assert d["pasture"] == "meadow-1"
        assert d["health"] == "healthy"

    def test_log_entry_to_dict(self):
        e = LogEntry(timestamp=1234, message="test", severity=Severity.ERROR, source="x")
        d = e.to_dict()
        assert d["timestamp"] == 1234
        assert d["severity"] == "error"


class TestEnums:
    def test_health_values(self):
        assert Health.HEALTHY.value == "healthy"
        assert Health.OFFLINE.value == "offline"

    def test_pasture_mode_values(self):
        assert PastureMode.PLOW.value == "plow"
        assert PastureMode.GRAZE.value == "graze"
        assert PastureMode.FALLOW.value == "fallow"

    def test_severity_values(self):
        assert Severity.INFO.value == "info"
        assert Severity.CRITICAL.value == "critical"


class TestBugFixes:
    """Regression tests for bugs found in v0.1.0 audit."""

    def test_fence_status_gap_at_0_7(self, console):
        """Bug: Fence.status() had gap at budget_fraction=0.7 returning 'healthy' instead of 'moderate'."""
        f = Fence(name="test", limit=100)
        f.consumed = 30  # 70% remaining = 0.7 budget_fraction
        assert f.budget_fraction == pytest.approx(0.7)
        assert f.status == "moderate", "budget_fraction=0.7 should return moderate"

    def test_fence_consume_negative_amount(self, console):
        """Bug: Fence.consume() allowed negative amounts, reducing consumed value."""
        f = Fence(name="test", limit=100)
        f.consumed = 50
        with pytest.raises(ValueError, match="must be non-negative"):
            f.consume(-10)
        assert f.consumed == 50, "consumed should not change after negative consume attempt"

    def test_add_pasture_negative_capacity(self, console):
        """Bug: add_pasture() allowed negative capacity values."""
        with pytest.raises(ValueError, match="capacity must be non-negative"):
            console.add_pasture("bad", capacity=-5)

    def test_add_fence_negative_limit(self, console):
        """Bug: add_fence() allowed negative limit values."""
        with pytest.raises(ValueError, match="limit must be non-negative"):
            console.add_fence("bad", limit=-100)

    def test_complete_task_negative_cost(self, console):
        """Bug: complete_task() allowed negative cost, causing negative consumed."""
        with pytest.raises(ValueError, match="cost must be non-negative"):
            console.complete_task("worker-a", cost=-50)

    def test_assign_duplicate_animal_in_pasture(self, console):
        """Bug: assign() could duplicate animals in pasture list when old pasture didn't exist."""
        # Create scenario where animal's pasture reference points to non-existent pasture
        c = ShepherdsConsole()
        c.add_pasture("pasture-a")
        a = c.add_animal("test-animal", pasture="pasture-a")
        # Corrupt state (simulating scenario where old pasture was removed)
        a.pasture = "nonexistent"
        # Assign back to existing pasture
        c.assign("test-animal", "pasture-a")
        # Should only appear once
        assert c.pastures["pasture-a"].animals.count("test-animal") == 1

    def test_assign_same_pasture_twice(self, console):
        """Bug: assign() could duplicate when assigning to same pasture multiple times."""
        c = ShepherdsConsole()
        c.add_pasture("p1")
        c.add_animal("a1", pasture="p1")
        c.assign("a1", "p1")  # Assign to same pasture
        c.assign("a1", "p1")  # Assign again
        assert c.pastures["p1"].animals.count("a1") == 1, "Should not duplicate"

    def test_fence_consume_zero_amount(self, console):
        """Test that zero amount consumption is handled correctly."""
        f = Fence(name="test", limit=100)
        f.consumed = 50
        # Zero should be allowed (no-op)
        result = f.consume(0)
        assert result is True
        assert f.consumed == 50
