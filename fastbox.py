"""
FastBox Delivery Simulator
===========================
Simulates one day of delivery operations for FastBox logistics.

Given warehouses (with coordinates), delivery agents (with starting positions),
and packages (each tied to a warehouse and a destination), this simulator:
  1. Assigns each package to the nearest available agent.
  2. Routes that agent: current position → warehouse → destination.
  3. Produces a per-agent report with total distance and efficiency.

Usage:
    python fastbox    python fastbox.py Test_Cases/test_case_1.json
    python fastbox.py Test_Cases/test_case_1.json -o reports/report_1.json --csving assumptions made.
"""

import json
import math
import csv
import argparse

# ---------------------------------------------------------------------------
# Distance
# ---------------------------------------------------------------------------

def euclidean_distance(p1, p2):
    """
    Straight-line (Euclidean) distance between two 2-D points.

    ASSUMPTION [1]: We use Euclidean distance, not Manhattan or road-network
    distance. The assignment says "Euclidean distance" explicitly, so this
    is the correct metric.
    """
    return math.sqrt((p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2)


# ---------------------------------------------------------------------------
# Input parsing
# ---------------------------------------------------------------------------

def load_data(path):
    """
    Parse the input JSON and return (warehouses, agents, packages) as
    normalised Python dicts.

    ASSUMPTION [2] — Dual schema support:
        The assignment ships two different JSON layouts:
          • dict style  : "warehouses": {"W1": [x, y], ...}
                          "packages"  : [{"warehouse": "W1", ...}]
          • list style  : "warehouses": [{"id": "W1", "location": [x,y]}, ...]
                          "packages"  : [{"warehouse_id": "W1", ...}]
        Both are normalised to the same internal representation so the
        simulator works with either file without any code changes.
    """
    with open(path, "r") as f:
        raw = json.load(f)

    def normalize_locations(entries):
        """Convert dict-style or list-style location entries to {id: (x, y)}."""
        if isinstance(entries, dict):
            return {name: tuple(coords) for name, coords in entries.items()}
        return {item["id"]: tuple(item["location"]) for item in entries}

    warehouses = normalize_locations(raw["warehouses"])
    agents     = normalize_locations(raw["agents"])

    packages = []
    for pkg in raw["packages"]:
        # ASSUMPTION [2] continued: accept either "warehouse" or "warehouse_id"
        warehouse_key = pkg.get("warehouse") or pkg.get("warehouse_id")
        if warehouse_key not in warehouses:
            raise ValueError(
                f"Package '{pkg.get('id')}' references unknown warehouse "
                f"'{warehouse_key}'. Check your JSON."
            )
        packages.append({
            "id"         : pkg["id"],
            "warehouse"  : warehouse_key,
            "destination": tuple(pkg["destination"]),
        })

    return warehouses, agents, packages


# ---------------------------------------------------------------------------
# Core simulation
# ---------------------------------------------------------------------------

def assign_and_deliver(warehouses, agents, packages):
    """
    Process every package in order, assign it to the nearest agent, simulate
    the trip, and accumulate per-agent stats.

    Key assumptions (all documented in README.md as well):

    ASSUMPTION [3] — Sequential package processing:
        Packages are processed in the order they appear in the JSON file.
        The assignment does not specify a priority order, so we honour the
        input sequence. This is the most straightforward and reproducible
        approach.

    ASSUMPTION [4] — Live position tracking:
        After an agent delivers a package, their position updates to that
        package's destination. Subsequent nearest-agent lookups use this
        updated position, not the agent's original starting point. This
        reflects real-world logistics more accurately and avoids overloading
        agents who happen to start close to a busy warehouse cluster.

    ASSUMPTION [5] — Route legs per delivery:
        Each delivery consists of exactly two legs:
            Leg 1: agent's current position → package's warehouse
            Leg 2: warehouse → package's destination
        The agent does NOT return to base or to the warehouse after delivery.
        Their new position is the destination.

    ASSUMPTION [6] — Tie-breaking (nearest agent):
        If two or more agents are equidistant from a warehouse, the one that
        appears first in the JSON (i.e. earliest insertion order in the dict)
        is selected. Python's min() is stable with respect to insertion order,
        making this deterministic and reproducible.

    ASSUMPTION [7] — All packages are guaranteed to be delivered:
        Every package must be assigned to exactly one agent. An assertion at
        the end verifies the total delivered count matches the input count.
        There is no concept of a package being skipped or undeliverable.
    """

    # Current position of each agent (updated after every delivery)
    agent_position = dict(agents)

    # Per-agent accumulators
    stats = {
        aid: {"packages_delivered": 0, "total_distance": 0.0}
        for aid in agents
    }

    for pkg in packages:
        warehouse_loc = warehouses[pkg["warehouse"]]

        # ASSUMPTION [6]: tie resolved by dict insertion order via min()
        nearest_agent = min(
            agents.keys(),
            key=lambda aid: euclidean_distance(agent_position[aid], warehouse_loc),
        )

        # ASSUMPTION [5]: two-leg trip, agent ends at destination
        leg1 = euclidean_distance(agent_position[nearest_agent], warehouse_loc)
        leg2 = euclidean_distance(warehouse_loc, pkg["destination"])
        trip_distance = leg1 + leg2

        stats[nearest_agent]["total_distance"]    += trip_distance
        stats[nearest_agent]["packages_delivered"] += 1

        # ASSUMPTION [4]: update agent's live position to destination
        agent_position[nearest_agent] = pkg["destination"]

    # ASSUMPTION [7]: assert every package was delivered
    delivered_count = sum(s["packages_delivered"] for s in stats.values())
    assert delivered_count == len(packages), (
        f"Expected {len(packages)} deliveries, got {delivered_count}. "
        "A package was not assigned — this should never happen."
    )

    return stats


# ---------------------------------------------------------------------------
# Report generation
# ---------------------------------------------------------------------------

def build_report(stats):
    """
    Convert raw stats into the final report format.

    ASSUMPTION [8] — Efficiency definition:
        efficiency = total_distance / packages_delivered
        A LOWER efficiency value means the agent covered less distance per
        package, i.e. they are more efficient. The "best agent" is therefore
        the one with the LOWEST efficiency score among agents who delivered
        at least one package.

    ASSUMPTION [9] — Idle agents:
        Agents who delivered zero packages receive efficiency = 0.0 and are
        excluded from the best_agent selection. Giving them "infinite"
        efficiency (division by zero) or "zero" efficiency (making them
        incorrectly appear best) would both be misleading. Setting it to 0.0
        and excluding them is the clearest representation.

    ASSUMPTION [10] — Tie-breaking (best agent):
        If two agents have identical efficiency scores, the one whose ID
        appears first in the JSON is selected as best_agent. Same rationale
        as ASSUMPTION [6]: deterministic, reproducible, no arbitrary random
        choice.
    """
    report = {}

    for aid, s in stats.items():
        total_dist = round(s["total_distance"], 2)
        delivered  = s["packages_delivered"]

        # ASSUMPTION [9]: idle agents get efficiency 0.0 and are excluded later
        efficiency = round(total_dist / delivered, 2) if delivered > 0 else 0.0

        report[aid] = {
            "packages_delivered": delivered,
            "total_distance"    : total_dist,
            "efficiency"        : efficiency,
        }

    # ASSUMPTION [9] + [10]: only consider agents with at least one delivery
    active_agents = {aid: v for aid, v in report.items() if v["packages_delivered"] > 0}

    # ASSUMPTION [8]: best = lowest efficiency (least distance per package)
    # ASSUMPTION [10]: min() preserves insertion order on ties
    best_agent = (
        min(active_agents, key=lambda aid: active_agents[aid]["efficiency"])
        if active_agents else None
    )

    report["best_agent"] = best_agent
    return report


# ---------------------------------------------------------------------------
# Bonus: CSV export
# ---------------------------------------------------------------------------

def export_top_performer_csv(report, path="top_performer.csv"):
    """
    Bonus feature: write the best agent's stats to a CSV file.

    ASSUMPTION [11] — CSV export scope:
        Only the single best agent row is exported (not all agents), since
        the assignment asks for the "top performer" export specifically.
    """
    best = report.get("best_agent")
    if not best:
        print("No best agent found; CSV not written.")
        return

    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["agent", "packages_delivered", "total_distance", "efficiency"])
        row = report[best]
        writer.writerow([
            best,
            row["packages_delivered"],
            row["total_distance"],
            row["efficiency"],
        ])
    print(f"Top performer exported to: {path}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def simulate(warehouses, agents, packages):
    """Public entry point used by run_tests.py."""
    stats = assign_and_deliver(warehouses, agents, packages)
    return build_report(stats)


def main():
    parser = argparse.ArgumentParser(description="FastBox Delivery Simulator")
    parser.add_argument("input",           help="Path to input JSON file (e.g. Pypy/test_case_1.json)")
    parser.add_argument("-o", "--output",  default="report.json", help="Output report path (default: report.json)")
    parser.add_argument("--csv",           action="store_true",   help="Also export top performer to top_performer.csv")
    args = parser.parse_args()

    warehouses, agents, packages = load_data(args.input)
    report = simulate(warehouses, agents, packages)

    with open(args.output, "w") as f:
        json.dump(report, f, indent=2)

    print(json.dumps(report, indent=2))
    print(f"\nReport saved to: {args.output}")

    if args.csv:
        export_top_performer_csv(report)


if __name__ == "__main__":
    main()
