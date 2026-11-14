import React from 'react';
/** Display-only: never normalize the supplied quote or infer source-page layout. */
export function SourceQuoteReview({quote,historical=false}:{quote:string,historical?:boolean}){
 return <section aria-label={historical?'历史原文引用核对':'原文引用核对'}>
  <h5>{historical?'原文引用（历史包声明，未经认证）':'原文引用（与上方 AI 摘要、结构化主张分开核对）'}</h5>
  <blockquote style={{whiteSpace:'pre-wrap',overflowWrap:'anywhere'}}>{quote}</blockquote>
  <p>人工核对：“约 / 大约 / 至少 / 不明”等限定词不得默默丢失。空白或未记录不证明有，也不证明无，请核原页及其他证据。引用定位通过不等于语义支持。</p>
  <p>此处仅保留已提供引用文本的空白，不还原原 PDF 表格或版面。</p>
 </section>;
}
