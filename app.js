/* Interaction only. Python validates and saves every scheduling decision. */
(() => {
  let bubble = document.querySelector('.anchor-bubble');
  let opener = null;
  let anchorPoint = null;
  let drag = null;
  let suppressClickUntil = 0;
  const toast = document.querySelector('.ui-toast');
  const token = document.querySelector('meta[name="csrf-token"]').content;
  const scrollKey = 'planwise-calendar-scroll-'+(new URLSearchParams(location.search).get('span') || 'week');
  const translations=fetch('/translations').then(r=>r.json()).catch(()=>({}));
  let words={};
  translations.then(result=>{words=result;});
  const tr=text=>words[text] || text;
  const params=new URLSearchParams(location.search);
  if (matchMedia('(max-width:600px)').matches && params.get('tab')==='schedule' && !params.has('span')) {
    params.set('span','day');
    location.replace('/?'+params);
    return;
  }
  let toastTimer;

  function message(text) {
    toast.textContent = tr(text);
    toast.hidden = false;
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => { toast.hidden = true; }, 5000);
  }
  function saveScroll() {
    const scroller = document.querySelector('.calendar-scroll');
    if (scroller) {
      try { sessionStorage.setItem(scrollKey, JSON.stringify({top:scroller.scrollTop,left:scroller.scrollLeft})); } catch (_) {}
    }
  }
  function closeBubble() {
    if (!bubble) return;
    bubble.remove();
    bubble = null;
    opener?.focus({preventScroll:true});
  }
  function placeBubble() {
    if (!bubble) return;
    const gap = 12;
    const w = Math.min(350, innerWidth - 24);
    bubble.style.width = `${w}px`;
    const viewportH=Math.min(innerHeight,window.visualViewport?.height || innerHeight,window.outerHeight || innerHeight);
    bubble.style.maxHeight=`${viewportH-36}px`;
    bubble.querySelector('.bubble-body').style.maxHeight=`${viewportH-38}px`;
    const height = Math.min(bubble.getBoundingClientRect().height, viewportH - 36);
    const p = anchorPoint || {x:innerWidth/2,y:innerHeight/2};
    let left = p.x + 20;
    if (left + w > innerWidth - gap) left = p.x - w - 20;
    left = Math.max(gap, Math.min(left, innerWidth-w-gap));
    const top = Math.max(18, Math.min(p.y-70, viewportH-height-18));
    bubble.style.left = `${left}px`;
    bubble.style.top = `${top}px`;
    bubble.style.transformOrigin = `${p.x-left}px ${p.y-top}px`;
    const arrow = bubble.querySelector('.bubble-arrow');
    arrow.style.top = `${Math.max(22,Math.min(p.y-top,height-24))}px`;
    arrow.classList.toggle('on-right', p.x > left+w/2);
  }
  function pointFor(anchor, event) {
    const dot = anchor.querySelector('.point-dot');
    const rect = (dot || anchor).getBoundingClientRect();
    return event?.clientX ? {x:event.clientX,y:event.clientY} : {x:rect.left+rect.width/2,y:rect.top+rect.height/2};
  }
  async function openBubble(anchor, event) {
    await translations;
    const internal = !!anchor.closest('.anchor-bubble');
    if (!internal) {
      opener = anchor;
      anchorPoint = pointFor(anchor,event);
    }
    const url = new URL(anchor.getAttribute('href'),location.origin);
    url.pathname = '/bubble';
    if (anchor.dataset.entity === 'task') {
      url.searchParams.set('source_date',anchor.dataset.date);
      url.searchParams.set('source_start',stamp(Number(anchor.dataset.start)));
      url.searchParams.set('source_end',stamp(Number(anchor.dataset.end)));
    }
    try {
      const response = await fetch(url, {headers:{'X-Requested-With':'bubble'}});
      if (!response.ok) throw new Error(tr('無法載入任務，請稍後再試。'));
      const holder = document.createElement('div');
      holder.innerHTML = await response.text();
      const next = holder.querySelector('.anchor-bubble');
      if (!next) throw new Error(tr('無法載入詳情。'));
      bubble?.remove();
      bubble = next;
      document.body.append(bubble);
      placeBubble();
      if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
        bubble.animate([{opacity:0,transform:'scale(.08)'},{opacity:1,transform:'scale(1)'}],{duration:220,easing:'cubic-bezier(.2,.8,.25,1)'});
      }
      bubble.focus({preventScroll:true});
    } catch (error) { message(error.message); }
  }
  async function post(data) {
    await translations;
    data.set('token',token);
    const response = await fetch('/', {method:'POST',body:data,headers:{Accept:'application/json'}});
    const type = response.headers.get('Content-Type') || '';
    if (!type.includes('application/json')) throw new Error(tr('頁面已過期，請重新整理後再試。'));
    const result = await response.json();
    if (!response.ok || !result.ok) throw new Error(result.error || tr('修改未儲存。'));
    return result;
  }
  function stamp(minute) {
    return `${String(Math.floor(minute/60)).padStart(2,'0')}:${String(minute%60).padStart(2,'0')}`;
  }
  document.addEventListener('click', event => {
    const close = event.target.closest('[data-close-bubble]');
    if (close) { event.preventDefault(); closeBubble(); return; }
    if (Date.now() < suppressClickUntil) { event.preventDefault(); return; }
    const jump = event.target.closest('[data-scroll-hour]');
    if (jump) {
      const scroller = document.querySelector('.calendar-scroll');
      scroller.scrollTop = Number(jump.dataset.scrollHour)*60;
      saveScroll();
      return;
    }
    const anchor = event.target.closest('a[data-bubble],a.map-point');
    if (anchor) { event.preventDefault(); openBubble(anchor,event); return; }
    if (bubble && !event.target.closest('.anchor-bubble')) closeBubble();
  });
  document.addEventListener('keydown', event => {
    if (event.key === 'Escape') { closeBubble(); if (drag) cleanupDrag(); }
  });
  document.addEventListener('submit', async event => {
    const form = event.target;
    if (form.id==='import-form') {
      event.preventDefault();
      const button=event.submitter;
      if(button)button.disabled=true;
      try {
        const result=await post(new URLSearchParams(new FormData(form)));
        location.assign(result.redirect);
      } catch(error) { message(error.message); if(button)button.disabled=false; }
      return;
    }
    if (!form.closest('.anchor-bubble')) { saveScroll(); return; }
    event.preventDefault();
    const button = event.submitter;
    if (button) button.disabled = true;
    try {
      const data = new URLSearchParams(new FormData(form));
      if (button?.name) data.set(button.name,button.value);
      const result = await post(data);
      saveScroll();
      location.assign(result.redirect);
    } catch (error) {
      let errorBox = bubble?.querySelector('.bubble-error');
      if (!errorBox && bubble) { errorBox=document.createElement('p'); errorBox.className='bubble-error'; errorBox.setAttribute('role','alert'); bubble.querySelector('.bubble-body').prepend(errorBox); }
      if (errorBox) errorBox.textContent = error.message;
      else message(error.message);
      if (button) button.disabled = false;
    }
  });

  function cleanupDrag() {
    if (!drag) return;
    drag.copy?.remove();
    drag.marker?.remove();
    drag.source.classList.remove('drag-origin');
    drag = null;
  }
  document.addEventListener('pointerdown', event => {
    const source = event.target.closest('.event[data-draggable="true"]');
    if (!source || (event.pointerType==='mouse' && event.button!==0)) return;
    closeBubble();
    const rect=source.getBoundingClientRect();
    drag={source,x:event.clientX,y:event.clientY,grabX:event.clientX-rect.left,grabY:event.clientY-rect.top,rect,active:false,pointerId:event.pointerId,target:null};
    source.setPointerCapture(event.pointerId);
  });
  document.addEventListener('pointermove', event => {
    if (!drag || drag.pointerId!==event.pointerId) return;
    if (!drag.active && Math.hypot(event.clientX-drag.x,event.clientY-drag.y)<7) return;
    event.preventDefault();
    if (!drag.active) {
      drag.active=true;
      drag.source.classList.add('drag-origin');
      drag.copy=drag.source.cloneNode(true);
      drag.copy.removeAttribute('id');
      drag.copy.classList.add('drag-copy');
      Object.assign(drag.copy.style,{position:'fixed',width:`${drag.rect.width}px`,height:`${drag.rect.height}px`,pointerEvents:'none',zIndex:'100'});
      document.body.append(drag.copy);
    }
    drag.copy.style.left=`${event.clientX-drag.grabX}px`;
    drag.copy.style.top=`${event.clientY-drag.grabY}px`;
    const scroller=drag.source.closest('.calendar-scroll');
    const bounds=scroller.getBoundingClientRect();
    if(event.clientY<bounds.top+90)scroller.scrollTop-=10;
    if(event.clientY>bounds.bottom-30)scroller.scrollTop+=10;
    if(event.clientX<bounds.left+65)scroller.scrollLeft-=10;
    if(event.clientX>bounds.right-25)scroller.scrollLeft+=10;
    const column=document.elementFromPoint(event.clientX,event.clientY)?.closest('.day-column');
    drag.target=null;
    drag.marker?.remove();
    if (!column) return;
    const rect=column.getBoundingClientRect();
    const minute=Math.round((event.clientY-rect.top-drag.grabY)/30)*30;
    const duration=Number(drag.source.dataset.end)-Number(drag.source.dataset.start);
    if (minute<0 || minute+duration>1440) return;
    drag.target={date:column.dataset.date,start:minute};
    drag.marker=document.createElement('div');
    drag.marker.className='drop-marker';
    drag.marker.textContent=`${stamp(minute)}–${stamp(minute+duration)}`;
    drag.marker.style.top=`${minute}px`;
    drag.marker.style.height=`${duration}px`;
    column.append(drag.marker);
  },{passive:false});
  document.addEventListener('pointerup', async event => {
    if (!drag || event.pointerId!==drag.pointerId) return;
    if (!drag.active) { cleanupDrag(); return; }
    const {source,target}=drag;
    suppressClickUntil=Date.now()+700;
    cleanupDrag();
    if (!target) { message('請放到行程表內的半小時空格。'); return; }
    const data=new URLSearchParams({action:source.dataset.entity==='event'?'move_event':'move_block',id:source.dataset.id,tab:'schedule',source_date:source.dataset.date,source_start:stamp(Number(source.dataset.start)),source_end:stamp(Number(source.dataset.end)),new_date:target.date,new_start:stamp(target.start)});
    if (source.dataset.occurrence) data.set('occurrence_date',source.dataset.occurrence);
    try {
      const result=await post(data);
      saveScroll();
      location.assign(result.redirect);
    } catch (error) { message(error.message); }
  });
  document.addEventListener('pointercancel', cleanupDrag);
  function followAnchor(event) {
    if (!bubble || bubble.contains(event.target)) return;
    if (opener?.isConnected) anchorPoint=pointFor(opener);
    placeBubble();
  }
  window.addEventListener('resize',followAnchor);
  document.addEventListener('scroll',followAnchor,{capture:true,passive:true});

  const input=document.querySelector('#import-file');
  input?.addEventListener('change',async()=>{
    await translations;
    const file=input.files[0];
    if(!file)return;
    const textarea=document.querySelector('#backup-json');
    textarea.value='';
    try {
      if(file.size>2000000)throw new Error(tr('檔案不能超過 2 MB。'));
      const text=await file.text();
      JSON.parse(text);
      textarea.value=text;
      document.querySelector('#import-preview').textContent=file.name;
    } catch(error) {input.value='';message(error instanceof SyntaxError?tr('備份檔格式不正確，原有資料未更改。'):error.message || tr('無法讀取備份檔。'));}
  });

  const scroller=document.querySelector('.calendar-scroll');
  if(scroller) {
    let saved;
    try { saved=JSON.parse(sessionStorage.getItem(scrollKey)); } catch (_) {}
    scroller.scrollTop=saved?.top ?? Number(scroller.dataset.initialHour)*60;
    scroller.scrollLeft=saved?.left ?? 0;
    scroller.addEventListener('scroll',saveScroll,{passive:true});
  }
  if (bubble) {
    const id=bubble.dataset.anchorId;
    opener=id?document.querySelector(`[data-id="${CSS.escape(id)}"],.map-point[href*="${CSS.escape(id)}"]`):null;
    anchorPoint=opener?pointFor(opener):{x:innerWidth/2,y:innerHeight/2};
    placeBubble();
  }
})();
