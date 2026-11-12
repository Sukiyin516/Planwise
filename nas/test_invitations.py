"""Invitation registration, administrator boundaries and additive database upgrade."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime
import json
from pathlib import Path
import tempfile
import time
import unittest

from nas.application import create_app,HKT
from nas.database import digest


class InvitationTests(unittest.TestCase):
    def setUp(self):
        self.folder=tempfile.TemporaryDirectory()
        self.config=dict(TESTING=True,DATABASE=str(Path(self.folder.name)/'accounts.sqlite3'),NOW=lambda:datetime(2026,11,12,9,0,tzinfo=HKT))
        self.app=create_app(self.config)
        self.store=self.app.extensions['store']
        self.owner_id=self.store.create_user('owner','Owner-test-password',True)
        self.member_id=self.store.create_user('member','Member-test-password')
        self.owner=self.app.test_client()
        self.owner.post('/api/login',json=dict(username='owner',password='Owner-test-password'),headers={'X-Planwise-Client':'1'})

    def tearDown(self):
        self.folder.cleanup()

    def state(self,client=None):
        return (client or self.owner).get('/api/state').get_json()

    def post(self,path,data,client=None):
        client=client or self.owner
        current=self.state(client)
        return client.post(path,json=data,headers={'X-Planwise-Client':'1','X-CSRF-Token':current.get('csrf','')})

    def invitation(self):
        response=self.post('/api/invitations',dict(action='create'))
        self.assertEqual(response.status_code,200)
        return response.get_json()['code'],response.get_json()['invitations'][0]['id']

    def register(self,code,username='newmember',client=None,**overrides):
        client=client or self.app.test_client()
        fields=dict(invite_code=code,username=username,password='New-member-password',password_confirm='New-member-password')
        fields.update(overrides)
        return client.post('/api/register',json=fields,headers={'X-Planwise-Client':'1'})

    def test_creation_stores_only_digest_and_seven_day_expiry(self):
        before=self.state()['version'];now=int(time.time());code,ident=self.invitation()
        with closing(self.store.connect()) as db:
            row=db.execute('SELECT * FROM invitations WHERE id=?',(ident,)).fetchone()
        self.assertEqual(row['code_hash'],digest(code))
        self.assertNotEqual(row['code_hash'],code)
        self.assertGreaterEqual(row['expires_at'],now+7*86400)
        self.assertLessEqual(row['expires_at'],int(time.time())+7*86400)
        self.assertNotIn(code,self.owner.get('/api/invitations').get_data(as_text=True))
        self.assertNotIn(code,self.owner.get('/api/state').get_data(as_text=True))
        self.assertEqual(self.state()['version'],before)

    def test_invited_user_is_regular_even_if_admin_is_requested(self):
        code,ident=self.invitation();client=self.app.test_client()
        response=self.register(code,client=client,is_admin=True,admin=True,language='en')
        self.assertEqual(response.status_code,201,response.get_json())
        self.assertIn('HttpOnly',response.headers['Set-Cookie'])
        current=self.state(client)
        self.assertFalse(current['user']['is_admin'])
        self.assertEqual(current['state']['tasks'],[])
        self.assertEqual(current['state']['language'],'en')
        self.assertNotIn('invitations',current)
        self.assertEqual(client.get('/api/invitations').status_code,403)
        self.assertEqual(self.post('/api/invitations',dict(action='create'),client).status_code,403)
        with closing(self.store.connect()) as db:
            row=db.execute('SELECT used_by FROM invitations WHERE id=?',(ident,)).fetchone()
            self.assertEqual(row['used_by'],current['user']['id'])

    def test_one_code_cannot_create_two_accounts(self):
        code,_=self.invitation()
        self.assertEqual(self.register(code,'firstuser').status_code,201)
        response=self.register(code,'seconduser')
        self.assertEqual(response.status_code,400)
        self.assertEqual(response.get_json()['code'],'invalid_invitation')
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],3)

    def test_two_concurrent_registrations_only_one_consumes_code(self):
        code,_=self.invitation();clients=[self.app.test_client(),self.app.test_client()]
        with ThreadPoolExecutor(max_workers=2) as pool:
            statuses=sorted(pool.map(lambda i:self.register(code,'racer'+str(i),clients[i]).status_code,range(2)))
        self.assertEqual(statuses,[201,400])
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],3)

    def test_invalid_expired_and_revoked_codes_are_rejected(self):
        invalid='invalid-invitation-code-000000000'
        self.assertEqual(self.register(invalid).get_json()['code'],'invalid_invitation')
        expired,ident=self.invitation()
        with self.store.transaction() as db:
            db.execute('UPDATE invitations SET expires_at=0 WHERE id=?',(ident,))
        self.assertEqual(self.register(expired).get_json()['code'],'invalid_invitation')
        revoked,ident=self.invitation()
        self.assertEqual(self.post('/api/invitations',dict(action='revoke',id=ident)).status_code,200)
        self.assertEqual(self.register(revoked).get_json()['code'],'invalid_invitation')
        with closing(self.store.connect()) as db:
            self.assertEqual(db.execute('SELECT count(*) FROM users').fetchone()[0],2)

    def test_bad_password_and_duplicate_name_do_not_consume_invitation(self):
        code,_=self.invitation()
        for fields in [dict(password='short',password_confirm='short'),dict(password_confirm='Different-password'),dict(username='owner'),dict(username='bad name')]:
            response=self.register(code,**fields)
            self.assertEqual(response.status_code,400)
        self.assertEqual(self.register(code).status_code,201)

    def test_csrf_origin_and_role_protection(self):
        code,ident=self.invitation();anon=self.app.test_client()
        self.assertEqual(anon.get('/api/invitations').status_code,401)
        self.assertEqual(anon.post('/api/invitations',json=dict(action='create'),headers={'X-Planwise-Client':'1'}).status_code,401)
        self.assertEqual(self.owner.post('/api/invitations',json=dict(action='create'),headers={'X-Planwise-Client':'1'}).status_code,403)
        fields=dict(invite_code=code,username='newmember',password='New-member-password',password_confirm='New-member-password')
        self.assertEqual(anon.post('/api/register',json=fields,headers={'X-Planwise-Client':'1','Origin':'http://other.example'}).status_code,403)
        self.assertEqual(anon.post('/api/register',data=fields).status_code,403)
        self.assertEqual(self.register(code,client=self.owner).status_code,409)
        self.assertEqual(self.register(code,client=anon).status_code,201)

    def test_rate_limit_commits_and_expires_without_consuming_valid_code(self):
        for i in range(12):
            self.assertEqual(self.register('incorrect-code-00000000000').status_code,400)
        code,_=self.invitation()
        self.assertEqual(self.register(code).status_code,429)
        with self.store.transaction() as db:
            db.execute('UPDATE attempts SET at=? WHERE key LIKE ?', (int(time.time())-901,'register-ip:%'))
        self.assertEqual(self.register(code).status_code,201)

    def test_regular_user_cannot_create_or_revoke_invites(self):
        code,ident=self.invitation();member=self.app.test_client()
        member.post('/api/login',json=dict(username='member',password='Member-test-password'),headers={'X-Planwise-Client':'1'})
        for fields in [dict(action='create'),dict(action='revoke',id=ident)]:
            self.assertEqual(self.post('/api/invitations',fields,member).status_code,403)
        self.assertEqual(self.register(code).status_code,201)

    def test_revoking_used_invitation_cannot_remove_user_or_plan(self):
        code,ident=self.invitation();client=self.app.test_client()
        self.register(code,client=client)
        before=self.state(client)
        self.assertEqual(self.post('/api/invitations',dict(action='revoke',id=ident)).status_code,409)
        self.assertEqual(self.state(client)['state'],before['state'])

    def test_upgrade_from_old_schema_preserves_accounts_plans_and_sessions(self):
        self.state()
        with self.store.transaction() as db:
            before={table:[tuple(row) for row in db.execute('SELECT * FROM '+table)] for table in ('users','plans','sessions')}
            db.execute('DROP TABLE invitations')  # Simulate the previous release's schema in a disposable DB.
        upgraded=create_app(self.config)
        with closing(upgraded.extensions['store'].connect()) as db:
            after={table:[tuple(row) for row in db.execute('SELECT * FROM '+table)] for table in before}
            self.assertEqual(after,before)
            self.assertEqual(db.execute('SELECT count(*) FROM invitations').fetchone()[0],0)
        self.assertEqual(self.owner.get('/api/state').status_code,200)

    def test_invites_survive_database_backup_and_restart(self):
        code,_=self.invitation();backup=Path(self.folder.name)/'backup.sqlite3'
        self.store.backup_to(backup)
        restarted=create_app(dict(self.config,DATABASE=str(backup)))
        response=restarted.test_client().post('/api/register',json=dict(invite_code=code,username='restored',password='Restored-user-password',password_confirm='Restored-user-password'),headers={'X-Planwise-Client':'1'})
        self.assertEqual(response.status_code,201)
