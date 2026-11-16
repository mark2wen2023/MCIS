from pathlib import Path
import json,time,importlib.metadata,sys,hashlib,tarfile
import argparse
parser=argparse.ArgumentParser(description='Explicit public page6 local PP-OCRv5 trial; no server mounting')
parser.add_argument('--model-root',type=Path,required=True)
parser.add_argument('--image',type=Path,required=True)
parser.add_argument('--output',type=Path,required=True)
args=parser.parse_args();root=args.model_root;image=args.image;out=args.output
out.mkdir(parents=True,exist_ok=False)
assert hashlib.sha256(image.read_bytes()).hexdigest()=='e097321c40047e305beb50f2676370f89a452ba49a11dc962ec4add9b6a70aff'
for name in ('PP-OCRv5_mobile_det_infer','PP-OCRv5_mobile_rec_infer'):
 for file in ('inference.json','inference.pdiparams','inference.yml'):
  if not (root/name/file).is_file(): raise RuntimeError('Required local model missing; no download fallback')
expected_models={'PP-OCRv5_mobile_det':'50446e5d01ac2a73d5319c89513281f6578414c888c602f9af13f93feefffc58','PP-OCRv5_mobile_rec':'566b9512b34e34a9f0db54d87b51fa5a0b9ed2cf1ab7e49728cc0b8b5a64f414'}
for name,expected_sha in expected_models.items():
 archive_path=root/(name+'.tar')
 if hashlib.sha256(archive_path.read_bytes()).hexdigest()!=expected_sha: raise RuntimeError('Local model archive differs from recorded official download')
 with tarfile.open(archive_path) as archive:
  for member in archive:
   if member.isfile() and archive.extractfile(member).read()!=(root/member.name).read_bytes(): raise RuntimeError('Model differs from cached archive')
start=time.perf_counter()
from paddleocr import PaddleOCR
import paddle
ocr=PaddleOCR(text_detection_model_name='PP-OCRv5_mobile_det',text_detection_model_dir=str(root/'PP-OCRv5_mobile_det_infer'),text_recognition_model_name='PP-OCRv5_mobile_rec',text_recognition_model_dir=str(root/'PP-OCRv5_mobile_rec_infer'),use_doc_orientation_classify=False,use_doc_unwarping=False,use_textline_orientation=False,device='cpu',cpu_threads=4,enable_mkldnn=False)
loaded=time.perf_counter()
# No Python networking/subprocess launch while supplying the public page to prediction.
def no_network(event,args):
 if event in ('socket.connect','socket.getaddrinfo','subprocess.Popen','os.system'):
  raise RuntimeError('Unexpected networking/process during local OCR; stopping')
sys.addaudithook(no_network)
results=list(ocr.predict(str(image)));finished=time.perf_counter()
assert len(results)==1
results[0].save_to_json(str(out/'raw.json'))
metadata={'versions':{p:importlib.metadata.version(p) for p in ['paddlepaddle','paddleocr','paddlex']},'device':paddle.get_device(),'cuda_compiled':paddle.is_compiled_with_cuda(),'cpu_threads':4,'mkldnn':False,'initialization_seconds':loaded-start,'inference_seconds':finished-loaded,'image_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'raw_sha256':hashlib.sha256((out/'raw.json').read_bytes()).hexdigest(),'mode':'actual-local-ocr-run','network_guard':'Python audit during predict, not OS network certification'}
(out/'run.json').write_text(json.dumps(metadata,indent=2));print(json.dumps(metadata),flush=True)
