"""
Batch test runner for the FastBox delivery simulator.

Expects this project layout:
    Python Assignment(Delivery.../
        fastbox.py
        run_tests.py      <- this file
        base_case.json
        Test_Cases/
            test_case_1.json
            test_case_2.json
            ...

Run it from the project root:
    python run_tests.py

It runs fastbox's simulate() on every JSON file found, writes each report
into a "reports/" folder, and prints a one-line summary per file so you can
eyeball results without opening every report.json individually.
"""

import json
import glob
import os

from fastbox import load_data, simulate  # reuse the real simulator logic


def find_test_files():
    """Collect base_case.json (root) + everything inside Test_Cases/."""
    files = []
    if os.path.exists("base_case.json"):
        files.append("base_case.json")
    files.extend(sorted(glob.glob(os.path.join("Test_Cases", "*.json"))))
    return files


def run_one(path, out_dir):
    warehouses, agents, packages = load_data(path)
    report = simulate(warehouses, agents, packages)

    name = os.path.splitext(os.path.basename(path))[0]
    out_path = os.path.join(out_dir, f"report_{name}.json")
    with open(out_path, "w") as f:
        json.dump(report, f, indent=2)

    total_delivered = sum(
        v["packages_delivered"] for k, v in report.items() if k != "best_agent"
    )
    return report, total_delivered, out_path


def main():
    test_files = find_test_files()
    if not test_files:
        print("No test files found. Run this from the project root "
              "(the folder containing fastbox.py, base_case.json, and Pypy/).")
        return

    out_dir = "reports"
    os.makedirs(out_dir, exist_ok=True)

    print(f"{'File':<20} {'Packages':<10} {'Best Agent':<12} {'Report saved to'}")
    print("-" * 70)

    for path in test_files:
        try:
            report, total_delivered, out_path = run_one(path, out_dir)
            best = report.get("best_agent")
            name = os.path.basename(path)
            print(f"{name:<20} {total_delivered:<10} {str(best):<12} {out_path}")
        except Exception as e:
            print(f"{os.path.basename(path):<20} FAILED: {e}")


if __name__ == "__main__":
    main()
