"""Run with python -m nas.manage. Passwords are prompted, never command arguments."""
import argparse
import getpass
import os
import sys
from werkzeug.security import generate_password_hash
from nas.database import Database, password_valid


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--database',default=os.environ.get('PLANWISE_DATABASE','/data/planwise.sqlite3'))
    commands = parser.add_subparsers(dest='command',required=True)
    create = commands.add_parser('create-user')
    create.add_argument('username')
    create.add_argument('--admin',action='store_true')
    reset = commands.add_parser('reset-password')
    reset.add_argument('username')
    backup = commands.add_parser('backup-db')
    backup.add_argument('destination')
    args = parser.parse_args()
    store = Database(args.database)
    try:
        if args.command=='backup-db':
            store.backup_to(args.destination)
            print('Database backup saved.')
            return
        password = getpass.getpass('New password (12+ characters): ')
        if password != getpass.getpass('Repeat password: '):
            raise ValueError('Passwords do not match.')
        password_valid(password)
        if args.command=='create-user':
            store.create_user(args.username,password,args.admin)
        else:
            with store.transaction() as db:
                user = db.execute('SELECT id FROM users WHERE username=?',(args.username,)).fetchone()
                if user is None:
                    raise ValueError('Account not found.')
                db.execute('UPDATE users SET password_hash=? WHERE id=?',(generate_password_hash(password,method='scrypt'),user['id']))
                db.execute('DELETE FROM sessions WHERE user_id=?',(user['id'],))
        print('Account updated. Other plans were not changed.')
    except (ValueError,OSError) as exc:
        print(str(exc),file=sys.stderr)
        sys.exit(1)


if __name__=='__main__':
    main()
