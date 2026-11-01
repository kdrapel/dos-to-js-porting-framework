import { releaseMode } from './release-mode.mjs';
import { PlaybackClock } from '../runtime/transport.mjs';
import { frameDigest } from '../runtime/port-runner.mjs';
const $ = id => document.getElementById(id);

export class DemoPlayer {
  constructor() {
    this.canvas = $('screen'); this.ctx = this.canvas.getContext('2d');
    const fixtureMode = releaseMode ? null : new URLSearchParams(location.search).get('fixture');
    this.fixture = ['1', 'visual'].includes(fixtureMode);
    const adapterURL = new URL(this.fixture ? '../examples/reference-port.mjs' : './port.mjs', import.meta.url);
    if (fixtureMode === 'visual') adapterURL.searchParams.set('audio', 'pending');
    this.adapterURL = adapterURL.href;
    this.clock = null; this.metadata = null; this.worker = null; this.audioContext = null; this.audioNode = null;
    this.epoch = 0; this.pending = false; this.playing = false; this.starting = false; this.paused = true; this.frame = null;
    this.audioLevel = 0; this.workerStats = {}; this.raf = 0; this.lastFrameWall = 0; this.intervals = [];
    this.bindControls(); this.ready = this.prepare();
  }
  fail(error) {
    const message = error?.message ?? String(error);
    $('status').textContent = message; $('loading').hidden = true;
    this.clock?.pause(); this.paused = true;
    this.audioNode?.port.postMessage({ type: 'pause', paused: true });
    this.pending = false;
    if (!this.playing) { $('start').disabled = true; $('start').textContent = 'Port unavailable'; }
    throw new Error(message);
  }
  async prepare() {
    $('start').disabled = true;
    return new Promise((resolve, reject) => {
      this.worker = new Worker(new URL('./render-worker.mjs', import.meta.url), { type: 'module' });
      this.worker.onerror = event => { $('status').textContent = event.message; this.cancelSeek?.(new Error(event.message)); reject(new Error(event.message)); };
      this.worker.onmessage = ({ data }) => {
        if (data.type === 'ready') {
          this.metadata = data.metadata; this.clock = new PlaybackClock(data.metadata.duration);
          document.title = data.metadata.title; $('demo-title').textContent = data.metadata.displayTitle ?? data.metadata.title;
          if (data.metadata.displayAspect) this.canvas.style.aspectRatio = data.metadata.displayAspect;
          else this.canvas.style.aspectRatio = 'auto';
          $('timeline').max = String(data.metadata.duration ?? 0);
          $('timeline').removeAttribute('list');
          $('timeline').disabled = data.metadata.duration === null;
          if (this.fixture) $('demo-meta').textContent = 'Infrastructure fixture — no demo fidelity claim';
          else if (data.metadata.releaseInfo !== undefined) $('demo-meta').textContent = data.metadata.releaseInfo;
          $('demo-group').textContent = data.metadata.group ?? '';
          $('demo-credits').hidden = false;
          $('player-details').textContent = `Render: translated JS · Audio: ${data.metadata.audio}`;
          $('tracker-title').hidden = false; $('tracker').hidden = false;
          $('start').disabled = false; $('start').textContent = 'Start';
          $('status').textContent = this.fixture ? 'Framework fixture — not a demo port' : '';
          resolve(this.metadata);
        } else if (data.type === 'metrics-reset') {
          this.resolveMetricsReset?.(); this.resolveMetricsReset = null;
        } else if (data.type === 'error') {
          $('status').textContent = data.message; $('start').textContent = 'Port unavailable';
          if (!this.metadata) reject(new Error(data.message));
          else { this.cancelSeek?.(new Error(data.message)); this.clock.pause(); this.paused = true; this.pending = false; $('loading').hidden = true; this.audioNode?.port.postMessage({ type: 'pause', paused: true }); }
        } else if (data.type === 'frame') {
          if (data.epoch !== this.epoch) { this.recycle(data.buffer); return; }
          this.pending = false;
          const now = performance.now();
          if (this.lastFrameWall && !this.paused) { this.intervals.push(now - this.lastFrameWall); if (this.intervals.length > 240) this.intervals.shift(); }
          this.lastFrameWall = now;
          this.presentations ??= []; this.presentations.push(now);
          this.presentations = this.presentations.filter(t => t > now - 1000);
          const previous = this.frame;
          this.frame = { width: data.width, height: data.height, rgba: new Uint8ClampedArray(data.buffer), time: data.time };
          if (this.canvas.width !== data.width || this.canvas.height !== data.height) { this.canvas.width = data.width; this.canvas.height = data.height; }
          this.ctx.putImageData(new ImageData(this.frame.rgba, data.width, data.height), 0, 0);
          if (previous) this.recycle(previous.rgba.buffer);
          this.workerStats = data.stats;
          if (data.epoch === this.seekEpoch) { this.resolveVideoSeek?.(); this.resolveVideoSeek = null; }
          if (!this.seeking) $('loading').hidden = true;
          this.updateStats();
        }
      };
      this.worker.postMessage({ type: 'init', adapterURL: this.adapterURL });
    });
  }
  recycle(buffer) { this.worker?.postMessage({ type: 'recycle', buffer }, [buffer]); }
  bindControls() {
    const action = operation => () => Promise.resolve().then(operation).catch(error => { $('status').textContent = error.message; });
    $('start').onclick = action(() => this.start());
    $('pause').onclick = action(() => this.setPaused(!this.paused));
    $('stop').onclick = action(() => this.stop());
    $('backward').onclick = action(() => this.seek(this.time - 15));
    $('forward').onclick = action(() => this.seek(this.time + 15));
    const timeline = $('timeline');
    timeline.onpointerdown = event => { this.scrubbing = true; this.timelinePointer = true; timeline.setPointerCapture(event.pointerId); };
    timeline.oninput = () => { this.scrubbing = true; };
    timeline.onchange = () => {
      const target = Number(timeline.value);
      if (this.timelinePointer) { this.scrubTarget = target; return; }
      this.scrubbing = false;
      this.seek(target).catch(error => { $('status').textContent = error.message; });
    };
    timeline.onpointercancel = () => { this.scrubbing = false; this.timelinePointer = false; };
    timeline.onpointerup = () => {
      const target = Number(timeline.value); this.timelinePointer = false; this.scrubbing = false;
      this.seek(target).catch(error => { $('status').textContent = error.message; });
    };
    $('fullscreen').onclick = action(() => document.fullscreenElement ? document.exitFullscreen() : $('shell').requestFullscreen());
    $('stats-toggle').onchange = () => { $('nerd-panel').hidden = !$('stats-toggle').checked; };
    window.addEventListener('keydown', event => {
      if (['INPUT','SELECT','TEXTAREA','BUTTON'].includes(event.target.tagName) || event.target.isContentEditable) return;
      const operation = { Space: () => this.setPaused(!this.paused), ArrowLeft: () => this.seek(this.time - 15),
        ArrowRight: () => this.seek(this.time + 15), Escape: () => this.stop(), KeyF: () => $('fullscreen').click() }[event.code];
      if (operation) { event.preventDefault(); action(operation)(); }
    });
  }
  get time() { return this.clock?.now() ?? 0; }
  async initAudio() {
    if (!['original-code', 'fixture'].includes(this.metadata.audio)) return;
    if (this.metadata.audio === 'original-code' && !this.metadata.provenance) throw new Error('Original audio provenance is missing');
    this.audioContext = new AudioContext();
    await this.audioContext.resume();
    const adapter = await import(this.adapterURL);
    const resources = await adapter.loadAudioResources?.();
    await this.audioContext.audioWorklet.addModule(new URL(this.fixture ? '../examples/reference-audio-worklet.mjs' : './audio-worklet.mjs', import.meta.url));
    this.audioNode = new AudioWorkletNode(this.audioContext, 'original-code-audio', {
      numberOfInputs: 0, outputChannelCount: [this.metadata.audioChannels ?? 2],
    });
    const node = this.audioNode;
    await new Promise((resolve, reject) => {
      this.audioNode.onprocessorerror = () => { const error = new Error('Original audio processor failed'); this.cancelSeek?.(error); reject(error); $('status').textContent = error.message; this.clock.pause(); this.paused = true; };
      this.audioNode.port.onmessage = ({ data }) => {
        if (this.audioNode !== node) return;
        if (data.type === 'seeked' && data.epoch === this.epoch) { clearTimeout(this.audioSeekTimer); this.resolveAudioSeek?.(); this.resolveAudioSeek = null; }
        else if (data.type === 'ready') resolve();
        else if (data.type === 'error') { $('status').textContent = data.message; this.clock.pause(); this.paused = true; this.cancelSeek?.(new Error(data.message)); reject(new Error(data.message)); }
        else if (data.type === 'position' && data.epoch === this.epoch) {
          this.audioLevel = data.peak; this.trackerState = data.tracker;
          if (!this.paused && !data.paused) this.clock.seek(data.time);
        }
      };
      this.audioNode.port.postMessage({ type: 'init', resources });
    });
    this.outputGain = this.audioContext.createGain();
    this.outputGain.gain.value = Number($('volume').value);
    this.audioNode.connect(this.outputGain); this.outputGain.connect(this.audioContext.destination);
    this.audioNode.port.postMessage({ type: 'seek', time: this.clock.now(), epoch: this.epoch });
    this.clock.setSource(() => this.audioContext.currentTime);
  }
  async start() {
    await this.ready;
    if (this.playing || this.starting) return;
    this.starting = true; $('start').disabled = true;
    try { await this.initAudio(); }
    catch (error) {
      this.audioNode?.disconnect(); this.audioNode = null;
      await this.audioContext?.close(); this.audioContext = null;
      throw error;
    } finally { this.starting = false; $('start').disabled = false; }
    $('status').textContent = this.fixture ? 'Framework fixture — not a demo port' : '';
    this.playing = true; this.paused = false;
    $('gate').classList.add('dismissed'); $('hud').hidden = false; $('pause').textContent = 'Pause';
    this.clock.play(); this.audioNode?.port.postMessage({ type: 'pause', paused: false });
    this.pump();
  }
  pump() {
    if (!this.playing) return;
    const time = this.time;
    const ended = this.metadata.duration !== null && time >= this.metadata.duration;
    if (ended && !this.paused && !this.seeking) this.setPaused(true);
    const needsFinalFrame = ended && this.frame?.time !== this.metadata.duration;
    if (!this.seeking && (!this.paused || needsFinalFrame) && !this.pending) {
      this.pending = true; this.worker.postMessage({ type: 'render', time, epoch: this.epoch });
    }
    if (!this.scrubbing) $('timeline').value = String(time);
    const format = t => `${Math.floor(t / 60)}:${String(Math.floor(t % 60)).padStart(2, '0')}`;
    $('time').textContent = format(time) + (this.metadata.duration === null ? ' / open-ended' : ' / ' + format(this.metadata.duration));
    this.updateStats();
    this.raf = requestAnimationFrame(() => this.pump());
  }
  async setPaused(paused) {
    if (!this.playing) return;
    if (this.seeking) { this.resumeAfterSeek = !paused; this.requestedSeekResume = !paused; return; }
    if (paused) this.clock.pause(); else { await this.audioContext?.resume(); this.clock.play(); }
    this.paused = paused; if (paused) this.audioLevel = 0;
    this.audioNode?.port.postMessage({ type: 'pause', paused });
    $('pause').textContent = paused ? 'Resume' : 'Pause';
  }
  async seek(seconds) {
    await this.ready;
    const target = Math.min(this.metadata.duration ?? Infinity, Math.max(0, seconds));
    if (!Number.isFinite(target)) throw new Error('Seek time must be finite');
    if (!this.seeking) this.requestedSeekResume = !this.paused;
    const request = this.seekRequest = (this.seekRequest ?? 0) + 1;
    const operation = async () => {
      if (request !== this.seekRequest) return;
      this.resumeAfterSeek = this.requestedSeekResume;
      this.seeking = true; this.clock.pause(); this.paused = true;
      this.audioNode?.port.postMessage({ type: 'pause', paused: true });
      this.epoch++; this.seekEpoch = this.epoch; this.clock.seek(target); this.lastFrameWall = 0;
      $('timeline').value = String(target);
      $('loading').hidden = false; this.pending = true;
      const videoSeek = new Promise((resolve, reject) => { this.resolveVideoSeek = resolve; this.cancelSeek = reject; });
      const seekTimer = setTimeout(() => this.cancelSeek?.(new Error('Seek timed out')), this.metadata.seekTimeoutMs ?? 60000);
      const audioSeek = this.audioNode ? new Promise((resolve, reject) => {
        this.resolveAudioSeek = resolve; this.rejectAudioSeek = reject;
        this.audioSeekTimer = setTimeout(() => reject(new Error('Original audio seek exceeded 60 seconds')), 60000);
      }) : Promise.resolve();
      this.audioNode?.port.postMessage({ type: 'seek', time: target, epoch: this.epoch });
      this.worker.postMessage({ type: 'seek', time: target, epoch: this.epoch });
      try {
        await Promise.all([videoSeek, audioSeek]);
        this.clock.seek(target);
        this.seeking = false;
        await this.setPaused(request === this.seekRequest ? !this.resumeAfterSeek : true);
      } catch (error) {
        this.seeking = false; this.paused = true; this.clock?.pause();
        throw error;
      } finally {
        clearTimeout(this.audioSeekTimer); clearTimeout(seekTimer); this.cancelSeek = null; this.resolveVideoSeek = null;
        $('loading').hidden = true;
      }
    };
    this.seekChain = (this.seekChain ?? Promise.resolve()).catch(() => {}).then(operation);
    return this.seekChain;
  }
  async stop() {
    this.seekRequest = (this.seekRequest ?? 0) + 1;
    this.cancelSeek?.(new Error('Seek cancelled by Stop')); this.rejectAudioSeek?.(new Error('Seek cancelled by Stop'));
    clearTimeout(this.audioSeekTimer); this.seeking = false; this.scrubbing = false; this.timelinePointer = false;
    this.playing = false; this.paused = true; cancelAnimationFrame(this.raf);
    this.epoch++; this.worker?.terminate(); this.worker = null;
    this.audioNode?.disconnect(); this.audioNode = null;
    await this.audioContext?.close(); this.audioContext = null;
    this.frame = null; this.pending = false; this.lastFrameWall = 0;
    this.metadata = null; this.clock = null;
    $('hud').hidden = true; $('gate').classList.remove('dismissed');
    this.ready = this.prepare();
  }
  async snapshot() {
    if (!this.frame) throw new Error('No live frame has been presented');
    // Copy before awaiting: the worker may recycle the source buffer on the next frame.
    const frame = { width: this.canvas.width, height: this.canvas.height,
      rgba: this.ctx.getImageData(0, 0, this.canvas.width, this.canvas.height).data };
    return { time: this.frame.time, width: frame.width, height: frame.height,
      sha256: await frameDigest(frame), paused: this.paused, audioLevel: this.audioLevel,
      rgba_sha256: [...new Uint8Array(await crypto.subtle.digest('SHA-256', frame.rgba))].map(x => x.toString(16).padStart(2, '0')).join(''),
      fixture: this.fixture, stats: this.workerStats };
  }
  updateStats() {
    const now = performance.now();
    this.presentations = (this.presentations ?? []).filter(t => t > now - 1000);
    const stats = this.workerStats;
    $('stats').textContent = `FPS: ${this.paused ? '0 (paused)' : this.presentations.length} · Advance p95: ${(stats.advanceP95Ms ?? 0).toFixed(2)} ms · Render max: ${(stats.renderMaxMs ?? 0).toFixed(2)} ms`;
  }
  async resetMetrics() {
    await this.ready;
    this.intervals = []; this.lastFrameWall = 0;
    this.workerStats = { frames: 0, advanceMaxMs: 0, renderMaxMs: 0, advanceP95Ms: 0 };
    await new Promise(resolve => { this.resolveMetricsReset = resolve; this.worker.postMessage({ type: 'reset-metrics' }); });
  }
}

window.player = new DemoPlayer();
window.player.ready.catch(error => { $('status').textContent = error.message; });
