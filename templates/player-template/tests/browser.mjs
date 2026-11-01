/** Real page acceptance, not a renderer substitute. No npm dependencies. */
import { spawn } from 'node:child_process';
import { existsSync } from 'node:fs';
import { mkdtemp, rm, readFile, writeFile } from 'node:fs/promises';
import { tmpdir } from 'node:os';
import path from 'node:path';
import assert from 'node:assert/strict';
import { createPlayerServer } from '../server.mjs';
import { createVideoPort, metadata } from '../examples/reference-port.mjs';
import { frameDigest, PortRunner } from '../runtime/port-runner.mjs';

const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));
const option = name => { const at = process.argv.indexOf(name); return at >= 0 ? process.argv[at + 1] : null; };
const chrome = [process.env.CHROME, 'C:/Program Files/Google/Chrome/Application/chrome.exe',
  'C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe', '/usr/bin/google-chrome', '/usr/bin/chromium',
  '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'].find(p => p && existsSync(p));
if (!chrome) throw new Error('Set CHROME to an installed Chromium-based browser; no emulator is launched');
let nextId = 0;
class CDP {
  constructor(socket) {
    this.socket = socket; this.pending = new Map(); this.exceptions = [];
    socket.onmessage = ({ data }) => {
      const message = JSON.parse(data);
      if (message.method === 'Runtime.exceptionThrown') this.exceptions.push(message.params.exceptionDetails.text);
      const request = this.pending.get(message.id);
      if (request) { this.pending.delete(message.id); message.error ? request.reject(new Error(message.error.message)) : request.resolve(message.result); }
    };
  }
  request(method, params = {}, sessionId) {
    const id = ++nextId;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.socket.send(JSON.stringify({ id, method, params, sessionId }));
    });
  }
}
const profile = await mkdtemp(path.join(tmpdir(), 'port-browser-'));
const server = createPlayerServer();
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
const external = option('--url');
const url = external ?? `http://127.0.0.1:${server.address().port}/?fixture=1`;
if (external && !option('--expectations')) throw new Error('Real ports need --expectations with independently generated frame digests');
const browser = spawn(chrome, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check',
  '--autoplay-policy=no-user-gesture-required', '--mute-audio', '--remote-debugging-port=0', `--user-data-dir=${profile}`],
  { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] });
let socket;
try {
  const endpoint = await new Promise((resolve, reject) => {
    let text = '';
    const timer = setTimeout(() => reject(new Error('Browser debugging endpoint timed out')), 20000);
    browser.once('error', error => { clearTimeout(timer); reject(error); });
    browser.stderr.on('data', data => { text += data.toString(); const match = /DevTools listening on (ws:\/\/\S+)/.exec(text); if (match) { clearTimeout(timer); resolve(match[1]); } });
    browser.once('exit', code => { clearTimeout(timer); reject(new Error(`Browser exited before ready (${code}): ${text.slice(-1000)}`)); });
  });
  socket = new WebSocket(endpoint);
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject; });
  const cdp = new CDP(socket);
  const { targetId } = await cdp.request('Target.createTarget', { url: 'about:blank' });
  const { sessionId } = await cdp.request('Target.attachToTarget', { targetId, flatten: true });
  const command = (method, params) => cdp.request(method, params, sessionId);
  const evaluate = async expression => {
    const value = await command('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (value.exceptionDetails) throw new Error(JSON.stringify(value.exceptionDetails));
    return value.result.value;
  };
  const until = async (expression, predicate, label) => {
    const deadline = Date.now() + 20000;
    while (Date.now() < deadline) { const value = await evaluate(expression); if (predicate(value)) return value; await sleep(50); }
    throw new Error(`Timed out: ${label}`);
  };
  await command('Runtime.enable');
  await command('Emulation.setDeviceMetricsOverride', {width:1280,height:800,deviceScaleFactor:1,mobile:false});
  await command('Page.navigate', { url });
  await until('Boolean(window.player?.metadata)', Boolean, 'translated adapter ready');
  if(!external){
    const backgroundDigest=()=>evaluate("(async()=>{const c=document.getElementById('background');return [...new Uint8Array(await crypto.subtle.digest('SHA-256',c.getContext('2d').getImageData(0,0,c.width,c.height).data))].join(',');})()");
    await sleep(150);const before=await backgroundDigest();await sleep(250);
    assert.notEqual(await backgroundDigest(),before,'landing animates live');
  }
  await evaluate('window.player.start()');
  await until('window.player.time', t => t > .1, 'presentation clock advances');
  // Exercise a native slider outside the current thumb, while RAF is running.
  await evaluate("document.getElementById('hud').classList.add('visible')");
  const rect=await evaluate("(()=>{const r=document.getElementById('timeline').getBoundingClientRect();return {x:r.x,y:r.y,w:r.width,h:r.height};})()");
  const finite=await evaluate('window.player.metadata.duration !== null');
  if(finite){
    const gesture=async(type,fraction,buttons=0)=>command('Input.dispatchMouseEvent',{type,x:rect.x+8+(rect.w-16)*fraction,y:rect.y+rect.h/2,button:type==='mouseMoved'?'none':'left',buttons,clickCount:1});
    await gesture('mouseMoved',.3);await gesture('mousePressed',.3,1);
    await sleep(250);
    const held=await evaluate("Number(document.getElementById('timeline').value)");
    assert.ok(held>1,'RAF cannot overwrite the held slider');
    await gesture('mouseReleased',.3);
    await until('!window.player.seeking',Boolean,'playing seek completes');
    assert.equal(await evaluate('window.player.paused'),false,'playing seek resumes');
    await evaluate('window.player.setPaused(true)');
    await gesture('mousePressed',.3,1);await gesture('mouseMoved',.5,1);
    const target=await evaluate("Number(document.getElementById('timeline').value)");
    await gesture('mouseReleased',.5);
    await until('!window.player.seeking && Math.abs(window.player.frame.time-'+target+')<.11',Boolean,'drag cues exact paused frame');
    assert.equal(await evaluate('window.player.paused'),true,'paused seek stays paused');
    await evaluate('window.player.setPaused(false)');
  }
  await evaluate("document.getElementById('stats-toggle').click()");
  assert.equal(await evaluate("document.getElementById('nerd-panel').hidden"),false);
  assert.match(await evaluate("document.getElementById('stats').textContent"),/FPS:/);
  await evaluate("document.getElementById('stats-toggle').click()");
  const audio = await evaluate('window.player.metadata.audio');
  if (['original-code', 'fixture'].includes(audio)) await until('window.player.audioLevel', level => level > 0, 'actual non-silent audio output');
  await evaluate('window.player.setPaused(true)');
  await sleep(250);
  const frozen = await evaluate('window.player.snapshot()');
  const frozenTime = await evaluate('window.player.time');
  await sleep(300);
  assert.equal(await evaluate('window.player.time'), frozenTime, 'pause freezes presentation time');
  assert.equal((await evaluate('window.player.snapshot()')).sha256, frozen.sha256, 'pause freezes the real canvas');
  let expectations;
  if (external) expectations = JSON.parse(await readFile(option('--expectations'), 'utf8')).frames;
  else {
    const runner = new PortRunner(createVideoPort(), metadata);
    expectations = [];
    for (const time of [3.5, 9, 1.25, 11.95]) { runner.seek(time); expectations.push({ time, sha256: await frameDigest(runner.render()) }); }
  }
  assert.ok(Array.isArray(expectations) && expectations.length, 'expected frame cases are required');
  for (const expected of expectations) {
    await evaluate(`window.player.seek(${JSON.stringify(expected.time)})`);
    await until('window.player.frame?.time', t => t === expected.time, 'seek presents the requested paused frame');
    const actual = await evaluate('window.player.snapshot()');
    assert.equal(actual.sha256, expected.sha256, `actual page at ${expected.time}s equals the translated reference`);
  }
  await evaluate('window.player.seek(0)');
  await until('window.player.frame?.time', t => t === 0, 'restart seek presents frame zero');
  await evaluate('window.player.setPaused(false)');
  await sleep(250);
  const resumed = await evaluate('window.player.time');
  assert.ok(resumed > .1 && resumed < 1.5, 'resume advances from the paused position without including paused wall time');
  const duration = await evaluate('window.player.metadata.duration');
  if (duration !== null) {
    await evaluate(`window.player.seek(${Math.max(0, duration - .15)})`);
    await evaluate('window.player.setPaused(false)');
    await until('window.player.paused && window.player.frame?.time === window.player.metadata.duration', Boolean, 'natural ending presents the final frame');
  }
  if (!external && duration !== null) {
    const runner = new PortRunner(createVideoPort(), metadata); runner.advanceTo(duration);
    assert.equal((await evaluate('window.player.snapshot()')).sha256, await frameDigest(runner.render()), 'natural ending matches the translated final frame');
  }
  const metrics = await evaluate('({worker: window.player.workerStats, frameIntervals: window.player.intervals})');
  // Standard controls are exercised through DOM or trusted keyboard events.
  await evaluate("document.getElementById('scale').value='0.5';document.getElementById('scale').dispatchEvent(new Event('change'))");
  assert.equal(await evaluate("document.getElementById('screen').style.transform"),'scale(0.5)');
  await evaluate("document.getElementById('volume').value='0.25';document.getElementById('volume').dispatchEvent(new Event('input'))");
  if(['fixture','original-code'].includes(audio)) assert.equal(await evaluate('window.player.outputGain.gain.value'),.25);
  await evaluate("document.activeElement?.blur()");
  await command('Input.dispatchKeyEvent',{type:'keyDown',code:'Escape',key:'Escape'});
  await command('Input.dispatchKeyEvent',{type:'keyUp',code:'Escape',key:'Escape'});
  await until('!window.player.playing && Boolean(window.player.metadata)',Boolean,'Stop returns to ready landing');
  await evaluate("document.getElementById('start').click()");
  await until('window.player.playing && window.player.time>.1',Boolean,'restart starts clean playback');
  await command('Input.dispatchKeyEvent',{type:'keyDown',code:'Space',key:' '});
  await command('Input.dispatchKeyEvent',{type:'keyUp',code:'Space',key:' '});
  await until('window.player.paused',Boolean,'Space pauses');
  if(finite){
    await evaluate('Promise.all([window.player.seek(1),window.player.seek(2),window.player.seek(.5)])');
    assert.equal(await evaluate('window.player.frame.time'),.5,'latest rapid seek wins');
  }
  await command('Input.dispatchKeyEvent',{type:'keyDown',code:'KeyF',key:'f'});
  await command('Input.dispatchKeyEvent',{type:'keyUp',code:'KeyF',key:'f'});
  await until('Boolean(document.fullscreenElement)',Boolean,'F enters fullscreen');
  await evaluate('document.exitFullscreen()');
  await command('Emulation.setDeviceMetricsOverride',{width:390,height:844,deviceScaleFactor:1,mobile:false});
  await evaluate("document.getElementById('hud').classList.add('visible')");
  assert.equal(await evaluate("(()=>{const r=document.getElementById('timeline').getBoundingClientRect();return r.x>=0&&r.right<=innerWidth;})()"),true,'mobile timeline stays in viewport');
  await evaluate('window.player.stop()');
  if (!external) {
    const visualURL = new URL(url); visualURL.searchParams.set('fixture', 'visual');
    await command('Page.navigate', { url: visualURL.href });
    await until('window.player?.metadata?.audio', value => value === 'pending', 'visuals-first adapter ready');
    await evaluate('window.player.start()');
    await until('window.player.time', value => value > .1, 'silent presentation clock advances');
    assert.equal(await evaluate('window.player.audioContext'), null, 'pending sound does not require an AudioContext');
    await evaluate('window.player.setPaused(true)');
    await evaluate('window.player.seek(3.5)');
    await until('window.player.frame?.time', value => value === 3.5, 'silent seek presents a frame');
    const runner = new PortRunner(createVideoPort(), metadata); runner.seek(3.5);
    assert.equal((await evaluate('window.player.snapshot()')).sha256, await frameDigest(runner.render()), 'silent visuals match the same translated frame');
    await evaluate('window.player.stop()');
  }
  assert.deepEqual(cdp.exceptions, [], 'page has no unhandled exceptions');
  const report = { verdict: 'PASS', scope: external ? 'real-port browser expectations' : 'explicit infrastructure fixture only',
    tested: ['canvas equivalence', 'actual audio output when present', 'pause', 'paused seek', 'backward seek', duration === null ? 'open-ended: no ending claimed' : 'natural ending and final frame', 'resume'],
    visualsFirst: external ? 'not separately exercised' : 'PASS: pending sound is independent of visuals', metrics, ui: ['actual slider hold/click/drag','paused/running seek preservation','FPS panel','scale','volume','Escape stop and clean restart','Space pause','rapid seek','fullscreen','narrow viewport'], remaining: ['production full-run and human review','all release-standard checklist items not explicitly tested here'] };
  if(option('--output')) await writeFile(option('--output'),JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
} finally {
  socket?.close();
  browser.kill();
  await new Promise(resolve => { if (browser.exitCode !== null) resolve(); else { browser.once('exit', resolve); setTimeout(resolve, 3000); } });
  server.closeAllConnections(); await new Promise(resolve => server.close(resolve));
  // This temporary browser profile was created above, outside the workspace.
  if (!path.resolve(profile).startsWith(path.resolve(tmpdir()) + path.sep) || !path.basename(profile).startsWith('port-browser-')) {
    throw new Error('Refusing cleanup outside the test-created temporary profile');
  }
  await rm(profile, { recursive: true, force: true, maxRetries: 10, retryDelay: 100 }).catch(() => {});
}
