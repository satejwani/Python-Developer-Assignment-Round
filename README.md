# FastBox Delivery Simulator

A Python logistics simulator for the FastBox fictional delivery company.

## Project Structure

```
Python Assignment(Delivery.../
├── fastbox.py          # Core simulator
├── run_tests.py        # Batch test runner (all test cases at once)
├── README.md           # This file
├── base_case.json      # Base test case from the assignment PDF
└── Test_Cases/
    ├── test_case_1.json
    ├── test_case_2.json
    └── ... (up to test_case_10.json)
```

## How to Run

**Single file:**
```bash
python fastbox.py Test_Cases/test_case_1.json
python fastbox.py Test_Cases/test_case_1.json -o my_report.json
python fastbox.py Test_Cases/test_case_1.json -o my_report.json --csv
```

**All test cases at once:**
```bash
python run_tests.py
```
Reports are saved to a `reports/` folder automatically created in the project root.

## Output Format

```json
{
  "A1": { "packages_delivered": 2, "total_distance": 85.32, "efficiency": 42.66 },
  "A2": { "packages_delivered": 2, "total_distance": 120.12, "efficiency": 60.06 },
  "A3": { "packages_delivered": 1, "total_distance": 50.00, "efficiency": 50.00 },
  "best_agent": "A1"
}
```

---

## Engineering Assumptions

The assignment states: *"If you encounter any ambiguous logic or undefined scenarios,
assume the best possible scenario and document your assumptions."*

All 11 assumptions are listed here and also marked with `# ASSUMPTION [N]:`
comments at the exact line in `fastbox.py` where they take effect.

---

### ASSUMPTION [1] — Distance Metric: Euclidean

**Decision:** We use straight-line (Euclidean) distance for all calculations.

**Reason:** The assignment explicitly states *"Euclidean distance"* in the
task description. Manhattan distance or real road-network routing were
considered but rejected as the spec is unambiguous on this point.

**Formula:** `sqrt((x2-x1)² + (y2-y1)²)`

---

### ASSUMPTION [2] — Dual JSON Schema Support

**Decision:** The loader auto-detects and normalises two different input formats.

**Reason:** The assignment PDF uses a dict-style schema (`"warehouses": {"W1": [x,y]}`),
but the supplied `base_case.json` uses a list-of-objects schema
(`"warehouses": [{"id": "W1", "location": [x, y]}]`). Rather than failing
on one format or requiring the user to reformat files, the loader detects
which variant is present and normalises both to the same internal structure.

| Field | Dict style | List style |
|-------|-----------|------------|
| Warehouse key | `"warehouse"` | `"warehouse_id"` |
| Location format | `"W1": [x, y]` | `{"id": "W1", "location": [x, y]}` |

---

### ASSUMPTION [3] — Package Processing Order: JSON Input Order

**Decision:** Packages are processed (and assigned to agents) in the order
they appear in the JSON `packages` array.

**Reason:** The assignment does not specify a dispatch priority (e.g., nearest
destination first, heaviest package first). Honouring input order is the most
straightforward, deterministic, and reproducible choice. It also avoids
introducing optimisation complexity that is out of scope for this assignment.

---

### ASSUMPTION [4] — Live Agent Position Tracking

**Decision:** After each delivery, the agent's position is updated to the
delivery destination. All future nearest-agent calculations use this live
position, not the original starting point.

**Reason:** This reflects real-world logistics — an agent who just delivered
to point (70, 80) is now physically at (70, 80), not back at their depot.
Using stale starting positions would cause one agent to be overloaded simply
because they started near a busy warehouse cluster, which is neither realistic
nor efficient.

---

### ASSUMPTION [5] — Two-Leg Route Per Delivery

**Decision:** Each delivery consists of exactly two legs:
- **Leg 1:** Agent's current position → Package's warehouse (pickup)
- **Leg 2:** Warehouse → Package's destination (delivery)

The agent does **not** return to base or to the warehouse after completing a
delivery. Their new position is the destination.

**Reason:** The assignment shows `total_distance` as a cumulative sum across
all deliveries, implying the agent moves continuously through the day without
returning to a depot between jobs.

---

### ASSUMPTION [6] — Tie-Breaking: Nearest Agent

**Decision:** When two or more agents are exactly equidistant from a warehouse,
the agent whose ID appears first in the JSON file (earliest dict insertion
order) is selected.

**Reason:** Python's `min()` is stable with respect to iteration order, making
this fully deterministic and reproducible. The alternative — random selection —
would produce different results across runs, which is undesirable for a
simulation that should be verifiable.

---

### ASSUMPTION [7] — Every Package Must Be Delivered

**Decision:** All packages in the input are guaranteed to be delivered by the
end of the simulation. An assertion verifies this post-simulation.

**Reason:** The assignment explicitly states *"Make sure total packages
delivered matches total packages."* There is no concept of an undeliverable
package, insufficient agent capacity, or package cancellation in the spec.

---

### ASSUMPTION [8] — Efficiency Definition (Lower = Better)

**Decision:**
```
efficiency = total_distance / packages_delivered
```
A **lower** efficiency value means the agent covered less distance per
package — i.e. they are **more efficient**. The `best_agent` is the one
with the **lowest** efficiency score.

**Reason:** The assignment's example output (`A1: efficiency 42.66`,
`A2: efficiency 60.06`, `best_agent: A1`) confirms that 42.66 < 60.06
and A1 is best. This validates the "lower is better" interpretation.

---

### ASSUMPTION [9] — Idle Agents (Zero Deliveries)

**Decision:** Agents who were assigned zero packages receive:
- `packages_delivered: 0`
- `total_distance: 0.0`
- `efficiency: 0.0`

They are **excluded** from `best_agent` selection.

**Reason:** Two alternatives were rejected:
- Setting efficiency to infinity (division by zero) would crash or produce
  ugly output.
- Treating efficiency 0.0 as "best" would incorrectly award `best_agent`
  to an agent who did nothing.

Excluding idle agents from the `best_agent` race and reporting their
efficiency as 0.0 is the clearest and most honest representation.

---

### ASSUMPTION [10] — Tie-Breaking: Best Agent

**Decision:** If two agents share the same (lowest) efficiency score, the
one whose ID appears first in the JSON is selected as `best_agent`.

**Reason:** Same rationale as ASSUMPTION [6] — deterministic, reproducible,
no arbitrary randomness.

---

### ASSUMPTION [11] — CSV Export Scope (Bonus Feature)

**Decision:** The `--csv` flag exports only the **single best agent** row
to `top_performer.csv`, not all agents.

**Reason:** The assignment bonus asks to *"Export top performer to CSV"*,
which unambiguously refers to the single best agent only.

---

## Evaluation Criteria Coverage

| Criterion | Weight | How it is addressed |
|-----------|--------|---------------------|
| JSON parsing | 10% | `load_data()` with dual-schema support (ASSUMPTION [2]) |
| Distance calculation | 20% | `euclidean_distance()` — explicit formula (ASSUMPTION [1]) |
| Agent-package assignment | 25% | `assign_and_deliver()` — live positions, sequential processing (ASSUMPTIONS [3][4][6]) |
| Simulation & report | 25% | `build_report()` — efficiency, best_agent, idle handling (ASSUMPTIONS [8][9][10]) |
| Code clarity & comments | 10% | All functions docstrings + 11 inline assumption labels |
| Bonus creativity | 10% | CSV export (`--csv`), batch test runner (`run_tests.py`) |
