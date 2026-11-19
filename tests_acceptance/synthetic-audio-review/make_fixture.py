"""Hand-authored text scenario only; no recording, ASR or database writes."""
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=True, sort_keys=True,
                                     separators=(',', ':')).encode('ascii')).hexdigest()


def fixture():
    case, evidence, run = 'SYN-TRAINING-ONLY', 'EV-SYN-TEXT-AUDIO', 'AR-SYN-REVIEW'
    source_hash = digest({'synthetic-placeholder': 'no audio bytes supplied'})
    artifact_hash = digest({'synthetic-placeholder': 'no recognition executed'})
    source = dict(caseId=case, evidenceId=evidence, currentSha256=source_hash,
                  registeredSha256=source_hash, stateDigest=digest({'synthetic-register': 1}),
                  durationMs=12000)
    transcript = {'segments': [], 'unlocatedSegments': [
        {'id': 'SEG-SYN-1', 'text': '听到提示后，过了一会儿才记录。'}]}
    draft = dict(source=source, artifactSha256=artifact_hash, transcript=transcript)
    initial = dict(machineDraft=draft, draftBytesSha256=digest(draft))
    common = dict(segmentId='SEG-SYN-1', hearingStatus='pending',
                  startMs=None, endMs=None, timeStatus='unknown',
                  speaker={'status': 'unknown', 'id': None},
                  machineArtifactSha256=artifact_hash, audioSha256=source_hash,
                  operator='SYNTHETIC-REVIEWER', role='Investigator', factVerified=False)
    first = dict(common, expectedRevision=0, revision=1,
                 text='听到提示后才记录；间隔未确定，不能据此认定具体时间。',
                 reason='第一次核对：保留时间歧义，未听取实际录音。',
                 utc='2026-01-01T00:00:01Z')
    second = dict(common, expectedRevision=1, revision=2,
                  text='独立合成参考说明：提示后约三秒记录；原音定位仍未知。',
                  reason='仅依据 SYN-REF-1 手造参考修订文字；不是听取或事实核验。',
                  utc='2026-01-01T00:00:02Z')
    rows = [dict(case_id=case, run_id=run, revision=n, doc=d)
            for n, d in enumerate([initial, first, second])]
    return {
        'scope': 'handmade-saved-row-shape-not-persisted-not-uploadable',
        'scenario': '短录音脚本（未录制）：提示后记录。没有船名、人员、地点或真实事件。',
        'independentReference': {'id': 'SYN-REF-1',
                                'text': '自造计时卡：提示到记录约三秒；不提供原音片段起止。',
                                'synthetic': True},
        'rows': rows,
        'evidenceItem': dict(caseId=case, evidenceId=evidence, currentSha256=source_hash),
        'request': dict(media='audio', case_id=case, run_id=run, revision=1,
                        evidence_id=evidence, evidence_role='audio'),
        'notExecuted': [
            {'scenario': 'unauthorized-context', 'expected': '不得读出或导出引用内容；由真实授权交集验收，纯比较器不授权'},
            {'scenario': 'missing-evidence', 'expected': '无法建立精确引用；不回退 latest，不伪造来源'}
        ]
    }


if __name__ == '__main__':
    print(json.dumps(fixture(), ensure_ascii=False, indent=2))
