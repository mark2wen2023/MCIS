"""Explicit scripted demonstration only. No model adapter is imported or invoked."""
import argparse
import sys
from research.expert_group.engine import ROLES, _packet, load_packet
from research.expert_meeting.machine import Meeting, MAX_SNAPSHOT, canonical, verify_snapshot


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    modes = parser.add_mutually_exclusive_group(required=True)
    modes.add_argument('--simulate', action='store_true')
    modes.add_argument('--verify-stdin', action='store_true')
    parser.add_argument('--stop-after-turn', type=int, choices=range(1, 5))
    args = parser.parse_args(argv)
    if args.verify_stdin:
        if args.stop_after_turn is not None: parser.error('stop only applies to simulation')
        try:
            checked = verify_snapshot(sys.stdin.buffer.read(MAX_SNAPSHOT + 1))
            sys.stdout.buffer.write(canonical(checked) + b'\n')
            return 0
        except Exception:
            print('Snapshot rejected; no execution or identity proof.', file=sys.stderr)
            return 2
    meeting = Meeting()
    packet = _packet(load_packet())
    turns = 0
    try:
        for _ in range(2):
            meeting.act({'type': 'start_round'})
            for index, role in enumerate(ROLES):
                ticket = meeting.act({'type': 'issue_turn', 'roleId': role})['activeTurn']
                reviews = [{'itemId': item['itemId'], 'label': 'supported' if index == 0 else 'insufficient',
                            'quote': item['citation']['quote'], 'rationale': '脚本模拟占位意见，非模型能力结果。',
                            'uncertainty': '仅演示分歧保留，未核实来源、语义或事实。'} for item in packet['items']]
                meeting.act({'type': 'submit_simulated', 'ticketId': ticket['ticketId'],
                             'contextDigest': ticket['contextDigest'], 'reviews': reviews})
                turns += 1
                if args.stop_after_turn == turns:
                    meeting.act({'type': 'stop'})
                    sys.stdout.buffer.write(meeting.export() + b'\n')
                    return 0
    except KeyboardInterrupt:
        meeting.act({'type': 'stop'})
    sys.stdout.buffer.write(meeting.export() + b'\n')
    return 0


if __name__ == '__main__':
    sys.exit(main())
