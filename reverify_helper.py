"""Reverify-loop state helper.

Subcommands:
  init        Build priority queue from golf_courses.json + url_check_report.json
              and write data/reverify_state.json (no-op if state already exists).
              Also creates data/reverify_proposals/ and data/reverify_log.md.
  pick N      Pop top-N IDs from the queue, update state, print JSON
              {"iteration": int, "ids": [...], "course_data": {id: {...}, ...}}
              to stdout. Re-initializes queue if empty (full-cycle restart).
  finalize    Args: <iteration> <batch_path> <diff_count> <queue_remaining>
              Append a log line. Idempotent.
  status      Print short status summary.
"""

import json
import sys
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
COURSES_PATH = ROOT / "data" / "golf_courses.json"
URL_REPORT_PATH = ROOT / "url_check_report.json"
STATE_PATH = ROOT / "data" / "reverify_state.json"
PROPOSALS_DIR = ROOT / "data" / "reverify_proposals"
LOG_PATH = ROOT / "data" / "reverify_log.md"


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_courses():
    with open(COURSES_PATH, "r", encoding="utf-8") as f:
        doc = json.load(f)
    return doc.get("courses", []) or doc


def _load_url_failures():
    """Return set of golf course IDs whose any tracked URL is 4xx/5xx/ERR."""
    if not URL_REPORT_PATH.exists():
        return set()
    try:
        with open(URL_REPORT_PATH, "r", encoding="utf-8") as f:
            rep = json.load(f)
    except Exception:
        return set()
    failed_ids = set()
    # Schema is unknown — best-effort: scan for any object with "id" + "status"/"http_status"
    def walk(obj):
        if isinstance(obj, dict):
            cid = obj.get("id") or obj.get("course_id")
            status = obj.get("status") or obj.get("http_status") or obj.get("code")
            if cid and status is not None:
                s = str(status)
                if s.startswith(("4", "5")) or s.upper() in ("ERR", "ERROR", "TIMEOUT"):
                    failed_ids.add(cid)
            for v in obj.values():
                walk(v)
        elif isinstance(obj, list):
            for v in obj:
                walk(v)
    walk(rep)
    return failed_ids


def _priority_key(course, failed_ids):
    """Lower tuple = higher priority. Sort ascending."""
    cid = course.get("id", "")
    op = course.get("operating_status", {}) or {}
    last_verified = op.get("last_verified") or ""
    confidence = op.get("confidence") or "high"
    fees = course.get("fees_2026_05") or {}
    verification_needed = bool(fees.get("verification_needed"))
    fee_last_verified = fees.get("last_verified") or ""

    bucket_a = 0 if cid in failed_ids else 1                  # 1) URL failures
    bucket_b = last_verified or "0000-00-00"                  # 2) oldest op last_verified
    conf_rank = {"low": 0, "medium": 1, "high": 2}.get(confidence, 2)
    bucket_c = conf_rank                                       # 3) low confidence first
    bucket_d = 0 if verification_needed else 1                # 4) verification_needed
    bucket_e = fee_last_verified or "0000-00-00"              # 5) fee staleness

    return (bucket_a, bucket_b, bucket_c, bucket_d, bucket_e, cid)


def build_queue(courses, failed_ids, exclude_done=None):
    exclude = set(exclude_done or [])
    sortable = [c for c in courses if c.get("id") and c["id"] not in exclude]
    sortable.sort(key=lambda c: _priority_key(c, failed_ids))
    return [c["id"] for c in sortable]


def cmd_init():
    if STATE_PATH.exists():
        print(json.dumps({"status": "exists", "state_path": str(STATE_PATH)}))
        PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
        return
    courses = _load_courses()
    failed = _load_url_failures()
    queue = build_queue(courses, failed)
    state = {
        "queue": queue,
        "done": [],
        "iteration": 0,
        "started_at": _now_iso(),
        "last_iteration_at": None,
        "cycles_completed": 0,
        "url_failures_seed": sorted(failed),
        "total_courses": len(courses),
    }
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    PROPOSALS_DIR.mkdir(parents=True, exist_ok=True)
    if not LOG_PATH.exists():
        with open(LOG_PATH, "w", encoding="utf-8") as f:
            f.write("# Reverify Loop Log\n\n")
            f.write(f"Started: {state['started_at']}\n")
            f.write(f"Total courses: {state['total_courses']}\n")
            f.write(f"URL-failure seed count: {len(failed)}\n\n")
    print(json.dumps({"status": "initialized", "queue_size": len(queue), "url_failures": len(failed)}))


def cmd_pick(n):
    if not STATE_PATH.exists():
        cmd_init()
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)

    # Restart cycle if empty
    if not state["queue"]:
        courses = _load_courses()
        failed = _load_url_failures()
        # On restart, exclude none — full re-sweep
        state["queue"] = build_queue(courses, failed)
        state["cycles_completed"] = state.get("cycles_completed", 0) + 1
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(f"\n## FULL CYCLE COMPLETE — restarting from highest-priority items ({_now_iso()})\n\n")

    picked = state["queue"][:n]
    state["queue"] = state["queue"][n:]
    state["done"].extend(picked)
    state["iteration"] = state.get("iteration", 0) + 1
    state["last_iteration_at"] = _now_iso()

    # Load full course data for picked
    courses = _load_courses()
    by_id = {c["id"]: c for c in courses if c.get("id")}
    course_data = {cid: by_id.get(cid) for cid in picked}

    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)

    # Write full pick payload (with course data, may contain non-ASCII) to a file.
    pick_path = ROOT / "data" / f"reverify_pick_iter{state['iteration']:04d}.json"
    pick_payload = {
        "iteration": state["iteration"],
        "ids": picked,
        "queue_remaining": len(state["queue"]),
        "cycles_completed": state.get("cycles_completed", 0),
        "course_data": course_data,
    }
    with open(pick_path, "w", encoding="utf-8") as f:
        json.dump(pick_payload, f, ensure_ascii=False, indent=2)

    # Stdout: ASCII-safe summary only.
    print(json.dumps({
        "iteration": state["iteration"],
        "ids": picked,
        "queue_remaining": len(state["queue"]),
        "cycles_completed": state.get("cycles_completed", 0),
        "pick_file": str(pick_path),
    }))


def cmd_finalize(iteration, batch_path, diff_count, queue_remaining):
    line = f"- [{_now_iso()}] iter{iteration} · 6 courses · diffs: {diff_count} · proposals: `{batch_path}` · queue remaining: {queue_remaining}\n"
    with open(LOG_PATH, "a", encoding="utf-8") as f:
        f.write(line)
    print(json.dumps({"status": "logged"}))


def cmd_status():
    if not STATE_PATH.exists():
        print(json.dumps({"status": "uninitialized"}))
        return
    with open(STATE_PATH, "r", encoding="utf-8") as f:
        state = json.load(f)
    print(json.dumps({
        "iteration": state.get("iteration"),
        "queue_remaining": len(state.get("queue", [])),
        "done_count": len(state.get("done", [])),
        "cycles_completed": state.get("cycles_completed", 0),
        "started_at": state.get("started_at"),
        "last_iteration_at": state.get("last_iteration_at"),
    }))


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("usage: reverify_helper.py {init|pick N|finalize iter batch_path diff_count queue_remaining|status}", file=sys.stderr)
        sys.exit(2)
    cmd = sys.argv[1]
    if cmd == "init":
        cmd_init()
    elif cmd == "pick":
        cmd_pick(int(sys.argv[2]))
    elif cmd == "finalize":
        cmd_finalize(sys.argv[2], sys.argv[3], sys.argv[4], sys.argv[5])
    elif cmd == "status":
        cmd_status()
    else:
        print(f"unknown command: {cmd}", file=sys.stderr)
        sys.exit(2)
