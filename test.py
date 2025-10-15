import json
import ast

audio_results = []


def summarize_results(results):
    summary_dict = {}
    for result in results:
        name, confidence = result.get("name", "Unknown"), result.get("confidence", 0.0)
        summary_dict.setdefault(name, {"count": 0, "total_confidence": 0.0})
        # for each name, find number of occurrences and average confidence
        summary_dict[name]["count"] += 1
        summary_dict[name]["total_confidence"] += confidence
        summary_dict[name]["average_confidence"] = (
            summary_dict[name]["total_confidence"] / summary_dict[name]["count"]
        )
    summary_dict = dict(
        sorted(summary_dict.items(), key=lambda x: x[1]["count"], reverse=True)
    )
    return summary_dict


with open("audio_results.txt", "r", encoding="utf-8") as f:
    for lineno, line in enumerate(f, start=1):
        raw = line.strip()
        if not raw:
            continue
        # Try JSON first, then fall back to Python literal parsing
        try:
            obj = json.loads(raw)
        except json.JSONDecodeError:
            try:
                obj = ast.literal_eval(raw)
                # ast.literal_eval may return tuples/lists; ensure dict
                if not isinstance(obj, dict):
                    raise ValueError("Parsed object is not a dict")
            except Exception as e:
                print(f"Skipping malformed line {lineno}: {e} -- '{raw[:120]}'")
                continue
        audio_results.append(obj)
audio_results_summary = summarize_results(audio_results)

print(json.dumps(audio_results_summary, indent=2))
