"""Regressions: locked fixed events and suggestions which never block ordinary work."""
from copy import deepcopy
from datetime import timedelta
from io import BytesIO
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
from urllib.parse import urlencode
import unittest
from unittest.mock import patch

from events import cancel_occurrence, move_occurrence, occurrences, save_event
from android.runtime.main import Handler, TOKEN, event_bubble, render
from storage import load_state, save_state
from test_events import event
from test_planner import TODAY, D0, D1, form, task
from test_timetable import example, early_finish
from timetable import cells, decide, refresh


def request(state,path,**fields):
    payload=urlencode(dict(token=TOKEN,tab='schedule',**fields)).encode()
    handler=Handler.__new__(Handler)
    handler.path='/'
    handler.headers={'Content-Length':str(len(payload)),'Accept':'application/json'}
    handler.rfile=BytesIO(payload)
    handler.server=SimpleNamespace(state=state,data_path=path,notice='',demo=False,read_only=False)
    result=[]
    handler.reply=lambda code,body,*args,**kwargs:result.append((code,json.loads(body)))
    with patch('android.runtime.main.today_hk',return_value=TODAY),patch('android.runtime.main.current_floor',return_value=0):
        handler.do_POST()
    return handler.server.state,result[0]


class FixedEventTests(unittest.TestCase):
    def test_cancel_one_daily_overnight_occurrence_and_persist(self):
        s=example()
        s['events']=[event(start=1320,end=1800,repeat='daily')]
        cancel_occurrence(s,form(id='e',occurrence_date=D0))
        rows=occurrences(s,TODAY,TODAY+timedelta(days=2))
        self.assertFalse(any(r['occurrence_date']==D0 for r in rows))
        self.assertEqual([(r['date'],r['start']) for r in rows],[(D1,1320),((TODAY+timedelta(days=2)).isoformat(),0),((TODAY+timedelta(days=2)).isoformat(),1320)])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'data.json'
            save_state(path,s)
            restored,_=load_state(path,TODAY)
        self.assertEqual(occurrences(restored,TODAY,TODAY+timedelta(days=2)),rows)

    def test_fixed_event_cannot_move_even_with_direct_post(self):
        s=example()
        s['events']=[event(repeat='daily')]
        before=deepcopy(s)
        with self.assertRaisesRegex(ValueError,'固定事項不能移動'):
            move_occurrence(s,form(id='e',occurrence_date=D0,new_date=D1,new_start='11:00'),TODAY)
        self.assertEqual(s,before)
        html=event_bubble(s,TODAY,'e','schedule',{'occurrence_date':[D1]})
        self.assertIn('cancel_occurrence',html)
        self.assertIn('value="'+D1+'"',html)
        self.assertNotIn('name="new_start"',html)
        with patch('android.runtime.main.today_hk',return_value=TODAY):
            html=render(s,query={'tab':['schedule']})
        self.assertIn('data-end="600" data-draggable="false"',html)

    def test_invalid_and_repeated_cancellation_rejected(self):
        s=example()
        s['events']=[event(repeat='weekly')]
        with self.assertRaises(ValueError):cancel_occurrence(s,form(id='e',occurrence_date=D1))
        self.assertEqual(s['events'][0]['overrides'],{})
        cancel_occurrence(s,form(id='e',occurrence_date=D0))
        with self.assertRaises(ValueError):cancel_occurrence(s,form(id='e',occurrence_date=D0))

    def test_series_edit_keeps_cancelled_dates(self):
        s=example()
        s['events']=[event(repeat='daily')]
        cancel_occurrence(s,form(id='e',occurrence_date=D1))
        save_event(s,form(action='save_event',id='e',title='New title',category='fixed',date=D0,event_start='10:00',event_end='11:00',repeat='daily'))
        self.assertFalse(any(r['date']==D1 for r in occurrences(s,TODAY,TODAY+timedelta(days=2))))
        self.assertEqual(len(occurrences(s,TODAY,TODAY+timedelta(days=2))),2)


class NonblockingSuggestionTests(unittest.TestCase):
    def pending(self):
        s=example()
        early_finish(s)
        s['tasks'].append(task('goal',kind='goal'))
        return s

    def test_repeated_logs_accepted_while_suggestion_pending(self):
        s=self.pending()
        old=deepcopy(s['calendar'])
        revision=s['proposal']['id']
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'data.json'
            save_state(path,s)
            for start in ('18:30','19:00'):
                s,(code,reply)=request(s,path,action='progress',id='goal',actual='0.5',session_start=start)
                self.assertEqual(code,200,reply)
                self.assertEqual(s['calendar'],old)
                self.assertNotEqual(s['proposal']['id'],revision)
            restored,_=load_state(path,TODAY)
        self.assertEqual(sum(r['minutes'] for r in s['work_log'] if r['task_id']=='goal'),60)
        self.assertEqual(s,restored)
        with self.assertRaises(ValueError):decide(s,'confirm_move',revision,TODAY)

    def test_new_task_and_task_edit_do_not_move_existing_schedule(self):
        s=self.pending()
        old=deepcopy(s['calendar'])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'data.json'
            s,(code,reply)=request(s,path,action='save',id='',title='C',kind='deadline',due=D0,hours='0.5',important='yes')
            self.assertEqual(code,200,reply)
            self.assertTrue(all(b in s['calendar'] for b in old))
            s,(code,reply)=request(s,path,action='save',id='B',title='Renamed',kind='deadline',due=D1,hours='1',important='no')
            self.assertEqual(code,200,reply)
            self.assertTrue(all(b in s['calendar'] for b in old))

    def test_duplicate_actual_work_still_rejected_during_suggestion(self):
        s=self.pending()
        revision=s['proposal']['id']
        with tempfile.TemporaryDirectory() as folder:
            s,(code,reply)=request(s,Path(folder)/'data.json',action='progress',id='B',actual='0.5',session_start='18:00')
        # This logging conflicts with A's existing actual work and is correctly rejected.
        self.assertEqual(code,400)
        self.assertEqual(s['proposal']['id'],revision)

    def test_task_progress_reduces_original_block_before_optional_move(self):
        s=self.pending()
        revision=s['proposal']['id']
        with tempfile.TemporaryDirectory() as folder:
            s,(code,reply)=request(s,Path(folder)/'data.json',action='progress',id='B',actual='0.5',session_start='18:30')
        self.assertEqual(code,200,reply)
        self.assertEqual(s['calendar'],[dict(task_id='B',date=D1,start=1080,end=1110)])
        self.assertEqual(next(t for t in s['tasks'] if t['id']=='B')['minutes'],30)
        self.assertNotEqual(s['proposal']['id'],revision)

    def test_cancel_event_pending_keeps_other_tasks_and_releases_only_one_date(self):
        s=self.pending()
        s['events']=[event(repeat='daily',start=600,end=660)]
        old=deepcopy(s['calendar'])
        with tempfile.TemporaryDirectory() as folder:
            s,(code,reply)=request(s,Path(folder)/'data.json',action='cancel_occurrence',id='e',occurrence_date=D0)
        self.assertEqual(code,200,reply)
        self.assertEqual(s['calendar'],old)
        self.assertFalse(any(r['date']==D0 for r in occurrences(s,TODAY,TODAY+timedelta(days=1))))
        self.assertTrue(any(r['date']==D1 for r in occurrences(s,TODAY,TODAY+timedelta(days=1))))

    def test_drag_original_works_during_suggestion(self):
        s=self.pending()
        with tempfile.TemporaryDirectory() as folder:
            s,(code,reply)=request(s,Path(folder)/'data.json',action='move_block',id='B',source_date=D1,source_start='18:00',source_end='19:00',new_date=D0,new_start='19:00')
        self.assertEqual(code,200,reply)
        self.assertEqual(cells(s['calendar']),{(D0,1140):'B',(D0,1170):'B'})


if __name__=='__main__':unittest.main()
