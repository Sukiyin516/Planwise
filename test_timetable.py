from copy import deepcopy
from datetime import timedelta
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from main import render
from planner import mutate
from storage import load_state,save_state
from test_planner import TODAY,D0,D1,form,state,task
from timetable import (available_cells,candidate,cells,clock,decide,initialize,occupied,
                       preview_parts,record_clock,refresh,update_windows)


def example():
    s=state([task('A',delta=0),task('B',delta=1,amount=60)])
    s['availability']={D0:[[1080,1200]],D1:[[1080,1140]]}
    s['capacity']={D0:120,D1:60}
    initialize(s,TODAY)
    return s


def early_finish(s):
    data=form(action='progress',id='A',actual='0.5',finished='yes',session_start='18:00')
    begin,end=record_clock(s,data,TODAY)
    mutate(s,data,TODAY)
    s['work_log'][-1].update(start=begin,end=end)
    refresh(s,TODAY,propose=True)


class ClockAndApprovalTests(unittest.TestCase):
    def test_split_across_two_windows_and_respect_actual(self):
        s=state([task(amount=180)])
        s['availability']={D0:[[540,600],[900,960]],D1:[[600,660]]}
        plan,missing=candidate(s,TODAY)
        self.assertEqual([(b['date'],b['start'],b['end']) for b in plan],[(D0,540,600),(D0,900,960),(D1,600,660)])
        self.assertEqual(missing,[])
        s['work_log']=[dict(task_id='other',title='other',date=D0,minutes=30,start=540,end=570,finished=False)]
        plan,_=candidate(s,TODAY)
        self.assertNotIn((D0,540),cells(plan))

    def test_early_finish_keeps_origin_until_confirmation(self):
        s=example()
        early_finish(s)
        self.assertIsNotNone(s['proposal'])
        self.assertEqual(s['calendar'],[dict(task_id='B',date=D1,start=1080,end=1140)])
        solid,old,new=preview_parts(s)
        self.assertEqual(solid,[])
        self.assertEqual(old,s['calendar'])
        self.assertEqual(new,[dict(task_id='B',date=D0,start=1110,end=1170)])
        self.assertEqual(occupied(s,D0),{1080})

    def test_confirm_changes_destination_to_solid(self):
        s=example()
        early_finish(s)
        expected=deepcopy(s['proposal']['after'])
        decide(s,'confirm_move',s['proposal']['id'],TODAY)
        self.assertEqual(s['calendar'],expected)
        self.assertEqual(preview_parts(s),(expected,[],[]))
        self.assertIsNone(s['proposal'])

    def test_decline_retains_original_and_spare_time(self):
        s=example()
        early_finish(s)
        before=deepcopy(s['calendar'])
        decide(s,'keep_plan',s['proposal']['id'],TODAY)
        self.assertEqual(s['calendar'],before)
        self.assertEqual(len([cell for cell in available_cells(s,TODAY) if cell[0]==D0]),3)
        self.assertIsNone(s['proposal'])

    def test_stale_confirmation_rejected(self):
        s=example()
        early_finish(s)
        with self.assertRaises(ValueError):
            decide(s,'confirm_move','stale',TODAY)
        with self.assertRaises(ValueError):
            decide(s,'confirm_move',s['proposal']['id'],TODAY+timedelta(days=1))

    def test_pending_move_and_clock_logs_survive_restart(self):
        s=example()
        early_finish(s)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'test.json'
            save_state(path,s)
            restored,_=load_state(path,TODAY)
            initialize(restored,TODAY)
            self.assertEqual(restored,s)
            decide(restored,'confirm_move',restored['proposal']['id'],TODAY)
            self.assertEqual(restored['calendar'][0]['date'],D0)

    def test_new_day_discards_expired_proposal(self):
        s=example()
        early_finish(s)
        initialize(s,TODAY+timedelta(days=1))
        self.assertIsNone(s['proposal'])
        self.assertTrue(all(b['date']>=D1 for b in s['calendar']))

    def test_no_followup_leaves_free_time_without_proposal(self):
        s=example()
        s['tasks']=s['tasks'][:1]
        initialize(s,TODAY)
        early_finish(s)
        self.assertEqual(s['calendar'],[])
        self.assertIsNone(s['proposal'])
        self.assertEqual(len([cell for cell in available_cells(s,TODAY) if cell[0]==D0]),3)

    def test_half_hour_windows_overlap_and_clock_validation(self):
        for bad in ['18:15','24:30','25:00','abc']:
            with self.subTest(bad=bad),self.assertRaises(ValueError):
                clock(bad)
        self.assertEqual(clock('24:00'),1440)
        s=state([])
        data=form(**{f'{D0}_start_0':'18:00',f'{D0}_end_0':'20:00',f'{D0}_start_1':'19:30',f'{D0}_end_1':'21:00'})
        with self.assertRaises(ValueError):
            update_windows(s,data,TODAY)
        self.assertEqual(s['availability'],{})
        data[f'{D0}_start_1']=['20:00']
        update_windows(s,data,TODAY)
        self.assertEqual(s['capacity'][D0],180)
        self.assertEqual(s['availability'][D1],[])

    def test_actual_overlap_and_midnight_rejected(self):
        s=example()
        early_finish(s)
        with self.assertRaises(ValueError):
            record_clock(s,form(actual='0.5',session_start='18:00'),TODAY)
        with self.assertRaises(ValueError):
            record_clock(s,form(actual='1',session_start='23:30'),TODAY)

    def test_current_time_cutoff_and_goal_exclusion(self):
        s=example()
        s['tasks'].append(task('goal',kind='goal'))
        plan,_=candidate(s,TODAY,not_before=1110)
        self.assertTrue(all(b['start']>=1110 for b in plan if b['date']==D0))
        self.assertTrue(all(b['task_id']!='goal' for b in plan))
        self.assertEqual(len(cells(plan)),sum((b['end']-b['start'])//30 for b in plan))

    def test_map_and_calendar_preview_markup(self):
        s=example()
        early_finish(s)
        with patch('main.today_hk',return_value=TODAY):
            map_page=render(s)
            calendar=render(s,query={'tab':['schedule']})
        self.assertIn('map-point',map_page)
        self.assertNotIn('class="task"',map_page)
        self.assertIn('solid origin',calendar)
        self.assertIn('ghost destination',calendar)
        self.assertIn('確認前移',calendar)
        decide(s,'confirm_move',s['proposal']['id'],TODAY)
        with patch('main.today_hk',return_value=TODAY):
            confirmed=render(s,query={'tab':['schedule']})
        self.assertNotIn('ghost destination',confirmed)
        self.assertNotIn('ghost origin',confirmed)


if __name__=='__main__':
    unittest.main()
