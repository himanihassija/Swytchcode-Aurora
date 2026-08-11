const STATUS_LABEL = {
  upcoming: "Upcoming",
  scheduled: "Scheduled",
  summarized: "Summarized",
  followed_up: "Followed up",
  needs_summary: "Needs summary",
  needs_followup: "Needs follow-up",
};

const PIPELINE_STEPS = [
  "Analyzing meetings…",
  "Deciding next actions…",
  "Drafting follow-ups…",
  "Syncing with Calendar & Resend…",
  "Wrapping up…",
];

function statusClass(status) {
  if (status === "needs_summary") return "status-upcoming";
  if (status === "needs_followup") return "status-summarized";
  return "status-" + status;
}

function statusLabel(status) {
  return STATUS_LABEL[status] || status;
}

function timeAgo(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const diffMin = Math.round((Date.now() - d.getTime()) / 60000);
  if (diffMin < 1) return "just now";
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.round(diffHr / 24)}d ago`;
}

function el(tag, attrs = {}, children = []) {
  const node = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v;
    else if (k === "text") node.textContent = v;
    else if (k === "html") node.innerHTML = v;
    else node.setAttribute(k, v);
  }
  for (const c of [].concat(children)) if (c) node.appendChild(c);
  return node;
}

function showToast(msg) {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.classList.add("visible");
  setTimeout(() => t.classList.remove("visible"), 2600);
}

function renderMeetings(meetings) {
  const list = document.getElementById("meetingList");
  document.getElementById("meetingCount").textContent = `${meetings.length} total`;
  list.innerHTML = "";

  if (!meetings.length) {
    list.appendChild(el("p", { class: "empty-note", text: "No meetings yet." }));
    return;
  }

  meetings.forEach((m) => {
    const card = el("div", { class: "meeting-card", "data-id": m.id });

    const top = el("div", { class: "meeting-card-top" }, [
      el("div", { class: "meeting-who" }, [
        el("div", { class: "meeting-name", text: m.attendee_name }),
        el("div", { class: "meeting-meta", text: m.company }),
      ]),
      el("span", { class: `status-pill ${statusClass(m.status)}` }, [
        el("span", { class: "status-dot" }),
        el("span", { text: statusLabel(m.status) }),
      ]),
    ]);

    const topic = el("div", { class: "meeting-topic", text: m.topic });

    const detail = el("div", { class: "meeting-detail" });
    if (m.summary) {
      detail.appendChild(el("h4", { text: "Summary" }));
      detail.appendChild(el("p", { text: m.summary }));
    } else {
      detail.appendChild(el("p", { class: "empty-note", text: "No summary yet — context: " + m.context }));
    }

    if (m.action_items && m.action_items.length) {
      detail.appendChild(el("h4", { text: "Action items" }));
      const ul = el("ul", { class: "action-items" });
      m.action_items.forEach((item) => {
        let owner = "—", text = item;
        const match = item.match(/^([A-Za-z][A-Za-z\s]{0,24}):\s*(.*)$/);
        if (match) { owner = match[1].trim(); text = match[2].trim(); }
        ul.appendChild(el("li", {}, [
          el("span", { class: "owner-tag", text: owner }),
          el("span", { text }),
        ]));
      });
      detail.appendChild(ul);
    }

    if (m.followup_sent_at) {
      const tag = m.followup_rescued ? " (rescued)" : "";
      detail.appendChild(el("p", {
        class: "text-muted",
        text: `Follow-up sent ${timeAgo(m.followup_sent_at)}${tag}`,
      }));
    }

    card.appendChild(top);
    card.appendChild(topic);
    card.appendChild(detail);

    card.addEventListener("click", () => {
      const wasOpen = card.classList.contains("open");
      document.querySelectorAll(".meeting-card.open").forEach((c) => c.classList.remove("open"));
      if (!wasOpen) card.classList.add("open");
    });

    list.appendChild(card);
  });
}

function renderTracker(tracker) {
  const list = document.getElementById("trackerList");
  document.getElementById("trackerCount").textContent = tracker.length ? `${tracker.length} items` : "";
  list.innerHTML = "";

  if (!tracker.length) {
    list.appendChild(el("p", { class: "empty-note", text: "Nothing tracked yet." }));
    return;
  }

  tracker.forEach((entry) => {
    const row = el("div", { class: "tracker-item" }, [
      el("span", { class: `tracker-check ${entry.status === "done" ? "done" : ""}` }),
      el("div", { class: "tracker-text" }, [
        el("span", {}, [
          el("span", { class: "owner", text: entry.owner }),
          document.createTextNode(entry.item),
        ]),
        el("span", { class: "meeting-ref", text: entry.meeting_topic }),
      ]),
    ]);
    list.appendChild(row);
  });
}

function renderDigest(meetings) {
  const today = new Date().toISOString().slice(0, 10);
  const box = document.getElementById("digestLines");
  box.innerHTML = "";
  const lines = [];

  meetings.forEach((m) => {
    const touched = [m.summary_generated_at, m.followup_sent_at].some(
      (t) => t && t.startsWith(today)
    );
    if (!touched) return;
    if (m.status === "scheduled") lines.push(`Scheduled — ${m.attendee_name}: ${m.topic}`);
    else if (m.status === "summarized") lines.push(`Summarized — ${m.attendee_name}: ${m.topic} (${m.action_items.length} action items)`);
    else if (m.status === "followed_up") lines.push(`Followed up — ${m.attendee_name}: ${m.topic}${m.followup_rescued ? " (rescued)" : ""}`);
  });

  if (!lines.length) {
    box.appendChild(el("p", { class: "empty-note", text: "No activity yet today." }));
    return;
  }
  lines.forEach((l) => box.appendChild(el("div", { class: "digest-line", text: l })));
}

function renderKpis(roi) {
  document.getElementById("kpiMeetings").textContent = roi.meetings_processed;
  document.getElementById("kpiActions").textContent = roi.action_items_extracted;
  document.getElementById("kpiFollowups").textContent = roi.followups_sent;
  document.getElementById("kpiMinutes").innerHTML = `${roi.minutes_saved} <span class="unit">min</span>`;
}

async function loadState() {
  const res = await fetch("/api/state");
  const data = await res.json();
  renderMeetings(data.meetings);
  renderTracker(data.tracker);
  renderDigest(data.meetings);
  renderKpis(data.roi);
  document.getElementById("lastUpdated").textContent = "Updated " + timeAgo(data.generated_at);
  return data;
}

function setLoading(btn, loading) {
  btn.classList.toggle("loading", loading);
  btn.disabled = loading;
}

// Cycles the button's label through pipeline stages while a run is in flight,
// so it reads as "here's what it's doing" instead of a plain spinner.
function startStepCycler(btn) {
  const labelEl = btn.querySelector(".btn-label");
  const originalLabel = labelEl.textContent;
  let i = 0;
  labelEl.textContent = PIPELINE_STEPS[0];
  const interval = setInterval(() => {
    i = (i + 1) % PIPELINE_STEPS.length;
    labelEl.textContent = PIPELINE_STEPS[i];
  }, 900);
  return () => {
    clearInterval(interval);
    labelEl.textContent = originalLabel;
  };
}

document.getElementById("runPipelineBtn").addEventListener("click", async () => {
  const btn = document.getElementById("runPipelineBtn");
  setLoading(btn, true);
  const stopCycler = startStepCycler(btn);
  try {
    const res = await fetch("/api/run-pipeline", { method: "POST" });
    const data = await res.json();
    renderMeetings(data.meetings);
    renderTracker(data.tracker);
    renderDigest(data.meetings);
    renderKpis(data.roi);
    document.getElementById("lastUpdated").textContent = "Updated " + timeAgo(data.generated_at);
    showToast("Pipeline run complete.");
  } catch (e) {
    showToast("Pipeline run failed — check the terminal.");
  } finally {
    stopCycler();
    setLoading(btn, false);
  }
});

function appendChatBubble(thread, role, text) {
  const initials = role === "user" ? "You" : "AI";
  const bubble = el("div", { class: `chat-bubble ${role}` }, [
    el("div", { class: "chat-avatar", text: initials }),
    el("div", { class: "chat-text", text }),
  ]);
  thread.appendChild(bubble);
  thread.classList.add("visible");
  thread.scrollTop = thread.scrollHeight;
}

document.getElementById("askBtn").addEventListener("click", async () => {
  const input = document.getElementById("askInput");
  const question = input.value.trim();
  if (!question) return;
  const btn = document.getElementById("askBtn");
  const thread = document.getElementById("askThread");

  appendChatBubble(thread, "user", question);
  input.value = "";
  setLoading(btn, true);

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question }),
    });
    const data = await res.json();
    appendChatBubble(thread, "aurora", data.answer || data.error || "No answer.");
  } catch (e) {
    appendChatBubble(thread, "aurora", "Something went wrong reaching Aurora.");
  } finally {
    setLoading(btn, false);
  }
});

// --- Schedule meeting modal ---
const scheduleBackdrop = document.getElementById("scheduleBackdrop");
const scheduleForm = document.getElementById("scheduleForm");

function openScheduleModal() {
  scheduleBackdrop.classList.add("visible");
  document.getElementById("schedName").focus();
}

function closeScheduleModal() {
  scheduleBackdrop.classList.remove("visible");
  scheduleForm.reset();
}

document.getElementById("newMeetingBtn").addEventListener("click", openScheduleModal);
document.getElementById("scheduleCloseBtn").addEventListener("click", closeScheduleModal);
document.getElementById("scheduleCancelBtn").addEventListener("click", closeScheduleModal);
scheduleBackdrop.addEventListener("click", (e) => {
  if (e.target === scheduleBackdrop) closeScheduleModal();
});

scheduleForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const btn = document.getElementById("scheduleSubmitBtn");
  setLoading(btn, true);

  const payload = {
    attendee_name: document.getElementById("schedName").value.trim(),
    attendee_email: document.getElementById("schedEmail").value.trim(),
    company: document.getElementById("schedCompany").value.trim(),
    topic: document.getElementById("schedTopic").value.trim(),
    context: document.getElementById("schedContext").value.trim(),
    date: document.getElementById("schedDate").value,
    time: document.getElementById("schedTime").value,
  };

  try {
    const res = await fetch("/api/schedule-meeting", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();
    if (!res.ok) {
      showToast(data.error || "Couldn't schedule that meeting.");
      return;
    }
    renderMeetings(data.meetings);
    renderTracker(data.tracker);
    renderDigest(data.meetings);
    renderKpis(data.roi);
    document.getElementById("lastUpdated").textContent = "Updated " + timeAgo(data.generated_at);
    showToast("Meeting scheduled — calendar invite + Slack note sent.");
    closeScheduleModal();
  } catch (err) {
    showToast("Something went wrong scheduling the meeting.");
  } finally {
    setLoading(btn, false);
  }
});

loadState();
