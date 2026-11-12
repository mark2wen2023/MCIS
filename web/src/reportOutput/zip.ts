export const MAX_ZIP=19*1024*1024
export const memberNames=(format:'pdf'|'docx')=>['report.'+format,'report.json','audit.json','manifest.json']
export async function sha256(bytes:Uint8Array){return [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes as BufferSource))].map(x=>x.toString(16).padStart(2,'0')).join('')}
const crcTable=Array.from({length:256},(_,n)=>{for(let k=0;k<8;k++)n=n&1?0xedb88320^(n>>>1):n>>>1;return n>>>0})
export function crc32(bytes:Uint8Array){let c=0xffffffff;for(const b of bytes)c=crcTable[(c^b)&255]!^(c>>>8);return (c^0xffffffff)>>>0}
/** Exact four-member protocol, never a generic ZIP extractor. DOCX remains opaque. */
export function unzipStored(bytes:Uint8Array,format:'pdf'|'docx'):Map<string,Uint8Array>{
 if(bytes.length>MAX_ZIP||bytes.length<22)throw Error('ZIP预算不符');const view=new DataView(bytes.buffer,bytes.byteOffset,bytes.byteLength),names=memberNames(format),caps=[16*1024*1024,2*1024*1024,256*1024,16*1024],records:{offset:number;size:number;crc:number;name:string}[]=[],out=new Map<string,Uint8Array>();let pos=0
 function need(n:number){if(!Number.isSafeInteger(n)||n<0||pos+n>bytes.length)throw Error('ZIP越界')}
 function eq(a:number,b:number){if(a!==b)throw Error('ZIP固定结构不符')}
 function nameAt(offset:number,length:number,name:string){eq(length,name.length);for(let j=0;j<length;j++)eq(bytes[offset+j]!,name.charCodeAt(j))}
 for(let i=0;i<4;i++){need(30);const start=pos;eq(view.getUint32(pos,true),0x04034b50);eq(view.getUint16(pos+4,true),20);eq(view.getUint16(pos+6,true),0);eq(view.getUint16(pos+8,true),0);eq(view.getUint16(pos+10,true),0);eq(view.getUint16(pos+12,true),33);const crc=view.getUint32(pos+14,true),size=view.getUint32(pos+18,true);eq(size,view.getUint32(pos+22,true));if(size<1||size>caps[i]!)throw Error('ZIP成员预算不符');const n=view.getUint16(pos+26,true);eq(view.getUint16(pos+28,true),0);need(30+n+size);nameAt(pos+30,n,names[i]!);pos+=30+n;const body=bytes.subarray(pos,pos+size);eq(crc32(body),crc);out.set(names[i]!,body);records.push({offset:start,size,crc,name:names[i]!});pos+=size}
 const central=pos
 for(const r of records){need(46);eq(view.getUint32(pos,true),0x02014b50);eq(view.getUint16(pos+4,true),20);eq(view.getUint16(pos+6,true),20);eq(view.getUint16(pos+8,true),0);eq(view.getUint16(pos+10,true),0);eq(view.getUint16(pos+12,true),0);eq(view.getUint16(pos+14,true),33);eq(view.getUint32(pos+16,true),r.crc);eq(view.getUint32(pos+20,true),r.size);eq(view.getUint32(pos+24,true),r.size);const n=view.getUint16(pos+28,true);eq(view.getUint16(pos+30,true),0);eq(view.getUint16(pos+32,true),0);eq(view.getUint16(pos+34,true),0);eq(view.getUint16(pos+36,true),0);eq(view.getUint32(pos+38,true),0x20);eq(view.getUint32(pos+42,true),r.offset);need(46+n);nameAt(pos+46,n,r.name);pos+=46+n}
 const length=pos-central;need(22);eq(view.getUint32(pos,true),0x06054b50);eq(view.getUint16(pos+4,true),0);eq(view.getUint16(pos+6,true),0);eq(view.getUint16(pos+8,true),4);eq(view.getUint16(pos+10,true),4);eq(view.getUint32(pos+12,true),length);eq(view.getUint32(pos+16,true),central);eq(view.getUint16(pos+20,true),0);eq(pos+22,bytes.length);return out
}
