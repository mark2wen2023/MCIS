"""Deterministic non-speech PCM markers; explicit NEW output directory only."""
import argparse
import hashlib
import json
from pathlib import Path
import struct
import wave

RATE = 8000
FRAMES = 96000
# Half-open frame intervals; integer-period square waves, no random/clock input.
MARKERS = (
    ('outside-before', 2000, 4000, 200),
    ('revision-1-low', 9600, 14400, 400),
    ('revision-2-high', 33600, 38400, 800),
    ('outside-after', 64000, 66000, 200),
)


def generate(output_dir):
    output_dir = Path(output_dir)
    # Never overwrite or reuse an existing directory; parent must already exist.
    output_dir.mkdir(parents=False, exist_ok=False)
    samples = [0] * FRAMES
    for _, start, end, hz in MARKERS:
        period = RATE // hz
        for frame in range(start, end):
            samples[frame] = 2048 if (frame - start) % period < period // 2 else -2048
    path = output_dir / 'synthetic-markers.wav'
    with wave.open(str(path), 'wb') as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(RATE)
        out.writeframes(struct.pack('<' + 'h' * FRAMES, *samples))
    manifest = {
        'scope': 'synthetic-non-speech-not-asr-not-a-report-binding',
        'filename': path.name, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
        'sampleRateHz': RATE, 'frames': FRAMES, 'channels': 1, 'sampleWidthBytes': 2,
        'durationMs': 12000, 'intervalConvention': '[startFrame,endFrame)',
        'markers': [dict(id=name, startFrame=start, endFrame=end, frequencyHz=hz)
                    for name, start, end, hz in MARKERS],
        'referenceRangesMs': [[1000, 2500], [4000, 5500]],
        'warning': 'Old fixture source hashes are placeholders, NOT this WAV digest. No media registered or report linked.'
    }
    (output_dir / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', required=True, type=Path,
                        help='New directory under an existing parent; no overwrite')
    args = parser.parse_args()
    result = generate(args.output_dir)
    print('Generated non-speech WAV; SHA-256:', result['sha256'])
