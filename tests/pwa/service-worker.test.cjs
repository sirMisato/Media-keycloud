'use strict';
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const vm = require('node:vm');
const source = readFileSync('public/sw.js', 'utf8');

function harness({ offline = false } = {}) {
    const listeners = {};
    const stored = [];
    const deleted = [];
    const assets = new Map([['/offline.html', new Response('Sedang offline')], ['/assets/media.css', new Response('cached shell')]]);
    const context = {
        URL,
        self: { location: { origin: 'https://media.example' }, addEventListener: (type, callback) => listeners[type] = callback, skipWaiting() {}, clients: { claim: async () => {} } },
        caches: {
            open: async () => ({ addAll: async urls => stored.push(...urls), put: async (key, value) => { stored.push(key); assets.set(key, value); } }),
            match: async key => assets.get(key)?.clone(),
            keys: async () => ['mahad-shell-v1', 'mahad-shell-v2', 'unrelated-app'],
            delete: async key => deleted.push(key),
        },
        fetch: async () => { if (offline) throw new Error('offline'); return new Response('fresh response'); },
    };
    vm.runInNewContext(source, context);
    async function request(path, { method = 'GET', mode = 'navigate' } = {}) {
        let response;
        const work = [];
        listeners.fetch({ request: { url: new URL(path, context.self.location.origin).href, method, mode }, respondWith: result => response = result, waitUntil: result => work.push(result) });
        await Promise.all(work);
        return response;
    }
    async function lifecycle(name) { const work = []; listeners[name]({ waitUntil: result => work.push(result) }); await Promise.all(work); }
    return { request, lifecycle, stored, deleted };
}

test('private routes, uploaded covers, POST and external requests bypass the service worker', async () => {
    const worker = harness({ offline: true });
    for (const path of ['/masuk', '/redaksi', '/redaksi/revisi/9/pratinjau', '/media/cover.jpg', '/up']) {
        assert.equal(await worker.request(path), undefined, path);
    }
    assert.equal(await worker.request('/artikel', { method: 'POST' }), undefined);
    assert.equal(await worker.request('https://other.example/'), undefined);
    assert.deepEqual(worker.stored, []);
});

test('public navigation is network only, with an offline notice instead of stale articles', async () => {
    const online = harness();
    assert.equal(await (await online.request('/baca/artikel')).text(), 'fresh response');
    assert.equal(await (await online.request('/profil-mahad-aly')).text(), 'fresh response');
    assert.deepEqual(online.stored, []);
    const offline = harness({ offline: true });
    assert.equal(await (await offline.request('/baca/ditarik-redaksi')).text(), 'Sedang offline');
    assert.deepEqual(offline.stored, []);
});

test('versioned shell assets work offline, while arbitrary files and query strings are never cached', async () => {
    const online = harness();
    assert.equal(await (await online.request('/assets/media.css?v=abc123def456', { mode: 'cors' })).text(), 'fresh response');
    assert.deepEqual(online.stored, ['/assets/media.css']);
    const offline = harness({ offline: true });
    assert.equal(await (await offline.request('/assets/media.css?v=abc123def456', { mode: 'cors' })).text(), 'cached shell');
    assert.equal(await offline.request('/assets/private.json', { mode: 'cors' }), undefined);
    assert.equal(await offline.request('/assets/media.css?token=anything', { mode: 'cors' }), undefined);
});

test('install only stores public shell and activation retires this app’s old cache', async () => {
    const worker = harness();
    await worker.lifecycle('install');
    assert(worker.stored.includes('/offline.html'));
    assert(worker.stored.includes('/assets/media.css'));
    assert(!worker.stored.some(path => /^\/(baca|media|redaksi|masuk)(\/|$)/.test(path)));
    await worker.lifecycle('activate');
    assert.deepEqual(worker.deleted, ['mahad-shell-v1']);
});
