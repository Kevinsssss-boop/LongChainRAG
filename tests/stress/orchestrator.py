"""
Stress test orchestrator — runs all 3 scenarios sequentially.

Scenarios:
  1. Load Test:  0->100 users, 5/min ramp, 5 min at peak  (realistic 100-user simulation)
  2. Limit Test: 10 users, +10 every 60s until >50% failure (find breaking point)
  3. Bottleneck: 4 sub-scenarios isolating each subsystem (DB/ChromaDB/SSE/Full)
"""
import os
import subprocess
import sys
import time
from datetime import datetime

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
LOCUSTFILE = os.path.join(os.path.dirname(__file__), "locustfile.py")
REPORTS_DIR = os.path.join(os.path.dirname(__file__), "reports")
HOST = os.environ.get("STRESS_TARGET_HOST", "http://localhost:8000")

os.makedirs(REPORTS_DIR, exist_ok=True)


def run_locust(scenario_name, users, spawn_rate, run_time, extra_args=None):
    """Run a single Locust session and return stats."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    prefix = os.path.join(REPORTS_DIR, f"{scenario_name}_{timestamp}")

    cmd = [
        sys.executable, "-m", "locust",
        "-f", LOCUSTFILE,
        "--headless",
        "--host", HOST,
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", run_time,
        "--html", f"{prefix}.html",
        "--csv", prefix,
        "--loglevel", "WARNING",
    ]
    if extra_args:
        cmd.extend(extra_args)

    print(f"\n{'='*60}")
    print(f"  Scenario: {scenario_name}")
    print(f"  Users: {users} | Spawn: {spawn_rate}/s | Duration: {run_time}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'='*60}\n")

    result = subprocess.run(cmd, cwd=PROJECT_ROOT)
    print(f"  Exit code: {result.returncode}")
    return prefix


def run_load_test():
    """Scenario 1: Realistic 100-user load test."""
    return run_locust(
        scenario_name="load_test",
        users=100,
        spawn_rate=5,      # Ramp up 5 users/sec -> reaches 100 in 20s
        run_time="320s",   # 20s ramp + 300s (5 min) at peak
    )


def run_limit_test():
    """Scenario 2: Step-up to find breaking point."""
    results = []
    user_count = 10
    max_users = 1000

    while user_count <= max_users:
        prefix = run_locust(
            scenario_name=f"limit_{user_count}u",
            users=user_count,
            spawn_rate=max(1, user_count // 3),  # Ramp over ~30s
            run_time="60s",
        )

        # Parse CSV stats for failure rate
        stats_csv = f"{prefix}_stats.csv"
        failure_rate = 0.0
        total_requests = 0
        total_failures = 0
        p95 = 0

        try:
            with open(stats_csv, "r") as f:
                lines = f.readlines()
            # Skip header, parse each row
            for line in lines[1:]:
                parts = line.strip().split(",")
                if len(parts) < 10:
                    continue
                method, name = parts[0], parts[1]
                req_count = int(parts[2])
                fail_count = int(parts[3])
                p95_val = float(parts[10]) if len(parts) > 10 and parts[10] != "N/A" else 0

                total_requests += req_count
                total_failures += fail_count
                p95 = max(p95, p95_val)

            failure_rate = total_failures / max(total_requests, 1)
        except FileNotFoundError:
            print(f"  WARN: Stats file not found: {stats_csv}")
            failure_rate = 0.0

        results.append({
            "users": user_count,
            "total_requests": total_requests,
            "failures": total_failures,
            "failure_rate": failure_rate,
            "p95_ms": p95,
        })

        print(f"  [{user_count} users] requests={total_requests}, "
              f"failures={total_failures}, fail_rate={failure_rate:.1%}, p95={p95:.0f}ms")

        # Stop condition: >50% failure rate or P95 > 30 seconds
        if failure_rate > 0.50 or p95 > 30000:
            print(f"\n  >>> BREAKING POINT at {user_count} users <<<")
            break

        user_count += 10
        if failure_rate > 0.10:
            # Slow down as we approach the limit
            time.sleep(10)
        else:
            time.sleep(5)

    # Print summary table
    print(f"\n{'='*60}")
    print(f"  Limit Test Summary")
    print(f"{'='*60}")
    print(f"  {'Users':<8} {'Requests':<10} {'Failures':<10} {'Fail%':<10} {'P95(ms)':<10}")
    print(f"  {'-'*48}")
    for r in results:
        print(f"  {r['users']:<8} {r['total_requests']:<10} {r['failures']:<10} "
              f"{r['failure_rate']:<10.1%} {r['p95_ms']:<10.0f}")

    return results


def run_bottleneck_analysis():
    """Scenario 3: Four sub-scenarios isolating different bottlenecks."""
    sub_scenarios = [
        ("bottleneck_db_write", 50, 10, "120s",
         "DB write contention: rapid session creation, no chat"),
        ("bottleneck_chat_full", 50, 5, "120s",
         "Full pipeline: chat with retrieval + mock LLM"),
        ("bottleneck_sessions_list", 50, 10, "120s",
         "Session list browsing: N+1 query load"),
        ("bottleneck_health", 100, 20, "60s",
         "Health check: pure FastAPI throughput baseline"),
    ]

    results = []
    for name, users, spawn_rate, run_time, desc in sub_scenarios:
        print(f"\n  Sub-scenario: {name}")
        print(f"  Description: {desc}")
        prefix = run_locust(name, users, spawn_rate, run_time)

        # Parse and store key metrics
        stats_csv = f"{prefix}_stats.csv"
        try:
            with open(stats_csv, "r") as f:
                lines = f.readlines()
            total_req = 0
            total_fail = 0
            p95 = 0
            for line in lines[1:]:
                parts = line.strip().split(",")
                if len(parts) < 11:
                    continue
                total_req += int(parts[2])
                total_fail += int(parts[3])
                p95_val = parts[10] if len(parts) > 10 and parts[10] != "N/A" else "0"
                p95 = max(p95, float(p95_val))
            results.append({
                "name": name,
                "desc": desc,
                "total_requests": total_req,
                "failures": total_fail,
                "p95_ms": p95,
                "throughput": total_req / int(run_time.replace("s", "")),
            })
        except FileNotFoundError:
            results.append({"name": name, "desc": desc, "error": "stats file not found"})

    print(f"\n{'='*60}")
    print(f"  Bottleneck Analysis Summary")
    print(f"{'='*60}")
    for r in results:
        if "error" in r:
            print(f"  {r['name']}: ERROR - {r['error']}")
        else:
            print(f"  {r['name']}: {r['total_requests']} req, {r['failures']} fail, "
                  f"p95={r['p95_ms']:.0f}ms, {r['throughput']:.1f} req/s")
            print(f"    {r['desc']}")

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: python orchestrator.py [load|limit|bottleneck|all]")
        print()
        print("  load       - Run 100-user realistic load test (5 min at peak)")
        print("  limit      - Step-up test to find breaking point")
        print("  bottleneck - Isolate bottlenecks (4 sub-scenarios)")
        print("  all        - Run all three scenarios sequentially")
        sys.exit(1)

    scenario = sys.argv[1]

    if scenario in ("load", "all"):
        print("\n### SCENARIO 1: LOAD TEST (100 users, 5 min at peak) ###")
        run_load_test()

    if scenario in ("limit", "all"):
        print("\n### SCENARIO 2: LIMIT TEST (step-up to breaking point) ###")
        run_limit_test()

    if scenario in ("bottleneck", "all"):
        print("\n### SCENARIO 3: BOTTLENECK ANALYSIS ###")
        run_bottleneck_analysis()

    print(f"\nReports saved to: {REPORTS_DIR}")


if __name__ == "__main__":
    main()
