/** Explicit synthetic audio transport fixture, never production evidence. */
export const metadata = { audio: 'fixture' };

export function createAudioPort({ sampleRate }) {
  let position = 0;
  return {
    reset() { position = 0; },
    seek(seconds) { position = Math.round(seconds * sampleRate); },
    render(channels, frames) {
      for (let i = 0; i < frames; i++, position++) {
        const value = ((position % 100) / 100 - .5) * .02;
        for (const channel of channels) channel[i] = value;
      }
      return frames;
    },
  };
}
