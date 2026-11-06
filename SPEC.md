# Planwise specification v2

## Purpose and scope

Help university students finish tasks before their deadlines and begin work early enough to avoid last-minute pressure. Important long-term goals remain visible without automatically consuming the time needed for assignments.

Local, single-user Python + HTML/CSS application. No AI feature, JavaScript, external API, account, or calendar integration. All time estimates, capacity, work logs and allocations use 30-minute units. Dates follow Asia/Hong_Kong.

## Acceptance requirements

| ID | Requirement | Acceptance evidence |
|---|---|---|
| R1 | Separate deadline tasks from long-term goals. Deadline tasks require a due date and at least 30 minutes of remaining work. Goals need neither. | `test_half_hour_and_invalid_numbers`, browser goal creation |
| R2 | Quadrant importance is user-selected. A deadline within 3 days, including today and overdue dates, is urgent. Goals are non-urgent. | `test_urgent_boundary_and_goal` |
| R3 | Allocate deadline tasks by earliest deadline first; importance breaks same-date ties. Start as early as capacity and the optional start date permit. | `test_deadline_prevents_old_priority_conflict`, `test_equal_deadline_uses_importance`, `test_start_date_respected` |
| R4 | Produce a rolling 7-day plan. Split tasks across dates. Never allocate after a deadline or before a start date. Today counts as a possible work day. | `test_today_allowed_overdue_excluded`, `test_allocation_invariants` |
| R5 | Distinguish overdue work, insufficient capacity before a deadline inside the window, and work not scheduled within this week when its deadline is beyond the window. | `test_missing_reasons_are_distinct` |
| R6 | Daily budget includes work already logged. Remaining capacity is max(0, budget minus actual work logged today). Scheduled work cannot exceed it. | `test_partial_work_does_not_create_capacity`, `test_allocation_invariants` |
| R7 | Users can explicitly finish a task early. Record actual work, set the task complete, release all unneeded estimates, then recompute the remaining plan. Keep completed tasks visible in history. | `test_early_finish_moves_next_task_and_preserves_free_time`, `test_early_finish_without_next_task_leaves_free_time`, browser completion |
| R8 | Partial progress reduces remaining estimates for deadline tasks. A goal remains active until explicitly marked complete. Repeated completion submissions are rejected. | `test_goal_stays_active_until_explicitly_completed`, `test_partial_work_does_not_create_capacity` |
| R9 | Goals never occupy automatic schedule slots. After their optional start date, show an optional half-hour suggestion only when a day has spare capacity. That capacity remains free. | `test_goals_are_reminders_and_start_later`, browser spare-time reminder |
| R10 | Validate half-hour units on both HTML controls and the Python server; daily budgets cannot exceed 24 h. Actual work beyond the planned budget is recorded, with free time clamped to zero. | `test_half_hour_and_invalid_numbers`, `test_capacity_validation_and_spent_over_budget` |
| R11 | Persist tasks, daily capacity, completion status, and work logs in local JSON. Use a temporary file and replacement to avoid truncating the original on failed writes. | `test_save_reload_and_restart_equivalence`, `test_failed_atomic_write_keeps_original` |
| R12 | Migrate v1 work estimates upward and capacity downward to half-hour units. Keep the original untouched during reads and back it up on the first v2 save. | `test_legacy_migration_and_original_backup` |
| R13 | Unreadable or invalid saved data must not be silently replaced with sample data. Show a read-only page and block writes until repaired or moved aside. | `test_corrupt_json_and_schema_preserve_original`, `test_corrupt_file_starts_read_only_and_blocks_writes` |
| R14 | Display scheduling reasons, completed tasks and recent work logs; escape user text in HTML. | `test_page_explains_rules_and_escapes_input`, browser checks |

## Clarifying examples

1. **Deadline beats importance:** A is important, takes 1 h and is due in 5 days. B is less important, takes 1 h and is due today. With 1 h available today and tomorrow, B gets today and A gets tomorrow. The previous quadrant-first strategy left B unallocated.
2. **Early finish with follow-up:** Today has 2 h. A was estimated at 2 h and B at 1 h. A finishes after 0.5 h. Today now has 0.5 h actual work + 1 h B + 0.5 h free. If B were originally scheduled tomorrow, it moves forward.
3. **Early finish without follow-up:** A was estimated at 2 h and finishes in 0.5 h. With no other deadlines, the remaining 1.5 h stays free. A goal may be suggested, but is not scheduled automatically.
4. **Overdue:** An unfinished assignment was due yesterday. It is flagged overdue and not assigned past its deadline. The user may revise the deadline or complete it manually.
5. **Capacity shortage:** An assignment needs 4 h by tomorrow, but only 2 h remain across today and tomorrow. The unallocated 2 h is flagged as a deadline-capacity issue. Existing earlier-deadline work may also account for the shortage.
6. **Outside this week:** An assignment is due in 20 days and has 3 h left outside the seven-day plan. The app says it is not scheduled this week; it does not claim those 3 h will be late.
7. **Holiday goal:** Japanese N1 has a start date two weeks away. It remains in the important/non-urgent quadrant, without suggestions before that date. No estimated total study hours are required.

## Data and module responsibilities

- `planner.py`: classification, allocation, validation and progress updates; accepts an explicit date for repeatable tests.
- `storage.py`: v2 validation, v1 migration, sample data, local atomic JSON writes.
- `main.py`: HTTP forms, HTML rendering, local server, Hong Kong date and read-only recovery.
- `style.css`: visual layout and responsive rules.
- JSON: `version`, `tasks`, `capacity`, `work_log`. Task types: `deadline` or `goal`. Completion is an explicit status, not inferred from goal estimates.

## Boundaries

Daily totals, not exact clock appointments. A due date is usable through that day; no intra-day deadline or time-of-day scheduling. No automatic detection of elapsed time: users log actual effort in half-hour units (round up when needed). Changing an estimate is not evidence of time spent. Long-term goals with a real exam or booking deadline can be converted to deadline tasks and given a current, bounded work estimate. Earliest-deadline-first is an explainable heuristic; it does not guarantee maximum weighted completions or a globally optimal schedule. The seven-day window cannot establish feasibility beyond that window. Deleting a task does not delete its actual work from the daily budget.

# v3 interface and clock-schedule amendment — 2026-11-05

This section supersedes the v2 daily-total UI, automatic movement after progress, and the no-clock boundary above. `planner.schedule` remains a daily-total reference used in baseline tests; the live interface now uses `timetable.py`.

- **Task map:** one responsive coordinate diagram, with hand-drawn axes and soft paper colors. Dots represent individual tasks. Desktop shows short titles when there are at most 12 active tasks; denser maps and screens <=600 px hide labels. Links retain full accessible names and open details. Positions within a category spread dots apart; they are not numerical importance or urgency scores.
- **Zoom:** server-rendered controls support 75%–200%, in 25% increments; the graph scrolls internally when enlarged. No JavaScript or external graphics dependency is added.
- **Separate schedule tab:** seven-day clock calendar with half-hour rows, day view, and task details. The visible clock range begins an hour before the earliest availability/actual record to avoid an empty morning when all work is in the evening. Weekly columns scroll horizontally on narrow screens; day view fits one screen width.
- **Availability:** at most two non-overlapping half-hour-aligned windows per date. Empty date means no availability. Old daily budgets are converted into a default evening window (18:00 where possible); users can change it. Existing v2 actual totals have no clock information, so they are represented at the beginning of availability as a migration approximation, not measured timestamps.
- **Actual effort:** new records include a start time and end time. The same clock interval cannot be logged twice. Effort outside availability is recorded, but only actual overlap consumes available clock slots. Recording past work is allowed; scheduling new work earlier than the next half-hour boundary today is not.
- **Proposed movement:** completion and actual effort are saved immediately. Existing remaining arrangements stay accepted. A new deadline-first candidate is compared in half-hour cells; unchanged cells stay solid, old-only cells show a translucent origin, and new-only cells show a translucent destination. These are alternative arrangements, not simultaneous bookings.
- **Confirmation:** the entire linked proposal is accepted atomically. Confirm uses the candidate as the accepted calendar and removes the ghosts. Keep-original clears the proposal and retains original positions; freed time remains free. This avoids accepting one move which conflicts with another linked move.
- **Pending edits:** confirm or keep the existing proposal before making other task/window edits. A revision token rejects stale confirmations. A proposal persists across restart and expires when the planning date changes.
- **Persistence:** v2 JSON gains optional `availability`, `calendar`, `calendar_day` and `proposal` fields. Old v1/v2 data remains readable; originals are retained during reads. Actual task/work data is never packaged in the Android app.
- **Android preview:** native WebView shell embeds the same Python server/runtime, binds only a random loopback port and saves JSON under app-private storage. It does not require a desktop host or public service. This adds Java/Gradle solely for the Android shell/build; scheduling and storage logic remain Python.

## New acceptance evidence

`test_timetable.py` adds 12 checks: clock splitting across windows; original positions retained pending approval; confirmation makes destination solid; decline keeps original/free time; stale revision/date rejected; pending state survives save/load; new-day invalidation; no-follow-up free time; window/clock validation; duplicate actual/midnight validation; current-time cutoff and goal exclusion; map/preview markup.

# v4 commitments, privacy and direct interaction — 2026-11-05

This amendment supersedes v3's two daily availability windows as the normal user interface, no-JavaScript statement, side panels and incomplete clock range.

## Plan the gaps after real life

The default `time_model=free` exposes the complete 00:00–24:00 date. There is **no assumed 08:00–16:00 work block** and no assumed sleep pattern. Users first enter their own fixed commitments and private periods in a separate Events tab. Unentered time is interpreted as free. The old custom-window allocator remains only for previously explicit custom data and reference tests; v2 data without a model migrates to the new free-time model.

For every half-hour cell, ordinary availability is the full date minus fixed appointments, protected private periods, already logged work and earlier-than-now cells today. DDL tasks are assigned into those gaps. Classes and shift work are fixed appointments and never enter the importance/urgency map.

An explicit `borrow_private` option defaults to false. When enabled, an unfinished deadline task due within three days may use private cells **only after ordinary eligible gaps are exhausted**. Fixed commitments remain unavailable under every policy. Borrowed task blocks are labeled in the calendar. Long-term goals never borrow or automatically schedule.

## Repeating events

`events` records include title, fixed/private category, first date, start/end minutes, repeat rule, optional inclusive last date, weekly weekday choices and per-occurrence overrides.

- None, daily, weekly (one or more weekdays), monthly on the same date.
- A nonexistent monthly date is skipped; it is not shifted to a different date.
- An end time earlier than its start means the next day. Overnight work/private time is split at midnight for display and blocking.
- Editing an event series changes the complete series and clears previous single-occurrence overrides; the form states this explicitly.
- Dragging a recurring event changes only that occurrence. Original recurrence dates are retained as override keys.
- The allocator treats overlapping fixed/private events as a union of occupied time; it does not treat two overlaps as twice the elapsed time.

## Manual task movement

A drag preserves a block's duration and changes its date/start only, snapping to half-hour cells. It does not squeeze or recalculate the rest of the accepted calendar. Its freed cells stay empty immediately after the move. The target is checked by Python against availability, fixed/private/actual-time conflicts, other tasks, task start/deadline, planning horizon and current time. An outdated source block is rejected.

Example: a previous task occupies 09:00–10:00, a 1 h task occupies 10:00–11:00, and the day is usable until 12:00. Moving the 1 h task to 11:00–12:00 keeps the preceding task unchanged and leaves 10:00–11:00 free for a rest. No estimate is changed and no new task fills that hour merely because of the drag.

Manual target positions are saved as `pins` and remain reserved during subsequent automatic replanning while valid. Other unreserved gaps may be used during a later explicit replan. To protect a rest gap itself across all future replanning, enter it as private time. If a new fixed commitment or disabled private borrowing invalidates a pin, the conflicting reservation is pruned before replanning.

Manual task time can also be changed using a form inside its bubble. Overnight recurring segments are edited through the event form rather than partially dragging just one clipped day segment.

## Anchored bubbles and native browser interaction

Map dots, task time blocks and event blocks open an interactive nonmodal bubble at the clicked anchor. It grows from that anchor, stays inside the viewport, has an explicit close control, supports Escape and restores focus. Full forms scroll inside the bubble. Background content remains visible. Reduced-motion preferences are respected. Mobile widths hide point labels and clamp the same bubble to screen margins.

A small local `app.js` handles bubble fetching/animation, pointer drag previews, snapping and scroll position. All validation, recurrence, allocation, privacy rules and persistence remain in Python. CSP permits only same-origin scripts; no third-party JavaScript or UI framework is used. Without JavaScript the detail form is shown as a centered fallback bubble.

## Compatibility and packaging

New optional JSON fields: `events`, `borrow_private`, `time_model`, `pins`, `calendar_model`. A `.pre-events.bak` backup is kept before the first save of pre-v4 input. Existing tasks, completion and actual-work records remain. The Android APK stays at 0.3.0-preview by explicit user instruction; these v4 interactions are currently web-only.

## v5 amendment — 2026-11-06

- Long-term goals have a reference effort target (`target_minutes`, optional in older data; default 600). Actual logged minutes for the goal fill the map dot from bottom to top, capped at 100%. Reaching the target does not complete or automatically schedule the goal. Users can change the reference in the edit bubble; progress records are preserved.
- Recurrence adds `workdays` and `holidays`. The default working weekdays are Monday–Friday, editable on page 3. Hong Kong general holidays (including Sundays) are excluded; days off are the complement. These labels do not reserve time without an event. Offline holiday data covers 2026–2027, with dates from government announcements (including substitutes). Outside these years only selected weekdays / Sundays are used and the UI warns.
- Holiday names and red dates appear in calendar headers. User-entered event hours remain authoritative.
- Phones (≤600 CSS px) default to a full-width single day. Explicit week overview fits all seven dates with compact blocks; tapping a date opens the readable day. All views retain 00:00–24:00 and half-hour drag snapping.
- Page 3 (“Life & settings”) stores Traditional Chinese, Simplified Chinese or English. UI translations are local files; user titles, categories and form values stay unchanged.
- Page 3 exports the whole state as `planwise-backup`, backup version 1 JSON. Imports accept this envelope or previous raw state JSON. Import replaces rather than merges data after schema validation and explicit replacement confirmation. Existing data gets a timestamped `.before-import-*.bak` before atomic save; invalid imports leave the state and file unchanged. Maximum selected file size 2 MB; no upload to external servers.
- Android source supports document pickers for JSON import and export using the same local API. Only the owned loopback `/export` URL is accepted by its download handler. No APK is built or updated in this iteration; native picker behavior still needs device verification.

## v5.1 amendment — original schedule first

Fixed events cannot be dragged or moved individually, enforced in both markup and the Python mutation boundary. Their series can still be edited explicitly. “Remove only this occurrence” records a cancellation keyed to the original start date; overnight segments are removed together. Other dates remain, and editing the series preserves previously cancelled dates. Private-time occurrences retain their manual move option.

Pending move suggestions never block logging effort, task edits, event changes, personal-time settings or manual task moves. On each valid change, the accepted calendar is sanitized against the new facts, existing valid slots are reserved first, and only unallocated work is fitted into gaps. A separate candidate can suggest moving existing work. It applies only after explicit approval. New changes replace any older proposal revision, so stale approvals cannot overwrite newer records. Original calendar blocks remain solid and interactive; candidate positions remain translucent. Suggestions are collapsed by default. Logging effort keeps the current page rather than redirecting to the schedule.
