import json
import sys


def main():
    data = json.load(sys.stdin)

    # Identical event IDs are specified to have identical fields, so retain
    # one event for each ID and count the remaining rows as duplicates.
    by_id = {}
    for event in data["events"]:
        by_id.setdefault(event["event_id"], event)
    ignored_duplicates = len(data["events"]) - len(by_id)

    events = sorted(by_id.values(), key=lambda e: (e["at"], e["event_id"]))
    open_by_service = {}
    resolved_cycles = 0
    ignored_orphan_events = 0
    severity_rank = {"low": 0, "medium": 1, "high": 2}

    for event in events:
        service = event["service"]
        kind = event["kind"]
        current = open_by_service.get(service)

        if kind == "trigger":
            if current is None:
                open_by_service[service] = {
                    "service": service,
                    "opened_at": event["at"],
                    "last_trigger_at": event["at"],
                    "severity": event["severity"],
                    "acknowledged_by": None,
                }
            else:
                current["last_trigger_at"] = event["at"]
                if severity_rank[event["severity"]] > severity_rank[current["severity"]]:
                    current["severity"] = event["severity"]
        elif kind == "ack":
            if current is None:
                ignored_orphan_events += 1
            else:
                current["acknowledged_by"] = event["actor"]
        else:  # resolve
            if current is None:
                ignored_orphan_events += 1
            else:
                del open_by_service[service]
                resolved_cycles += 1

    result = {
        "open": [open_by_service[s] for s in sorted(open_by_service)],
        "resolved_cycles": resolved_cycles,
        "ignored_orphan_events": ignored_orphan_events,
        "ignored_duplicates": ignored_duplicates,
    }
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
