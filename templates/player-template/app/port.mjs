import { metadata as sound } from './audio-port.mjs';
/** Replace only this adapter and its imported translated routines/data for a port. */
export const metadata = {
  title: 'No translated production configured',
  // Standard shell metadata; populate from original credits/release evidence.
  displayTitle: 'No translated production configured', // Landing heading; title also labels the browser tab.
  group: '', releaseInfo: '', credits: [], links: { pouet: '', github: '' },
  palette: { accent: '#7faac4', text: '#c9dce9' },
  landing: null, // {start,end,drawRate}: verified first-animation loop; required for release.

  duration: 0, // Recover from the original; do not copy a duration from an example.
  displayAspect: null, // Recover the intended display geometry; no fixed VGA assumption.
  audio: sound.audio, // Original-code, verified none, or pending (visuals first).
  audioChannels: sound.audioChannels,
  provenance: sound.provenance,
};

export async function createVideoPort() {
  throw new Error('Configure app/port.mjs with this production’s translated graphics');
}

export { createAudioPort, loadAudioResources } from './audio-port.mjs';
