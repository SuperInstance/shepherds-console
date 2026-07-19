# The Shepherd's Console v0.1.1 - Audit Report

**Date:** 2026-07-19
**Audited Version:** v0.1.0 → v0.1.1
**Files:** `src/shepherds_console/*.py`, `tests/test_console.py`

## Summary

A comprehensive audit of the v0.1.0 codebase revealed **5 real bugs** across validation and edge-case handling. All have been fixed and regression tests added.

- **Total Issues Found:** 5 bugs
- **Issues Fixed:** 5
- **Tests Added:** 8 regression tests
- **Test Status:** 41/41 passing

---

## Bugs Found and Fixed

### 1. Fence.status() Gap at budget_fraction=0.7

**Severity:** Low
**Location:** `src/shepherds_console/__init__.py:130-143`

**Description:**
The `Fence.status()` method had a logic gap in its conditional checks. When `budget_fraction` was exactly 0.7, it would return `"healthy"` instead of `"moderate"` because the condition used `if frac < 0.7` rather than `if frac <= 0.7`.

**Failure Scenario:**
```python
f = Fence(name="test", limit=100)
f.consumed = 30  # 70% remaining = 0.7 budget_fraction
# Expected: "moderate"
# Actual (v0.1.0): "healthy"
```

**Fix:**
Changed `if frac < 0.7:` to `if frac <= 0.7:` to include the boundary case.

**Test:** `TestBugFixes::test_fence_status_gap_at_0_7`

---

### 2. Fence.consume() Accepted Negative Amounts

**Severity:** Medium
**Location:** `src/shepherds_console/__init__.py:145-156`

**Description:**
`Fence.consume()` did not validate that `amount` was non-negative. Passing a negative value would decrease `consumed`, effectively adding to the budget—a nonsensical operation that could be exploited.

**Failure Scenario:**
```python
f = Fence(name="test", limit=100)
f.consumed = 50
f.consume(-10)  # Returns True
# Now consumed = 40, remaining = 60
```

**Fix:**
Added validation at the start of the method:
```python
if amount < 0:
    raise ValueError(f"consume amount must be non-negative, got {amount}")
```

**Test:** `TestBugFixes::test_fence_consume_negative_amount`

---

### 3. add_pasture() Allowed Negative Capacity

**Severity:** Medium
**Location:** `src/shepherds_console/__init__.py:207-221`

**Description:**
`ShepherdsConsole.add_pasture()` did not validate that `capacity` was non-negative. Negative capacity values led to nonsensical states (e.g., negative utilization).

**Failure Scenario:**
```python
c = ShepherdsConsole()
c.add_pasture("bad", capacity=-5)
# Creates pasture with capacity=-5
p = c.pastures["bad"]
p.utilization  # Returns -0.0 (weird behavior)
```

**Fix:**
Added validation:
```python
if capacity < 0:
    raise ValueError(f"capacity must be non-negative, got {capacity}")
```

**Test:** `TestBugFixes::test_add_pasture_negative_capacity`

---

### 4. add_fence() Allowed Negative Limits

**Severity:** Medium
**Location:** `src/shepherds_console/__init__.py:223-233`

**Description:**
`ShepherdsConsole.add_fence()` did not validate that `limit` was non-negative. Negative limits don't make sense for a conservation enforcer.

**Failure Scenario:**
```python
c = ShepherdsConsole()
c.add_fence("bad", limit=-100)
# Creates fence with negative limit
```

**Fix:**
Added validation:
```python
if limit < 0:
    raise ValueError(f"limit must be non-negative, got {limit}")
```

**Test:** `TestBugFixes::test_add_fence_negative_limit`

---

### 5. complete_task() Allowed Negative Cost

**Severity:** Medium
**Location:** `src/shepherds_console/__init__.py:274-298`

**Description:**
`ShepherdsConsole.complete_task()` did not validate that `cost` was non-negative. This could cause fences to have negative `consumed` values.

**Failure Scenario:**
```python
c = ShepherdsConsole()
c.add_pasture("p")
c.add_animal("a", pasture="p")
c.add_fence("f", limit=100)
c.complete_task("a", cost=-50)
# fence.consumed = -50.0 (nonsensical)
```

**Fix:**
Added validation:
```python
if cost < 0:
    raise ValueError(f"cost must be non-negative, got {cost}")
```

**Test:** `TestBugFixes::test_complete_task_negative_cost`

---

### 6. assign() Could Duplicate Animals in Pasture List

**Severity:** Low
**Location:** `src/shepherds_console/__init__.py:257-272`

**Description:**
When `assign()` was called and the animal's current `pasture` attribute referenced a pasture not in `self.pastures`, but the animal was already in the target pasture's `animals` list, the animal would be added twice to the target pasture. This could occur if:
- A pasture was removed from `self.pastures` but animals still referenced it
- The state was otherwise corrupted

**Failure Scenario:**
```python
c = ShepherdsConsole()
c.add_pasture("pasture-a")
a = c.add_animal("test", pasture="pasture-a")
# State gets corrupted (old pasture removed but animal.pasture not updated)
a.pasture = "nonexistent"
c.assign("test", "pasture-a")
# pasture-a.animals = ["test", "test"]  # Duplicate!
```

**Fix:**
Added check before appending:
```python
if animal not in self.pastures[pasture].animals:
    self.pastures[pasture].animals.append(animal)
```

**Tests:** `TestBugFixes::test_assign_duplicate_animal_in_pasture`, `TestBugFixes::test_assign_same_pasture_twice`

---

## Additional Observations

### Not Considered Bugs

1. **Fence with limit=0**: Handled correctly—returns `status="exhausted"` and `budget_fraction=0.0`.

2. **Pasture with capacity=0**: Handled correctly—`utilization` returns `0.0` via the guard clause.

3. **Log trimming**: The existing implementation is correct. Logs are only trimmed when `len(self.logs) > self._max_logs`, and the slice `self.logs[-self._max_logs:]` correctly keeps the most recent entries.

4. **HTML XSS via Animal.metadata**: Not a bug because `metadata` is not rendered in the HTML output. The web renderer only displays: name, role, pasture, health, tasks_completed, and last_active.

---

## Testing

### Test Coverage
- **Before audit:** 33 tests passing
- **After audit:** 41 tests passing (33 original + 8 new regression tests)

### New Test Class: `TestBugFixes`
All regression tests are grouped under `TestBugFixes` for easy identification:
- `test_fence_status_gap_at_0_7`
- `test_fence_consume_negative_amount`
- `test_add_pasture_negative_capacity`
- `test_add_fence_negative_limit`
- `test_complete_task_negative_cost`
- `test_assign_duplicate_animal_in_pasture`
- `test_assign_same_pasture_twice`
- `test_fence_consume_zero_amount`

### Test Command
```bash
PYTHONPATH=src python3 -m pytest tests/ -v
```

---

## Recommendations

1. **Consider using `pydantic` or similar** for runtime validation of dataclass fields to catch invalid inputs at construction time rather than during operations.

2. **Add invariant checks** in critical methods to detect state inconsistencies (e.g., an animal's `pasture` value not matching its presence in pasture `animals` lists).

3. **Consider adding type stubs** (`.pyi` files) for stricter type checking.

---

## Version Changes

- **v0.1.0** → **v0.1.1**
- 5 bugs fixed
- 8 regression tests added
- No breaking API changes
