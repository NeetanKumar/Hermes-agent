# Use Cases: With More Work

Directions Hermes could grow into, beyond the current Mail/Calendar/Reminders
scope. Each of these needs real architecture work (see notes) — they're not
free extensions of what exists today.

- **Sales/recruiting ops** — read inbound leads or candidate replies,
  auto-classify (interested/rejected/needs follow-up), draft responses for
  review. Needs a classification pipeline beyond ad-hoc chat queries.
- **Customer support triage** — same read-classify-draft pattern applied to
  a shared support inbox instead of a personal one.
- **EA-as-a-service tool** — package this for non-technical users (execs,
  small business owners) as a "talk to your inbox" desktop app. The
  installable pip package is a start; would need a real GUI and
  onboarding flow.
- **Compliance/audit trail** — log every action taken (what was read, what
  was sent) for regulated industries where an AI touching email needs an
  audit log. Currently nothing is logged beyond the terminal session.
- **Multi-app orchestration** — extend past Mail/Calendar/Reminders to
  Slack, Notion, Salesforce, etc., turning this into a general "AI chief
  of staff" for a desktop. Each new app needs its own automation module
  (see `hermes/tools/`) and possibly a different mechanism (Accessibility
  API or vision-based control) where AppleScript support doesn't exist.

The most defensible next step from the current build is the **job search /
pipeline tracker** in [USE_CASES.md](USE_CASES.md) — it's narrow, the
AppleScript-only approach already handles it well, and it doesn't require
expanding scope.
