"""Offline, static research review sheet. No network, model or durable review state."""
import argparse
import html
import json
import os
import sys
from evaluate import load, evaluate

MAX_OUTPUT_BYTES = 8 * 1024 * 1024
CSP = "default-src 'none'; style-src 'unsafe-inline'; connect-src 'none'; form-action 'none'; base-uri 'none'; frame-src 'none'"

def esc(value):
    return html.escape(str(value), quote=True)

def render(corpus, corpus_sha, predictions):
    # Never accept a caller's pre-computed comparison as authoritative.
    result = evaluate(corpus, corpus_sha, predictions)
    original = {x['id']: x for x in corpus['items']}
    parts = ['<!doctype html><html lang="zh-CN"><head><meta charset="utf-8">',
             '<meta name="viewport" content="width=device-width,initial-scale=1">',
             '<meta http-equiv="Content-Security-Policy" content="'+esc(CSP)+'">',
             '<title>语义解释研究复核页</title><style>body{font:16px/1.6 system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem;color:#18212b}article{border:1px solid #aab5c0;padding:1.2rem;margin:1.5rem 0;break-inside:avoid}pre,blockquote{white-space:pre-wrap;overflow-wrap:anywhere;background:#f4f6f8;padding:1rem}textarea{display:block;width:95%;min-height:6rem}label{display:block;margin:.5rem 0}.notice{border-left:4px solid #995b00;padding:.8rem;background:#fff7e5}.source{overflow-wrap:anywhere}@media print{body{max-width:none;margin:0}textarea{min-height:5rem}details{display:block}}</style></head><body>',
             '<h1>语义解释研究复核页</h1>',
             '<p class="notice">仅本页临时勾选和备注，未保存；刷新可能丢失，也可能被浏览器恢复，均不构成持久审核记录。页面可被编辑，无真人身份认证、无自动检测、不改事实。此页生成过程不调用模型。打印件也不是经认证的审核记录。</p>',
             '<p>标签一致不等于解释有依据；引用定位不等于语义支持。下列标签与解释均为未审核提议，不是裁定。请分别核对时间关联、来源关联及其他解释问题。</p>',
             '<p>语料：'+esc(result['corpusId'])+'；冻结摘要：'+esc(corpus_sha)+'</p>']
    for index, item in enumerate(result['items'], 1):
        prediction = item['prediction']; source = item['sourceLocator']; quote = item['citation']
        origin = '模拟脚本预测，非真实模型' if prediction['origin']=='scripted_fixture' else '外部模型输出声明，身份与来源未认证'
        parts += ['<article><h2>第 '+str(index)+' 项 · '+esc(item['itemId'])+'</h2>',
                  '<p>'+origin+'</p><h3>模型标签（未审核）</h3><pre>'+esc(prediction['label'])+'</pre>',
                  '<h3>模型完整解释（未审核）</h3><pre>'+esc(prediction['rationale'])+'</pre>',
                  '<h3>待检主张</h3><pre>'+esc(item['claim'])+'</pre>',
                  '<h3>原引用（提供的文本，不还原 PDF 版面）</h3><blockquote>'+esc(quote['quote'])+'</blockquote>',
                  '<p>引用定位检查：'+esc(quote['status'])+'；坐标为 Unicode 码点，起点 '+str(quote['start'])+'，长度 '+str(quote['length'])+'。此检查不是语义支持或事实核定。</p>',
                  '<div class="source"><h3>来源声明（未经本页核验）</h3><p>URL（纯文本）：'+esc(source['url'])+'</p><p>PDF 摘要：'+esc(source['pdfSha256'])+'；PDF 页 '+str(source['pdfPage'])+'；印刷页 '+str(source['printedPage'])+'</p><p>来源说明：'+esc(source['section'])+'</p></div>',
                  '<details><summary>展开本项提供的源文本（非原版面）</summary><pre>'+esc(original[item['itemId']]['sourceText'])+'</pre></details>',
                  '<p>“约 / 大约 / 至少 / 不明”等限定不得默默丢失；空白或未记录不证明有，也不证明无，应核原页及其他证据。</p>',
                  '<fieldset><legend>本页临时人工核对，未保存、非身份认证</legend>',
                  '<label><input type="checkbox" autocomplete="off"> 时间关联需核实</label>',
                  '<label><input type="checkbox" autocomplete="off"> 来源关联需核实</label>',
                  '<label><input type="checkbox" autocomplete="off"> 其他解释问题</label>',
                  '<label>临时备注<textarea autocomplete="off" spellcheck="false"></textarea></label></fieldset>',
                  '<p class="notice">本项勾选与备注仅本页临时状态，未保存，刷新可能丢失；不是自动检测或持久审核，不激活事实。</p></article>']
    parts.append('</body></html>')
    output=''.join(parts).encode('utf-8')
    if len(output)>MAX_OUTPUT_BYTES: raise ValueError('output budget')
    return output

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--corpus',required=True);parser.add_argument('--predictions',required=True);parser.add_argument('--output',required=True);args=parser.parse_args()
    corpus,sha=load(args.corpus);predictions,_=load(args.predictions)
    output=render(corpus,sha,predictions)
    fd=os.open(args.output,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'wb') as target: target.write(output);target.flush();os.fsync(target.fileno())
    print(json.dumps({'ok':True,'items':len(corpus['items']),'persistentReview':False,'modelCalled':False,'factActivated':False}))

if __name__=='__main__':
    try:main()
    except Exception:
        print('{"ok":false,"errorCode":"RESEARCH_REVIEW_REJECTED"}',file=sys.stderr);sys.exit(2)
