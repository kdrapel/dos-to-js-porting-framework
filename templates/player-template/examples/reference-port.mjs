import { SceneSequence } from '../runtime/port-runner.mjs';
/** Explicit infrastructure fixture. It is not a demoscene port or fidelity proof. */
export const metadata = { title: 'Framework fixture — not a demo port', duration: 12,
  group: 'Infrastructure only', landing: {start:0,end:6,drawRate:24}, displayAspect: '3 / 2', audio: new URL(import.meta.url).searchParams.get('audio') === 'pending' ? 'pending' : 'fixture',
  audioChannels: 2, provenance: 'synthetic transport test only' };

export function createVideoPort() {
  const create = phase => ({ handoff }) => {
    const base = handoff?.time ?? 0;
    let time = base;
    const width = 48, height = 32, rgba = new Uint8ClampedArray(width * height * 4);
    return {
      reset() { time = base; },
      advanceTo(seconds) { time = base + seconds; },
      handoff() { return { time }; },
      render() {
        const tick = Math.floor(time * 24);
        for (let y = 0, p = 0; y < height; y++) for (let x = 0; x < width; x++, p += 4) {
          rgba[p] = (x * 7 + tick + phase * 89) & 255;
          rgba[p + 1] = (y * 11 + tick * 3) & 255;
          rgba[p + 2] = (x ^ y ^ tick ^ phase) & 255; rgba[p + 3] = 255;
        }
        return { width, height, rgba };
      },
    };
  };
  return new SceneSequence([{ duration: 6, create: create(0) }, { duration: 6, create: create(1) }]);
}

export { createAudioPort } from './reference-audio-port.mjs';
