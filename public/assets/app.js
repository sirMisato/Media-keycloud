'use strict';
const toast = message => { const el=document.createElement('div'); el.className='toast';el.setAttribute('role','status');el.textContent=message;document.body.append(el);setTimeout(()=>el.remove(),4000); };
// Native dialogs keep keyboard focus inside the sheet and restore it on close.
const openDialog = id => {
    const dialog = document.getElementById(id);
    if (!dialog || typeof dialog.showModal !== 'function') return false;
    document.querySelectorAll('dialog[open]').forEach(open => open.close());
    dialog.showModal();
    document.body.classList.add('modal-open');
    return true;
};
document.querySelectorAll('[data-open-dialog]').forEach(link => {
    link.addEventListener('click', event => {
        if (openDialog(link.dataset.openDialog)) event.preventDefault();
    });
});
document.querySelectorAll('dialog').forEach(dialog => {
    dialog.querySelectorAll('[data-close-dialog]').forEach(button => button.addEventListener('click', () => dialog.close()));
    dialog.addEventListener('close', () => document.body.classList.toggle('modal-open', !!document.querySelector('dialog[open]')));
    dialog.addEventListener('click', event => {
        const bounds = dialog.getBoundingClientRect();
        if (event.target === dialog && (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom)) dialog.close();
    });
});
let installPrompt = null;
const standalone = window.matchMedia('(display-mode: standalone)');
const setInstalled = () => document.querySelectorAll('[data-install], [data-install-area]').forEach(element => element.hidden = true);
if (standalone.matches || navigator.standalone) setInstalled();
standalone.addEventListener('change', event => { if (event.matches) setInstalled(); });
const ios = /iPad|iPhone|iPod/.test(navigator.userAgent) || (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);
document.querySelectorAll('[data-install-ios]').forEach(element => element.hidden = !ios);
document.querySelectorAll('[data-install-other]').forEach(element => element.hidden = ios);
window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault();
    installPrompt = event;
});
window.addEventListener('appinstalled', () => {
    installPrompt = null;
    setInstalled();
    document.getElementById('install-dialog')?.close();
    toast('Aplikasi berhasil ditambahkan.');
});
document.querySelectorAll('[data-install]').forEach(button => button.addEventListener('click', async () => {
    if (!installPrompt) { openDialog('install-dialog'); return; }
    const prompt = installPrompt;
    installPrompt = null; // An install event can only be consumed once.
    try {
        await prompt.prompt();
        const choice = await prompt.userChoice;
        if (choice.outcome === 'accepted') setInstalled();
    } catch {
        openDialog('install-dialog');
    }
}));
document.querySelectorAll('[data-share]').forEach(button=>button.addEventListener('click',async()=>{try{if(navigator.share)await navigator.share({title:document.title,url:location.href});else{await navigator.clipboard.writeText(location.href);toast('Tautan artikel disalin.');}}catch(error){if(error.name!=='AbortError')toast('Salin alamat artikel dari bilah alamat browser.');}}));
document.querySelectorAll('form[data-confirm]').forEach(form=>form.addEventListener('submit',event=>{if(!window.confirm(form.dataset.confirm))event.preventDefault();}));
const editor=document.querySelector('[data-editor]');
if(editor){let dirty=false;const body=editor.querySelector('[name=body]');const count=editor.querySelector('[data-word-count]');const update=()=>{count.textContent=`${body.value.trim().split(/\s+/u).filter(Boolean).length} kata · Simpan untuk menyimpan perubahan`;};editor.addEventListener('input',()=>{dirty=true;update();});editor.addEventListener('submit',()=>dirty=false);window.addEventListener('beforeunload',event=>{if(dirty){event.preventDefault();event.returnValue='';}});update();}
if('serviceWorker' in navigator && !/^\/(redaksi|masuk)(\/|$)/.test(location.pathname)) navigator.serviceWorker.register('/sw.js').catch(()=>{});
