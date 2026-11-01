"""Compare declared observables; missing evidence never passes."""
import argparse
import hashlib
import json
from pathlib import Path
import re


def load_json(value):
    return json.loads(Path(value).read_text(encoding="utf-8-sig")) if isinstance(value, (str, Path)) else value


def normalize_int(value):
    if isinstance(value, bool):
        raise ValueError("boolean is not an integer observation")
    if isinstance(value, int):
        return value
    if isinstance(value, float) and not value.is_integer():
        raise ValueError('fractional numeric observation')
    if isinstance(value, str) and (value.lower().startswith("0x") or any(c in value.lower() for c in "abcdef")):
        return int(value, 16)
    return int(value)


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def compare_states(reference_report, js_report, contract=None):
    differences, missing, checks = [], [], []
    ref, js, spec = {}, {}, {}
    try:
        ref, js, spec = load_json(reference_report), load_json(js_report), load_json(contract)
        if not all(isinstance(v, dict) for v in (ref, js, spec)):
            raise ValueError("reference, JavaScript report and contract must be objects")
    except (OSError, ValueError, TypeError) as exc:
        missing.append(str(exc))
        ref, js, spec = {}, {}, {}

    def required(report, path, side):
        value = report
        for key in path.split("."):
            if not isinstance(value, dict) or key not in value:
                missing.append(f"{side}: missing {path}")
                return None
            value = value[key]
        return value

    def compare(name, a, b, numeric=False, digest=False):
        if a is None or b is None:
            missing.append(f"{name}: missing/null observation")
            return
        try:
            if numeric:
                a, b = normalize_int(a), normalize_int(b)
            if digest:
                if not all(isinstance(v, str) and re.fullmatch(r"[a-fA-F0-9]{64}", v) for v in (a, b)):
                    raise ValueError("expected SHA-256")
                a, b = a.lower(), b.lower()
            checks.append(name)
            if a != b:
                differences.append({"name": name, "reference": a, "javascript": b})
        except (TypeError, ValueError) as exc:
            missing.append(f"{name}: invalid observation: {exc}")

    if spec:
        if spec.get("schema_version") != 1:
            missing.append("contract.schema_version must be 1")
        allowed = {"schema_version", "name", "evidence_class", "registers", "flags_mask", "whole_memory",
                   "memory_ranges", "ordered_writes", "framebuffer", "stop_reasons", "exclusions"}
        if set(spec) - allowed:
            missing.append(f"unknown contract fields: {sorted(set(spec) - allowed)}")
        compare("initial_state_sha256", required(ref, "initial_state_sha256", "reference"),
                required(js, "initial_state_sha256", "javascript"), digest=True)
        if differences:
            missing.append("different initial states: not a same-input comparison")
        stops = spec.get("stop_reasons", {})
        for side, report in [("reference", ref), ("javascript", js)]:
            accepted = stops.get(side) if isinstance(stops, dict) else None
            if not isinstance(accepted, list) or not accepted or not all(isinstance(s, str) and s.strip() for s in accepted):
                missing.append(f"contract.stop_reasons.{side} must list successful endpoints")
            elif report.get("stop_reason") not in accepted:
                missing.append(f"{side}: unexpected endpoint {report.get('stop_reason')!r}")
            elif any(word in report['stop_reason'].lower() for word in ('exception', 'error', 'limit', 'unsupported', 'timeout', 'uncaptured', 'unmapped', 'partial', 'failed', 'failure', 'incomplete')):
                missing.append(f"{side}: execution failure cannot be accepted as a successful endpoint")
        registers = spec.get("registers", [])
        if not isinstance(registers, list) or not all(isinstance(r, str) and r and "." not in r for r in registers):
            missing.append("contract.registers must list register names")
            registers = []
        for reg in registers:
            compare(f"register.{reg}", required(ref, f"final_registers.{reg}", "reference"),
                    required(js, f"final_registers.{reg}", "javascript"), numeric=True)
        if spec.get("flags_mask") is not None:
            try:
                mask = normalize_int(spec["flags_mask"])
                if mask <= 0 or mask > 0xffffffff:
                    raise ValueError("flag mask must be nonzero and 32 bit")
                a, b = required(ref, "final_registers.eflags", "reference"), required(js, "final_registers.eflags", "javascript")
                if a is not None and b is not None:
                    compare("flags", normalize_int(a) & mask, normalize_int(b) & mask)
            except (TypeError, ValueError) as exc:
                missing.append(f"flags: {exc}")
        for field in ("whole_memory", "ordered_writes", "framebuffer"):
            if field in spec and type(spec[field]) is not bool:
                missing.append(f"contract.{field} must be boolean")
        if spec.get("whole_memory") is True:
            compare("memory", required(ref, "final_memory_sha256", "reference"),
                    required(js, "final_memory_sha256", "javascript"), digest=True)
        ranges = spec.get("memory_ranges", [])
        if not isinstance(ranges, list):
            missing.append("contract.memory_ranges must be a list")
            ranges = []
        names = set()
        def observed_range(report, name):
            values = report.get('memory_ranges', {})
            value = values.get(name, {}) if isinstance(values, dict) else {}
            return value if isinstance(value, dict) else {}
        for region in ranges:
            try:
                name = region["name"]
                address, length = normalize_int(region["address"]), normalize_int(region["length"])
                if not isinstance(name, str) or not name or "." in name or name in names or address < 0 or length <= 0:
                    raise ValueError("invalid/duplicate range name or bounds")
                names.add(name)
                for side, report in [("reference", ref), ("javascript", js)]:
                    observed = required(report, f"memory_ranges.{name}", side)
                    if not isinstance(observed, dict) or normalize_int(observed.get("address", -1)) != address or normalize_int(observed.get("length", -1)) != length:
                        missing.append(f"{side}: {name} does not describe the declared range")
                compare(f"memory.{name}", required(ref, f"memory_ranges.{name}.sha256", "reference"),
                        required(js, f"memory_ranges.{name}.sha256", "javascript"), digest=True)
                # Optional bounded bytes localize a mismatch; hashes still cover the full range.
                for side, report in [('reference', ref), ('javascript', js)]:
                    observed = observed_range(report, name)
                    if isinstance(observed, dict) and 'bytes_hex' in observed:
                        payload = bytes.fromhex(observed['bytes_hex'])
                        if len(payload) != length or hashlib.sha256(payload).hexdigest() != str(observed.get('sha256')).lower():
                            missing.append(f'{side}: {name} diagnostic bytes disagree with the range digest')
                left = observed_range(ref, name).get('bytes_hex')
                right = observed_range(js, name).get('bytes_hex')
                if left is not None and right is not None and left != right:
                    a, b = bytes.fromhex(left), bytes.fromhex(right)
                    at = next((i for i, pair in enumerate(zip(a, b)) if pair[0] != pair[1]), None)
                    if at is not None and differences and differences[-1]['name'] == f'memory.{name}':
                        differences[-1].update(first_offset=at, first_address=address+at,
                                               reference_bytes=a[at:at+16].hex(), javascript_bytes=b[at:at+16].hex())
            except (KeyError, TypeError, ValueError) as exc:
                missing.append(f"invalid memory range: {exc}")
        if spec.get("ordered_writes") is True:
            for side, report in [("reference", ref), ("javascript", js)]:
                if report.get("write_trace_complete") is not True:
                    missing.append(f"{side}: write digest must cover the complete stream")
                try:
                    count = normalize_int(report.get('writes_count'))
                    if count < 0:
                        raise ValueError('negative count')
                except (TypeError, ValueError):
                    missing.append(f'{side}: invalid write count')
            compare("writes.count", required(ref, "writes_count", "reference"), required(js, "writes_count", "javascript"), numeric=True)
            compare("writes.order", required(ref, "write_trace_sha256", "reference"), required(js, "write_trace_sha256", "javascript"), digest=True)
        if spec.get("framebuffer") is True:
            for field in ("width", "height"):
                compare(f"framebuffer.{field}", required(ref, f"framebuffer.{field}", "reference"), required(js, f"framebuffer.{field}", "javascript"), numeric=True)
                for side, report in [('reference', ref), ('javascript', js)]:
                    value = report.get('framebuffer', {})
                    try:
                        valid = isinstance(value, dict) and normalize_int(value.get(field, 0)) > 0
                    except (TypeError, ValueError):
                        valid = False
                    if not valid:
                        missing.append(f'{side}: invalid framebuffer geometry')
            compare("framebuffer.rgba", required(ref, "framebuffer.sha256", "reference"), required(js, "framebuffer.sha256", "javascript"), digest=True)
        if not (registers or spec.get("flags_mask") or ranges or any(spec.get(f) is True for f in ("whole_memory", "ordered_writes", "framebuffer"))):
            missing.append("contract must declare at least one observable")
    else:
        missing.append("an explicit nonempty comparison contract is required")
    return {
        "verdict": "INSUFFICIENT_EVIDENCE" if missing else "FAIL" if differences else "PASS",
        "difference_count": len(differences), "differences": differences, "missing_evidence": missing,
        "checks_performed": checks, "contract_sha256": canonical_hash(spec) if spec else None,
        "evidence_class": spec.get("evidence_class", "unspecified")
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--reference", required=True)
    parser.add_argument("--js", required=True)
    parser.add_argument("--contract", required=True)
    parser.add_argument("--output")
    args = parser.parse_args()
    report = compare_states(args.reference, args.js, args.contract)
    output = json.dumps(report, indent=2)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    print(output)
    return {"PASS": 0, "FAIL": 1, "INSUFFICIENT_EVIDENCE": 2}[report["verdict"]]


if __name__ == "__main__":
    raise SystemExit(main())
