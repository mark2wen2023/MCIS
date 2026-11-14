"""Explicit real-Pi-process protocol demonstration; provider responses are scripted."""
import argparse
import sys
from research.expert_meeting.machine import Meeting, canonical
from research.expert_bridge.protocol import Bridge
from research.expert_group.engine import ROLES
from research.expert_executor.executor import Executor, ExecutionError


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scripted-pi',action='store_true',required=True)
    args=parser.parse_args(argv)
    m=Meeting();bridge=Bridge(m);executor=Executor(bridge)
    code=0
    try:
        for _ in range(2):
            m.act({'type':'start_round'})
            for role in ROLES:executor.run_turn(role)
    except (ExecutionError,KeyboardInterrupt):
        executor.cancel();code=2
        print('Protocol run not accepted; not a real DeepSeek capability test.',file=sys.stderr)
    sys.stdout.buffer.write(canonical(executor.receipt())+b'\n')
    return code


if __name__=='__main__':sys.exit(main())
