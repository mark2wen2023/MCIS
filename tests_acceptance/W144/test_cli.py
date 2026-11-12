"""Independent mathematical verification of the enabled hypothetical model only."""
import json,math,subprocess
from pathlib import Path
import pytest
ROOT=Path(__file__).resolve().parents[2]
CLI=ROOT/'tools/mcis-nomoto/mcis-nomoto.sh'
def parameters(**changes):
    p={'headingDeg':'0','speedKn':'10','k':'0.1','tSeconds':'20','referenceSpeedKn':'10','maxRudderDeg':'35','rudderRateDegPerSec':'2','commandRudderDeg':'10','durationSeconds':'60','provenanceNote':'合成输入，不代表实船','uncertaintyNote':'参数未校准 🛳'}
    p.update(changes);return p

def run(p):
    out=subprocess.run([str(CLI)],input=json.dumps(p,ensure_ascii=False).encode(),capture_output=True,timeout=60)
    assert out.returncode==0,out.stderr.decode()
    data=json.loads(out.stdout);assert data['ok'] is True
    return data['result']

@pytest.mark.parametrize('heading',['0','90','270'])
def test_zero_command_straight_line(heading):
    d=run(parameters(headingDeg=heading,commandRudderDeg='0'))
    assert d['response']==d['baseline']
    for i,p in enumerate(d['response']):
        distance=10*1852/3600*i;angle=math.radians(float(heading))
        assert p['timeSeconds']==i and p['speedKn']==10
        assert abs(p['eastM']-distance*math.sin(angle))<1e-6
        assert abs(p['northM']-distance*math.cos(angle))<1e-6
        assert p['headingDeg']==float(heading) and p['rotDegPerSec']==p['rudderDeg']==0


def test_signed_turns_mirror():
    a=run(parameters());b=run(parameters(commandRudderDeg='-10'))
    for x,y in zip(a['response'],b['response']):
        assert abs(x['eastM']+y['eastM'])<1e-6 and abs(x['northM']-y['northM'])<1e-6
        assert abs(x['rotDegPerSec']+y['rotDegPerSec'])<1e-6 and x['rudderDeg']==-y['rudderDeg']
        assert abs((x['headingDeg']+y['headingDeg']+180)%360-180)<1e-6


def test_piecewise_constant_rudder_analytic_rot_heading():
    d=run(parameters());h=0.1;T=20.;K=0.1;rot=0.;heading=0.
    expected={0:(0.,0.)}
    for step in range(1,601):
        rudder=min(step*h*2,10);target=K*rudder;decay=math.exp(-h/T)
        heading+=target*h+(rot-target)*T*(1-decay)
        rot=target+(rot-target)*decay
        if step%10==0:expected[step//10]=(rot,heading%360)
    for p in d['response']:
        r,psi=expected[p['timeSeconds']]
        assert abs(p['rotDegPerSec']-r)<1e-6
        assert abs((p['headingDeg']-psi+180)%360-180)<1e-6
    diff=d['numericalDifference']
    assert d['stepSeconds']==0.1 and d['comparisonStepSeconds']==0.05
    assert all(math.isfinite(v) and v>=0 for v in diff.values())
    assert diff['endpointDistanceM']>0

@pytest.mark.parametrize('key,value',[('k',0.1),('k','1e-1'),('headingDeg','-0'),('speedKn','01'),('commandRudderDeg','36'),('durationSeconds','1.0'),('provenanceNote','')])
def test_invalid_input_not_silent_default(key,value):
    out=subprocess.run([str(CLI)],input=json.dumps(parameters(**{key:value})).encode(),capture_output=True,timeout=60)
    assert out.returncode==4 and json.loads(out.stdout)['ok'] is False


def test_inactive_constructor_fields_do_not_change_enabled_response(tmp_path):
    import hashlib,os,shutil
    manifest=json.loads((ROOT/'tools/mcis-nomoto/out/build-manifest.json').read_text())
    original={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in manifest['inputs']}
    for name in manifest['inputs']:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    program=tmp_path/'tools/mcis-nomoto/src/Program.cs';src=program.read_text()
    assert src.count('double inactive=1')==1
    program.write_text(src.replace('double inactive=1','double inactive=19'))
    sdk=os.environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet'))
    out=tmp_path/'out'
    built=subprocess.run([sdk,'build',str(tmp_path/'tools/mcis-nomoto/McisNomoto.csproj'),'-o',str(out),'-v','q'],capture_output=True,timeout=60)
    assert built.returncode==0,built.stderr.decode()
    for changes in [{},{'speedKn':'0'},{'commandRudderDeg':'-35','durationSeconds':'120'}]:
        p=parameters(**changes)
        probe=subprocess.run([sdk,str(out/'mcis-nomoto.dll')],input=json.dumps(p,ensure_ascii=False).encode(),capture_output=True,timeout=30)
        assert probe.returncode==0
        assert json.loads(probe.stdout)['result']==run(p)
    assert original=={name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in manifest['inputs']}


def test_reported_step_differences_match_isolated_fine_core(tmp_path):
    import os,shutil
    manifest=json.loads((ROOT/'tools/mcis-nomoto/out/build-manifest.json').read_text())
    for name in manifest['inputs']:
        target=tmp_path/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    program=tmp_path/'tools/mcis-nomoto/src/Program.cs';src=program.read_text()
    assert src.count('duration,.1)')==2 and src.count('states[i*10]')==1
    program.write_text(src.replace('duration,.1)','duration,.05)').replace('states[i*10]','states[i*20]'))
    sdk=__import__('os').environ.get('MCIS_DOTNET',str(Path.home()/'.dotnet/dotnet'));out=tmp_path/'out'
    built=subprocess.run([sdk,'build',str(tmp_path/'tools/mcis-nomoto/McisNomoto.csproj'),'-o',str(out),'-v','q'],capture_output=True,timeout=60)
    assert built.returncode==0,built.stderr.decode()
    p=parameters();coarse=run(p)
    probe=subprocess.run([sdk,str(out/'mcis-nomoto.dll')],input=json.dumps(p,ensure_ascii=False).encode(),capture_output=True,timeout=30)
    assert probe.returncode==0;fine=json.loads(probe.stdout)['result']
    a,z=coarse['response'][-1],fine['response'][-1]
    expected={'endpointDistanceM':math.hypot(a['eastM']-z['eastM'],a['northM']-z['northM']),
              'endpointHeadingDifferenceDeg':abs((a['headingDeg']-z['headingDeg']+180)%360-180),
              'endpointRotDifferenceDegPerSec':abs(a['rotDegPerSec']-z['rotDegPerSec'])}
    for k,v in expected.items():assert abs(coarse['numericalDifference'][k]-v)<1e-6
