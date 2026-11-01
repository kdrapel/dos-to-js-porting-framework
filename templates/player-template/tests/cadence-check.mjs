/** Offline property check: display requests must not advance simulation state. */
import { PortRunner, frameDigest } from '../runtime/port-runner.mjs';

export async function checkPresentationSchedules(createPort, metadata, {
  times, rates = [30, 60, 144], maxFrames = 20000,
} = {}) {
  if (!Array.isArray(times) || !times.length || times.some(t => !Number.isFinite(t) || t < 0) ||
      times.some((t, i) => i && t <= times[i - 1]) ||
      !rates.length || rates.some(r => !Number.isFinite(r) || r <= 0)) {
    throw new Error('Provide increasing sample times and positive presentation test rates');
  }
  const baseline = new Map();
  const observations = [];
  let frames = 0;
  try {
    for (const rate of rates) {
      const runner = new PortRunner(await createPort(), metadata);
      let next = 1;
      for (const time of times) {
        while (next / rate < time) {
          if (++frames > maxFrames) throw new Error('Cadence check exceeds its frame budget');
          runner.advanceTo(next++ / rate); runner.render();
        }
        runner.advanceTo(time);
        const digest = await frameDigest(runner.render());
        const redraw = await frameDigest(runner.render());
        if (redraw !== digest) return { verdict: 'FAIL', rate, time, reason: 'redraw_changed_frame' };
        runner.advanceTo(time);
        if (await frameDigest(runner.render()) !== digest) {
          return { verdict: 'FAIL', rate, time, reason: 'same_time_update_changed_frame' };
        }
        if (baseline.has(time) && baseline.get(time) !== digest) {
          return { verdict: 'FAIL', rate, time, reason: 'presentation_schedule_changed_frame', expected: baseline.get(time), actual: digest };
        }
        baseline.set(time, digest);
        observations.push({ rate, time, sha256: digest });
        // Do not insert an older request after an exact sample on this rate's grid.
        while (next / rate <= time) next++;
      }
    }
    return { verdict: 'PASS', observations,
      scope: 'sampled frame repeatability and presentation-cadence independence; not original draw-rate or state-fidelity proof' };
  } catch (error) {
    return { verdict: 'INSUFFICIENT_EVIDENCE', reason: error.message };
  }
}
