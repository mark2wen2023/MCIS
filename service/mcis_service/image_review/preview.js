/* Local PNG view only. Never executes OCR or certifies a PDF/page association. */
(function(root){
'use strict';
function pngSize(bytes, expected){
  const b = new Uint8Array(bytes);
  const signature = [137,80,78,71,13,10,26,10];
  if(b.length < 33 || signature.some((v,i)=>b[i]!==v)) throw Error('仅支持PNG页图预览；其他格式请下载核对');
  const v = new DataView(b.buffer,b.byteOffset,b.byteLength);
  if(v.getUint32(8)!==13 || String.fromCharCode(...b.slice(12,16))!=='IHDR') throw Error('PNG头无效');
  const width=v.getUint32(16),height=v.getUint32(20);
  if(!width||!height||width>8192||height>8192||width*height>25000000) throw Error('页图超过预览尺寸上限');
  if(width!==expected.width||height!==expected.height) throw Error('页图尺寸与OCR坐标声明不符，不显示定位框');
  return {width,height};
}
function rectangle(box,size){
  if(!Array.isArray(box)||box.length!==4||box.some(n=>typeof n!=='number'||!Number.isFinite(n))) throw Error('行坐标无效');
  const [x,y,right,bottom]=box;
  if(x<0||y<0||right<x||bottom<y||right>size.width||bottom>size.height) throw Error('行坐标超出页图');
  return {x,y,width:right-x,height:bottom-y};
}
function create({page,crop,message,decode,controls}){
  let generation=0,bitmap=null,size=null,selection=null,kind='registered-original',source=null,locked=[];
  function restoreControls(){for(const [button,disabled] of locked)button.disabled=disabled;locked=[];}
  function lockControls(){
    if(typeof controls!=='function')throw Error('派生页需要明确提供原件与OCR操作控件');
    const c=controls();
    if(!c||!Array.isArray(c.originalRead)||!Array.isArray(c.ocrReview)||[...c.originalRead,...c.ocrReview].some(b=>!b||typeof b.disabled!=='boolean'))throw Error('派生页操作控件无效');
    locked=[...new Set([...c.originalRead,...c.ocrReview])].map(b=>[b,b.disabled]);
    for(const [button] of locked)button.disabled=true;
  }
  function assertOriginalAction(){if(kind==='pdf-derived-page')throw Error('PDF派生页不提供原件下载或OCR修订');}
  function derivedLabel(){return 'PDF派生页 · 物理页 '+source.physicalPage+' · 原PDF SHA256 '+source.sourceSha256+' · 派生PNG SHA256 '+source.pageSha256+'；不是登记原图、OCR结果或事实核验。';}
  function erase(){page.width=1;page.height=1;crop.width=1;crop.height=1;}
  function clear(){generation++;restoreControls();kind='registered-original';source=null;if(bitmap)bitmap.close();bitmap=null;size=null;selection=null;erase();message.textContent='页图未显示。点击授权载入；此操作记录一次访问。';}
  function draw(){
    const c=page.getContext('2d');c.clearRect(0,0,size.width,size.height);c.drawImage(bitmap,0,0);
    if(selection){
      const r=rectangle(selection.box,size);c.strokeStyle='#d02600';c.lineWidth=Math.max(2,size.width/500);c.strokeRect(r.x,r.y,r.width,r.height);
      const x=Math.max(0,Math.floor(r.x)-12),y=Math.max(0,Math.floor(r.y)-12);
      const w=Math.min(size.width-x,Math.ceil(r.width)+24),h=Math.min(size.height-y,Math.ceil(r.height)+24);
      crop.width=w;crop.height=h;crop.getContext('2d').drawImage(bitmap,x,y,w,h,0,0,w,h);
      message.textContent=kind==='pdf-derived-page'?derivedLabel()+' 显示声明区域 '+selection.index+' 及邻近派生像素；不核验文字。':'显示OCR行 '+selection.index+' 的声明框及邻近原图。框与文字未自动核验；不是PDF跳页。';
    }
  }
  async function load(read,expected){
    clear();const token=generation;message.textContent='授权载入页图中…';
    let decoded=null;
    try{
      const bytes=await read();if(token!==generation)return false;
      const dimensions=pngSize(bytes,expected);
      decoded=await decode(new Blob([bytes],{type:'image/png'}));
      if(token!==generation){decoded.close();return false;}
      if(decoded.width!==dimensions.width||decoded.height!==dimensions.height) throw Error('解码尺寸不一致');
      bitmap=decoded;decoded=null;size=dimensions;page.width=size.width;page.height=size.height;draw();
      message.textContent='页图已载入，字节摘要与登记匹配。选择OCR行高亮；PDF页码关系仍为人工声明。';return true;
    }catch(e){if(decoded)decoded.close();if(token===generation){clear();message.textContent=e.message+'；未显示页图，不自动重试。';}throw e;}
  }
  async function loadDerived(bytes,description){
    clear();const token=generation;let decoded=null;
    try{
      kind='pdf-derived-page';lockControls();message.textContent='PDF派生页校验中；原件下载和OCR修订不可用。';
      if(!(bytes instanceof ArrayBuffer)&&!ArrayBuffer.isView(bytes))throw Error('派生PNG字节无效');
      const length=bytes.byteLength;if(length<33||length>1024*1024)throw Error('派生PNG大小无效');
      const copy=new Uint8Array(bytes instanceof ArrayBuffer?bytes:bytes.buffer,bytes instanceof ArrayBuffer?0:bytes.byteOffset,length).slice();
      const d=description;
      if(!d||Object.keys(d).sort().join(',')!=='height,pageSha256,physicalPage,renderSpec,sourceSha256,width'||
         typeof d.sourceSha256!=='string'||typeof d.pageSha256!=='string'||!/^[0-9a-f]{64}$/.test(d.sourceSha256)||!/^[0-9a-f]{64}$/.test(d.pageSha256)||
         !Number.isInteger(d.physicalPage)||d.physicalPage<1||d.physicalPage>8||
         !Number.isInteger(d.width)||!Number.isInteger(d.height)||d.width<1||d.height<1||d.width>256||d.height>256||
         !d.renderSpec||Object.keys(d.renderSpec).sort().join(',')!=='dpi,format,pageBox,scaleTo'||
         d.renderSpec.format!=='PNG'||d.renderSpec.dpi!==72||d.renderSpec.scaleTo!==256||d.renderSpec.pageBox!=='MediaBox')throw Error('派生页来源描述无效');
      source={sourceSha256:d.sourceSha256,pageSha256:d.pageSha256,physicalPage:d.physicalPage,width:d.width,height:d.height,renderSpec:{...d.renderSpec}};
      const dimensions=pngSize(copy,source);
      const hash=Array.from(new Uint8Array(await root.crypto.subtle.digest('SHA-256',copy)),n=>n.toString(16).padStart(2,'0')).join('');
      if(token!==generation)return false;
      if(hash!==source.pageSha256)throw Error('派生PNG摘要不符');
      decoded=await decode(new Blob([copy],{type:'image/png'}));
      if(token!==generation){decoded.close();return false;}
      if(decoded.width!==dimensions.width||decoded.height!==dimensions.height)throw Error('解码尺寸不一致');
      bitmap=decoded;decoded=null;size=dimensions;page.width=size.width;page.height=size.height;draw();
      message.textContent=derivedLabel();return true;
    }catch(e){if(decoded)decoded.close();if(token===generation){
      // Failure remains a derived context: do not re-enable original/write actions.
      if(bitmap)bitmap.close();bitmap=null;size=null;selection=null;erase();
      message.textContent='派生页未显示，不自动回退原图；'+e.message;
    }throw e;}
  }
  function select(index,box){if(!bitmap)throw Error('请先授权载入页图');rectangle(box,size);selection={index,box:box.slice()};draw();}
  clear();return {load,loadDerived,select,clear,assertOriginalAction,get inputKind(){return kind;}};
}
const api={pngSize,rectangle,create};
if(typeof module!=='undefined'&&module.exports)module.exports=api;else root.OcrPagePreview=api;
})(typeof globalThis!=='undefined'?globalThis:this);
