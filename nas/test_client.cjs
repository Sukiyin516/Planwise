// Browser-free checks for the cache-first client with an unreachable or stalled NAS.
const {test}=require('node:test');
const assert=require('node:assert/strict');
const vm=require('node:vm');
const fs=require('node:fs');
const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'static/ui.js'),'utf8');

function snapshot(version=1){
  return {api_version:1,user:{id:1,username:'demo',is_admin:false},version,saved_at:1,
    state:{language:'en',tasks:[{id:'task',title:'Cached essay',kind:'deadline',due:'2026-11-14',start:'',minutes:60,important:true,completed:false}],events:[],work_log:[],calendar:[],proposal:null,workdays:[0,1,2,3,4]},
    view:{today:'2026-11-12',cutoff:540,days:Array.from({length:7},(_,i)=>({date:`2026-11-${12+i}`,weekday:i%7,holiday:''})),ranks:{task:0},progress:{},available:[],occurrences:[],missing:[],preview:{same:[],removed:[],added:[]}}};
}
function boot(cache=snapshot(),query=''){
  const nodes=new Map(),timers=new Map(),calls=[],writes=[];let next=0,reply=null;
  const node=()=>({innerHTML:'',hidden:true,textContent:'',disabled:false,classList:{toggle(){},add(){},remove(){}},append(){},prepend(){},remove(){},scrollIntoView(){}});
  for(const key of ['#app','#bubble','#notice','#content','#offline-banner','#connection','#login-form','#login-language'])nodes.set(key,node());
  const writeButton=node();
  const storage=new Map(cache===null?[]:[['planwise-nas-snapshot-v1',typeof cache==='string'?cache:JSON.stringify(cache)]]);
  const context=vm.createContext({console,URLSearchParams,AbortController,structuredClone,Date,
    location:{search:query,origin:'http://nas.test:9473'},navigator:{userAgent:'PlanwiseNAS/0.2.0'},
    localStorage:{getItem:key=>storage.get(key)||null,setItem:(key,value)=>{storage.set(key,value);writes.push(key);},removeItem:key=>storage.delete(key)},
    document:{getElementById:()=>null,documentElement:{},body:{classList:{toggle(){}}},visibilityState:'visible',querySelector:key=>nodes.get(key)||null,querySelectorAll:selector=>selector.includes('[data-write]')?[writeButton]:[],createElement:node,addEventListener(){}},
    window:{addEventListener(){},isSecureContext:false,scrollTo(){}},history:{replaceState(){}},innerWidth:390,
    requestAnimationFrame:()=>{},setInterval:()=>1,
    setTimeout:(callback,delay)=>{const id=++next;timers.set(id,{callback,delay});return id;},clearTimeout:id=>timers.delete(id),
    fetch:(url,options)=>{calls.push({url,options});return reply?Promise.resolve({ok:true,json:async()=>reply}):new Promise((resolve,reject)=>options.signal.addEventListener('abort',()=>reject(new Error('aborted'))));}
  });
  vm.runInContext(source+'\nglobalThis.client={sync,change,command,isOffline:()=>offline,current:()=>snap};',context);
  return {client:context.client,nodes,calls,writes,writeButton,
    respond:data=>{reply=data;},advance:ms=>{for(const [id,timer] of timers)if(timer.delay<=ms){timers.delete(id);timer.callback();}},
    flush:()=>new Promise(resolve=>setImmediate(resolve)),timerDelays:()=>[...timers.values()].map(timer=>timer.delay)};
}

test('cold offline launch paints cached plan immediately, before any network result',async()=>{
  const app=boot();
  assert.match(app.nodes.get('#app').innerHTML,/Cached essay/);
  assert.match(app.nodes.get('#app').innerHTML,/Showing the last cached plan/);
  assert.equal(app.client.isOffline(),true);
  assert.equal(app.writeButton.disabled,true);
  assert.equal(app.calls.length,1);
  assert.deepEqual(app.writes,[]);
  assert.equal(await app.client.change('save',{title:'Offline attempt'}),false);
  assert.equal(app.calls.length,1);
});

test('stalled connection is aborted at eight seconds and keeps cached data visible',async()=>{
  const app=boot();
  assert.ok(app.timerDelays().includes(8000));
  app.advance(8000);await app.flush();
  assert.equal(app.calls[0].options.signal.aborted,true);
  assert.equal(app.client.isOffline(),true);
  assert.equal(app.client.current().state.tasks[0].title,'Cached essay');
  assert.equal(app.writeButton.disabled,true);
});

test('refresh reconnects, loads latest version, then enables editing',async()=>{
  const app=boot();app.advance(8000);await app.flush();
  const latest=snapshot(2);latest.csrf='online-session-token';app.respond(latest);
  await app.client.sync(true);
  assert.equal(app.client.current().version,2);
  assert.equal(app.client.isOffline(),false);
  assert.equal(app.writeButton.disabled,false);
  const saved=app.nodes.get('#app').innerHTML;
  assert.doesNotMatch(saved,/Showing the last cached plan/);
});

test('mobile defaults to all seven columns and retains explicit day view',async()=>{
  const app=boot(snapshot(),'?tab=schedule');
  assert.equal((app.nodes.get('#app').innerHTML.match(/class="day-head /g)||[]).length,7);
  assert.match(app.nodes.get('#app').innerHTML,/week-view/);
  await app.client.command('span-day');
  assert.equal((app.nodes.get('#app').innerHTML.match(/class="day-head /g)||[]).length,1);
  await app.client.command('span-week');
  assert.equal((app.nodes.get('#app').innerHTML.match(/class="day-head /g)||[]).length,7);
});

test('first use without cache shows sign-in immediately and a retry after timeout',async()=>{
  const app=boot(null);
  assert.match(app.nodes.get('#app').innerHTML,/login-form/);
  app.advance(8000);await app.flush();
  assert.match(app.nodes.get('#app').innerHTML,/retry-connect/);
  assert.match(app.nodes.get('#app').innerHTML,/首次登入需要連線/);
});

test('invalid cache cannot turn a cold launch into an empty page',()=>{
  for(const broken of ['{bad json','{"api_version":1,"user":{},"view":{},"state":{"tasks":2}}']){
    const app=boot(broken);assert.match(app.nodes.get('#app').innerHTML,/login-form/);
  }
});
