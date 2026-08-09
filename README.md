# Swytchcode-Aurora-Himani-Hassija

### An AI Meeting and Follow up Assistant, built on Swytchcode

Aurora turns every meeting into a completed loop. It schedules the call, listens to what was said, extracts what needs to happen next, follows up automatically, and quietly rescues any thread that starts to go cold, all with its reasoning visible at every step.

---

## The Problem

Meetings generate momentum. Most of that momentum dies in someone's notes app.

Agendas get skipped. Summaries never get written. Action items live in someone's memory instead of a system. Follow up emails get sent late, or not at all. By the time anyone notices a deal or a project has gone quiet, days or weeks have already been lost.

Aurora exists to close that gap automatically.

---

## What Aurora Does

Aurora manages the full lifecycle of a meeting from a single, continuously running agent pipeline:

* Proposes a time and a focused agenda before the meeting happens
* Reads a transcript and produces a clear, human sounding summary
* Extracts concrete action items, with an owner attached wherever possible
* Drafts and sends a personalized follow up email, grounded in what was actually discussed
* Detects meetings where a follow up went unanswered and automatically initiates a recovery sequence
* Remembers everything it has already done, so it never repeats itself or spams the same person twice
* Answers plain English questions about any past meeting, on demand, through a chat interface

None of this is templated. Every summary, every email, and every decision is generated fresh by reasoning over the specific context of that meeting.

---

## How It Works: A Real Multi Agent Pipeline

Rather than one prompt trying to do everything, Aurora is split into three specialized agents that hand work off to each other, the same way a real team would:

**The Scheduler** looks at a meeting's context and proposes a time slot and a focused, relevant agenda.

**The Summarizer** reads a transcript and produces a tight summary plus a structured list of action items, attributed to whoever owns them.

**The Writer** takes that summary and drafts a follow up email that references the actual conversation, not a generic template. When a rescue is triggered, the Writer shifts tone automatically, from a warm first touch to a more direct re engagement message.

Every stage of this pipeline is visible in the dashboard as it happens, so you can watch Aurora think, not just see the final result.

---

## The Signature Feature: Stale Follow Up Rescue

This is the part of Aurora that goes beyond automation into genuine judgment.

Aurora continuously checks its own memory for meetings where a follow up was sent but no response ever came back. When it finds one, it does not just wait quietly. It flags the meeting as at risk, regenerates a fresh, more direct follow up using everything it already knows about that conversation, sends it, and escalates a quiet notification to the responsible human as a safety net.

The effect is a system that does not just execute tasks. It notices when something is falling through the cracks and acts on its own initiative to fix it.

---

## Persistent Memory

Every decision Aurora makes is written to a durable memory store. That memory is not just a log. It actively shapes future behavior.

Run Aurora twice on the same set of meetings and it will not repeat itself. It knows what it already sent, when it sent it, and whether it is still waiting on a response. This is what allows the Stale Follow Up Rescue to work at all, and it is what makes Aurora feel like an ongoing presence rather than a one shot script.

---

## Ask Aurora

A built in chat interface lets anyone ask natural questions about what Aurora has done, and get a grounded answer pulled directly from its own memory.

Examples:

* What happened on the call with Priya?
* Which action items are still outstanding?
* Did the tender win follow up ever get answered?

No digging through inboxes or calendars required.

---

## Live Dashboard

Aurora ships with a real time dashboard, not a terminal log. It shows:

* Meetings and their current status, color coded at a glance
* Action items with owners, tracked across every meeting
* A daily digest of everything Aurora touched today
* Running impact metrics: meetings processed, action items extracted, follow ups sent, and estimated time saved
* The chat interface, live, in the same view

While a pipeline run is in progress, the interface shows exactly what Aurora is doing in that moment, from analyzing to drafting to syncing, rather than a generic loading spinner.

---

## Integrations

All execution runs through Swytchcode, which handles authentication, retries, and idempotency across every connected service:

* Google Calendar, for real scheduling on a dedicated calendar
* Resend, for real, deliverable follow up emails
* Notion, for structured meeting records
* Slack, kept as a bonus escalation channel for the rescue flow
* Gmail and Zoom, as planned extensions of the pipeline

---

## Tech Stack

* Python for the core agent pipeline
* Groq running Llama 3.3 70B for fast, free, low latency reasoning
* Flask serving a lightweight dashboard API
* Vanilla HTML, CSS, and JavaScript for the frontend, no framework overhead
* JSON backed persistent memory
* Swytchcode as the execution and integration layer for every external action

---

## Why This Matters

Most automation tools execute a fixed sequence of steps. Aurora reasons about what to do, remembers what it already did, and notices when its own previous actions did not land. That combination, visible reasoning, persistent memory, and self initiated recovery, is what separates an agent from a script.

---

## Getting Started

1. Clone the repository and install dependencies from requirements.txt
2. Set your GROQ_API_KEY environment variable
3. Connect Google Calendar, Resend, and Slack through the Swytchcode CLI
4. Run app.py and open the dashboard in your browser
5. Click Run pipeline and watch Aurora work

---

## Built By

Himani Hassija, for the Swytchcode Hackathon, Track 2: AI Meeting and Follow up Assistant.
