"""
Swytchcode Aurora — an agentic meeting & follow-up assistant that handles
scheduling, summaries, and follow-ups for the whole team, powered by
Swytchcode integrations.

Multi-agent framing — three named roles, each shown separately:
    🗓️  Scheduler  -> proposes time + agenda, creates the Calendar event
    📝 Summarizer  -> turns a transcript into a summary + action items
    ✍️  Writer     -> drafts a personalized follow-up email, sends it

Plus:
- Memory across runs (won't re-notify / re-send too soon)
- "Stale Follow-up Rescue": scans memory for meetings that got a
  summary + action items but never got a follow-up sent, and
  re-triggers the Writer for them.
- ROI/impact counter: meetings processed, action items extracted,
  estimated time saved.
- Daily digest: posts a "here's what happened today" summary to Slack.
"""

import subprocess
import shutil
import json
import os
from datetime import datetime, timedelta
from groq import Groq

client = Groq(api_key=os.environ["GROQ_API_KEY"])
MEMORY_FILE = "agent_memory.json"

# Resolved once so we don't repeatedly hit PATH lookup. shutil.which() finds the
# real target (works whether it's an .exe, or a .cmd/.bat shim on Windows from a
# global npm/pip install) so we can call it directly without needing shell=True.
# shell=True is intentionally avoided everywhere below: on POSIX, shell=True with
# a list argument only executes args[0] and silently drops the rest (they go to
# the shell itself, not the command) — a real footgun. Resolving the executable
# path up front sidesteps that on every platform.
_SWYTCHCODE_PATH = shutil.which("swytchcode") or "swytchcode"


def run_swytchcode(*args: str) -> subprocess.CompletedProcess:
    """Runs a `swytchcode exec ...` CLI call safely, cross-platform, and
    surfaces failures instead of letting them pass silently."""
    result = subprocess.run(
        [_SWYTCHCODE_PATH, *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        print(f"  ⚠️  swytchcode call failed ({' '.join(args)}): {result.stderr.strip()}")
    return result
LOGO_URL = "https://raw.githubusercontent.com/himanihassija/Swytchcode-Aurora-Himani-Hassija/main/aurora_logo.png"
CALENDAR_ID = "f60a9f1d42cd19be5c7b007633d79700d736661ccce017fa446416272dcd1034@group.calendar.google.com"
# Everyone who should get a calendar invite (and see the event on their own
# calendar) in addition to whoever's on CALENDAR_ID.
MEETING_ATTENDEES = ["24f3000056@ds.study.iitm.ac.in", "himanihassija1609@gmail.com"]
SLACK_CHANNEL = "C0BNPFZ9YAX"
# LOGO_URL (defined above) doubles as the Slack message avatar. Slack fetches
# this URL server-side, so it must be a real hosted image link — a local file
# path or base64 data URI will NOT work here.

# How long we'll wait after a summary before flagging the follow-up as "at risk"
FOLLOWUP_RISK_HOURS = 24

# Estimated minutes saved per meeting on manual notes + follow-up (for the ROI counter)
MINUTES_SAVED_PER_MEETING = 15

# We're now inside Swytchcode itself — Aurora is the internal agent's name,
# not a product being pitched. No sales pitch, just internal team ops.
COMPANY_NAME = "Swytchcode"
AGENT_NAME = "Swytchcode Aurora"

# --- Fake meetings (stand-in for real Calendar/Zoom data) ---
# These are INTERNAL Swytchcode team meetings, not client/lead calls.
# status: "upcoming" (needs scheduling), "needs_summary" (has a transcript
# waiting to be processed), or "needs_followup" (summary exists already)
meetings = [
    {
        "id": "m1",
        "attendee_name": "Rohan Mehta",
        "attendee_email": "himanihassija@gmail.com",
        "company": "Swytchcode",
        "topic": "Sprint planning — Track 2 build",
        "context": "Kicking off the meeting-assistant sprint; need to align on scope for the week",
        "status": "upcoming",
    },
    {
        "id": "m2",
        "attendee_name": "Priya Kapoor",
        "attendee_email": "himanihassija@gmail.com",
        "company": "Swytchcode",
        "topic": "Integrations sync — Zoom escalation & upcoming partner integrations",
        "context": "Checking in on the Zoom OAuth blocker and scoping the next integrations on the roadmap",
        "status": "needs_summary",
        "transcript": (
            "Priya: Where do we stand on Zoom? Us: Still blocked — their team confirmed "
            "the OAuth authorize-button bug is on their end and there's no ETA yet, so "
            "we're moving forward with the paste-transcript fallback as our primary path "
            "for the demo, not just a backup. Priya: Understood, and Notion? Us: Auth is "
            "connected but page.create is still failing on their end with a schema error, "
            "so we're routing meeting notes to Slack instead for now. Priya: That's fine. "
            "What about the new integrations we discussed, Shorthills AI and Optum? Us: "
            "Both are lined up for the sprint right after this one, once our integrations "
            "layer stabilizes. We've already scoped what data would sync on each side. "
            "Priya: Good, let's lock that timeline in. Action for Rohan: send Zoom's "
            "support team a follow-up ticket today. Action for Priya: share the Shorthills "
            "AI integration spec with the team by tomorrow."
        ),
    },
    {
        "id": "m3",
        "attendee_name": "Arjun Shah",
        "attendee_email": "himanihassija@gmail.com",
        "company": "Swytchcode",
        "topic": "Hackathon roadmap — upcoming events & submission plan",
        "context": "Planning what comes after this Track 2 submission and whether Aurora becomes an internal tool",
        "status": "needs_summary",
        "transcript": (
            "Rohan: Let's talk about what's next after this Track 2 submission. Us: We're "
            "planning to enter at least two more hackathons this quarter — one focused on "
            "enterprise workflow automation, one on healthcare-adjacent tooling, since that "
            "lines up well with the Optum work. Rohan: Are we resubmitting Aurora or "
            "building something new? Us: Aurora's core, the multi-agent scheduling and "
            "follow-up loop, is reusable, so we'd fork it and adapt the integrations "
            "rather than start from scratch. Rohan: That saves us time. What about "
            "internal adoption? Us: We want to pilot Aurora with the actual Swytchcode "
            "team full-time after today's demo, not just as a hackathon project. Rohan: "
            "Let's put together a two-week pilot plan. Action for Priya: draft the pilot "
            "rollout doc. Action for Rohan: identify two more upcoming hackathons to "
            "target this quarter."
        ),
    },
    {
        "id": "m4",
        "attendee_name": "Priya Kapoor",
        "attendee_email": "himanihassija@gmail.com",
        "company": "Swytchcode",
        "topic": "Tender win — enterprise workflow automation",
        "context": "Confirming the enterprise automation tender win and next onboarding steps",
        "status": "needs_followup",  # summary already exists in memory from a prior run
    },
    {
        "id": "m5",
        "attendee_name": "Priya Kapoor",
        "attendee_email": "himanihassija@gmail.com",
        "company": "Swytchcode",
        "topic": "Partnership sync — Shorthills AI",
        "context": "Scoping the formal partnership with Shorthills AI on the AI-agent tooling side",
        "status": "needs_summary",
        "transcript": (
            "Priya: Shorthills AI confirmed they want to formally partner with us on the "
            "AI-agent tooling side. Us: That's great, what's the scope? Priya: They want "
            "to integrate our meeting-assistant agents into their own client workflows, so "
            "we'd be white-labeling parts of Aurora for them. Us: We'll need our "
            "integrations layer to support their auth model, that's the main blocker on "
            "our side right now. Priya: They said end of month is workable for that. Us: "
            "Good, let's also nail down the revenue share before the kickoff call. Priya: "
            "Agreed, I'll draft terms this week. Action for Priya: schedule the Shorthills "
            "AI kickoff call. Action for Rohan: get the auth model requirements from "
            "Shorthills AI's engineering team."
        ),
    },
    {
        "id": "m6",
        "attendee_name": "Priya Kapoor",
        "attendee_email": "himanihassija@gmail.com",
        "company": "Swytchcode",
        "topic": "Partnership sync — Optum",
        "context": "Scoping the pilot integration with Optum for their internal ops workflows",
        "status": "needs_summary",
        "transcript": (
            "Priya: Optum's team signed off on a pilot integration for their internal ops "
            "workflows. Us: That's a big one, what's the timeline? Priya: They want to "
            "start the pilot in three weeks, but before any real data touches our system "
            "we need a compliance review, since it's healthcare. Us: Right, we should loop "
            "in legal early then. Priya: Agreed, I'll set that up this week. Us: What's the "
            "actual integration scope? Priya: Mainly syncing meeting notes and action items "
            "into their internal ops dashboard, nothing patient-facing. Us: Good, that keeps "
            "the compliance surface smaller. Action for Rohan: loop in legal on Optum's "
            "compliance requirements. Action for Priya: confirm the three-week pilot start "
            "date with Optum."
        ),
    },
    {
        "id": "m7",
        "attendee_name": "Aman Garg",
        "attendee_email": "himanihassija@gmail.com",
        "company": "Amazon",
        "topic": "Mentorship call — Amazon SDE feedback on Aurora",
        "context": "Getting external engineering feedback on Aurora's architecture ahead of the demo",
        "status": "needs_summary",
        "transcript": (
            "Us: Thanks for taking the time to look at Aurora's architecture. Aman: Happy "
            "to help, overall the multi-agent framing is solid, naming each role clearly, "
            "Scheduler, Summarizer, Writer, is a strong pattern for judges to follow. Us: "
            "Appreciate that. Anything you'd flag? Aman: One thing worth tightening for a "
            "real production version is that your idempotency check trusts your local "
            "memory file rather than the actual state of external systems, so if something "
            "changes outside your pipeline, the agent won't know. For a hackathon demo "
            "that's fine, just worth a line in the writeup as a known limitation. Us: Good "
            "catch, we'll note that. Aman: Otherwise the ROI counter and ambient "
            "Stale Follow-up Rescue feature are the kind of details that stand out in a "
            "judged demo, a lot of teams skip that layer. Action for Us: add a note about "
            "memory-versus-live-state reconciliation as a known limitation in the writeup."
        ),
    },
]


def load_memory() -> dict:
    if os.path.exists(MEMORY_FILE):
        with open(MEMORY_FILE) as f:
            return json.load(f)
    return {}


def save_memory(memory: dict):
    with open(MEMORY_FILE, "w") as f:
        json.dump(memory, f, indent=2)


def ask_llm(prompt: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
    )
    return response.choices[0].message.content.strip()


def parse_json_block(text: str) -> dict:
    text = text.replace("```json", "").replace("```", "").strip()
    start, end = text.find("{"), text.rfind("}")
    if start == -1 or end == -1:
        return {}
    try:
        return json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return {}


def ask_llm_json(prompt: str) -> dict:
    """Calls the LLM expecting a JSON object back. If the first response fails
    to parse (cut off mid-response, or an unescaped quote breaking the JSON),
    retries once with a stricter reminder before giving up."""
    parsed = parse_json_block(ask_llm(prompt))
    if not parsed:
        stricter_prompt = prompt + (
            "\n\nIMPORTANT: Respond with ONLY a single valid JSON object, nothing "
            "before or after it. Escape any quotes inside string values so the "
            "JSON stays valid, and keep it concise enough to finish completely."
        )
        parsed = parse_json_block(ask_llm(stricter_prompt))
    return parsed


# --------------------------------------------------------------------------
# ROLE 1: Scheduler — proposes a time + agenda, creates the Calendar event
# --------------------------------------------------------------------------
def scheduler_agent(meeting: dict) -> dict:
    # Compute tomorrow's date ourselves — don't trust the LLM with "today's date,"
    # it has no reliable clock and will hallucinate old/wrong years.
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    prompt = f"""You are a scheduling assistant. Propose a meeting time on {tomorrow}
(business hours, IST) and a short 3-bullet agenda for this meeting.

Meeting: {meeting['topic']} with {meeting['attendee_name']} at {meeting['company']}
Context: {meeting['context']}

Respond in this exact JSON format, nothing else — start_time and end_time MUST use
the date {tomorrow} exactly, only the time portion is yours to choose:
{{"start_time": "{tomorrow}THH:MM:SS+05:30", "end_time": "{tomorrow}THH:MM:SS+05:30", "agenda": ["...", "...", "..."]}}
"""
    plan = ask_llm_json(prompt)
    if not plan:
        return plan

    # Safety net: if the LLM still gets the date wrong, force it back to tomorrow.
    for key in ("start_time", "end_time"):
        if not str(plan.get(key, "")).startswith(tomorrow):
            time_part = plan.get(key, "T10:00:00+05:30").split("T")[-1]
            plan[key] = f"{tomorrow}T{time_part}"

    with open("calendar_event.json", "w") as f:
        json.dump({
            "summary": f"{meeting['topic']} — {meeting['attendee_name']} ({meeting['company']})",
            "description": "Agenda:\n" + "\n".join(f"- {item}" for item in plan.get("agenda", [])),
            "start": {"dateTime": plan.get("start_time")},
            "end": {"dateTime": plan.get("end_time")},
            "attendees": [{"email": email} for email in MEETING_ATTENDEES],
        }, f)
    run_swytchcode(
        "exec", "calendar.calendar.events.create",
        "--body", "calendar_event.json",
        "--input", f"calendarId={CALENDAR_ID}",
        "--input", "sendUpdates=all",
        "--json",
    )
    slack_notify(f"Meeting scheduled with *{meeting['attendee_name']}* on {plan.get('start_time', '')[:10]} — _{meeting['topic']}_")
    return plan


# --------------------------------------------------------------------------
# Manual scheduling — triggered from the dashboard "New meeting" form rather
# than from the seeded `meetings` list. Creates the real Calendar event (with
# attendees + Slack note), then adds the meeting to memory and to the
# in-memory `meetings` list so it shows up on the dashboard right away.
# --------------------------------------------------------------------------
def create_manual_meeting(
    attendee_name: str,
    attendee_email: str = "",
    company: str = "",
    topic: str = "",
    context: str = "",
    date_str: str | None = None,
    time_str: str | None = None,
) -> dict:
    meeting_date = date_str or (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    start_time = f"{meeting_date}T{time_str or '10:00:00'}+05:30"
    end_time = (datetime.fromisoformat(start_time) + timedelta(minutes=30)).strftime("%Y-%m-%dT%H:%M:%S+05:30")

    prompt = f"""You are a scheduling assistant. Write a short 3-bullet agenda for
this meeting.

Meeting: {topic} with {attendee_name} at {company}
Context: {context}

Respond in this exact JSON format, nothing else:
{{"agenda": ["...", "...", "..."]}}
"""
    plan = ask_llm_json(prompt)
    agenda = plan.get("agenda", []) if plan else []

    meeting_id = "manual-" + datetime.now().strftime("%Y%m%d%H%M%S")

    # De-duped: our two default attendees, plus this meeting's actual
    # attendee email if one was given and it isn't already in the list.
    attendees = list(dict.fromkeys(MEETING_ATTENDEES + ([attendee_email] if attendee_email else [])))

    with open("calendar_event.json", "w") as f:
        json.dump({
            "summary": f"{topic} — {attendee_name}" + (f" ({company})" if company else ""),
            "description": "Agenda:\n" + "\n".join(f"- {item}" for item in agenda),
            "start": {"dateTime": start_time},
            "end": {"dateTime": end_time},
            "attendees": [{"email": email} for email in attendees],
        }, f)
    run_swytchcode(
        "exec", "calendar.calendar.events.create",
        "--body", "calendar_event.json",
        "--input", f"calendarId={CALENDAR_ID}",
        "--input", "sendUpdates=all",
        "--json",
    )
    slack_notify(f"🗓️ New meeting scheduled with *{attendee_name}*" + (f" ({company})" if company else "") + f" on {meeting_date} — _{topic}_")

    meeting = {
        "id": meeting_id,
        "attendee_name": attendee_name,
        "attendee_email": attendee_email,
        "company": company,
        "topic": topic,
        "context": context,
        "status": "scheduled",
    }
    meetings.append(meeting)

    memory = load_memory()
    memory[meeting_id] = {
        "status": "scheduled",
        "agenda": agenda,
        "start_time": start_time,
        "scheduled_at": datetime.now().isoformat(),
    }
    save_memory(memory)

    return {"meeting": meeting, "start_time": start_time, "end_time": end_time, "agenda": agenda}


# --------------------------------------------------------------------------
# Slack — drops a short notification into the team channel
# --------------------------------------------------------------------------
def slack_notify(text: str):
    payload = {"channel": SLACK_CHANNEL, "text": text}
    if LOGO_URL:
        payload["icon_url"] = LOGO_URL
    with open("slack_msg.json", "w") as f:
        json.dump(payload, f)
    run_swytchcode("exec", "slack.chat.postmessage.create", "--body", "slack_msg.json", "--json")


# --------------------------------------------------------------------------
# ROLE 2: Summarizer — transcript -> structured summary + action items
# --------------------------------------------------------------------------
def summarizer_agent(meeting: dict) -> dict:
    prompt = f"""Summarize this meeting transcript into a detailed summary and a list
of concrete action items (who owns each one, if mentioned). The summary should
cover what was discussed, any decisions made, and the overall outcome in enough
detail that someone who missed the meeting understands the full picture.

The only external attendee in this meeting is {meeting['attendee_name']}. Do not
introduce, name, or attribute quotes/actions to any person who is not either
"{meeting['attendee_name']}" or "Us" — even if another name feels plausible or
familiar. If the transcript labels a speaker "{meeting['attendee_name'].split()[0]}"
or similar, that speaker IS {meeting['attendee_name']}; do not substitute a
different full name for them.

Meeting: {meeting['topic']} with {meeting['attendee_name']} at {meeting['company']}
Transcript:
{meeting.get('transcript', '')}

Respond in this exact JSON format, nothing else:
{{"summary": "4-5 sentence summary", "action_items": ["...", "..."]}}
"""
    return ask_llm_json(prompt)


# --------------------------------------------------------------------------
# Notion — logs the meeting summary + action items as a real Notion page
# (Notion is connected now, so this is a live call, not a text fallback)
# --------------------------------------------------------------------------
def notion_agent(meeting: dict, summary_data: dict, parent_page_id: str):
    action_items_blocks = [
        {
            "object": "block",
            "type": "to_do",
            "to_do": {"rich_text": [{"text": {"content": item}}], "checked": False},
        }
        for item in summary_data.get("action_items", [])
    ]

    with open("notion_page.json", "w") as f:
        json.dump({
            "parent": {"page_id": parent_page_id},
            "properties": {
                "title": [{"text": {"content": f"{meeting['topic']} — {meeting['attendee_name']}"}}]
            },
            "children": [
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": [{"text": {"content": summary_data.get("summary", "")}}]},
                },
                {"object": "block", "type": "heading_3", "heading_3": {"rich_text": [{"text": {"content": "Action items"}}]}},
                *action_items_blocks,
            ],
        }, f)

    run_swytchcode("exec", "notion.page.create", "--body", "notion_page.json", "--json")


# --------------------------------------------------------------------------
# Meeting notes -> Slack (Notion fallback). Notion's page.create is broken
# on Swytchcode's side right now, so notes get posted as a formatted Slack
# message instead — reuses the same slack_notify plumbing as everything else.
# --------------------------------------------------------------------------
def post_meeting_notes_to_slack(meeting: dict, summary_data: dict):
    lines = [
        f"*Meeting Notes: {meeting['topic']}*",
        "```",
        f"{'Attendee':<10}{meeting['attendee_name']}",
        f"{'Company':<10}{meeting['company']}",
        f"{'Context':<10}{meeting['context']}",
        "```",
        "",
        "*Summary*",
        summary_data.get("summary", "No summary was available for this meeting."),
        "",
        "*Action items*",
    ]
    action_items = summary_data.get("action_items", [])
    if action_items:
        lines.append("```")
        lines.append(f"{'Owner':<12}{'Action Item'}")
        lines.append(f"{'-' * 12}{'-' * 40}")
        for raw_item in action_items:
            owner, item_text = parse_owner_and_item(raw_item)
            lines.append(f"{owner:<12}{item_text}")
        lines.append("```")
    else:
        lines.append("No action items were extracted from this meeting.")

    slack_notify("\n".join(lines))


# --------------------------------------------------------------------------
# ROLE 3: Writer — drafts + sends a personalized follow-up email
# --------------------------------------------------------------------------
def writer_agent(meeting: dict, summary_data: dict) -> dict:
    prompt = f"""Write a warm, detailed internal follow-up email after a team meeting
at {COMPANY_NAME}. Aim for two short paragraphs (roughly 6-8 sentences total): the
first recapping what was discussed and why it matters, the second walking through
the action items and who owns each one, plus a brief note on what happens next.

Teammate: {meeting['attendee_name']}
Meeting topic: {meeting['topic']}
Summary: {summary_data.get('summary', '')}
Action items: {', '.join(summary_data.get('action_items', []))}

Reference the actual action items and who owns what. Keep it internal-team tone —
no sales pitch, no product name-dropping, no "I hope this finds you well."

Respond in this exact JSON format, nothing else:
{{"subject": "...", "body_html": "<p>...</p><p>...</p>"}}
"""
    email_content = ask_llm_json(prompt)
    body_html = email_content.get("body_html", f"<p>Hi {meeting['attendee_name']},</p>")

    if AGENT_NAME not in body_html:
        body_html += f"<p style=\"color:#888;font-size:12px;\">Sent by {AGENT_NAME}</p>"

    if LOGO_URL:
        body_html += f'<img src="{LOGO_URL}" alt="{AGENT_NAME}" width="120" style="margin-top:16px;" />'

    with open("email.json", "w") as f:
        json.dump({
            "from": "onboarding@resend.dev",
            "to": meeting["attendee_email"],
            "subject": email_content.get("subject", f"Following up on {meeting['topic']}"),
            "html": body_html,
        }, f)
    run_swytchcode("exec", "resend.email.create", "--body", "email.json", "--json")
    return email_content


# --------------------------------------------------------------------------
# Stale Follow-up Rescue: scan memory for meetings with a summary but no
# follow-up sent within FOLLOWUP_RISK_HOURS, and re-run the Writer for them.
# --------------------------------------------------------------------------
def stale_followup_rescue(memory: dict):
    print("\n=== Stale Follow-up Rescue scan ===")
    now = datetime.now()
    rescued_any = False

    for meeting_id, record in memory.items():
        if meeting_id.startswith("_"):
            continue  # skip non-meeting entries like _action_item_tracker
        if not record.get("summary_generated_at") or record.get("followup_sent_at"):
            continue  # no summary yet, or follow-up already went out

        summarized_at = datetime.fromisoformat(record["summary_generated_at"])
        hours_elapsed = (now - summarized_at).total_seconds() / 3600

        if hours_elapsed >= FOLLOWUP_RISK_HOURS:
            print(f"  ⚠️  FOLLOW-UP AT RISK: {meeting_id} — {hours_elapsed:.1f}h since summary, no follow-up sent")
            match = next((m for m in meetings if m["id"] == meeting_id), None)
            if match:
                print("  🤖 RECOVERY INITIATED — re-drafting and sending follow-up...")
                summary_data = {
                    "summary": record.get("summary", ""),
                    "action_items": record.get("action_items", []),
                }
                writer_agent(match, summary_data)
                record["followup_sent_at"] = now.isoformat()
                record["followup_rescued"] = True
                rescued_any = True

    if not rescued_any:
        print("  No stale follow-ups found.")


# --------------------------------------------------------------------------
# Cross-meeting action item tracker — instead of action items living only
# inside each meeting's own memory record, keep one running list across
# ALL meetings with an owner + status, stored under memory["_action_item_tracker"].
# --------------------------------------------------------------------------
def parse_owner_and_item(raw_item: str) -> tuple:
    """Splits 'Rohan: ping support' into ('Rohan', 'ping support').
    Falls back to 'Unassigned' if there's no clear 'Name: ...' prefix."""
    if ":" in raw_item:
        owner, rest = raw_item.split(":", 1)
        owner = owner.strip()
        if 0 < len(owner.split()) <= 3:  # looks like a name, not a full sentence
            return owner, rest.strip()
    return "Unassigned", raw_item.strip()


def update_action_tracker(memory: dict, meeting: dict, action_items: list):
    tracker = memory.setdefault("_action_item_tracker", [])
    already_tracked = {
        (entry["owner"], entry["item"]) for entry in tracker if entry["meeting_id"] == meeting["id"]
    }
    for raw_item in action_items:
        owner, item_text = parse_owner_and_item(raw_item)
        if (owner, item_text) in already_tracked:
            continue
        tracker.append({
            "meeting_id": meeting["id"],
            "meeting_topic": meeting["topic"],
            "owner": owner,
            "item": item_text,
            "status": "open",
            "created_at": datetime.now().isoformat(),
        })


def print_action_tracker(memory: dict):
    tracker = memory.get("_action_item_tracker", [])
    print("\n=== ✅ Action Item Tracker (across all meetings) ===")
    if not tracker:
        print("  No action items tracked yet.")
        return
    for entry in tracker:
        icon = "✅" if entry["status"] == "done" else "🔲"
        print(f"  {icon} [{entry['owner']}] {entry['item']}  — ({entry['meeting_topic']})")


# --------------------------------------------------------------------------
# Chat with the agent — quick Q&A over everything in memory + the tracker.
# e.g. "what were the action items from the Priya sync?"
# --------------------------------------------------------------------------
def chat_with_agent(question: str, memory: dict) -> str:
    context_lines = []
    for meeting_id, record in memory.items():
        if meeting_id == "_action_item_tracker":
            continue
        match = next((m for m in meetings if m["id"] == meeting_id), None)
        name = match["attendee_name"] if match else meeting_id
        topic = match["topic"] if match else ""
        context_lines.append(
            f"Meeting with {name} ({topic}): status={record.get('status', '')}; "
            f"summary={record.get('summary', '')}; action_items={record.get('action_items', [])}"
        )

    tracker = memory.get("_action_item_tracker", [])
    if tracker:
        context_lines.append("\nAction item tracker (across all meetings):")
        for entry in tracker:
            context_lines.append(f"- [{entry['owner']}] {entry['item']} ({entry['status']}) — {entry['meeting_topic']}")

    context = "\n".join(context_lines)

    prompt = f"""You are {AGENT_NAME}, an assistant with knowledge of the team's recent meetings.
Use ONLY the context below to answer. If the answer truly isn't in the context, say so plainly.
Never introduce a person's name that does not appear verbatim in the context below —
if you're unsure who said something, refer to them by their role or the attendee name
given, not a name you're inferring.

Context:
{context}

Question: {question}

Answer in 1-3 concise sentences."""
    return ask_llm(prompt)


# --------------------------------------------------------------------------
# ROI / impact counter — pure arithmetic over memory, no LLM call needed.
# e.g. "3 meetings processed, 4 action items extracted, ~45 min saved."
# --------------------------------------------------------------------------
def print_roi_summary(memory: dict) -> dict:
    current_ids = {m["id"] for m in meetings}
    meeting_records = {k: v for k, v in memory.items() if k in current_ids}
    meetings_processed = len(meeting_records)
    action_items_extracted = sum(len(r.get("action_items", [])) for r in meeting_records.values())
    followups_sent = sum(1 for r in meeting_records.values() if r.get("followup_sent_at"))
    minutes_saved = meetings_processed * MINUTES_SAVED_PER_MEETING

    print("\n=== 📊 Impact so far ===")
    print(f"  {meetings_processed} meetings processed")
    print(f"  {action_items_extracted} action items extracted")
    print(f"  {followups_sent} follow-ups sent")
    print(f"  ~{minutes_saved} min saved (est. {MINUTES_SAVED_PER_MEETING} min/meeting on notes + follow-up)")

    return {
        "meetings_processed": meetings_processed,
        "action_items_extracted": action_items_extracted,
        "followups_sent": followups_sent,
        "minutes_saved": minutes_saved,
    }


# --------------------------------------------------------------------------
# Daily digest — one Slack message summarizing everything that happened
# today, reusing the same memory + Slack plumbing as everything else.
# --------------------------------------------------------------------------
def send_daily_digest(memory: dict):
    today = datetime.now().strftime("%Y-%m-%d")
    todays_lines = []

    for meeting_id, record in memory.items():
        if meeting_id.startswith("_"):
            continue  # skip non-meeting entries like _action_item_tracker
        match = next((m for m in meetings if m["id"] == meeting_id), None)
        name = match["attendee_name"] if match else meeting_id
        topic = match["topic"] if match else record.get("status", "")

        touched_today = any(
            str(record.get(field, "")).startswith(today)
            for field in ("last_run", "summary_generated_at", "followup_sent_at")
        )
        if not touched_today:
            continue

        if record.get("status") == "scheduled":
            todays_lines.append(f"Scheduled: *{name}* — _{topic}_")
        elif record.get("status") == "summarized":
            n_items = len(record.get("action_items", []))
            todays_lines.append(f"Summarized: *{name}* — _{topic}_ ({n_items} action items)")
        elif record.get("status") == "followed_up":
            tag = " (rescued)" if record.get("followup_rescued") else ""
            todays_lines.append(f"Followed up: *{name}* — _{topic}_{tag}")

    if not todays_lines:
        digest_text = f"*{AGENT_NAME} — Daily Digest ({today})*\nNo meeting activity today."
    else:
        digest_text = f"*{AGENT_NAME} — Daily Digest ({today})*\n" + "\n".join(todays_lines)

    slack_notify(digest_text)
    print("\n=== 📨 Daily digest sent to Slack ===")
    print(digest_text)


# --- Main loop ---
def run_pipeline():
    memory = load_memory()

    for meeting in meetings:
        record = memory.get(meeting["id"], {})
        # Use whatever status memory already has for this meeting (if any) instead
        # of always trusting the hardcoded seed status — this is what stops the
        # agent from re-scheduling/re-summarizing/re-sending on every re-run.
        effective_status = record.get("status", meeting["status"])

        print(f"\n=== {meeting['attendee_name']} ({meeting['company']}) — {meeting['topic']} ===")

        if effective_status == "upcoming":
            print("🗓️  [Scheduler Agent] — proposing time + agenda...")
            plan = scheduler_agent(meeting)
            print("  →", plan)
            record.update({"status": "scheduled", "agenda": plan.get("agenda", [])})

        elif effective_status == "needs_summary":
            print("📝 [Summarizer Agent] — processing transcript...")
            summary_data = summarizer_agent(meeting)
            print("  →", summary_data)
            record.update({
                "status": "summarized",
                "summary": summary_data.get("summary", ""),
                "action_items": summary_data.get("action_items", []),
                "summary_generated_at": datetime.now().isoformat(),
            })

            print("📓 [Notes Agent] — posting meeting notes to Slack (Notion is down on their end)...")
            post_meeting_notes_to_slack(meeting, summary_data)

            update_action_tracker(memory, meeting, summary_data.get("action_items", []))

        elif effective_status == "needs_followup":
            print("✍️  [Writer Agent] — drafting + sending follow-up...")
            # In a real run this summary would already be in memory from a prior pass.
            summary_data = {
                "summary": record.get("summary", (
                    "The team confirmed a win on the enterprise workflow automation tender "
                    "submitted last month, with onboarding conversations starting next week. "
                    "The next step is preparing onboarding materials and assigning an internal "
                    "point of contact so the new account gets a smooth handoff into delivery."
                )),
                "action_items": record.get("action_items", [
                    "Priya: prepare onboarding materials for the tender client",
                    "Rohan: assign an internal point of contact for the new account",
                ]),
            }
            email_content = writer_agent(meeting, summary_data)
            print("  →", email_content)
            record["followup_sent_at"] = datetime.now().isoformat()
            record["status"] = "followed_up"
            update_action_tracker(memory, meeting, summary_data.get("action_items", []))

        else:
            print(f"  ⏭️  Already processed (status: {effective_status}) — skipping to avoid duplicates")

        memory[meeting["id"]] = record
        save_memory(memory)

    # Run the flagship demo feature after the main pass
    stale_followup_rescue(memory)
    save_memory(memory)

    # Impact counter + tracker + daily digest — cheap, big pitch payoff
    print_roi_summary(memory)
    print_action_tracker(memory)
    send_daily_digest(memory)
    save_memory(memory)

    print(f"\nDone. {AGENT_NAME} saved memory to", MEMORY_FILE)
    return memory


if __name__ == "__main__":
    run_pipeline()

    # Quick live-demo moment: ask the agent a question about your meetings.
    # Press Enter with no question to skip this entirely.
    print(f"\n=== 💬 Ask {AGENT_NAME} about your meetings (press Enter to skip) ===")
    try:
        question = input("Your question: ").strip()
        if question:
            print("\n" + chat_with_agent(question, load_memory()))
    except EOFError:
        pass
