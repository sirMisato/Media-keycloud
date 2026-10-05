'use strict';
const { chromium, devices } = require(process.env.MEDIA_PLAYWRIGHT_MODULE || 'playwright');
const assert = require('node:assert/strict');
const { mkdirSync, writeFileSync } = require('node:fs');
const path = require('node:path');
const base = process.env.MEDIA_TEST_URL || 'http://127.0.0.1:8085';
const output = process.env.MEDIA_BROWSER_OUTPUT || '/tmp/media-browser-results';
mkdirSync(output, { recursive: true });

(async () => {
    const browser = await chromium.launch();
    const context = await browser.newContext({ viewport: { width: 1440, height: 1000 } });
    const page = await context.newPage();
    const errors = [];
    const checks = [];
    page.on('pageerror', error => errors.push(error.message));
    page.on('console', message => { if (message.type() === 'error') errors.push(message.text()); });
    const capture = name => page.screenshot({ path: path.join(output, name + '.png'), fullPage: true });
    try {
        for (const width of [1440, 390, 320, 768]) {
            await page.setViewportSize({ width, height: 900 });
            for (const route of ['/', '/profil-mahad-aly', '/artikel', '/baca/demo-1']) {
                const response = await page.goto(base + route, { waitUntil: 'networkidle' });
                assert.equal(response.status(), 200, `${width}: ${route}`);
                assert(await page.locator('h1').innerText());
                assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), `Horizontal overflow: ${width} ${route}`);
                if ([1440, 390].includes(width) && ['/', '/profil-mahad-aly', '/baca/demo-1'].includes(route)) {
                    await capture(`${width}-${route === '/' ? 'home' : route === '/profil-mahad-aly' ? 'profile' : 'article'}`);
                }
            }
            checks.push(`Routes and no overflow at ${width}px`);
        }
        await page.setViewportSize({ width: 390, height: 844 });
        await page.goto(base, { waitUntil: 'networkidle' });
        await page.locator('.mobile-nav [data-open-dialog="menu-dialog"]').click();
        assert(await page.locator('#menu-dialog').isVisible());
        await page.keyboard.press('Escape');
        assert(!(await page.locator('#menu-dialog').isVisible()));
        assert.equal(await page.evaluate(() => document.activeElement.dataset.openDialog), 'menu-dialog');
        await page.locator('.mobile-nav [data-open-dialog="search-dialog"]').click();
        await page.locator('#dialog-query').fill('kitab');
        await page.locator('#dialog-query').press('Enter');
        await page.waitForURL('**/artikel?q=kitab');
        assert.match(await page.locator('#content').innerText(), /Kitab kuning/);
        checks.push('Mobile menu, focus restoration, search submission and results');
        await page.locator('.mobile-nav a[href$="/profil-mahad-aly"]').click();
        await page.waitForURL('**/profil-mahad-aly');
        assert.equal(await page.locator('.mobile-nav a[aria-current="page"]').innerText(), 'Profil');
        await page.evaluate(() => window.scrollTo(0, document.body.scrollHeight));
        assert(await page.evaluate(() => document.querySelector('footer').getBoundingClientRect().bottom <= document.querySelector('.mobile-nav').getBoundingClientRect().top + 1), 'Bottom navigation covers footer');
        await page.evaluate(() => {
            const event = new Event('beforeinstallprompt', { cancelable: true });
            event.prompt = async () => { throw new Error('Install UI unavailable'); };
            window.dispatchEvent(event);
        });
        await page.locator('[data-install]').first().click();
        assert(await page.locator('#install-dialog').isVisible());
        assert.match(await page.locator('[data-install-other]').innerText(), /Instal aplikasi/);
        await page.keyboard.press('Escape');
        await page.evaluate(() => {
            const event = new Event('beforeinstallprompt', { cancelable: true });
            event.prompt = async () => { window.installCalled = true; };
            event.userChoice = Promise.resolve({ outcome: 'accepted' });
            window.dispatchEvent(event);
        });
        await page.locator('[data-install]').first().click();
        await page.waitForFunction(() => window.installCalled === true && [...document.querySelectorAll('[data-install]')].every(button => button.hidden));
        checks.push('Install guide fallback and supported-browser prompt');
        await page.goto(base, { waitUntil: 'networkidle' });
        await page.evaluate(() => navigator.serviceWorker.ready);
        await page.waitForFunction(() => !!navigator.serviceWorker.controller);
        await context.setOffline(true);
        await page.goto(base + '/artikel?offline=1', { waitUntil: 'load' });
        assert.match(await page.locator('h1').innerText(), /Kita sambung/);
        await capture('390-offline');
        const cached = await page.evaluate(async () => {
            const urls = [];
            for (const name of await caches.keys()) for (const request of await (await caches.open(name)).keys()) urls.push(new URL(request.url).pathname);
            return urls;
        });
        assert(cached.includes('/assets/media.css'));
        assert(cached.every(url => ['/offline.html', '/assets/app.css', '/assets/media.css', '/assets/app.js', '/icons/icon-192.png', '/icons/icon-512.png'].includes(url)));
        await context.setOffline(false);
        await page.goto(base, { waitUntil: 'networkidle' });
        checks.push('Offline notice, shell-only cache and recovery');
        assert.deepEqual(errors, []);
        const iosContext = await browser.newContext({ ...devices['iPhone 13'] });
        const iosPage = await iosContext.newPage();
        await iosPage.goto(base);
        await iosPage.locator('[data-install]').first().click();
        assert(await iosPage.locator('[data-install-ios]').isVisible());
        assert(!(await iosPage.locator('[data-install-other]').isVisible()));
        await iosContext.close();
        checks.push('iPhone installation instructions');
        const noJsContext = await browser.newContext({ javaScriptEnabled: false });
        const noJsPage = await noJsContext.newPage();
        await noJsPage.goto(base + '/kanal/khazanah');
        await noJsPage.locator('#archive-query').fill('kitab');
        await noJsPage.locator('#archive-query').press('Enter');
        await noJsPage.waitForURL('**/kanal/khazanah?q=kitab');
        assert.match(await noJsPage.locator('#content').innerText(), /Kitab kuning/);
        await noJsContext.close();
        checks.push('Search works without JavaScript and retains channel');
        writeFileSync(path.join(output, 'results.json'), JSON.stringify({ passed: true, checks, errors }, null, 2));
        console.log(JSON.stringify({ passed: true, checks, errors }, null, 2));
    } catch (error) {
        await capture('failure').catch(() => {});
        writeFileSync(path.join(output, 'results.json'), JSON.stringify({ passed: false, checks, errors, failure: error.message }, null, 2));
        throw error;
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
