"""Normal-path generated-byte checks only; no playback, app, network or Save."""
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import wave
from make_wav import generate
from make_fixture import timed_fixture


def require(ok, message):
    if not ok:
        raise RuntimeError(message)


with tempfile.TemporaryDirectory(prefix='mcis-synthetic-wav-') as tmp:
    root = Path(tmp)
    generate(root / 'first')
    generate(root / 'second')
    raw = (root / 'first/synthetic-markers.wav').read_bytes()
    require(raw == (root / 'second/synthetic-markers.wav').read_bytes(), 'Deterministic bytes')
    manifest = json.loads((root / 'first/manifest.json').read_text())
    require(hashlib.sha256(raw).hexdigest() == manifest['sha256'], 'Whole WAV hash')
    with wave.open(str(root / 'first/synthetic-markers.wav'), 'rb') as inp:
        require((inp.getnchannels(), inp.getsampwidth(), inp.getframerate(), inp.getnframes(), inp.getcomptype())
                == (1, 2, 8000, 96000, 'NONE'), 'PCM header and true time basis')
        pcm = inp.readframes(96000)
        require(inp.readframes(1) == b'', 'No additional PCM frames')
    samples = struct.unpack('<96000h', pcm)
    # Independent expected windows, not imported generator marker constants.
    expected = [(2000, 4000, 40), (9600, 14400, 20), (33600, 38400, 10), (64000, 66000, 40)]
    require([(m['startFrame'], m['endFrame'], 8000 // m['frequencyHz']) for m in manifest['markers']]
            == expected, 'Marker manifest agrees with expected positions/frequencies')
    for i, value in enumerate(samples):
        window = next(((a, period) for a, b, period in expected if a <= i < b), None)
        wanted = 0 if window is None else (2048 if (i-window[0]) % window[1] < window[1] // 2 else -2048)
        require(value == wanted, 'PCM marker/silence mismatch at frame ' + str(i))
    data = timed_fixture()
    bounds = [(r['doc']['startMs'], r['doc']['endMs']) for r in data['rows'][1:]]
    require(bounds == [(1000, 2500), (4000, 5500)], 'Existing timed fixture range compatibility')
    require(data['rows'][0]['doc']['audio'] == {'frames': 96000, 'sampleRateHz': 8000}, 'Fixture sample basis')
    for (start, end), (a, b, _) in zip(bounds, expected[1:3]):
        require(start * 8 <= a < b <= end * 8, 'Internal marker wholly inside corresponding range')
    require(all(not (start*8 <= a < end*8 or start*8 < b <= end*8)
                for start, end in bounds for a, b, _ in (expected[0], expected[3])), 'Outside cues outside both ranges')
    require(data['rows'][0]['doc']['machineDraft']['source']['currentSha256'] != manifest['sha256'],
            'Existing placeholder must not be presented as generated WAV identity')
    print('PASS deterministic PCM: 96000 frames / 8000Hz, all marker samples and silence, fixture range alignment')
    print('WAV SHA-256:', manifest['sha256'])
    print('NOT RUN: playback/browser, ASR, media registration, report location, Save, HTTP or backend')
