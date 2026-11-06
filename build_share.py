"""Build the source-only desktop share ZIP; never include private JSON or Android artifacts."""
from pathlib import Path
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED
import stat

ROOT=Path(__file__).resolve().parent
output=ROOT/'output'/'Planwise-v5.1-Mac-Windows.zip'
files={p.name:p for p in (ROOT/'distribution').iterdir() if p.is_file()}
for name in ('main.py','planner.py','storage.py','timetable.py','events.py','holidays.py','i18n.py','translations.json','app.js','style.css','test_planner.py','test_timetable.py','test_events.py','test_preferences.py','test_schedule_changes.py'):
    files['app/'+name]=ROOT/name
for name in ('README.md','SPEC.md','TESTING.md','REVIEW.md'):
    files['docs/'+name]=ROOT/name
output.parent.mkdir(exist_ok=True)
with ZipFile(output,'w',ZIP_DEFLATED) as archive:
    for name,path in sorted(files.items()):
        info=ZipInfo('Planwise-v5.1/'+name)
        info.create_system=3
        info.external_attr=(stat.S_IFREG | (0o755 if name.endswith('.command') else 0o644)) << 16
        info.compress_type=ZIP_DEFLATED
        data=path.read_bytes()
        if name.endswith('.bat'):data=data.replace(b'\r\n',b'\n').replace(b'\n',b'\r\n')
        archive.writestr(info,data)
with ZipFile(output) as archive:
    assert archive.testzip() is None
    assert all(not name.endswith(('.apk','.bak')) for name in archive.namelist())
    assert all(not name.endswith('.json') or name.endswith('/translations.json') for name in archive.namelist())
print(output)
