const b=document.querySelector('.menu'),n=document.querySelector('.links');if(b&&n){const close=()=>{n.classList.remove('open');b.setAttribute('aria-expanded','false')};b.addEventListener('click',()=>{const o=n.classList.toggle('open');b.setAttribute('aria-expanded',String(o))});n.addEventListener('click',e=>{if(e.target.closest('a'))close()});document.addEventListener('keydown',e=>{if(e.key==='Escape')close()})}

const f=document.querySelector('#contact');
let submitting=false;
if(f)f.addEventListener('submit',async e=>{
  e.preventDefault();
  if(submitting)return;
  const s=document.querySelector('#status'),btn=f.querySelector('button[type="submit"]'),trap=f.querySelector('input[name="website"]');
  if(trap&&trap.value){f.reset();if(s){s.textContent='Thanks — your message has been received.';s.setAttribute('role','status')}return}
  submitting=true;
  if(btn){btn.disabled=true;btn.textContent='Sending…'}
  if(s){s.textContent='Sending your message…';s.setAttribute('role','status')}
  try{
    const r=await fetch(f.action,{method:'POST',body:new FormData(f),headers:{Accept:'application/json'}});
    if(r.ok){trackEvent('generate_lead',{form_id:'contact',lead_source:'website_inquiry'});f.reset();if(s)s.textContent='Thanks — your message has been sent. JBR will respond within one business day.'}
    else{if(s)s.textContent='We couldn’t send your message. Please try again in a moment.'}
  }catch(_){if(s)s.textContent='We couldn’t send your message. Please check your connection and try again.'}
  finally{submitting=false;if(btn){btn.disabled=false;btn.textContent='Send Message →'}}
});

// Measure intent separately from successful inquiries. Never send form values to GA.
function trackEvent(name,params){
  try{if(typeof window.gtag==='function')window.gtag('event',name,params)}catch(_){}
}
document.addEventListener('click',e=>{
  const link=e.target.closest('a[href]');
  if(!link)return;
  const destination=new URL(link.href,window.location.href);
  if(destination.origin===window.location.origin&&destination.pathname==='/contact.html'){
    trackEvent('contact_click',{link_location:link.closest('main')?'main':link.closest('header')?'header':'footer',source_path:window.location.pathname});
  }
});
if(f)f.addEventListener('input',()=>trackEvent('inquiry_start',{form_id:'contact'}),{once:true});
