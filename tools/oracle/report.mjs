/** Offline JavaScript report helper; no CPU emulator or module player is shipped. */
import { readFile, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const number = value => {
  const parsed = typeof value === 'string' && !value.toLowerCase().startsWith('0x') && /[a-f]/i.test(value) ? Number.parseInt(value, 16) : Number(value);
  if (typeof value === 'boolean' || !Number.isSafeInteger(parsed)) throw new Error('Expected an exact integer address/size');
  return parsed;
};

export async function loadCaseInput(path) {
  const input = JSON.parse(await readFile(path, 'utf8'));
  const regions = [];
  for (const region of input.regions) {
    const data = new Uint8Array(await readFile(region.path));
    if (data.length !== region.length || sha(data) !== region.sha256) throw new Error('Captured input changed or has the wrong hash');
    regions.push({ address: region.address, data });
  }
  const contract = JSON.parse(await readFile(input.contract, 'utf8'));
  for (const asset of Object.values(input.auxiliary ?? {})) {
    if (['complete', 'ok'].includes(asset.status)) {
      const bytes = await readFile(asset.path);
      if (bytes.length !== asset.size || sha(bytes) !== asset.sha256) throw new Error('Captured auxiliary state changed');
    }
  }
  return { input, contract, memory: new WorkingMemory(regions), registers: { ...input.registers } };
}

export class WorkingMemory {
  constructor(regions) {
    this.regions = regions.map(r => ({ address: r.address, data: r.data.slice() }));
    this.writes = createHash('sha256'); this.writesCount = 0; this.writesComplete = true;
  }
  read(address, length) {
    const result = new Uint8Array(length);
    let written = 0;
    while (written < length) {
      const current = address + written;
      const region = this.regions.find(r => r.address <= current && current < r.address + r.data.length);
      if (!region) throw new RangeError(`Uncaptured memory at ${current.toString(16)}`);
      const count = Math.min(length - written, region.address + region.data.length - current);
      result.set(region.data.subarray(current - region.address, current - region.address + count), written);
      written += count;
    }
    return result;
  }
  write(address, bytes) {
    this.read(address, bytes.length); // Validate complete coverage before modifying any alias.
    for (const region of this.regions) {
      const lo = Math.max(address, region.address), hi = Math.min(address + bytes.length, region.address + region.data.length);
      if (lo < hi) region.data.set(bytes.subarray(lo - address, hi - address), lo - region.address);
    }
    if (bytes.length > 8) { this.writesComplete = false; return; }
    let value = 0n;
    for (let i = bytes.length - 1; i >= 0; i--) value = (value << 8n) | BigInt(bytes[i]);
    this.writes.update(`${address}:${bytes.length}:${value.toString(16)}\n`);
    this.writesCount++;
  }
}

export function finishCase(state, { stopReason, registers = state.registers, framebuffer } = {}) {
  if (!stopReason) throw new Error('Report the actual successful stop or failure reason');
  const { input, contract, memory } = state;
  const ranges = {};
  for (const range of contract.memory_ranges ?? []) {
    const address = number(range.address), length = number(range.length);
    const bytes = memory.read(address, length);
    ranges[range.name] = { address, length, sha256: sha(bytes) };
    if (length <= 4096) ranges[range.name].bytes_hex = Buffer.from(bytes).toString('hex');
  }
  const report = { initial_state_sha256: input.initial_state_sha256, stop_reason: stopReason,
    final_registers: registers, memory_ranges: ranges,
    final_memory_sha256: sha(Buffer.concat(memory.regions.map(r => Buffer.from(r.data)))),
    writes_count: memory.writesCount, write_trace_complete: memory.writesComplete,
    write_trace_sha256: memory.writes.copy().digest('hex') };
  if (framebuffer) report.framebuffer = { width: framebuffer.width, height: framebuffer.height, sha256: sha(framebuffer.rgba) };
  return report;
}

export async function saveReport(path, report) { await writeFile(path, JSON.stringify(report, null, 2)); }
