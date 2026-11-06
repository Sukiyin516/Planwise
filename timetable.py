"""Half-hour clock slots and explicit approval of earlier task moves."""
from datetime import date, timedelta
import secrets
from events import event_cells


def clock(value):
    try:
        hour, minute = map(int, value.split(':'))
    except (ValueError, AttributeError):
        raise ValueError('請填寫時間，例如 18:00 或 18:30。') from None
    if not 0 <= hour <= 24 or minute not in (0,30) or (hour == 24 and minute):
        raise ValueError('時間以半小時為單位，範圍為 00:00–24:00。')
    return hour*60+minute


def stamp(value):
    return f'{value//60:02}:{value%60:02}'


def day_windows(state, day):
    if state.get('time_model')=='free':
        return [[0,1440]]
    if day in state.get('availability', {}):
        return state['availability'][day]
    amount = state['capacity'].get(day, 0)
    begin = min(18*60,1440-amount)
    return [[begin,begin+amount]] if amount else []


def occupied(state, day):
    cells = set()
    legacy_windows=state.get('availability',{}).get(day)
    if legacy_windows is None:
        amount=state['capacity'].get(day,0)
        begin=min(1080,1440-amount)
        legacy_windows=[[begin,begin+amount]] if amount else []
    fallback = [minute for a,b in legacy_windows for minute in range(a,b,30)]
    for row in state['work_log']:
        if row['date'] != day:
            continue
        if 'start' in row:
            cells.update(range(row['start'],row['end'],30))
        else:
            # shortcut: v2 recorded daily totals only; place them at the beginning of availability.
            candidates = [minute for minute in fallback if minute not in cells]
            cells.update(candidates[:row['minutes']//30])
    return cells


def available_cells(state, today, not_before=0, include_private=False):
    result = set()
    blocked=event_cells(state,today,'fixed')
    if not include_private:blocked|=event_cells(state,today,'private')
    for i in range(7):
        day = (today+timedelta(days=i)).isoformat()
        used = occupied(state,day)
        for begin,end in day_windows(state,day):
            result.update((day,t) for t in range(begin,end,30) if t not in used and (day,t) not in blocked and (i or t >= not_before))
    return result


def may_borrow(state,task,today):
    return state.get('borrow_private',False) and today.isoformat()<=task['due']<=(today+timedelta(days=3)).isoformat()


def task_cells(state,task,today,not_before=0):
    return {cell for cell in available_cells(state,today,not_before,include_private=may_borrow(state,task,today)) if max(today.isoformat(),task['start'] or today.isoformat())<=cell[0]<=task['due']}


def cells(blocks):
    return {(b['date'],m):b['task_id'] for b in blocks for m in range(b['start'],b['end'],30)}


def blocks_from_cells(mapping):
    blocks = []
    for (day,minute),ident in sorted(mapping.items()):
        if blocks and blocks[-1]['date'] == day and blocks[-1]['task_id'] == ident and blocks[-1]['end'] == minute:
            blocks[-1]['end'] += 30
        else:
            blocks.append(dict(task_id=ident,date=day,start=minute,end=minute+30))
    return blocks


def candidate(state,today,not_before=0):
    free = available_cells(state,today,not_before)
    result,missing = {},[]
    tasks = [t for t in state['tasks'] if t['kind']=='deadline' and not t['completed']]
    remaining={t['id']:t['minutes']//30 for t in tasks}
    by_id={t['id']:t for t in tasks}
    for block in state.get('pins',[]):
        task=by_id.get(block['task_id'])
        if not task:continue
        allowed=task_cells(state,task,today,not_before)
        for cell in sorted(cells([block])):
            if cell in allowed and cell not in result and remaining[task['id']]>0:
                result[cell]=task['id']
                free.discard(cell)
                remaining[task['id']]-=1
    for task in sorted(tasks,key=lambda t:(t['due'],not t['important'],t['id'])):
        eligible = sorted(cell for cell in free if max(today.isoformat(),task['start'] or today.isoformat()) <= cell[0] <= task['due'])
        chosen = eligible[:remaining[task['id']]]
        for cell in chosen:
            result[cell] = task['id']
            free.remove(cell)
        left = (remaining[task['id']]-len(chosen))*30
        if left and may_borrow(state,task,today):
            extra=sorted(task_cells(state,task,today,not_before).difference(result))[:left//30]
            for cell in extra:
                result[cell]=task['id']
                free.discard(cell)
            left-=len(extra)*30
        if left:
            end = (today+timedelta(days=6)).isoformat()
            reason = 'overdue' if task['due'] < today.isoformat() else ('outside_week' if task['due'] > end else 'deadline_capacity')
            missing.append((task,left,reason))
    return blocks_from_cells(result),missing


def clean_calendar(state,today,not_before=0):
    free = available_cells(state,today,not_before,include_private=True)
    tasks = {t['id']:t for t in state['tasks'] if t['kind']=='deadline' and not t['completed']}
    left = {ident:t['minutes'] for ident,t in tasks.items()}
    result = {}
    for cell,ident in sorted(cells(state.get('calendar',[])).items()):
        task = tasks.get(ident)
        if task and cell in free and cell in task_cells(state,task,today,not_before) and left[ident] >= 30:
            result[cell]=ident
            free.remove(cell)
            left[ident]-=30
    return blocks_from_cells(result)


def refresh(state,today,propose=False,not_before=0):
    valid={}
    tasks={t['id']:t for t in state['tasks'] if t['kind']=='deadline' and not t['completed']}
    for cell,ident in cells(state.get('pins',[])).items():
        if ident in tasks and cell in task_cells(state,tasks[ident],today,not_before):valid[cell]=ident
    state['pins']=blocks_from_cells(valid)
    after,_ = candidate(state,today,not_before)
    if propose:
        before = clean_calendar(state,today,not_before)
        # Existing accepted slots come first. Allocate only missing work into the gaps.
        stable=dict(state,pins=before)
        before,_=candidate(stable,today,not_before)
        state['calendar']=before
        old,new = cells(before),cells(after)
        moved = {ident for cell,ident in new.items() if old.get(cell)!=ident and ident in old.values()}
        state['proposal'] = dict(id=secrets.token_hex(8),date=today.isoformat(),after=after) if moved else None
    else:
        state['calendar']=after
        state['proposal']=None
    state['calendar_day']=today.isoformat()
    state['calendar_model']='events-v4'


def initialize(state,today,not_before=0):
    if state.get('calendar_day') != today.isoformat() or state.get('calendar_model')!='events-v4':
        refresh(state,today,propose=bool(state.get('calendar_day')),not_before=not_before)


def decide(state,decision,revision,today):
    proposal=state.get('proposal')
    if not proposal or proposal['id']!=revision or proposal['date']!=today.isoformat():
        raise ValueError('前移建議已更新，請重新整理後再確認。')
    if decision=='confirm_move':
        state['calendar']=proposal['after']
    elif decision!='keep_plan':
        raise ValueError('未知的排程選擇。')
    state['proposal']=None


def update_windows(state,data,today):
    updates={}
    for i in range(7):
        day=(today+timedelta(days=i)).isoformat()
        windows=[]
        for index in range(2):
            a=data.get(f'{day}_start_{index}',[''])[0]
            b=data.get(f'{day}_end_{index}',[''])[0]
            if not a and not b:
                continue
            begin,end=clock(a),clock(b)
            if begin>=end:
                raise ValueError('時段結束必須晚於開始。休息日請留空。')
            windows.append([begin,end])
        windows.sort()
        if any(a[1]>b[0] for a,b in zip(windows,windows[1:])):
            raise ValueError('同一天的可用時段不能重疊。')
        updates[day]=windows
    state.setdefault('availability',{}).update(updates)
    state['time_model']='custom'
    for day,windows in updates.items():
        state['capacity'][day]=sum(b-a for a,b in windows)


def record_clock(state,data,today):
    """Validate clock information before planner.mutate records actual effort."""
    from planner import minutes
    begin=clock(data.get('session_start',[''])[0])
    amount=minutes(data.get('actual',[''])[0])
    end=begin+amount
    if amount<=0 or end>1440:
        raise ValueError('實際投入至少半小時，且不能跨過午夜。')
    if occupied(state,today.isoformat()).intersection(range(begin,end,30)):
        raise ValueError('這段時間已記錄過投入，請檢查開始時間。')
    return begin,end


def preview_parts(state):
    old=cells(state.get('calendar',[]))
    proposal=state.get('proposal')
    if not proposal:
        return state.get('calendar',[]),[],[]
    new=cells(proposal['after'])
    same={cell:ident for cell,ident in old.items() if new.get(cell)==ident}
    removed={cell:ident for cell,ident in old.items() if new.get(cell)!=ident}
    added={cell:ident for cell,ident in new.items() if old.get(cell)!=ident}
    return blocks_from_cells(same),blocks_from_cells(removed),blocks_from_cells(added)


def move_block(state,data,today,not_before=0):
    def field(key):return data.get(key,[''])[0]
    try:
        source=dict(task_id=field('id'),date=date.fromisoformat(field('source_date')).isoformat(),start=clock(field('source_start')),end=clock(field('source_end')))
        new_day=date.fromisoformat(field('new_date')).isoformat()
        begin=clock(field('new_start'))
    except (ValueError,TypeError):raise ValueError('拖動時段不正確。') from None
    if source not in state.get('calendar',[]):
        raise ValueError('這段安排已更新，請重新整理後再拖動。')
    task=next((t for t in state['tasks'] if t['id']==source['task_id'] and not t['completed']),None)
    if task is None:raise ValueError('找不到這份待做任務。')
    length=source['end']-source['start']
    if begin+length>1440:raise ValueError('任務不能拖過午夜；可先分成較短時段。')
    old=cells(state['calendar'])
    source_cells=set(cells([source]))
    new_cells={(new_day,m) for m in range(begin,begin+length,30)}
    if not new_cells.issubset(task_cells(state,task,today,not_before)):
        raise ValueError('這裡有固定事項、受保護私人時間，或超出任務期限／可規劃範圍。')
    if new_cells.intersection(set(old)-source_cells):
        raise ValueError('這段時間已有其他任務，請選擇空檔。')
    mapping={cell:ident for cell,ident in old.items() if cell not in source_cells}
    mapping.update({cell:task['id'] for cell in new_cells})
    state['calendar']=blocks_from_cells(mapping)
    pins={cell:ident for cell,ident in cells(state.get('pins',[])).items() if cell not in source_cells}
    pins.update({cell:task['id'] for cell in new_cells})
    state['pins']=blocks_from_cells(pins)
