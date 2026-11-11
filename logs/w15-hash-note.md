# W15 验收哈希记录（2026-11-11，UTC+8）
- 前：logs/w15-impl-hashes-before.txt（约 19:35 记录，30 个 .cs：Systemic + 依赖的 Core/Common/Models/Evidence/HumanFactors/Recommendations + Tests_W15_Sys）
- 后：logs/w15-impl-hashes-after.txt（19:43）
- Systemic/** 与 Tests_W15_Sys/** 前后完全一致。
- 差异 2 个依赖文件：Evidence/EvidenceItem.cs（mtime 19:38:11）、Recommendations/SafetyRecommendation.cs（mtime 19:39:03）。
  验收方未写入 unity/ 任何文件；这是验收期间其他 bot 并行修改（推测是 W3 缺陷修复）。改动后复跑：开发自测 60/60（logs/w15-dev-selftest-rerun2.txt），验收结果以 19:43 那次运行为准。
- 只读参考：reports/haili5/case.json sha256 130926c4…fe3a；ecfc.json sha256 90d33d58…8989。
