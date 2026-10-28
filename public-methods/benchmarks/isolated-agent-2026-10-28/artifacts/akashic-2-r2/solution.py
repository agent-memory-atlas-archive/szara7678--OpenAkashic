import json
import sys


def rounded(value):
    # Keep JSON numbers numeric, while avoiding negative zero in serialized output.
    result = round(value, 6)
    return 0 if result == 0 else result


def main():
    data = json.load(sys.stdin)
    records = data["records"]
    latest = {}
    for record in records:
        participant = record["participant_id"]
        key = (record["revision"], record["record_id"])
        current = latest.get(participant)
        if current is None or key > (current["revision"], current["record_id"]):
            latest[participant] = record

    removed_duplicates = len(records) - len(latest)
    final_records = list(latest.values())
    excluded_ineligible = sum(1 for r in final_records if not r["eligible"])
    eligible = [r for r in final_records if r["eligible"]]

    def analyze(missing_as_failure):
        groups = {"A": [], "B": []}
        for r in eligible:
            if r["outcome"] == "missing" and not missing_as_failure:
                continue
            groups[r["variant"]].append(r)

        stats = {}
        rates = {}
        for variant in ("A", "B"):
            group = groups[variant]
            n = len(group)
            successes = sum(1 for r in group if r["outcome"] == "success")
            rate = successes / n if n else None
            stats[variant] = {"n": n, "success": successes,
                              "rate": rounded(rate) if rate is not None else None}
            rates[variant] = rate

        if rates["A"] is None or rates["B"] is None:
            uplift = None
            passes_gain = False
        else:
            raw_uplift = (rates["B"] - rates["A"]) * 100
            uplift = rounded(raw_uplift)
            passes_gain = raw_uplift >= data["min_gain_pp"]

        decision = ("pass" if stats["A"]["n"] >= data["min_n"]
                    and stats["B"]["n"] >= data["min_n"]
                    and passes_gain else "hold")
        return {"A": stats["A"], "B": stats["B"],
                "uplift_pp": uplift, "decision": decision}

    result = {
        "removed_duplicates": removed_duplicates,
        "excluded_ineligible": excluded_ineligible,
        "analyses": {
            "exclude_missing": analyze(False),
            "missing_as_failure": analyze(True),
        },
    }
    json.dump(result, sys.stdout, separators=(",", ":"))
    sys.stdout.write("\n")


if __name__ == "__main__":
    main()
