"""Check timeline cadence and profile structure; flag unverified RAM coverage."""

import argparse
import json
import sys
from pathlib import Path


def validate_timeline(config):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    def object_field(name):
        value = config.get(name, {})
        if not isinstance(value, dict):
            errors.append(f"{name} must be an object")
            return {}
        return value

    trigger = object_field("trigger")
    process = object_field("process")
    events = object_field("events")
    reference = object_field("reference")
    assets = object_field("assets")
    memory = config.get("memory", [])

    require(config.get("version") == 2, "version must be 2")
    require(trigger.get("type") == "emulated_time", "trigger.type must be emulated_time")
    interval = trigger.get("interval_ms")
    require(type(interval) is int and 1000 <= interval <= 2000,
            "trigger.interval_ms must be 1000-2000 (1-2 seconds)")
    delay = trigger.get("initial_delay_ms")
    require(type(delay) is int and 0 <= delay <= 2000,
            "trigger.initial_delay_ms must be 0-2000")
    require(process.get("on_exit") == "stop", "process.on_exit must be stop")
    require(events.get("execution_addresses", []) == [],
            "events.execution_addresses must be empty for the first timeline capture")
    require(reference.get("enabled", False) is False,
            "reference.enabled must be false for the first timeline capture")
    require(reference.get("trace_instructions", False) is False,
            "reference.trace_instructions must be false")
    require(reference.get("start_at_first_address", False) is False,
            "reference.start_at_first_address must be false")
    require(reference.get("expected_cycles", 0) == 0,
            "reference.expected_cycles must be 0 or omitted; record actual menu setting separately")
    for name in ("registers", "screenshot", "machine_state", "vga_state"):
        asset = assets.get(name, {})
        require(asset.get("enabled") is True and asset.get("every_n_captures") == 1,
                f"assets.{name} must be enabled on every snapshot")
    errors.extend(validate_memory_regions(memory))
    return errors


def validate_memory_regions(memory):
    errors = []

    def require(condition, message):
        if not condition:
            errors.append(message)

    require(isinstance(memory, list) and len(memory) > 0,
            "at least one memory region is required")
    if isinstance(memory, list):
        for index, region in enumerate(memory):
            require(isinstance(region, dict) and bool(region.get("segment")),
                    f"memory[{index}] needs a segment selector")
            if not isinstance(region, dict):
                continue
            values = {}
            for field, maximum in (("segment", 0xffff), ("offset", 0xffffffff), ("length", 0xffffffff)):
                value = region.get(field)
                try:
                    if not isinstance(value, str) or not value or any(c not in '0123456789abcdefABCDEF' for c in value):
                        raise ValueError
                    number = int(value, 16)
                    if number > maximum or (field == "length" and number == 0):
                        raise ValueError
                    values[field] = number
                except ValueError:
                    errors.append(f"memory[{index}].{field} must be a valid hexadecimal string within its address/size bounds")
            if "offset" in values and "length" in values:
                require(values["offset"] + values["length"] <= 0x100000000,
                        f"memory[{index}] offset + length exceeds the 32-bit offset range")
    return errors


def validate_paired_targeted(config, call_bytes=None):
    """Validate one E8 rel32 entry/return pair; supplied bytes need provenance."""
    errors = validate_memory_regions(config.get('memory', []))

    def require(condition, message):
        if not condition:
            errors.append(message)

    def hex_field(event, key, maximum=0xffffffff):
        value = event.get(key)
        try:
            if not isinstance(value, str) or not value or any(c not in '0123456789abcdefABCDEF' for c in value):
                raise ValueError
            number = int(value, 16)
            if number > maximum:
                raise ValueError
            return number
        except ValueError:
            errors.append(f'paired event {key} must be a hexadecimal string within bounds')
            return None

    require(config.get('version') == 2, 'version must be 2')
    events = config.get('events', {})
    reference = config.get('reference', {})
    if not isinstance(events, dict) or not isinstance(reference, dict):
        return errors + ['events and reference must be objects']
    addresses = events.get('execution_addresses', [])
    if not isinstance(addresses, list) or any(not isinstance(a, dict) for a in addresses):
        return errors + ['execution_addresses must be a list of event objects']
    sources = [a for a in addresses if a.get('pair_source') is True]
    returns = [a for a in addresses if a.get('pair_return') is True]
    if len(sources) != 1 or len(returns) != 1 or len(addresses) != 2:
        return errors + ['paired-targeted check requires exactly one pair_source and one pair_return event']
    source, endpoint = sources[0], returns[0]
    require(events.get('enabled') is True, 'events.enabled must be true')
    require(reference.get('enabled') is True and reference.get('trace_instructions') is True,
            'paired reference capture requires enabled instruction tracing')
    require(reference.get('start_at_first_address') is True, 'start_at_first_address must be true')
    maximum = reference.get('max_events', 100000)
    require(type(maximum) is int and 1 <= maximum <= 1000000, 'max_events must be 1-1000000')
    require(config.get('on_capture_error') == 'stop', 'on_capture_error must be stop')
    require(type(source.get('occurrence')) is int and source['occurrence'] > 0,
            'pair_source requires a positive occurrence')
    require(not source.get('pair_return') and not source.get('stop_after_capture'),
            'pair_source must not be a return or stop event')
    require(endpoint.get('occurrence') == 1 and endpoint.get('stop_after_capture') is True,
            'pair_return requires occurrence=1 and stop_after_capture=true')
    require(not endpoint.get('pair_source'), 'pair_return must not also be pair_source')
    source_selector = hex_field(source, 'selector', 0xffff)
    return_selector = hex_field(endpoint, 'selector', 0xffff)
    require(source_selector == return_selector, 'near-call pair must use the same CS selector')
    call_offset = hex_field(source, 'previous_offset')
    entry_offset = hex_field(source, 'offset')
    return_offset = hex_field(endpoint, 'offset')
    try:
        code = bytes.fromhex(call_bytes or '')
        if len(code) != 5 or code[0] != 0xe8:
            raise ValueError
    except (ValueError, TypeError):
        return errors + ['provide verified five-byte E8 rel32 CALL bytes with --call-bytes; other call encodings need separate review']
    if call_offset is not None:
        expected_return = (call_offset + 5) & 0xffffffff
        expected_entry = (expected_return + int.from_bytes(code[1:], 'little', signed=True)) & 0xffffffff
        require(entry_offset == expected_entry,
                f'pair_source.offset must be the post-CALL routine entry {expected_entry:08X}, not the CALL site; previous_offset identifies CALL')
        require(return_offset == expected_return,
                f'pair_return.offset must be the post-return caller continuation {expected_return:08X}')
    assets = config.get('assets', {})
    for name in ('registers', 'machine_state'):
        asset = assets.get(name, {}) if isinstance(assets, dict) else {}
        require(isinstance(asset, dict) and asset.get('enabled') is True and asset.get('every_n_captures') == 1,
                f'assets.{name} must be enabled at both endpoints')
    return errors


def memory_coverage_warnings(config):
    """A size warning is not a proof of coverage or a universal RAM minimum."""
    lengths = [int(region['length'], 16) for region in config['memory']]
    if max(lengths, default=0) < 0x00800000:
        return [
            'All memory regions are smaller than the starter 8 MiB region. '
            'Justify the reduction using selector bases/limits, available RAM, and required input/heap/stack ranges. '
            'Overlapping selector dumps do not add coverage; do not call this a complete-memory capture.'
        ]
    return []


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--purpose", choices=["timeline", "paired-targeted"], required=True)
    parser.add_argument("--call-bytes", help="Verified five-byte E8 rel32 encoding at the source event's previous_offset")
    parser.add_argument("profile", type=Path)
    args = parser.parse_args()
    try:
        config = json.loads(args.profile.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"FAIL: cannot read profile: {exc}", file=sys.stderr)
        return 1
    if not isinstance(config, dict):
        print("FAIL: JSON root must be an object", file=sys.stderr)
        return 1
    errors = (validate_timeline(config) if args.purpose == 'timeline'
              else validate_paired_targeted(config, args.call_bytes))
    if errors:
        for error in errors:
            print(f"FAIL: {error}", file=sys.stderr)
        return 1
    for warning in memory_coverage_warnings(config):
        print(f"WARNING: {warning}", file=sys.stderr)
    if args.purpose == 'timeline':
        print("PASS: timeline profile samples every 1-2 seconds without a stopping address event or instruction trace")
    else:
        print("PASS: paired-targeted entry and return agree with supplied E8 rel32 CALL bytes")
        print("NOTE: verify CALL bytes against captured code and confirm normal core, 32-bit stack, selector bases, and an unmissed trigger in the human-run session.")
    print("NOTE: PASS does not verify memory coverage. Check descriptor bases/limits, required pointer ranges, and partial/unreadable assets after capture.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
