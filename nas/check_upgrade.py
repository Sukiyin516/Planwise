"""CI-only: replace a 0.2.0 container with the current image on the same test volume.

Requires images planwise-nas:previous and planwise-nas:test; never targets an
existing installation. Run: python nas/check_upgrade.py
"""
import http.cookiejar
import json
import subprocess
import time
import urllib.request
import uuid


def docker(*args):
    return subprocess.check_output(['docker', *args], text=True).strip()


def start(image, volume, name):
    docker('run', '-d', '--name', name, '--read-only', '--tmpfs', '/tmp',
           '-v', volume+':/data', '-p', '127.0.0.1:8089:8080', image)
    for _ in range(30):
        try:
            return request('/healthz')
        except OSError:
            time.sleep(1)
    raise RuntimeError('Upgrade test server did not start.')


client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def request(path, fields=None, csrf=''):
    headers = {'Content-Type': 'application/json', 'X-Planwise-Client': '1', 'X-CSRF-Token': csrf}
    data = json.dumps(fields).encode() if fields is not None else None
    with client.open(urllib.request.Request('http://127.0.0.1:8089'+path, data=data, headers=headers), timeout=10) as response:
        return json.load(response)


def change(action, fields):
    state = request('/api/state')
    return request('/api/actions', dict(action=action,fields=fields,version=state['version'],request_id=str(uuid.uuid4())),state['csrf'])


def rows(name):
    # Read existing rows without invoking the new application or its initializer.
    script = "import sqlite3,json; d=sqlite3.connect('/data/planwise.sqlite3'); print(json.dumps({t:d.execute('SELECT * FROM '+t+' ORDER BY 1').fetchall() for t in ('users','plans','sessions')}))"
    return json.loads(docker('exec', name, 'python', '-c', script))


if __name__ == '__main__':
    suffix = uuid.uuid4().hex[:10]
    volume, name = 'nas-upgrade-'+suffix, 'nas-upgrade-'+suffix
    docker('volume', 'create', volume)
    try:
        start('planwise-nas:previous', volume, name)
        docker('exec', name, 'python', '-c', "from nas.database import Database; d=Database('/data/planwise.sqlite3'); d.create_user('existingadmin','Upgrade-test-password',True); d.create_user('existingmember','Upgrade-member-password')")
        request('/api/login', dict(username='existingadmin',password='Upgrade-test-password'))
        change('save',dict(title='Existing N1 goal',kind='goal',important='yes',target_hours='10'))
        today = request('/api/state')['view']['today']
        change('save_event',dict(title='Existing class',category='fixed',date=today,event_start='10:00',event_end='12:00',repeat='weekly'))
        change('save_event',dict(title='Existing personal time',category='private',date=today,event_start='18:00',event_end='19:00',repeat='daily'))
        previous = request('/api/state')
        before = rows(name)
        docker('exec', name, 'python', '-m', 'nas.manage', 'backup-db', '/data/before-upgrade.sqlite3')
        docker('rm', '-f', name)  # Only this uniquely named disposable CI container.
        health = start('planwise-nas:test', volume, name)
        assert health['version'] == '0.3.0', health
        assert rows(name) == before, 'Existing account, plan or session rows changed during startup.'
        current = request('/api/state')  # Reuse the old cookie, without signing in again.
        assert current['user'] == previous['user'] and current['state'] == previous['state']
        invitation = request('/api/invitations',dict(action='create'),current['csrf'])
        client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))
        request('/api/register',dict(invite_code=invitation['code'],username='invitedmember',password='Invited-test-password',password_confirm='Invited-test-password'))
        new = request('/api/state')
        assert not new['user']['is_admin'] and new['state']['tasks'] == []
        print('0.2.0 -> 0.3.0: accounts, full plans and sessions preserved; backup and invite registration passed.')
    finally:
        subprocess.run(['docker','rm','-f',name],check=False)
        subprocess.run(['docker','volume','rm',volume],check=False)
