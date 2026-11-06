"""Behavioral checks for v5 preferences, effort, holiday rules and portable backups."""
from copy import deepcopy
from datetime import date
from pathlib import Path
import json
import tempfile
import unittest
from unittest.mock import patch
from events import occurrences, save_event
from holidays import holiday_name, is_workday, HOLIDAYS
from i18n import localize_html, translate
from planner import goal_progress, mutate
from storage import empty_state, import_state, export_state, load_state, save_state
from main import render, task_bubble
from test_events import event, free_state
from test_planner import form, TODAY, task


class PreferencesTests(unittest.TestCase):
    def test_hk_2026_substitute_holidays_and_2027_new_year(self):
        self.assertEqual(len(HOLIDAYS),34)
        for day in ['2026-04-06','2026-04-07','2026-05-25','2026-10-19','2027-02-09','2027-12-27']:
            dt=date.fromisoformat(day)
            self.assertTrue(holiday_name(dt))
            self.assertFalse(is_workday(dt))
        self.assertTrue(is_workday(date(2026,4,8)))
        self.assertFalse(is_workday(date(2026,4,5)))

    def test_workday_and_holiday_rules_are_complements_with_custom_workdays(self):
        s=free_state()
        s['events']=[event('work',day='2026-12-24',repeat='workdays'),event('rest',day='2026-12-24',repeat='holidays')]
        rows=occurrences(s,date(2026,12,24),date(2026,12,28))
        self.assertEqual([(r['event_id'],r['date']) for r in rows],[('work','2026-12-24'),('rest','2026-12-25'),('rest','2026-12-26'),('rest','2026-12-27'),('work','2026-12-28')])
        s['workdays']=[5]
        rows=occurrences(s,date(2026,11,6),date(2026,11,8))
        self.assertEqual(rows,[])  # Before the series start.
        s['events'][0]['date']=s['events'][1]['date']='2026-11-06'
        rows=occurrences(s,date(2026,11,6),date(2026,11,8))
        self.assertEqual([(r['event_id'],r['date']) for r in rows],[('rest','2026-11-06'),('work','2026-11-07'),('rest','2026-11-08')])

    def test_new_repeat_options_round_trip(self):
        for rule in ('workdays','holidays'):
            s=empty_state()
            save_event(s,form(action='save_event',title='repeat',category='fixed',date='2026-11-06',event_start='09:00',event_end='10:00',repeat=rule))
            self.assertEqual(import_state(export_state(s)),s)

    def test_goal_effort_fills_without_completing_and_survives_restart(self):
        s=empty_state()
        mutate(s,form(action='save',title='N1',kind='goal',important='yes',target_hours='2'),TODAY)
        goal=s['tasks'][0]
        self.assertEqual(goal_progress(s,goal),(0,120,0))
        mutate(s,form(action='progress',id=goal['id'],actual='0.5'),TODAY)
        self.assertEqual(goal_progress(s,goal),(30,120,.25))
        mutate(s,form(action='progress',id=goal['id'],actual='3'),TODAY)
        self.assertEqual(goal_progress(s,goal),(210,120,1))
        self.assertFalse(goal['completed'])
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'state.json'
            save_state(path,s)
            loaded,_=load_state(path,TODAY)
        self.assertEqual(goal_progress(loaded,loaded['tasks'][0]),(210,120,1))

    def test_goal_svg_contains_partial_fill_and_clear_reference_label(self):
        s=empty_state()
        mutate(s,form(action='save',title='N1',kind='goal',important='yes',target_hours='2'),TODAY)
        mutate(s,form(action='progress',id=s['tasks'][0]['id'],actual='1'),TODAY)
        html=render(s)
        self.assertIn('class="goal-fill"',html)
        self.assertIn('height="7"',html)
        self.assertIn('50%',task_bubble(s,TODAY,s['tasks'][0]['id'],False,'map'))
        self.assertFalse(s['tasks'][0]['completed'])

    def test_complete_backup_round_trip_and_legacy_raw_json(self):
        s=free_state([task()])
        s.update(language='en',workdays=[1,2,3,4,5],borrow_private=True)
        s['events']=[event(repeat='holidays')]
        s['pins']=[dict(task_id=s['tasks'][0]['id'],date=TODAY.isoformat(),start=600,end=630)]
        s['calendar']=deepcopy(s['pins'])
        self.assertEqual(import_state(export_state(s)),s)
        self.assertEqual(import_state(json.dumps(s)),s)

    def test_invalid_imports_do_not_modify_original(self):
        s=empty_state()
        before=deepcopy(s)
        invalid=['no json','[]','null',json.dumps(dict(s,language='fr')),json.dumps(dict(s,events=[42])),json.dumps(dict(s,workdays=[True])),json.dumps(dict(format='planwise-backup',backup_version=9,data=s))]
        for text in invalid:
            with self.subTest(text=text),self.assertRaises(ValueError):import_state(text)
        self.assertEqual(s,before)

    def test_localization_preserves_user_text_and_input_values(self):
        html='<p>任務地圖</p><b data-user>重要事項：任務地圖 &amp; N1</b><input name="title" value="任務地圖"><textarea>任務地圖</textarea>'
        en=localize_html(html,'en')
        self.assertIn('<p>Task map</p>',en)
        self.assertIn('重要事項：任務地圖 &amp; N1',en)
        self.assertIn('value="任務地圖"',en)
        self.assertIn('<textarea>任務地圖</textarea>',en)
        self.assertEqual(translate('任務地圖','zh-Hans'),'任务地图')

    def test_three_languages_all_tabs_and_bubble(self):
        s=empty_state()
        for language,label in [('zh-Hant','資料導入／導出'),('zh-Hans','数据导入／导出'),('en','Import / export data')]:
            s['language']=language
            for tab in ('map','schedule','events'):
                html=render(s,query={'tab':[tab]})
                self.assertIn('lang="'+language+'"',html)
                self.assertIn('/app.js',html)
                if tab=='events':self.assertIn(label,html)
        s['language']='en'
        en=localize_html(task_bubble(s,TODAY,'',True,'map'),'en')
        self.assertIn('Reference hours for a full dot',en)
        self.assertNotIn('參考',en)

    def test_mobile_grid_is_full_day_and_day_navigation_exists(self):
        html=render(empty_state(),query={'tab':['schedule'],'span':['day']})
        self.assertIn('24:00',html)
        self.assertIn('00:00',html)
        self.assertIn('single-day',html)
        self.assertEqual(html.count('class="day-heading '),1)
        self.assertIn('span=week',html)


if __name__=='__main__':unittest.main()
