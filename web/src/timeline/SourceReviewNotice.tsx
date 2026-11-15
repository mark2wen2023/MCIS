/** Workflow guidance only; never infers a source version or grants permission. */
export function SourceReviewNotice() {
  return <aside aria-label="来源复核说明" style={{ padding: '8px 12px' }}>
    <strong>处理记录与来源核验分开</strong>
    <p>保存处理说明或选择“已解决”等状态，不表示已核验来源版本或原件。本页未记录您阅读时的证据版本，也不会生成已读证明。</p>
    <p>无法查看来源时，可按现有权限保留处理说明，注明待核实事项，再由具备相应权限的调查员复核；不要将当前登记版本当作自己已看过的版本。</p>
  </aside>
}
