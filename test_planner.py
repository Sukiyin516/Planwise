"""Acceptance checks for the rules in SPEC.md; all data is temporary."""
from copy import deepcopy
from datetime import date, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace

from android.runtime.main import Handler, make_server, render
from planner import minutes, mutate, rank, schedule, spent_on, suggestions
from storage import empty_state, load_state, migrate, save_state, seed

TODAY = date(2026, 11, 5)
D0 = TODAY.isoformat()
D1 = (TODAY + timedelta(days=1)).isoformat()


def task(ident='a', delta=2, amount=120, important=True, kind='deadline', start=''):
    return dict(id=ident, title=ident, course='test', kind=kind, due=(TODAY + timedelta(days=delta)).isoformat() if kind == 'deadline' else '', start=start, minutes=amount if kind == 'deadline' else 0, important=important, completed=False, completed_on='')


def state(tasks, capacity=None):
    result = empty_state()
    result.update(tasks=tasks, capacity=capacity if capacity is not None else {D0:120, D1:120})
    result['time_model']='custom'
    return result


def form(**values):
    return {key: [str(value)] for key, value in values.items()}


class SchedulingTests(unittest.TestCase):
    def test_urgent_boundary_and_goal(self):
        self.assertEqual(rank(task(delta=3), TODAY), 0)
        self.assertEqual(rank(task(delta=4), TODAY), 1)
        self.assertEqual(rank(task(delta=0, important=False), TODAY), 2)
        self.assertEqual(rank(task(kind='goal'), TODAY), 1)

    def test_deadline_prevents_old_priority_conflict(self):
        s = state([task('A', delta=5, amount=60), task('B', delta=0, amount=60, important=False)], {D0:60,D1:60})
        plan, _, missing = schedule(s, TODAY)
        self.assertEqual(plan[D0][0][0]['id'], 'B')
        self.assertEqual(plan[D1][0][0]['id'], 'A')
        self.assertEqual(missing, [])

    def test_equal_deadline_uses_importance(self):
        plan, _, _ = schedule(state([task('a', important=False), task('z', important=True)]), TODAY)
        self.assertEqual(plan[D0][0][0]['id'], 'z')

    def test_today_allowed_overdue_excluded(self):
        plan, _, missing = schedule(state([task('late', delta=-1),task('today', delta=0)]), TODAY)
        self.assertEqual([t['id'] for t, _ in plan[D0]], ['today'])
        self.assertEqual(missing[0][2], 'overdue')

    def test_missing_reasons_are_distinct(self):
        _, free, missing = schedule(state([task('past', delta=-1),task('near', delta=1),task('far', delta=20)], {}), TODAY)
        self.assertEqual({t['id']:code for t, _, code in missing}, {'past':'overdue','near':'deadline_capacity','far':'outside_week'})
        self.assertEqual(sum(free.values()), 0)

    def test_start_date_respected(self):
        plan, _, _ = schedule(state([task(start=D1)]), TODAY)
        self.assertEqual(plan[D0], [])
        self.assertEqual(sum(n for _, n in plan[D1]), 120)

    def test_goals_are_reminders_and_start_later(self):
        goal = task('N1', kind='goal', start=D1)
        s = state([goal])
        plan, free, missing = schedule(s, TODAY)
        self.assertFalse(any(plan.values()))
        self.assertEqual(missing, [])
        self.assertEqual(suggestions(s, D0, free[D0]), [])
        self.assertEqual(suggestions(s, D1, free[D1]), [goal])
        self.assertEqual(suggestions(s, D1, 0), [])

    def test_early_finish_moves_next_task_and_preserves_free_time(self):
        s = state([task('A', delta=0),task('B', delta=1, amount=60)])
        before, _, _ = schedule(s, TODAY)
        self.assertEqual(before[D1][0][0]['id'], 'B')
        mutate(s, form(action='progress', id='A', actual='0.5', finished='yes'), TODAY)
        after, free, missing = schedule(s, TODAY)
        self.assertTrue(s['tasks'][0]['completed'])
        self.assertEqual(s['tasks'][0]['minutes'], 0)
        self.assertEqual(after[D0][0][0]['id'], 'B')
        self.assertEqual(sum(n for _, n in after[D0]), 60)
        self.assertEqual(spent_on(s,D0), 30)
        self.assertEqual(free[D0], 30)
        self.assertEqual(after[D1], [])
        self.assertEqual(missing, [])
        # Actual work remains deducted even if a task is deleted.
        mutate(s, form(action='delete', id='A'), TODAY)
        self.assertEqual(spent_on(s,D0), 30)

    def test_early_finish_without_next_task_leaves_free_time(self):
        s = state([task(delta=0)])
        mutate(s, form(action='progress',id='a',actual='0.5',finished='yes'), TODAY)
        plan, free, _ = schedule(s,TODAY)
        self.assertEqual(plan[D0], [])
        self.assertEqual(free[D0],90)

    def test_partial_work_does_not_create_capacity(self):
        s = state([task()])
        mutate(s, form(action='progress',id='a',actual='0.5'), TODAY)
        plan, free, _ = schedule(s,TODAY)
        self.assertFalse(s['tasks'][0]['completed'])
        self.assertEqual(s['tasks'][0]['minutes'],90)
        self.assertEqual(sum(n for _, n in plan[D0]),90)
        self.assertEqual(free[D0],0)

    def test_goal_stays_active_until_explicitly_completed(self):
        s = state([task(kind='goal')])
        mutate(s,form(action='progress',id='a',actual='0.5'),TODAY)
        self.assertFalse(s['tasks'][0]['completed'])
        mutate(s,form(action='progress',id='a',actual='0.5',finished='yes'),TODAY)
        self.assertTrue(s['tasks'][0]['completed'])
        with self.assertRaises(ValueError):
            mutate(s,form(action='progress',id='a',actual='0.5'),TODAY)

    def test_half_hour_and_invalid_numbers(self):
        for value in ['0.25','0.75','nan','inf','-1','abc']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                minutes(value)
        self.assertEqual(minutes('0.5'),30)
        self.assertEqual(minutes('0'),0)
        s = state([])
        mutate(s,form(action='save',title='長期成長',kind='goal',important='yes'),TODAY)
        self.assertEqual(s['tasks'][0]['due'],'')
        with self.assertRaises(ValueError):
            mutate(s,form(action='save',title='missing ddl',kind='deadline',hours='1',important='yes'),TODAY)

    def test_dates_normalized_for_sorting(self):
        s = state([])
        mutate(s,form(action='save',title='basic ISO',kind='deadline',hours='1',important='yes',due='20261106',start='20261105'),TODAY)
        self.assertEqual(s['tasks'][0]['due'],D1)
        self.assertEqual(s['tasks'][0]['start'],D0)
        self.assertEqual(sum(n for _,n in schedule(s,TODAY)[0][D0]),60)

    def test_capacity_validation_and_spent_over_budget(self):
        s = state([task()])
        data = form(action='capacity', **{(TODAY+timedelta(days=i)).isoformat():'1' for i in range(7)})
        data[D0] = ['24.5']
        with self.assertRaises(ValueError):
            mutate(s,data,TODAY)
        mutate(s,form(action='progress',id='a',actual='2.5'),TODAY)
        _, free, _ = schedule(s,TODAY)
        self.assertEqual(free[D0],0)
        with self.assertRaises(ValueError):
            mutate(state([task()]),form(action='progress',id='a',actual='24.5'),TODAY)

    def test_allocation_invariants(self):
        s = seed(TODAY)
        plan, free, missing = schedule(s,TODAY)
        for day, rows in plan.items():
            used = sum(n for _, n in rows)
            self.assertEqual(used+free[day]+spent_on(s,day),s['capacity'][day])
            for t,n in rows:
                self.assertEqual(n % 30,0)
                self.assertGreaterEqual(n,30)
                self.assertLessEqual(day,t['due'])
                self.assertEqual(t['kind'],'deadline')
        demand = sum(t['minutes'] for t in s['tasks'] if t['kind']=='deadline')
        self.assertEqual(sum(n for rows in plan.values() for _,n in rows)+sum(n for _,n,_ in missing),demand)
        self.assertEqual(schedule(empty_state(),TODAY)[2],[])


class StorageAndPageTests(unittest.TestCase):
    def test_save_reload_and_restart_equivalence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'data.json'
            s = seed(TODAY)
            mutate(s,form(action='progress',id=s['tasks'][0]['id'],actual='0.5',finished='yes'),TODAY)
            save_state(path,s)
            restored,_ = load_state(path,TODAY+timedelta(days=1))
            self.assertEqual(restored,s)
            self.assertEqual(spent_on(restored,D0),30)

    def test_legacy_migration_and_original_backup(self):
        old = {'tasks':[dict(id='a',title='old',course='test',due=D1,minutes=45,important=True)],'capacity':{D0:75}}
        original = json.dumps(old).encode()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'data.json'
            path.write_bytes(original)
            s,message = load_state(path,TODAY)
            self.assertEqual(s['tasks'][0]['minutes'],60)
            self.assertEqual(s['capacity'][D0],60)
            self.assertTrue(message)
            self.assertEqual(path.read_bytes(),original)
            save_state(path,s)
            self.assertEqual(path.with_suffix('.v1.bak').read_bytes(),original)
            self.assertEqual(json.loads(path.read_text())['version'],2)

    def test_corrupt_json_and_schema_preserve_original(self):
        for bad in [b'{broken',b'{"tasks": [], "capacity": {"bad-date": 5}}',b'[]']:
            with self.subTest(bad=bad), tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'data.json'
                path.write_bytes(bad)
                with self.assertRaises(ValueError):
                    load_state(path,TODAY)
                self.assertEqual(path.read_bytes(),bad)

    def test_corrupt_file_starts_read_only_and_blocks_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'data.json'
            path.write_bytes(b'{broken')
            with patch('android.runtime.main.HTTPServer',return_value=SimpleNamespace()):
                server = make_server(path)
            self.assertTrue(server.read_only)
            self.assertIn('原檔已保留',server.notice)
            handler = object.__new__(Handler)
            handler.server,handler.path = server,'/'
            with patch.object(handler,'reply') as reply:
                handler.do_POST()
            self.assertEqual(reply.call_args.args[0],503)
            self.assertEqual(path.read_bytes(),b'{broken')

    def test_failed_atomic_write_keeps_original(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'data.json'
            save_state(path,seed(TODAY))
            before = path.read_bytes()
            with patch.object(Path,'replace',side_effect=OSError('simulated write failure')):
                with self.assertRaises(OSError):
                    save_state(path,empty_state())
            self.assertEqual(path.read_bytes(),before)

    def test_page_explains_rules_and_escapes_input(self):
        s = state([task()])
        s['tasks'][0]['title'] = '<script>alert(1)</script>'
        with patch('android.runtime.main.today_hk', return_value=TODAY):
            page = render(s,query={'add':['1']})
        self.assertNotIn('<script>',page)
        self.assertIn('&lt;script&gt;',page)
        self.assertIn('step="0.5"',page)
        self.assertNotIn('step="0.25"',page)
        self.assertIn('任務地圖',page)
        self.assertIn('action="/"',page)


if __name__ == '__main__':
    unittest.main()
