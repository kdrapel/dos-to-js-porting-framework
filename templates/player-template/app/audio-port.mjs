/** Keep top-level imports worklet-safe. Translate the original sound code here. */
export const metadata = { audio: 'pending', audioChannels: 2, provenance: null };

export async function loadAudioResources() {
  // Called on the main thread. Fetch/decode verified original data here.
  return null;
}

export async function createAudioPort({ sampleRate, resources }) {
  throw new Error('Translate the original sound code; module-player libraries are not a substitute');
}
