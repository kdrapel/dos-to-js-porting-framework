import * as adapter from './reference-audio-port.mjs';
import { registerOriginalAudioProcessor } from '../runtime/audio-processor.mjs';
registerOriginalAudioProcessor(adapter, { fixture: true });
