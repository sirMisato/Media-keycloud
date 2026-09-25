'use strict';
const toast = message => { const el=document.createElement('div'); el.className='toast';el.setAttribute('role','status');el.textContent=message;document.body.append(el);setTimeout(()=>el.remove(),4000); };
let installPrompt;
window.addEventListener('beforeinstallprompt',event=>{event.preventDefault();installPrompt=event;document.querySelectorAll('[data-install]').forEach(button=>button.hidden=false);});
document.querySelectorAll('[data-install]').forEach(button=>button.addEventListener('click',async()=>{if(!installPrompt)return;await installPrompt.prompt();installPrompt=null;button.hidden=true;}));
document.querySelectorAll('[data-share]').forEach(button=>button.addEventListener('click',async()=>{try{if(navigator.share)await navigator.share({title:document.title,url:location.href});else{await navigator.clipboard.writeText(location.href);toast('Tautan artikel disalin.');}}catch(error){if(error.name!=='AbortError')toast('Salin alamat artikel dari bilah alamat browser.');}}));
document.querySelectorAll('form[data-confirm]').forEach(form=>form.addEventListener('submit',event=>{if(!window.confirm(form.dataset.confirm))event.preventDefault();}));
const editor=document.querySelector('[data-editor]');
if(editor){let dirty=false;const body=editor.querySelector('[name=body]');const count=editor.querySelector('[data-word-count]');const update=()=>{count.textContent=`${body.value.trim().split(/\s+/u).filter(Boolean).length} kata · Simpan untuk menyimpan perubahan`;};editor.addEventListener('input',()=>{dirty=true;update();});editor.addEventListener('submit',()=>dirty=false);window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});update();}
if('serviceWorker' in navigator && !/^\/(redaksi|masuk)(\/|$)/.test(location.pathname)) navigator.serviceWorker.register('/sw.js').catch(()=>{});
