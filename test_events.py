from copy import deepcopy
from datetime import date,timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from events import occurrences,save_event,move_occurrence
from android.runtime.main import render,event_bubble
from storage import empty_state,save_state,load_state
from timetable import available_cells,candidate,cells,refresh,move_block
from test_planner import TODAY,D0,D1,task,state,form


def event(ident='e',day=D0,start=540,end=600,category='fixed',repeat='none',weekdays=None,until=''):
    return dict(id=ident,title=ident,category=category,date=day,start=start,end=end,repeat=repeat,weekdays=weekdays or [date.fromisoformat(day).weekday()],until=until,overrides={})


def free_state(tasks=None):
    s=state(tasks or [])
    s['time_model']='free'
    return s


class RecurrenceAndPrivacyTests(unittest.TestCase):
    def test_unassigned_work_hours_are_free_not_assumed_busy(self):
        s=free_state()
        free=available_cells(s,TODAY)
        self.assertIn((D0,8*60),free)
        self.assertIn((D0,15*60+30),free)
        self.assertIn((D0,23*60),free)
        self.assertEqual(len(free),7*48)

    def test_fixed_and_private_are_removed_before_scheduling(self):
        s=free_state()
        s['events']=[event(start=540,end=660),event('p',start=660,end=720,category='private')]
        free=available_cells(s,TODAY)
        self.assertIn((D0,480),free)
        self.assertNotIn((D0,540),free)
        self.assertNotIn((D0,690),free)
        self.assertIn((D0,720),free)

    def test_daily_and_until_are_inclusive(self):
        s=free_state()
        s['events']=[event(repeat='daily',until=D1)]
        rows=occurrences(s,TODAY,TODAY+timedelta(days=6))
        self.assertEqual([b['date'] for b in rows],[D0,D1])

    def test_weekly_multiple_days(self):
        s=free_state()
        s['events']=[event(repeat='weekly',weekdays=[3,5])]
        rows=occurrences(s,TODAY,TODAY+timedelta(days=8))
        self.assertEqual([date.fromisoformat(b['date']).weekday() for b in rows],[3,5,3])

    def test_monthly_31_skips_short_month_and_crosses_year(self):
        s=free_state()
        s['events']=[event(day='2026-12-31',repeat='monthly')]
        rows=occurrences(s,date(2026,12,31),date(2027,3,31))
        self.assertEqual([b['date'] for b in rows],['2026-12-31','2027-01-31','2027-03-31'])

    def test_overnight_is_split_and_previous_day_tail_visible(self):
        s=free_state()
        s['events']=[event(start=1320,end=1800)]
        rows=occurrences(s,TODAY,TODAY+timedelta(days=1))
        self.assertEqual([(b['date'],b['start'],b['end']) for b in rows],[(D0,1320,1440),(D1,0,360)])
        tail=occurrences(s,TODAY+timedelta(days=1),TODAY+timedelta(days=1))
        self.assertEqual([(b['start'],b['end']) for b in tail],[(0,360)])

    def test_form_accepts_overnight_rejects_quarter_hour_and_same_times(self):
        s=free_state()
        data=form(action='save_event',title='夜班',category='fixed',date=D0,event_start='22:00',event_end='06:00',repeat='daily')
        save_event(s,data)
        self.assertEqual(s['events'][0]['end'],1800)
        for bad in ['22:15','22:00']:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                save_event(free_state(),dict(data,event_end=[bad]))

    def test_private_borrow_requires_opt_in_and_urgent_deadline(self):
        s=state([task(delta=0,amount=60)])
        s['availability']={D0:[[540,600]]}
        s['capacity']={D0:60}
        s['events']=[event(category='private')]
        self.assertEqual(candidate(s,TODAY)[0],[])
        s['borrow_private']=True
        self.assertEqual(len(cells(candidate(s,TODAY)[0])),2)
        s['tasks'][0]['due']=(TODAY+timedelta(days=4)).isoformat()
        self.assertEqual(candidate(s,TODAY)[0],[])

    def test_fixed_never_borrowed_even_under_private_override(self):
        s=state([task(delta=0,amount=60)])
        s['availability']={D0:[[540,600]]}
        s['capacity']={D0:60}
        s['events']=[event(category='private'),event('fixed',start=540,end=570)]
        s['borrow_private']=True
        plan,missing=candidate(s,TODAY)
        self.assertEqual(set(cells(plan)),{(D0,570)})
        self.assertEqual(missing[0][1],30)

    def test_normal_free_time_used_before_private_time(self):
        s=state([task(delta=0,amount=60)])
        s['availability']={D0:[[540,660]]}
        s['capacity']={D0:120}
        s['events']=[event(category='private')]
        s['borrow_private']=True
        self.assertEqual(set(cells(candidate(s,TODAY)[0])),{(D0,600),(D0,630)})

    def test_moving_one_weekly_occurrence_keeps_other_weeks(self):
        s=free_state()
        s['events']=[event(repeat='weekly',category='private')]
        move_occurrence(s,form(id='e',occurrence_date=D0,new_date=D1,new_start='11:00'),TODAY)
        rows=occurrences(s,TODAY,TODAY+timedelta(days=8))
        self.assertEqual([(b['date'],b['start']) for b in rows],[(D1,660),((TODAY+timedelta(days=7)).isoformat(),540)])

    def test_recurring_override_persists_with_private_policy(self):
        s=free_state()
        s['events']=[event(repeat='daily',category='private')]
        s['borrow_private']=True
        move_occurrence(s,form(id='e',occurrence_date=D0,new_date=D1,new_start='11:00'),TODAY)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'data.json'
            save_state(path,s)
            restored,_=load_state(path,TODAY)
        self.assertEqual(restored,s)


class DragAndBubbleTests(unittest.TestCase):
    def test_delaying_one_hour_task_leaves_rest_gap_and_other_work_unchanged(self):
        s=state([task('prior',delta=0,amount=60),task('work',delta=0,amount=60)])
        s['availability']={D0:[[540,720]]}
        s['capacity']={D0:180}
        s['calendar']=[dict(task_id='prior',date=D0,start=540,end=600),dict(task_id='work',date=D0,start=600,end=660)]
        before=deepcopy(s['calendar'][0])
        move_block(s,form(id='work',source_date=D0,source_start='10:00',source_end='11:00',new_date=D0,new_start='11:00'),TODAY)
        self.assertEqual(s['calendar'][0],before)
        self.assertFalse(any((D0,m) in cells(s['calendar']) for m in (600,630)))
        self.assertEqual({cell for cell,ident in cells(s['calendar']).items() if ident=='work'},{(D0,660),(D0,690)})
        self.assertEqual(s['tasks'][1]['minutes'],60)

    def example(self):
        s=state([task('A',delta=0,amount=120),task('B',delta=1,amount=60)])
        s['availability']={D0:[[540,840]]}
        s['capacity']={D0:300}
        refresh(s,TODAY)
        return s

    def test_manual_drag_retained_on_next_replan(self):
        s=self.example()
        data=form(id='B',source_date=D0,source_start='11:00',source_end='12:00',new_date=D0,new_start='13:00')
        move_block(s,data,TODAY)
        s['tasks'].append(task('C',delta=0,amount=60))
        refresh(s,TODAY)
        self.assertEqual(cells(s['calendar'])[(D0,780)],'B')
        self.assertEqual(cells(s['calendar'])[(D0,660)],'C')

    def test_drag_rejects_task_fixed_private_deadline_and_stale_conflicts(self):
        for bad in ['09:00','12:00','12:30']:
            s=self.example()
            s['events']=[event(start=720,end=750),event('p',start=750,end=780,category='private')]
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                move_block(s,form(id='B',source_date=D0,source_start='11:00',source_end='12:00',new_date=D0,new_start=bad),TODAY)
        s=self.example()
        with self.assertRaises(ValueError):
            move_block(s,form(id='A',source_date=D0,source_start='09:00',source_end='11:00',new_date=D1,new_start='09:00'),TODAY)
        with self.assertRaises(ValueError):
            move_block(s,form(id='B',source_date=D0,source_start='10:30',source_end='11:30',new_date=D0,new_start='13:00'),TODAY)

    def test_private_override_disabling_removes_borrowed_pin(self):
        s=self.example()
        s['tasks'][1]['due']=D0
        s['events']=[event(category='private',start=780,end=840)]
        s['borrow_private']=True
        move_block(s,form(id='B',source_date=D0,source_start='11:00',source_end='12:00',new_date=D0,new_start='13:00'),TODAY)
        s['borrow_private']=False
        refresh(s,TODAY)
        self.assertNotIn((D0,780),cells(s['calendar']))
        self.assertEqual(s['pins'],[])

    def test_full_day_grid_events_tab_and_bubble_markup(self):
        s=self.example()
        s['events']=[event()]
        with patch('android.runtime.main.today_hk',return_value=TODAY):
            schedule=render(s,query={'tab':['schedule']})
            detail=render(s,query={'task':['A']})
            panel=render(s,query={'tab':['events']})
        self.assertIn('00:00',schedule)
        self.assertIn('24:00',schedule)
        self.assertIn('data-draggable="true"',schedule)
        self.assertIn('anchor-bubble',detail)
        self.assertNotIn('drawer-shade',detail)
        self.assertIn('固定事項',panel)
        self.assertIn('允許緊急 DDL',panel)
        self.assertIn('app.js',schedule)


if __name__=='__main__':
    unittest.main()
