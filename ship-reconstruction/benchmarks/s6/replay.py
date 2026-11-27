"""Reproduce S3 CLI, file readback, coordinate and missing-engine checks using only synthetic data."""
import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys

import numpy as np
import trimesh

CHAT='c9883e3060c1cee7a427a814d3a7735608e6c18b'
UPSTREAM='0cfbcb74ae7749e83a02baccab4ec68d71b134a4'
def git(root, *args):
    return subprocess.check_output(['git','-C',root,*args],text=True).strip()

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save(path, value):
    path.write_text(json.dumps(value,indent=2,ensure_ascii=False,allow_nan=False)+'\n')

def check(condition, description):
    if not condition:
        raise AssertionError(description)

def cli(command, log, cwd=None):
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1')
    p=subprocess.run(command,capture_output=True,text=True,env=env,cwd=cwd)
    log.write_text(p.stdout+'\n'+p.stderr)
    return p.returncode

def distance(a,b):
    import igl
    points=np.vstack([a.vertices,a.triangles_center,a.vertices[a.edges_unique].mean(axis=1)])
    sq=igl.point_mesh_squared_distance(np.ascontiguousarray(points),np.ascontiguousarray(b.vertices),np.ascontiguousarray(b.faces,dtype=np.int64))[0]
    return float(np.sqrt(sq.max()))

def origin_controls(output,exchange,read_exchange,hydro):
    vertices=np.array([[0.,0.,0.],[6.,0.,0.],[1.,3.,0.],[2.,-.5,2.5]])
    faces=[[0,2,1],[0,1,3],[1,2,3],[2,0,3]]
    truth=trimesh.Trimesh(vertices=vertices,faces=faces,process=False)
    volume=7.5
    center=vertices.mean(axis=0)
    upper_center=vertices[3]+.5*(center-vertices[3])
    wet_center=(center-.125*upper_center)/.875
    check(abs(truth.volume-volume)<1e-12 and truth.is_volume,'independent fixture orientation')
    origins=[('zero',[0.,0.,0.]),('shifted',[7.25,-8.5,4.75]),('opposite',[-31.5,17.75,-2.]),('decimal',[-.12345,.23456,-.34567]),('float32_boundary',[2.**24,-2.**24,2.**24])]
    rows=[]
    for label,offset in origins:
        folder=output/('origin-'+label);folder.mkdir()
        shift=np.asarray(offset);world=truth.copy();world.apply_translation(shift)
        before=world.vertices.copy()
        raw=folder/'raw.glb';converted=folder/'exchange.glb'
        world.export(raw);exchange(world).export(converted)
        check(np.array_equal(before,world.vertices),'exchange must preserve input coordinates')
        for mode in ('raw_direct_read','raw_with_exchange_reader','paired_exchange_read'):
            if mode=='raw_direct_read':
                result=trimesh.load_scene(raw,process=False).to_geometry()
            else:
                result=read_exchange(raw if mode=='raw_with_exchange_reader' else converted)
            result.apply_translation(-shift)
            vertex_error=float(np.linalg.norm(result.vertices-vertices,axis=1).max())
            surf=max(distance(truth,result),distance(result,truth))
            measured=hydro(result,[1.25])[0]
            actual_center=measured['center_of_buoyancy_m']
            center_error=None if actual_center is None else float(np.linalg.norm(np.array(actual_center)-wet_center))
            mode_positive=mode!='raw_with_exchange_reader'
            suitable=vertex_error<1e-6
            if label!='float32_boundary' and mode_positive:
                check(suitable and surf<1e-6 and abs(result.volume-volume)<3e-6 and abs(measured['volume_m3']-6.5625)<3e-6 and abs(measured['waterplane_m2']-2.25)<3e-6 and center_error<1e-6, (label,mode,vertex_error))
            elif not mode_positive:
                check(not suitable,(label,mode,'wrong frame invisible'))
            else:
                check(not suitable,(label,mode,'stress control did not exercise float32 quantization'))
            rows.append(dict(origin=label,offset_m=offset,route=mode,vertex_max_error_m=vertex_error,sampled_surface_max_m=surf,full_volume_m3=float(result.volume),expected_volume_m3=volume,wet_volume_m3=measured['volume_m3'],expected_wet_m3=6.5625,waterplane_m2=measured['waterplane_m2'],expected_waterplane_m2=2.25,buoyancy_error_m=center_error,synthetic_coordinate_budget_m=1e-6,within_coordinate_budget=suitable))
        if label=='float32_boundary':
            # Store local geometry without a giant world translation in its float32 accessor.
            # Use the true known double-precision origin out of band. This is a QA control.
            nearby=world.copy();nearby.apply_translation(-shift);f=folder/'local-plus-origin.glb';exchange(nearby).export(f)
            rebuilt=read_exchange(f);rebuilt.apply_translation(shift)
            exact=float(np.linalg.norm(rebuilt.vertices-before,axis=1).max());check(exact==0,'local coordinates + explicit origin')
            rows.append(dict(origin=label,offset_m=offset,route='local_float32_plus_external_double_origin',vertex_max_error_m=exact,within_coordinate_budget=True,synthetic_coordinate_budget_m=1e-6))
    return rows

def main():
    p=argparse.ArgumentParser(description=__doc__)
    for arg in ('original','patched','upstream','no-igl','no-cgal','output'):
        p.add_argument('--'+arg,type=Path,required=True)
    a=p.parse_args();output=a.output.resolve();output.mkdir(parents=True,exist_ok=False)
    sources={k:getattr(a,k).resolve() for k in ('original','patched','upstream')}
    check(git(sources['original'],'rev-parse','HEAD')==CHAT,'original commit')
    check(git(sources['upstream'],'rev-parse','HEAD')==UPSTREAM,'S2.1 commit')
    check(git(sources['patched'],'rev-parse','HEAD^')==CHAT,'patch parent')
    for directory in sources.values():
        check(not git(directory,'status','--porcelain'),'dirty checkout')
    script=Path('ship-reconstruction/scripts')
    sys.path.insert(0,str(sources['patched']/script))
    from geometry import exchange,read_exchange,hydro,quality
    import igl
    from igl.copyleft import cgal
    check(callable(cgal.remesh_self_intersections),'positive control lacks CGAL')
    base=sources['upstream']/'ship-reconstruction/examples/s21'
    # Construct the negative drawing by changing just the original symmetry statement.
    import ezdxf
    asym=output/'different-sides.dxf';d=ezdxf.readfile(base/'A/input.dxf')
    marked=[e for e in d.modelspace().query('TEXT') if e.dxf.text.startswith('SYMMETRIC ABOUT CENTERLINE')]
    check(len(marked)==1,'unsupported synthetic fixture')
    marked[0].dxf.text='PORT AND STARBOARD SECTIONS DIFFER. DISTINCT OFFSETS REQUIRED.';d.saveas(asym)
    fixtures={name:base/name/'input.dxf' for name in 'ABC'};fixtures['asymmetric_drawing']=asym
    envs={'full':Path(sys.executable),'no-igl':a.no_igl.absolute(),'no-cgal':a.no_cgal.absolute()}
    env_info={}
    probe="""import importlib.util, json
igl=importlib.util.find_spec('igl') is not None
try:
    from igl.copyleft import cgal
    valid=callable(cgal.remesh_self_intersections)
except ImportError:
    valid=False
print(json.dumps(dict(igl=igl,cgal=valid)))"""
    for name,python in envs.items():
        env_info[name]=json.loads(subprocess.check_output([python,'-c',probe],text=True))
    check(env_info=={'full':{'igl':True,'cgal':True},'no-igl':{'igl':False,'cgal':False},'no-cgal':{'igl':True,'cgal':False}},env_info)
    rows=[];suites=[]
    expected_box=trimesh.creation.box(extents=[6.,3.,2.]);expected_box.apply_translation([3.,0.,1.])
    for flavor in ('original','patched'):
        src=sources[flavor]/'ship-reconstruction'
        for scope,pattern in [('s3','test_s3*.py'),('all','test*.py')]:
            log=output/(flavor+'-'+scope+'-unittest.log')
            rc=cli([sys.executable,'-m','unittest','discover','-s','tests','-p',pattern,'-v'],log,src)
            match=re.search(r'Ran (\d+) tests? in ([\d.]+)s',log.read_text())
            check(match is not None,(flavor,scope,'suite did not run'))
            suites.append(dict(version=flavor,suite=scope,tests=int(match[1]),seconds=float(match[2]),exit=rc))
            if scope=='s3':check(rc==0 and int(match[1])==55,(flavor,scope,rc))
        for scenario,input_file in fixtures.items():
            active_envs=envs if scenario=='A' else {'full':envs['full']}
            for env,python in active_envs.items():
                case=output/(flavor+'-'+scenario+'-'+env)
                digest=sha(input_file)
                rc=cli([python,src/'scripts/s3_run.py',sources['upstream'],input_file,case],case.with_suffix('.log'))
                report=json.loads((case/'report.json').read_bytes())
                meshfile=case/'research.glb';approved=report['engineering_approved']
                check(rc==0 and approved is False and digest==sha(input_file)==report['source_sha256'],(case.name,'handoff'))
                expected_mesh=scenario in ('A','B') and (env=='full' or flavor=='original')
                check(meshfile.is_file()==expected_mesh and (report['status']=='research_mesh')==expected_mesh,case.name)
                if report['status']=='research_mesh':
                    metrics=report['mesh_report']['quality']
                    check(metrics['closed_verified']==(env=='full'),(case.name,'quality'))
                else:metrics={}
                g=json.loads((case/'extract/geometry.json').read_bytes())
                row=dict(version=flavor,scenario=scenario,environment=env,exit=rc,input_sha256=digest,admission=g['modeling_admission']['state'],engineering_approved=approved,outcome=report['status'],reason=report.get('reason'),wrote_glb=meshfile.is_file(),closed_verified=metrics.get('closed_verified'),self_intersections=metrics.get('self_intersection_pairs'),vertex_manifold=metrics.get('vertex_manifold'),absolute_frame=report.get('mesh_report',{}).get('absolute_frame'))
                if env=='full' and expected_mesh:
                    for mode in ('raw_decoder','exchange_decoder'):
                        m=trimesh.load_scene(meshfile,process=False).to_geometry() if mode=='raw_decoder' else read_exchange(meshfile)
                        wet=hydro(m,[1.])[0];err=float(np.linalg.norm(np.array(wet['center_of_buoyancy_m'])-[3.,0.,.5]))
                        h=max(distance(expected_box,m),distance(m,expected_box))
                        correct=(flavor=='original')==(mode=='raw_decoder')
                        expected_volume=18. if correct else 30.
                        check(abs(wet['volume_m3']-expected_volume)<1e-9,(case.name,mode,wet))
                        if correct:check(h<1e-10 and abs(wet['waterplane_m2']-18.)<1e-9 and err<1e-10,case.name)
                        row[mode]=dict(volume_m3=wet['volume_m3'],waterplane_m2=wet['waterplane_m2'],center_m=wet['center_of_buoyancy_m'],center_error_m=err,sampled_surface_max_m=h,full_volume_m3=float(m.volume),bounds=m.bounds.tolist(),closed_verified=quality(m)['closed_verified'])
                rows.append(row)
    controls=origin_controls(output,exchange,read_exchange,hydro)
    save(output/'synthetic-results.json',dict(source_commits={k:git(v,'rev-parse','HEAD') for k,v in sources.items()},platform=dict(system=platform.system(),release=platform.release(),arch=platform.machine(),python=platform.python_version()),packages={k:importlib.metadata.version(k) for k in ('libigl','trimesh','numpy','scipy','ezdxf','shapely')},envs=env_info,suites=suites,cli_cases=rows,frame_cases=controls))
    with (output/'frame-comparison.csv').open('w') as f:
        w=csv.DictWriter(f,fieldnames=list(controls[0]));w.writeheader();w.writerows(controls)
    print('Suites:',suites,'; CLI:',len(rows),'; frame cases:',len(controls))
if __name__=='__main__':main()
