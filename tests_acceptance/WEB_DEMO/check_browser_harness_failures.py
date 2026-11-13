"""Stub-only harness cleanup checks; never real browser acceptance."""
import tempfile,pathlib,os,subprocess,json
script=pathlib.Path(__file__).resolve().parents[2]/'web/tests/web-demo-browser.mjs'
with tempfile.TemporaryDirectory() as td:
 p=pathlib.Path(td); marker=p/'events'; mod=p/'stub.cjs'; py=p/'fake-python'
 py.write_text('#!/bin/sh\nprintf "spawn\\n" >> "$MARKER"\ntrap \'printf "term\\n" >> "$MARKER"; exit 0\' TERM\nprintf "http://example.com:1234\\n"\nwhile :; do sleep 0.1; done\n');py.chmod(0o700)
 for mode in ['launch','context','origin']:
  marker.write_text('')
  mod.write_text('''const fs=require('fs');const log=x=>fs.appendFileSync(process.env.MARKER,x+'\\n');module.exports={chromium:{launch:async opts=>{if(opts.chromiumSandbox!==true)throw Error('sandbox');log('launch');if(process.env.MODE==='launch')throw Error('blocked');return {close:async()=>log('close'),newContext:async()=>{if(process.env.MODE==='context')throw Error('context');return {newPage:async()=>({})}}}}}};''')
  env={**os.environ,'MARKER':str(marker),'MODE':mode,'MCIS_PLAYWRIGHT_MODULE':str(mod),'MCIS_DEMO_PYTHON':str(py),'MCIS_PREFLIGHT_REAL_CORE':'unused','MCIS_BROWSER_ARTIFACTS':str(p/'shots')}
  r=subprocess.run(['node',str(script)],env=env,capture_output=True,text=True,timeout=8)
  events=marker.read_text().splitlines()
  assert r.returncode==1 and 'PASS:' not in r.stdout,(mode,r.stdout,r.stderr)
  if mode=='launch':assert events==['launch'] and 'BLOCKED' in r.stderr,events
  if mode=='context':assert events==['launch','close'] and 'FAIL:' in r.stderr,events
  if mode=='origin':assert events==['launch','spawn','close','term'],events
  print(mode,events,'expected non-pass exit',r.returncode)
