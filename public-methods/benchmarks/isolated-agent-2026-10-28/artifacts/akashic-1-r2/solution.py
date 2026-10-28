import json
import sys


def solve(data):
    # Keep the first copy of each identifier; the input guarantees identical
    # fields for any later copies.
    by_id = {}
    duplicates = 0
    for event in data["events"]:
        event_id = event["event_id"]
        if event_id in by_id:
            duplicates += 1
        else:
            by_id[event_id] = event

    events = sorted(by_id.values(), key=lambda e: (e["at"], e["event_id"]))
    open_by_service = {}
    resolved_cycles = 0
    orphan_events = 0
    severity_rank = {"low": 0, "medium": 1, "high": 2}

    for event in events:
        service = event["service"]
        kind = event["kind"]
        incident = open_by_service.get(service)

        if kind == "trigger":
            severity = event["severity"]
            if incident is None:
                open_by_service[service] = {
                    "service": service,
                    "opened_at": event["at"],
                    "last_trigger_at": event["at"],
                    "severity": severity,
                    "acknowledged_by": None,
                }
            else:
                incident["last_trigger_at"] = event["at"]
                if severity_rank[severity] > severity_rank[incident["severity"]]:
                    incident["severity"] = severity
        elif incident is None:
            orphan_events += 1
        elif kind == "ack":
            incident["acknowledged_by"] = event["actor"]
        else:  # resolve
            del open_by_service[service]
            resolved_cycles += 1

    return {
        "open": [open_by_service[s] for s in sorted(open_by_service)],
        "resolved_cycles": resolved_cycles,
        "ignored_orphan_events": orphan_events,
        "ignored_duplicates": duplicates,
    }


def main():
    data = json.load(sys.stdin)
    json.dump(solve(data), sys.stdout, ensure_ascii=True, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
