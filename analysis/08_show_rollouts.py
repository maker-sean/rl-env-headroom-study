"""Print full rollouts from a vf-run traces.jsonl, with scores and components.

Usage: uv run python scripts/08_show_rollouts.py outputs/<run-name> [n]

traces.jsonl holds one EPISODE per line; each episode carries a nested
`traces` list (one per agent). Rewards and metrics live on the inner trace.
"""
import json, sys
from pathlib import Path

sys.path.insert(0, "src")
from doc_extraction_study.cord import SCALAR_FIELDS

run = Path(sys.argv[1])
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 3
episodes = [json.loads(l) for l in (run / "traces.jsonl").read_text().splitlines() if l.strip()]
print(f"run: {run}   episodes: {len(episodes)}")

for ep in episodes[:limit]:
    data = (ep.get("task") or {}).get("data") or {}
    tr = (ep.get("traces") or [{}])[0]
    print("\n" + "=" * 78)
    print(f"task      : {data.get('id')}  condition={data.get('condition')}  "
          f"prompt={data.get('prompt_version')}")
    print(f"reward    : {tr.get('reward', 'n/a')}   stop={tr.get('stop_condition')}  "
          f"ok={tr.get('ok')}")
    rw = tr.get("rewards") or {}
    if rw:
        total = 0.0
        print("components:")
        for k, v in rw.items():
            val = v.get("score", v.get("value")) if isinstance(v, dict) else v
            wt = v.get("weight") if isinstance(v, dict) else None
            if isinstance(val, (int, float)) and isinstance(wt, (int, float)):
                total += val * wt
                print(f"   {k:<16} score={val:<8.4f} weight={wt:<5} -> {val*wt:.4f}")
            else:
                print(f"   {k:<16} {v}")
        if total:
            print(f"   {'WEIGHTED SUM':<16} {total:.4f}")

    truth = json.loads(data.get("truth_json") or "{}")
    print("\nGROUND TRUTH")
    for i in truth.get("line_items", []):
        print(f"   {i['name']!r:<28} qty={i['quantity']} price={i['price']}")
    sc = ", ".join(f"{f}={truth[f]}" for f in SCALAR_FIELDS if truth.get(f) is not None)
    print(f"   scalars: {sc or '(none)'}")

    reply = None
    for n in reversed(tr.get("nodes") or []):
        msg = n.get("message") or n
        if (msg.get("role") == "assistant") and msg.get("content"):
            reply = msg["content"]
            break
    print(f"\nMODEL REPLY\n{reply if reply else '(none found)'}")

    m = tr.get("metrics") or {}
    if m:
        print("\nMETRICS")
        for k, v in m.items():
            val = v.get("score", v.get("value")) if isinstance(v, dict) else v
            if isinstance(val, dict):
                nz = {kk: vv for kk, vv in val.items() if vv}
                if nz: print(f"   {k}: {nz}")
            elif val not in (None, 0, 0.0, ""):
                print(f"   {k}: {val}")
    print(f"\nTOKENS in={tr.get('num_input_tokens')} out={tr.get('num_output_tokens')}")
