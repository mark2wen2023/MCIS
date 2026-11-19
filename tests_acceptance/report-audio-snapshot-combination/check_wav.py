"""Pinned synthetic tone bytes + existing pure composition. No application imports."""
import hashlib
import io
from pathlib import Path
import runpy
import subprocess
from tempfile import TemporaryDirectory
import wave

ROOT = Path(__file__).resolve().parents[2]
COMMIT = 'c10b2cd787f4b70d404893be9b9bfeb4f7de4361'
SOURCE_PATH = 'tests_acceptance/synthetic-audio-review/make_wav.py'
SOURCE_SHA256 = 'd5a9285e64898077888f92615082e33278fd405ddabadad4e339a82fcec0cd23'
WAV_SHA256 = '48e65e6aa7493adecacf16a5a2bd09e0966303658ec2bf6c980cc239fb4c266f'


def need(ok, message):
    if not ok:
        raise RuntimeError(message)


# Fixed local object only. Disable lazy fetch and user/system Git configuration.
# No environment values are read, no fetch fallback, and no source copy is saved.
result = subprocess.run(['/usr/bin/git', '-C', str(ROOT), 'show', COMMIT+':'+SOURCE_PATH],
                        env={'PATH':'/usr/bin:/bin', 'GIT_NO_LAZY_FETCH':'1',
                             'GIT_CONFIG_NOSYSTEM':'1', 'GIT_CONFIG_GLOBAL':'/dev/null'},
                        stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
need(result.returncode == 0, 'Required fixed local generator object unavailable; stop, no automatic fetch')
need(hashlib.sha256(result.stdout).hexdigest() == SOURCE_SHA256, 'Generator source hash mismatch')
namespace = {'__name__':'pinned_synthetic_generator'}
exec(compile(result.stdout, '<pinned synthetic generator>', 'exec'), namespace)
scenario = runpy.run_path(str(Path(__file__).with_name('check.py')))['scenario']
with TemporaryDirectory(prefix='mcis-synthetic-wav-', dir='/tmp') as temporary:
    output = Path(temporary)/'generated'
    manifest = namespace['generate'](output)
    need({p.name for p in output.iterdir()} == {'synthetic-markers.wav','manifest.json'}, 'Unexpected generator members')
    content = (output/'synthetic-markers.wav').read_bytes()
    digest = hashlib.sha256(content).hexdigest()
    need(digest == WAV_SHA256 == manifest['sha256'], 'Generated WAV hash mismatch')
    with wave.open(io.BytesIO(content), 'rb') as audio:
        need(audio.getcomptype() == 'NONE', 'Expected PCM')
        channels, width, rate, frames = audio.getnchannels(), audio.getsampwidth(), audio.getframerate(), audio.getnframes()
        need((channels,width,rate,frames) == (1,2,8000,96000), 'Unexpected WAV sample basis')
        need(len(audio.readframes(frames+1)) == frames*channels*width, 'PCM byte count mismatch')
    wav = dict(sha256=digest, durationMs=frames*1000//rate,
               audio=dict(format='PCM_WAV',channels=channels,sampleWidthBytes=width,
                          sampleRateHz=rate,frames=frames))
    for unknown in (False, True):
        old, new, again = scenario(unknown, wav=wav)
        need(old == again, 'Old snapshot/range changed')
        for _, value in (old,new,again):
            need(value['sourceSha256'] == digest, 'Different original WAV digest')
            need(value['timeBasis'] == dict(kind='file-relative-milliseconds',frames=frames,sampleRateHz=rate), 'Different original sample basis')
            need(value['mediaRetrieved'] is False and value['factVerified'] is False, 'Unexpected verification claim')
        need((old[1]['startMs'],old[1]['endMs']) == ((None,None) if unknown else (1000,2500)), 'Old range')
        need((new[1]['startMs'],new[1]['endMs']) == (4000,5500), 'New range')
need(not Path(temporary).exists(), 'Temporary output not cleaned')
print('PASS pinned generated WAV SHA-256:', digest)
print('COMPLETE: synthetic 8 kHz tones only; no speech/ASR, playback, authority, registration or persistent binding verified')
