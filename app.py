"""
Aurora dashboard — a thin Flask layer over agent_loop.py.

Reads whatever's actually in agent_memory.json (no mock data) and exposes it
to the UI. The "Run pipeline" button in the UI calls the exact same
run_pipeline() that `python agent_loop.py` runs from the terminal.
"""

import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from flask import Flask, jsonify, request, render_template

import agent_loop as core

app = Flask(__name__)


def effective_status(meeting, record):
    return record.get("status", meeting["status"])


def build_meetings_payload(memory: dict) -> list:
    out = []
    for m in core.meetings:
        record = memory.get(m["id"], {})
        out.append({
            "id": m["id"],
            "attendee_name": m["attendee_name"],
            "company": m["company"],
            "topic": m["topic"],
            "context": m.get("context", ""),
            "status": effective_status(m, record),
            "summary": record.get("summary"),
            "action_items": record.get("action_items", []),
            "agenda": record.get("agenda", []),
            "summary_generated_at": record.get("summary_generated_at"),
            "followup_sent_at": record.get("followup_sent_at"),
            "followup_rescued": record.get("followup_rescued", False),
        })
    return out


@app.route("/")
def index():
    return render_template("index.html", agent_name=core.AGENT_NAME, company=core.COMPANY_NAME)


@app.route("/api/state")
def api_state():
    memory = core.load_memory()
    meetings = build_meetings_payload(memory)
    tracker = memory.get("_action_item_tracker", [])

    current_ids = {m["id"] for m in core.meetings}
    meeting_records = {k: v for k, v in memory.items() if k in current_ids}
    meetings_processed = len(meeting_records)
    action_items_extracted = sum(len(r.get("action_items", [])) for r in meeting_records.values())
    followups_sent = sum(1 for r in meeting_records.values() if r.get("followup_sent_at"))
    minutes_saved = meetings_processed * core.MINUTES_SAVED_PER_MEETING

    return jsonify({
        "agent_name": core.AGENT_NAME,
        "company": core.COMPANY_NAME,
        "meetings": meetings,
        "tracker": tracker,
        "roi": {
            "meetings_processed": meetings_processed,
            "action_items_extracted": action_items_extracted,
            "followups_sent": followups_sent,
            "minutes_saved": minutes_saved,
        },
        "generated_at": datetime.now().isoformat(),
    })


@app.route("/api/run-pipeline", methods=["POST"])
def api_run_pipeline():
    core.run_pipeline()
    return api_state()


@app.route("/api/chat", methods=["POST"])
def api_chat():
    question = (request.json or {}).get("question", "").strip()
    if not question:
        return jsonify({"error": "Ask something first."}), 400
    memory = core.load_memory()
    answer = core.chat_with_agent(question, memory)
    return jsonify({"answer": answer})


if __name__ == "__main__":
    app.run(debug=True, port=5000)