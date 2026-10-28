import json
import sys


def main():
    data = json.load(sys.stdin)
    seen = set()
    events = []
    ignored_duplicates = 0

    for event in data["events"]:
        event_id = event["event_id"]
        if event_id in seen:
            ignored_duplicates += 1
            continue
        seen.add(event_id)
        events.append(event)

    events.sort(key=lambda event: (event["at"], event["event_id"]))

    severity_rank = {"low": 0, "medium": 1, "high": 2}
    open_incidents = {}
    resolved_cycles = 0
    ignored_orphan_events = 0

    for event in events:
        service = event["service"]
        kind = event["kind"]
        incident = open_incidents.get(service)

        if kind == "trigger":
            if incident is None:
                open_incidents[service] = {
                    "service": service,
                    "opened_at": event["at"],
                    "last_trigger_at": event["at"],
                    "severity": event["severity"],
                    "acknowledged_by": None,
                }
            else:
                incident["last_trigger_at"] = event["at"]
                if severity_rank[event["severity"]] > severity_rank[incident["severity"]]:
                    incident["severity"] = event["severity"]
        elif incident is None:
            ignored_orphan_events += 1
        elif kind == "ack":
            incident["acknowledged_by"] = event["actor"]
        else:  # resolve
            del open_incidents[service]
            resolved_cycles += 1

    result = {
        "open": [open_incidents[key] for key in sorted(open_incidents)],
        "resolved_cycles": resolved_cycles,
        "ignored_orphan_events": ignored_orphan_events,
        "ignored_duplicates": ignored_duplicates,
    }
    json.dump(result, sys.stdout, ensure_ascii=False)
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
