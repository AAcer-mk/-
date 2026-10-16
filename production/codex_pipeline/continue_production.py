#!/usr/bin/env python3
"""One resumable entry point: render, conform, play, export, reconcile, audit.

Does not publish a film or start an unattended service. Existing actor gaps stay
explicit instead of being filled with repeated images.
"""
import fcntl
from pathlib import Path
import subprocess
import sys

HERE=Path(__file__).resolve().parent
SOURCE=Path('/workspace/silent-protocol-source')


def run(*args):subprocess.run([sys.executable,*map(str,args)],check=True)


def main():
    # Existing frame locks are checked before invoking the scheduler; a second
    # caller cannot open another configuration variant alongside active work.
    for path in (HERE/'output').glob('*/*/render.lock'):
        with path.open('r') as file:
            try:fcntl.flock(file,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError:
                print('ACTIVE_RENDER_PRESERVED',path,flush=True)
                run(HERE/'refresh_progress.py')
                return 75
    lock_path=HERE/'output/production.lock';lock_path.parent.mkdir(parents=True,exist_ok=True)
    with lock_path.open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
        run(HERE/'pipeline.py','--source',SOURCE,'produce','--width','1920','--samples','8')
        run(HERE/'render_native_cards.py','--source',SOURCE)
        run(HERE/'refresh_progress.py','--export-completed')
        run(HERE/'build_audit.py','--source',SOURCE,'--repo',HERE.parents[1])
        run(HERE/'build_production_graph.py','--source',SOURCE)
        print('IMPLEMENTED_QUEUE_VERIFIED_AND_EXPORTED; actor assets and performances remain unfinished',flush=True)
    return 0


if __name__=='__main__':sys.exit(main())
