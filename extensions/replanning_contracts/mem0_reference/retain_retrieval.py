#!/usr/bin/env python3
"""Reproduce the frozen no-model search run while retaining closed read copies.

Only TemporaryDirectory calls with the runner's exact prefix are intercepted.
The original runner, protocol and protected live inputs are left unchanged.
"""
import argparse
import hashlib
import json
import shutil
import tempfile
import time
from pathlib import Path

HERE=Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path,value):
    path.write_text(json.dumps(value,indent=2)+'\n')


def reproduce(original,out):
    require_new = not out.exists()
    if not require_new:
        raise ValueError('Reproduction output already exists; preserve measured evidence')
    out.mkdir(parents=True)
    protocol=json.loads((original/'protocol.json').read_text())
    if digest(original/'protocol.json') != (original/'protocol.sha256').read_text().strip():
        raise ValueError('Original protocol hash mismatch')
    if digest(HERE/'retrieval.py') != protocol['source_sha256']:
        raise ValueError('Original retrieval source changed')
    for name in ('protocol.json','protocol.sha256'):
        shutil.copy2(original/name,out/name)
    order=[(n,state) for n in protocol['sizes'] for state in protocol['states']]
    frozen=dict(prepared_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
        wrapper_source_sha256=digest(__file__),retrieval_source_sha256=digest(HERE/'retrieval.py'),
        original_protocol_sha256=digest(original/'protocol.json'),
        original_cases_sha256=digest(original/'cases.json'),
        original_summary_sha256=digest(original/'summary.json'),
        capture_prefix='memory-retrieval-copy-',expected_captures=len(order),
        interpretation='Computational reproduction of the same frozen query set, not independent experimental observations.',
        additional_model_requests=0)
    write(out/'retention_protocol.json',frozen)
    (out/'retention_protocol.sha256').write_text(digest(out/'retention_protocol.json')+'\n')
    # Import does not execute the measured run. Freeze above precedes all queries.
    import retrieval
    captures=[]
    native_temporary_directory=tempfile.TemporaryDirectory

    class RetainedDirectory:
        def __init__(self,delegate):
            self.delegate=delegate
            self.name=delegate.name

        def __enter__(self):
            return self.delegate.__enter__()

        def __exit__(self,exc_type,exc_value,traceback):
            # retrieval.run closes both native clients in its finally block
            # before control reaches this outer context manager's __exit__.
            ordinal=len(captures)
            if ordinal >= len(order):
                raise ValueError('More matching temporary read copies than frozen states')
            n,state=order[ordinal]
            relative=Path('retained_raw')/f'n{n}__{state}'
            destination=out/relative
            shutil.copytree(self.name,destination)
            record=dict(ordinal=ordinal,n_source_preferences=n,state=state,path=str(relative),
                captured_at_utc=time.strftime('%Y-%m-%dT%H:%M:%SZ',time.gmtime()),
                runner_body_exception=None if exc_type is None else exc_type.__name__,
                capture_boundary='TemporaryDirectory.__exit__, after runner closes native clients',
                files={str(p.relative_to(destination)):digest(p) for p in destination.rglob('*') if p.is_file()})
            captures.append(record)
            write(out/'retained_manifest.json',dict(captures=captures))
            return self.delegate.__exit__(exc_type,exc_value,traceback)

    def temporary_directory(*args,**kwargs):
        delegate=native_temporary_directory(*args,**kwargs)
        if kwargs.get('prefix') == 'memory-retrieval-copy-':
            return RetainedDirectory(delegate)
        return delegate

    tempfile.TemporaryDirectory=temporary_directory
    try:
        retrieval.run(out,HERE/'live_results')
    finally:
        tempfile.TemporaryDirectory=native_temporary_directory
    if len(captures) != len(order):
        raise ValueError('Incomplete after-close retention coverage')
    if digest(__file__) != frozen['wrapper_source_sha256']:
        raise ValueError('Frozen wrapper source changed during reproduction')
    if digest(out/'retention_protocol.json') != (out/'retention_protocol.sha256').read_text().strip():
        raise ValueError('Frozen retention protocol changed')
    print(json.dumps(dict(retained_states=len(captures),additional_model_requests=0,
        interpretation=frozen['interpretation'])))


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--original',type=Path,default=HERE/'retrieval_results')
    parser.add_argument('--out',type=Path,default=HERE/'retrieval_reproduction')
    args=parser.parse_args()
    reproduce(args.original.resolve(),args.out.resolve())
