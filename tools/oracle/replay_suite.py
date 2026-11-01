"""Run a declared validation ladder from immutable full-run checkpoints.

Commands are explicit offline Python/Node drivers, never shell strings or emulators.
Drivers receive one input manifest and write the comparison report schema.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys
import hashlib
import re

from capture_corpus import CaptureCorpus
from differential_compare import canonical_hash, compare_states, load_json, normalize_int
from unicorn_runner import UnicornCaptureRunner
from sequence_compare import compare_sequences

STAGES = ('routine', 'interval', 'scene', 'transition', 'browser')


def run_driver(command, input_path, output_path, cwd, timeout, *, json_output=True):
    if not isinstance(command, list) or not command or not all(isinstance(a, str) for a in command):
        raise ValueError('driver command must be an argument list')
    program = Path(command[0]).stem.lower()
    if not re.fullmatch(r'node|python\d*', program):
        raise ValueError('only explicit offline Node/Python drivers are accepted; no shell or emulator commands')
    substitutions = {'{input}': str(input_path), '{output}': str(output_path)}
    args = [substitutions.get(a, a) for a in command]
    if '{input}' not in command or '{output}' not in command:
        raise ValueError('driver must explicitly accept {input} and {output}')
    result = subprocess.run(args, cwd=cwd, capture_output=True, text=True, timeout=timeout, shell=False)
    if result.returncode:
        raise ValueError(f'offline driver failed ({result.returncode}): {result.stderr[-2000:]}')
    if not output_path.is_file():
        raise ValueError('driver did not produce its report')
    return load_json(output_path) if json_output else None


def run_suite(session, plan_path, output_directory):
    plan_path = Path(plan_path).resolve()
    plan = load_json(plan_path)
    corpus = CaptureCorpus(session)
    output = Path(output_directory).resolve()
    # Do not write inside any capture session or overwrite prior suite evidence.
    under_extract = any(p.name.lower() == 'extract' and p.parent.name.lower() == 'oracle' for p in [output, *output.parents])
    under_original = any(p.name.lower() == 'original' for p in [output, *output.parents])
    if output.is_relative_to(corpus.session) or under_extract or under_original or output.exists():
        raise ValueError('choose a new unused suite output directory outside the capture session')
    stages = plan.get('required_stages')
    if not isinstance(stages, list) or not stages or any(s not in STAGES for s in stages):
        raise ValueError('required_stages must explicitly name validation stages')
    cases = plan.get('cases')
    if not isinstance(cases, list) or not cases:
        raise ValueError('plan must contain real checkpoint cases')
    output.mkdir(parents=True)
    rows = []
    for index, case in enumerate(cases):
        row = {'name': case.get('name', str(index)), 'stage': case.get('stage'), 'capture': case.get('capture')}
        work = output / f'case_{index:04d}'
        work.mkdir()
        try:
            if case.get('stage') not in STAGES:
                raise ValueError('case needs an explicit validation stage')
            state = corpus.load(case['capture'])
            contract_path = (plan_path.parent / case['contract']).resolve()
            contract = load_json(contract_path)
            ranges = [dict(r, address=normalize_int(r['address']), length=normalize_int(r['length']))
                      for r in contract.get('memory_ranges', [])]
            manifest = {'capture': state.capture, 'elapsed_us': state.elapsed_us,
                        'capture_directory': str(state.directory), 'auxiliary': state.auxiliary,
                        'registers': state.registers, 'machine': state.machine,
                        'regions': [{'address': r.address, 'path': r.source, 'length': len(r.data),
                                     'sha256': hashlib.sha256(r.data).hexdigest()} for r in state.regions],
                        'parameters': case.get('parameters', {}), 'contract': str(contract_path),
                        'initial_state_sha256': canonical_hash({'capture':state.state_hash(), 'parameters':case.get('parameters',{})})}
            reference_path, js_path = work/'reference.json', work/'javascript.json'
            sequence = case.get('sequence', False)
            if type(sequence) is not bool:
                raise ValueError('sequence must be boolean')
            if sequence and not case.get('reference_command'):
                raise ValueError('sequence cases require an explicit offline reference driver and schedule')
            if sequence and case['stage'] in ('scene','transition') and (case.get('expected_samples') is None or case.get('final_tick') is None):
                raise ValueError('whole-scene/transition streams require expected_samples and final_tick to detect incomplete endings')
            if case.get('reference_command'):
                reference = None
            else:
                runner = UnicornCaptureRunner(snapshot=state, mode=case.get('mode'))
                reference = runner.run(stop_linear=normalize_int(case['stop_linear']),
                                       instruction_limit=case.get('instruction_limit', 1000000), ranges=ranges)
                manifest['initial_state_sha256'] = reference['initial_state_sha256']
                reference_path.write_text(json.dumps(reference, indent=2), encoding='utf-8')
            input_path = work/'input.json'
            input_path.write_text(json.dumps(manifest, indent=2), encoding='utf-8')
            timeout = case.get('timeout_seconds', 120)
            if reference is None:
                reference = run_driver(case['reference_command'], input_path, reference_path, plan_path.parent, timeout, json_output=not sequence)
            js = run_driver(case['javascript_command'], input_path, js_path, plan_path.parent, timeout, json_output=not sequence)
            if sequence:
                report = compare_sequences(reference_path, js_path, contract, expected_samples=case.get('expected_samples'),
                                           final_tick=case.get('final_tick'), expected_input=manifest['initial_state_sha256'])
            else:
                report = compare_states(reference, js, contract)
            if not sequence and any(r.get('initial_state_sha256') != manifest['initial_state_sha256'] for r in (reference, js)):
                report['verdict'] = 'INSUFFICIENT_EVIDENCE'
                report['missing_evidence'].append('driver input identity does not match the selected checkpoint')
            row.update(report, elapsed_us=state.elapsed_us, report=str(work/'comparison.json'))
            (work/'comparison.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        except Exception as exc:
            # Adapter/CPU setup failures are missing evidence, never a successful case.
            row.update(verdict='INSUFFICIENT_EVIDENCE', missing_evidence=[f'{type(exc).__name__}: {exc}'])
        rows.append(row)
    missing_stages = [s for s in stages if not any(r['stage']==s for r in rows)]
    verdict = ('INSUFFICIENT_EVIDENCE' if missing_stages or any(r['verdict']=='INSUFFICIENT_EVIDENCE' for r in rows)
               else 'FAIL' if any(r['verdict']=='FAIL' for r in rows) else 'PASS')
    summary = {'verdict': verdict, 'required_stages': stages, 'missing_stages': missing_stages,
               'cases':rows, 'scope':'declared checkpoints and observables only',
               'timing_model': plan.get('timing_model', 'unspecified; no hardware-timing claim')}
    (output/'summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
    return summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--session',required=True);parser.add_argument('--plan');parser.add_argument('--output')
    parser.add_argument('--list-checkpoints',action='store_true')
    args=parser.parse_args()
    if args.list_checkpoints:
        print(json.dumps(list(CaptureCorpus(args.session).checkpoints()),indent=2))
        return 0
    if not args.plan or not args.output: parser.error('--plan and --output are required for execution')
    report=run_suite(args.session,args.plan,args.output)
    print(json.dumps(report,indent=2))
    return {'PASS':0,'FAIL':1,'INSUFFICIENT_EVIDENCE':2}[report['verdict']]


if __name__=='__main__': raise SystemExit(main())
