# Verification record — 2026-11-05

## Automated checks

Executed from the project workspace:

```sh
python3 -B -m unittest discover -s planner_demo -v
```

Result: **21 tests passed** using local Python 3.14.7. Test dates are fixed at 2026-11-05. File tests use temporary directories; no personal JSON is modified.

| Area | Evidence |
|---|---|
| Urgency and importance | Three/four-day boundary, today's deadline, goal classification, same-deadline importance tie-break |
| Deadline-first allocation | Important A due in 5 days and less-important B due today; both fit into separate days instead of B being missed |
| Allocation boundaries | Half-hour blocks, deadline/start-date bounds, no capacity overuse, work conservation, empty input |
| Reasons | Distinct overdue, within-window capacity shortage and outside-week statuses |
| Early completion | Actual 0.5 h finishes estimated 2 h; later work moves forward; remaining free time is preserved |
| Actual time accounting | Partial work consumes capacity; deleting a task does not erase already-spent time; overspent budgets clamp free time to zero |
| Goals | No automatic slots; start-date gating; optional suggestions only when free; explicit completion required |
| Validation | Quarter-hour values, negatives, non-numbers and non-finite numbers rejected; missing deadline rejected; dates canonicalized before sorting |
| Persistence | Save/reload equivalence, completed status and actual logs retained, original v1 backup and half-hour migration |
| File failures | Broken JSON/schema does not alter input; corrupt startup enters read-only mode and blocks writes; simulated replace failure keeps original |
| HTML | User text escaped; half-hour controls and explicit form action present |

The read-only startup/POST check uses a mocked HTTP listener to avoid modifying live data. Browser verification below exercises the real local server for ordinary forms. No coverage percentage is claimed.

## Actual browser checks

Used the local server started with `python3 -B planner_demo/main.py --demo` and independent demo-data.json.

1. Python group report began with a 2 h estimate. Logged 0.5 h and explicitly marked complete. Confirmed it moved to completed history.
2. Confirmed today's 2 h budget became **0.5 h actual + 1 h class commentary + 0.5 h research presentation**. The research presentation had moved forward from a later date.
3. Added a long-term Japanese-listening goal with blank due date and blank work estimate. It appeared as a reminder and did not enter automatic allocations.
4. Increased the last day's capacity from 1 h to 3 h. Confirmed all remaining DDL work fitted and **0.5 h stayed free**, with an optional goal suggestion that did not consume it.
5. Reloaded the browser; completed task, actual work, newly added goal and capacity were retained.
6. Desktop viewport 1365 × 900: document width 1365; two-column workspace. Mobile viewport 375 × 812: document width 375; single-column quadrant layout. Both were visually inspected; viewport override reset afterwards.
7. Stopped and restarted the real Python server, then reloaded the browser. Confirmed the completed Python report, 0.5 h actual work, 3 goal reminders and 0.5 h free capacity were retained from disk.

Screenshots: `preview-v2.png` (desktop overview), `preview-schedule-v2.png` (actual/scheduled/free time and completed task). The original personal data.json was not rewritten; current preview uses separate sample data.

## Limits of verification

No multi-user or public-deployment testing; this is a local single-user application. No claim of globally optimal scheduling. Clock-based appointments and actual sub-half-hour tracking are outside scope. The tests verify specified behavior and failure handling, not an awarded grade or independent group-member review.

# v3 task map and clock calendar — 2026-11-05

Latest automated result: **33 tests passed** (21 baseline/persistence checks plus 12 clock/approval checks), using the same discovery command above. The live interface now uses `timetable.py`; earlier statements about automatic movement describe v2 and are superseded.

Additional actual browser verification:

- Desktop 1365 × 900: inspected the coordinate diagram and calendar. Fixed overlapping short titles by spacing labeled dots in two columns per region. Point labels are short; full titles remain in accessible link names/details.
- Zoom button changed SVG width from 100% to 125% of its internal viewport; reset restored 100%.
- Mobile 390 × 844: computed point-label display was `none`; document width equalled viewport width (390). Opened the Japanese N1 dot and verified the full task title appeared in details.
- Mobile day calendar also had document width 390; clock blocks and actual effort were visually inspected.
- In demo data, the 1 h class commentary was completed after 0.5 h at 18:30. The remaining research presentation and subsequent research plan received linked movement proposals.
- Original/candidate blocks had computed opacity **0.48 / 0.58** before approval. After pressing Confirm, ghost count was **0** and accepted event opacity was **1**.
- Screenshots saved: `preview-move-pending.png`, `preview-move-confirmed.png`, `preview-map-desktop.png`, `preview-map-mobile.png`, `preview-schedule-mobile.png`.
- The previous demo JSON was backed up as `demo-data.before-timetable.json`; personal `data.json` was not used for UI testing.

Android build and device verification are recorded separately in `android/README.md`. No physical-device execution is implied by browser emulation or a successful APK build.

# v4 fixed events, private time and manual drag — 2026-11-05

Latest automated result: **50 tests passed**. JavaScript syntax check: `node --check planner_demo/app.js` passed. New checks in `test_events.py` cover daily/weekly-multiple-day/monthly recurrence, inclusive recurrence end, month lengths/year changes, overnight splitting, no assumed work period, fixed/private subtraction, urgent-only explicit private borrowing, normal gaps before private borrowing, single-occurrence overrides, persistence, manual drag validation, pin preservation, and bubble/full-day markup.

A dedicated test reproduces the user's rest example: move a 1 h task from 10:00–11:00 to 11:00–12:00; 10:00–11:00 stays unassigned, the previous task stays in place and remaining work stays 60 minutes.

## Actual browser checks (isolated data)

Used a separate server at port 8766 with `/private/tmp/planwise-events-qa.json`; no test event was inserted into the user's production demo JSON.

- Created a recurring Python class on Monday and Friday, 09:00–12:00.
- Created protected sleep from 22:00–08:00 every day, starting the preceding date. Verified both sides of midnight were displayed and excluded from task allocation.
- Used a real pointer drag to move a Saturday 08:00–08:30 task to 09:00–09:30. Its old cell remained empty and the new block was labeled manually arranged.
- Tried dragging another task onto the Friday class. Python rejected the conflict; the original block remained.
- Dragged only the Friday class from 09:00–12:00 to 09:30–12:30. Monday's 09:00–12:00 occurrence stayed unchanged.
- Clicked a time block to open a bubble beside that block; background remained visible, without the previous right-side drawer.
- Caught and fixed an SVG-specific regression: SVG anchor `href` is an animated-string object, so fragment URLs now use `getAttribute('href')`. Verified the N1 dot opened N1 details rather than an empty add form.
- Desktop 1365 × 900 and mobile 390 × 844 were inspected. Mobile document width remained 390; its bubble stayed within horizontal and visible vertical bounds. Embedded-browser bounds also use the outer window limit to prevent an inflated layout viewport from placing the bubble below the visible host.

Screenshots: `preview-calendar-bubble-v4.png`, `preview-map-bubble-v4.png`, `preview-mobile-bubble-v4.png`. Physical touch/Android execution was not tested, and the APK was explicitly not updated this round.

## v5 — 2026-11-06

- `python3 -B -m unittest discover -s planner_demo -q`: 60 tests passed. New checks cover substitute public holidays, 2027 lunar-new-year substitute, complementary work/day-off recurrence with custom weekdays, cumulative goal effort (0%, partial, >100% capped without completion), persistence, complete backup round trip, malformed import rejection, all 3 languages and preservation of user content.
- `node --check planner_demo/app.js`: passed.
- Isolated browser test with `/private/tmp/planwise-v5-qa.json`, not personal/demo data: language switching among all three options; downloaded JSON via page 3, selected that downloaded file through the picker and successfully restored it. A malformed backup was rejected with original tasks/events retained.
- Phone viewport 390×844: default opens single day; day width fits viewport; explicit week shows all seven columns with no horizontal clipping. Goal bubble shows 1 / 2 h, 50%. Existing hand-drawn map style retained.
- Android `MainActivity.java` compiled with Java 17 against Android API 36 and the existing Chaquopy 17.2 runtime jar. No APK assembly, installation or native document-picker test performed.

## v5.1 — nonblocking suggestions and fixed-event exceptions

70 tests passed. Added mutation/handler checks for repeated effort logs while a proposal is pending, changes saved to disk, edits/new tasks preserving original slots, manually dragging an accepted task during a proposal, stale approval rejection, single-date and overnight cancellation, cancellation surviving restart and series edits, fixed-event move rejection and non-draggable markup. Existing event-move tests now exercise private time, as fixed events are deliberately locked.

Isolated browser data: `/private/tmp/planwise-v51-qa.json`. Removed the Nov 7 occurrence of a daily class: Nov 6 and Nov 8–12 remained, all marked non-draggable. Logged two N1 half-hour sessions while the proposal was pending: both saved; accepted task stayed at Nov 7 18:00–19:00. With the final page-retention fix, logging from the map stayed on the map. Schedule suggestion was collapsed and optional. Screenshot: `preview-optional-suggestion-v51.png`. No APK build/update or Android device check this iteration.
