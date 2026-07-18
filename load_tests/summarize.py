import argparse
import csv
import json
from pathlib import Path


def number(row, key, default=0.0):
    try:
        return float(row.get(key, default) or default)
    except (TypeError, ValueError):
        return float(default)


def read_aggregate(path):
    with path.open(encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    candidates = [row for row in rows if row.get("Name") == "Aggregated"]
    if not candidates:
        raise SystemExit("Locust aggregate row is missing")
    return candidates[-1], rows


def percentile_for(rows, marker, percentile):
    selected = [row for row in rows if marker in row.get("Name", "")]
    if not selected:
        return None
    return max(number(row, percentile) for row in selected)


def resource_peaks(path):
    peaks = {
        "cpu_percent": 0.0,
        "memory_percent": 0.0,
        "db_connections": 0,
        "redis_used_memory_bytes": 0,
    }
    if not path.exists():
        return peaks
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            peaks["cpu_percent"] = max(peaks["cpu_percent"], number(row, "cpu_percent"))
            peaks["memory_percent"] = max(
                peaks["memory_percent"], number(row, "memory_percent")
            )
            peaks["db_connections"] = max(
                peaks["db_connections"], int(number(row, "db_connections"))
            )
            peaks["redis_used_memory_bytes"] = max(
                peaks["redis_used_memory_bytes"],
                int(number(row, "redis_used_memory_bytes")),
            )
    return peaks


def max_users(path):
    if not path.exists():
        return 0
    maximum = 0
    with path.open(encoding="utf-8-sig", newline="") as source:
        for row in csv.DictReader(source):
            maximum = max(maximum, int(number(row, "User Count")))
    return maximum


def load_evidence(path):
    if not path.exists():
        return {
            "elapsed_seconds": 0,
            "full_concurrency_seconds": 0,
            "safety_stop_triggered": True,
            "readiness_failures": 1,
            "oom_count": 0,
            "restart_loop_count": 0,
            "db_connection_safety_limit": 50,
            "integrity_before": False,
            "integrity_after": False,
            "controlled_restart_completed": False,
        }
    return json.loads(path.read_text(encoding="utf-8"))


def summarize_run(*, artifacts, stage, users, duration_seconds):
    artifacts = Path(artifacts)
    aggregate, rows = read_aggregate(artifacts / "locust_stats.csv")
    requests = int(number(aggregate, "Request Count"))
    failures = int(number(aggregate, "Failure Count"))
    error_rate = failures / requests if requests else 1.0
    evidence = load_evidence(artifacts / "run-evidence.json")
    observed_users = max_users(artifacts / "locust_stats_history.csv")
    summary = {
        "measured": True,
        "stage": stage,
        "users": users,
        "max_active_users": observed_users,
        "duration_seconds": duration_seconds,
        "observed_duration_seconds": int(evidence.get("elapsed_seconds", 0)),
        "full_concurrency_seconds": int(evidence.get("full_concurrency_seconds", 0)),
        "requests": requests,
        "failures": failures,
        "error_rate": error_rate,
        "throughput_rps": number(aggregate, "Requests/s"),
        "workload": {
            "think_time_min_seconds": int(evidence.get("think_time_min_seconds", 0)),
            "think_time_max_seconds": int(evidence.get("think_time_max_seconds", 0)),
        },
        "response_ms": {
            "p50": number(aggregate, "50%"),
            "p95": number(aggregate, "95%"),
            "p99": number(aggregate, "99%"),
            "login_p95": percentile_for(rows, "[login]", "95%"),
            "typical_read_p95": percentile_for(rows, "[typical-read]", "95%"),
            "list_filter_p95": percentile_for(rows, "[list-filter]", "95%"),
            "business_write_p95": percentile_for(rows, "[business-write]", "95%"),
        },
        "resource_peaks": resource_peaks(artifacts / "resources.csv"),
        "safety": evidence,
    }
    acceptance = {
        "required_user_count_reached": observed_users >= users,
        "committed_business_pacing": summary["workload"]
        == {"think_time_min_seconds": 15, "think_time_max_seconds": 25},
        "required_duration_met": (
            int(evidence.get("elapsed_seconds", 0)) >= duration_seconds
            if stage == "spike"
            else int(evidence.get("full_concurrency_seconds", 0)) >= duration_seconds
        ),
        "error_rate_below_1_percent": error_rate < 0.01,
        "login_p95_below_2s": (summary["response_ms"]["login_p95"] or 1e99) < 2000,
        "typical_read_p95_below_2s": (
            summary["response_ms"]["typical_read_p95"] or 1e99
        ) < 2000,
        "list_filter_p95_below_3s": (
            summary["response_ms"]["list_filter_p95"] or 1e99
        ) < 3000,
        "business_write_p95_below_4s": (
            summary["response_ms"]["business_write_p95"] or 1e99
        ) < 4000,
        "core_p99_below_10s": summary["response_ms"]["p99"] < 10000,
        "no_safety_stop": not bool(evidence.get("safety_stop_triggered", True)),
        "no_readiness_loss": int(evidence.get("readiness_failures", 1)) == 0,
        "no_oom": int(evidence.get("oom_count", 1)) == 0,
        "no_restart_loop": int(evidence.get("restart_loop_count", 1)) == 0,
        "db_connections_within_safety_limit": summary["resource_peaks"][
            "db_connections"
        ] <= int(evidence.get("db_connection_safety_limit", 0)),
        "integrity_preserved": bool(evidence.get("integrity_before"))
        and bool(evidence.get("integrity_after")),
        "controlled_restart_passed": stage != "200"
        or bool(evidence.get("controlled_restart_completed")),
    }
    summary["acceptance"] = acceptance
    summary["overall_pass"] = all(acceptance.values())
    return summary


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--stage", required=True)
    parser.add_argument("--users", type=int, required=True)
    parser.add_argument("--duration-seconds", type=int, required=True)
    args = parser.parse_args()

    summary = summarize_run(
        artifacts=args.artifacts,
        stage=args.stage,
        users=args.users,
        duration_seconds=args.duration_seconds,
    )
    (args.artifacts / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    with (args.artifacts / "summary.csv").open("w", encoding="utf-8", newline="") as target:
        writer = csv.writer(target)
        writer.writerow(("metric", "value"))
        writer.writerow(("stage", summary["stage"]))
        writer.writerow(("users", summary["users"]))
        writer.writerow(("duration_seconds", summary["duration_seconds"]))
        writer.writerow(("throughput_rps", summary["throughput_rps"]))
        writer.writerow(("max_active_users", summary["max_active_users"]))
        writer.writerow(("observed_duration_seconds", summary["observed_duration_seconds"]))
        writer.writerow(("full_concurrency_seconds", summary["full_concurrency_seconds"]))
        writer.writerow(("error_rate", summary["error_rate"]))
        for key, value in summary["workload"].items():
            writer.writerow((key, value))
        for key, value in summary["response_ms"].items():
            writer.writerow((key, value))
        for key, value in summary["resource_peaks"].items():
            writer.writerow((key, value))
        for key, value in summary["acceptance"].items():
            writer.writerow((f"acceptance:{key}", value))
        writer.writerow(("overall_pass", summary["overall_pass"]))
    print(json.dumps(summary, sort_keys=True))


if __name__ == "__main__":
    main()
