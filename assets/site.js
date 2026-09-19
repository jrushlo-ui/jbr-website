const b=document.querySelector('.menu'),n=document.querySelector('.links');if(b&&n){const close=()=>{n.classList.remove('open');b.setAttribute('aria-expanded','false')};b.addEventListener('click',()=>{const o=n.classList.toggle('open');b.setAttribute('aria-expanded',String(o))});n.addEventListener('click',e=>{if(e.target.closest('a'))close()});document.addEventListener('keydown',e=>{if(e.key==='Escape')close()})}

const f=document.querySelector('#contact');
if(f)f.addEventListener('submit',async e=>{
  e.preventDefault();
  const s=document.querySelector('#status'),btn=f.querySelector('button[type="submit"]'),trap=f.querySelector('input[name="website"]');
  if(trap&&trap.value){f.reset();if(s){s.textContent='Thanks — your message has been received.';s.setAttribute('role','status')}return}
  if(btn){btn.disabled=true;btn.textContent='Sending…'}
  if(s){s.textContent='Sending your message…';s.setAttribute('role','status')}
  try{
    const r=await fetch(f.action,{method:'POST',body:new FormData(f),headers:{Accept:'application/json'}});
    if(r.ok){f.reset();if(s)s.textContent='Thanks — your message has been sent. JBR will respond within one business day.'}
    else{if(s)s.textContent='We couldn’t send your message. Please try again in a moment.'}
  }catch(_){if(s)s.textContent='We couldn’t send your message. Please check your connection and try again.'}
  finally{if(btn){btn.disabled=false;btn.textContent='Send Message →'}}
});