"""Narrow source-copy regression; not browser rendering or backend acceptance."""
from pathlib import Path
root=Path(__file__).resolve().parents[1]/'src'
text='无W10时1.2.0工作记录扩展；含W10时须1.3.0'
for path,count,limits in [
 ('pages/ReportPage.tsx',1,['完整性校验不等于可恢复','原始资料须独立保管','报告PDF/DOCX原导出文件']),
 ('pages/InterviewPage.tsx',1,['未知内容整包拒绝','原始资料须独立保管','过往签署与确认不代表本次认证']),
 ('packages/PackagePanel.tsx',2,['不是完整案件备份','默认策略','历史回执不可重放','超限整体拒绝，不截断历史'])]:
 source=(root/path).read_text()
 assert source.count(text)==count,path
 assert '1.2.0及以上' not in source and '1.3.0及以上' not in source,path
 for limit in limits:assert limit in source,(path,limit)
print('Archive version copy: 16 source assertions passed (not render assertions)')
