"""Stream interval/scene/operation reports and stop at the first divergent sample."""
import argparse
import itertools
import json
import math
from pathlib import Path

from differential_compare import compare_states, load_json


def compare_sequences(reference_path, javascript_path, contract, *, expected_samples=None, final_tick=None, expected_input=None):
    compared = 0
    try:
        contract = load_json(contract)
        if expected_samples is not None and (type(expected_samples) is not int or expected_samples <= 0):
            raise ValueError('expected sample count must be positive')
        with Path(reference_path).open(encoding='utf-8-sig') as reference, Path(javascript_path).open(encoding='utf-8-sig') as javascript:
            left = (json.loads(line) for line in reference if line.strip())
            right = (json.loads(line) for line in javascript if line.strip())
            previous = None
            for index, (a, b) in enumerate(itertools.zip_longest(left, right)):
                if a is None or b is None:
                    return {'verdict':'INSUFFICIENT_EVIDENCE','compared_samples':compared,'first_sample':index,
                            'reason':'one sequence ends before the other'}
                if not isinstance(a, dict) or not isinstance(b, dict):
                    raise ValueError('each sample must be a report object')
                sample = a.get('sample')
                if not isinstance(sample, dict) or not sample or sample != b.get('sample'):
                    return {'verdict':'INSUFFICIENT_EVIDENCE','compared_samples':compared,'first_sample':index,
                            'reason':'frame/tick/operation markers do not align','reference_sample':sample,'javascript_sample':b.get('sample')}
                tick = sample.get('tick')
                if not isinstance(tick, (int, float)) or isinstance(tick, bool) or not math.isfinite(tick) or tick < 0 or previous is not None and tick < previous:
                    raise ValueError('sample.tick must be nonnegative and nondecreasing')
                if expected_input is not None and any(report.get('initial_state_sha256') != expected_input for report in (a,b)):
                    raise ValueError('sequence input identity differs from the selected checkpoint')
                previous = tick
                result = compare_states(a, b, contract)
                if result['verdict'] != 'PASS':
                    return dict(result, compared_samples=compared, first_sample=index, sample=sample)
                compared += 1
        if not compared:
            raise ValueError('empty streams are not verification evidence')
        if expected_samples is not None and compared != expected_samples:
            raise ValueError(f'expected {expected_samples} samples, received {compared}')
        if final_tick is not None and previous != final_tick:
            raise ValueError(f'expected final tick {final_tick}, received {previous}')
        return {'verdict':'PASS','compared_samples':compared,'scope':'declared aligned samples/observables under the reported schedule'}
    except (OSError, ValueError, TypeError) as exc:
        return {'verdict':'INSUFFICIENT_EVIDENCE','compared_samples':compared,'reason':str(exc)}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--reference',required=True);p.add_argument('--js',required=True)
    p.add_argument('--contract',required=True);p.add_argument('--output')
    p.add_argument('--expected-samples',type=int);p.add_argument('--final-tick',type=float);a=p.parse_args()
    result=compare_sequences(a.reference,a.js,a.contract,expected_samples=a.expected_samples,final_tick=a.final_tick)
    text=json.dumps(result,indent=2)
    if a.output:Path(a.output).write_text(text,encoding='utf-8')
    print(text)
    raise SystemExit({'PASS':0,'FAIL':1,'INSUFFICIENT_EVIDENCE':2}[result['verdict']])
