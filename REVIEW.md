# Design and code review record — 2026-11-05

Reviewer: Codex, through code inspection, executable acceptance tests and browser checks. This is an AI-assisted development review, not evidence that group members have already performed peer review. Members should record their own review and contributions separately.

## Reviewed and addressed

| Finding | Decision/change | Verification |
|---|---|---|
| Quadrant-first priority could miss today's lower-importance deadline even when both tasks fit | Earliest deadline first, importance only for same-date ties; keep quadrants as an overview | `test_deadline_prevents_old_priority_conflict`, `test_equal_deadline_uses_importance` |
| Distant goals were treated as timed assignments | Explicit deadline/goal types; goals require no due date or total estimate and are optional spare-time reminders | `test_goals_are_reminders_and_start_later`, browser goal creation |
| Work progress reduced estimates without accounting for consumed daily capacity | Store dated actual-work logs; subtract actual work from total daily budget | `test_partial_work_does_not_create_capacity`, `test_allocation_invariants` |
| Finishing earlier than an estimate had no explicit completion action | Explicit completion checkbox; zero remaining estimate, retain completion record, recompute future allocation | Both `test_early_finish_*` cases, browser completion |
| A single generic unallocated warning blurred different problems | Separate overdue, deadline-capacity and outside-week reasons; add on-page explanation | `test_missing_reasons_are_distinct`, HTML/browser checks |
| Quarter-hour detail conflicted with the requested half-hour minimum | Half-hour server validation and HTML inputs; v1 migration with preserved original backup | `test_half_hour_and_invalid_numbers`, `test_legacy_migration_and_original_backup` |
| Invalid saved JSON could crash startup | Validate loaded schema and enter read-only recovery without overwriting original | Corruption and read-only tests |
| Date parsing accepted basic ISO dates while allocation compared date strings | Normalize parsed dates to YYYY-MM-DD before comparing or saving | `test_dates_normalized_for_sorting` |
| Scheduling, storage and web rendering were all in one source file | Separate planner.py, storage.py and main.py by responsibility | Pure scheduling tests and isolated persistence tests |

## Deliberate boundaries

- JSON remains sufficient for one local user. No database or cloud migration is required for these features.
- Seven-day daily totals, 30-minute units. Exact start/end times and automatic elapsed-time tracking are not implemented.
- Deadline-first greedy allocation is explainable and fixes the reproduced conflict, but is not a global optimizer.
- Optional goal suggestions do not reserve time and do not promise goal completion dates.
- Completion is recorded against the current Hong Kong date; backdated editing and undo are not implemented.

## Outstanding group work

The team should review the requirements, verify the trade-offs, record each member's actual contribution, cite external resources used, and prepare the presentation and individual reports. The documents here provide development evidence; they do not establish a final assessment grade.

## v3 follow-up review

- Replaced the stacked quadrant cards with a responsive SVG task map. Used code-native SVG/CSS rather than raster image generation so labels, links and zoom remain accessible and maintainable.
- Clock availability and work records are now explicit. The old daily-only record cannot establish precise historical clock times; migration uses an evening-window approximation and documents that limit.
- New `timetable.py` compares accepted and candidate half-hour cells. A pending proposal is saved, and confirmation/decline resolves the entire linked change together. Stale revisions and cross-date confirmation are rejected.
- Existing edits cannot accidentally approve a pending movement proposal: the handler requires confirmation or keep-original first.
- Android packages exact copies of production Python/CSS files, not a second implementation of the scheduling rules. No private ledger, browser token or existing demo JSON is included.
- Further real-device review remains necessary for Android launch, WebView controls, keyboard/insets, back navigation and offline persistence.

## v4 follow-up review

Fixed appointments and protected private time are expanded before determining free cells, not treated as priority-map tasks. Explicit urgent borrowing cannot override fixed appointments. Calendar movement is a direct user instruction: it preserves duration, leaves the source gap and saves a valid pinned target rather than immediately rerunning allocation. Recurring movement uses one-occurrence overrides so other dates are preserved.

Browser inspection found and repaired the SVGAnimatedString link issue and an embedded-viewport popup boundary issue. Real pointer dragging and conflict rejection were verified. New files `events.py` and `app.js` keep recurrence/domain rules and UI interaction separate. No external UI dependency was introduced. Android source/assets must be synchronized in a future packaging round; the existing APK remains intentionally unchanged.

## v5 review

Import validates a separate in-memory candidate before touching current state, requires CSRF and replacement confirmation, and creates a uniquely named backup before atomic write. JSON is never executed. Localization preserves user-authored text and input values, and does not rely on a remote translation service. Holiday rules use a fixed published dataset with an explicit supported-year notice rather than predicting future statutory changes. WebView file IO uses scoped system document pickers; export accepts only the app's own loopback endpoint. Native compilation passed; device picker/cancellation behavior is not yet verified. APK unchanged by explicit request.

## v5.1 review

The former blanket pending-proposal guard prevented ordinary records; it was removed in favor of rebuilding proposals from each successfully saved accepted state. The stable plan reserves valid existing slots before allocating deficits, while manual pins remain separate from these temporary reservations. Stale proposal IDs still reject approval. Fixed-event immobility is checked server-side, not merely hidden in the UI. Cancellation keys reference the original occurrence start so both overnight segments disappear. Series edits retain cancelled exceptions. Personal/demo state was not used for mutation tests. APK unchanged.
