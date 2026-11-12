"""The exact administrator setup/reset commands from INSTALL.md."""
from contextlib import closing, redirect_stdout, redirect_stderr
from io import StringIO
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from werkzeug.security import check_password_hash
from nas.database import Database
from nas.manage import main


class AccountCommandTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.path=str(Path(self.folder.name)/'accounts.sqlite3')

    def tearDown(self):
        self.folder.cleanup()

    def run_command(self,command,passwords):
        with patch('sys.argv',['nas.manage','--database',self.path,*command]), patch('getpass.getpass',side_effect=passwords), redirect_stdout(StringIO()) as out, redirect_stderr(StringIO()):
            main()
            return out.getvalue()

    def test_documented_admin_command_prompts_and_stores_only_hash(self):
        password='Local-test-password-2026'
        output=self.run_command(['create-user','admin','--admin'],[password,password])
        with closing(Database(self.path).connect()) as db:
            user=db.execute('SELECT * FROM users WHERE username=?',('admin',)).fetchone()
            self.assertEqual(user['is_admin'],1)
            self.assertNotEqual(user['password_hash'],password)
            self.assertTrue(check_password_hash(user['password_hash'],password))
        self.assertNotIn(password,output)

    def test_reset_command_preserves_plan_and_revokes_sessions(self):
        store=Database(self.path);ident=store.create_user('admin','Original-password-2026',True)
        with store.transaction() as db:
            store.session(db,ident)
            before=dict(db.execute('SELECT * FROM plans WHERE user_id=?',(ident,)).fetchone())
        self.run_command(['reset-password','admin'],['Replacement-password','Replacement-password'])
        with closing(store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM sessions').fetchone()[0],0)
            self.assertEqual(dict(db.execute('SELECT * FROM plans WHERE user_id=?',(ident,)).fetchone()),before)
            self.assertTrue(check_password_hash(db.execute('SELECT password_hash FROM users WHERE id=?',(ident,)).fetchone()[0],'Replacement-password'))

    def test_mismatched_passwords_do_not_create_account(self):
        with self.assertRaises(SystemExit):
            self.run_command(['create-user','admin','--admin'],['First-password','Different-password'])
        with closing(Database(self.path).connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],0)
