import test from 'node:test';
import assert from 'node:assert/strict';
import { PlaybackClock } from '../runtime/transport.mjs';
import { PortRunner, SceneSequence, frameDigest } from '../runtime/port-runner.mjs';
import { AudioRenderer } from '../runtime/audio-renderer.mjs';
import { DemoMachine } from '../runtime/machine.mjs';
import { encodeVerifiedCheckpoint, restoreVerifiedCheckpoint, restoreCheckpoint } from '../runtime/checkpoint.mjs';
import { metadata, createVideoPort, createAudioPort } from '../examples/reference-port.mjs';
import { checkPresentationSchedules } from './cadence-check.mjs';

test('pause excludes elapsed wall time; seek remains exact while paused', () => {
  let wall = 10;
  const clock = new PlaybackClock(30, () => wall);
  clock.play(); wall += 3; assert.equal(clock.now(), 3);
  clock.pause(); wall += 100; assert.equal(clock.now(), 3);
  clock.seek(7); assert.equal(clock.now(), 7);
  clock.play(); wall += 2; assert.equal(clock.now(), 9);
  clock.setSource(() => wall * 2); wall += 1; assert.equal(clock.now(), 11);
});

test('open-ended productions declare null duration without an invented ending', () => {
  let wall = 0;
  const clock = new PlaybackClock(null, () => wall); clock.play(); wall = 100000;
  assert.equal(clock.now(), 100000);
  const runner = new PortRunner(createVideoPort(), { ...metadata, duration: null });
  runner.advanceTo(1000); assert.equal(runner.time, 1000);
});

test('paused and backward seeking renders the same live frame as uninterrupted advance', async () => {
  const runner = new PortRunner(createVideoPort(), metadata);
  runner.advanceTo(5); const expected = await frameDigest(runner.render());
  runner.advanceTo(9); runner.seek(5);
  assert.equal(await frameDigest(runner.render()), expected);
  runner.seek(2); runner.advanceTo(5);
  assert.equal(await frameDigest(runner.render()), expected);
  assert.throws(() => runner.seek(NaN));
});

test('scene transition and seek inherit translated predecessor state', () => {
  const makeScene = (duration, offset) => ({ duration, create({ handoff }) {
    const initial = handoff?.value ?? 0; let value = initial;
    return { reset() { value = initial; }, advanceTo(t) { value = initial + Math.floor(t * 10) + offset; },
      handoff() { return { value }; }, render() { return { value }; } };
  } });
  const timeline = new SceneSequence([makeScene(2, 1), makeScene(3, 7)]);
  timeline.advanceTo(3); assert.equal(timeline.render().value, 38);
  timeline.advanceTo(1); timeline.advanceTo(3); assert.equal(timeline.render().value, 38);
  timeline.advanceTo(5); assert.equal(timeline.render().value, 58);
});

test('synthetic audio is rejected unless explicitly running the infrastructure fixture', () => {
  const port = createAudioPort({ sampleRate: 48000 });
  assert.throws(() => new AudioRenderer(port, metadata, 48000), /original code/);
  assert.throws(() => new AudioRenderer(port, { audio: 'module-library' }, 48000), /original code/);
});

test('audio transport is chunk invariant, pauses silently, and restores sample position', () => {
  const run = chunks => {
    const renderer = new AudioRenderer(createAudioPort({ sampleRate: 48000 }), metadata, 48000, { fixture: true });
    renderer.paused = false;
    const result = [];
    for (const frames of chunks) {
      const channels = [new Float32Array(frames), new Float32Array(frames)];
      assert.equal(renderer.process(channels), frames); result.push(...channels[0]);
    }
    return { result, renderer };
  };
  const a = run([128, 256, 128]); const b = run([512]);
  assert.deepEqual(a.result, b.result);
  a.renderer.paused = true;
  const silent = [new Float32Array(128).fill(1)];
  assert.equal(a.renderer.process(silent), 0); assert.equal(a.renderer.position, 512);
  assert.ok(silent[0].every(v => v === 0));
  a.renderer.seek(.25); assert.equal(a.renderer.position, 12000);
});

test('unimplemented port fails clearly instead of displaying a fake production', async () => {
  const adapter = await import('../app/port.mjs');
  await assert.rejects(adapter.createVideoPort(), /Configure/);
});

test('verified checkpoint includes a partial last page and explicit sound/FPU state', async () => {
  const base = new Uint8Array(4200);
  const machine = new DemoMachine(base.slice(), { eax: 123, eflags: 0x202 });
  machine.memory[4199] = 77;
  const state = { audio: { sample: 123456, phase: [1, 2] }, fpu: { extended80: ['80000000000000003fff'] }, scene: 3 };
  const checkpoint = await encodeVerifiedCheckpoint(base, machine, state);
  const restored = await restoreVerifiedCheckpoint(base, checkpoint);
  assert.equal(restored.machine.memory[4199], 77);
  assert.equal(restored.machine.r.eax, 123);
  assert.deepEqual(restored.state, state);
  const wrong = base.slice(); wrong[0] = 1;
  await assert.rejects(restoreVerifiedCheckpoint(wrong, checkpoint), /baseline/);
  assert.throws(() => restoreCheckpoint(base, checkpoint.subarray(0, 7)), /Truncated/);
});

test('presentation cadence and repeated redraws do not drive the visual simulation', async () => {
  const result = await checkPresentationSchedules(createVideoPort, metadata, { times: [2, 6.5, 11.9] });
  assert.equal(result.verdict, 'PASS', JSON.stringify(result));
  // This deliberately broken adapter advances per browser request, rather than logical time.
  const broken = () => {
    let value = 0;
    return { reset() { value = 0; }, advanceTo() { value++; },
      render() { return { width: 1, height: 1, rgba: new Uint8Array([value & 255, 0, 0, 255]) }; } };
  };
  assert.equal((await checkPresentationSchedules(broken, metadata, { times: [1] })).verdict, 'FAIL');
});
