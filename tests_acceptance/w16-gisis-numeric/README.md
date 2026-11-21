# W16 GISIS 数值校验窄回归

固定主线 94d5e38c926fda232bb987b60fa9145e4bcf01a7（本轮远端核对一致）。只修改 gisis._valid_type 的 number 分支，整数不先转浮点。没有修改模板/规则/来源/权限/生成器/导出。

## 本轮源码核对，不冒充本轮运行验收

- reports/templates.py：IMO、MAIB、中国海事三种项目结构及中英文标题已存在；普通 cn-msa 仍有 `pendingRuling=章节标题待裁定落实`。没有读取其链接指向的真实报告。
- test_reports_w16.py 的 test_templates_languages_draft_contract 已有三模板×zh/en/bilingual 测试；test_reports_w16_export.py 已有PDF/DOCX语言、状态、免责声明、字体/文本等检查。本轮不运行这些生成/HTTP/导出用例，不重新造断言，不据源码声称排版或流程已通过。
- contracts/gisis-mapping.md、GISIS_FIELDS 和 test_reports_w161_gisis.py 已覆盖20字段、必填/可选、对应程度、严重程度缺值及模板待核标记。待核包括国家名录、二级事件类型、船型映射、Serious/LessSerious、当地时区来源、重伤含义及每船严重程度；全部保留，不自行裁定。
- GISIS 本地准备不是IMO提交。现有代码中有布局/导出路径，但本轮没有实测布局、平台工作流或专业规则有效性；不能把标题和字段存在当作验收通过。

## 首个新增实证缺口

实际 validate_gisis 对数值字段使用 math.isfinite(int)。手造400位整数会抛 OverflowError，未到已有经纬度上下界。旧回归检查类型/范围/零值等，但没有超大整数边界。

新实现让整数直接进入原有范围规则，经纬度返回 field_range。没有给无 maximum 的总吨字段编造专业上限；这只是本地类型规则，不是对该值事实合理性的认定。bool仍不作数值，NaN/Infinity仍拒绝，0及上下界仍有效，缺值仍缺值。

```bash
python -I tests_acceptance/w16-gisis-numeric/check.py --old
python -I tests_acceptance/w16-gisis-numeric/check.py
```

实跑旧固定头：退出1，4项中出现5个 OverflowError（含子用例）；新源码4项通过、退出0。不是累计9项。仅标准库AST提取实际 _valid_type/_invalid/validate_gisis，并从真实 GISIS_FIELDS AST取三项现有字面规则；不执行模板模块、build_gisis、service或serializer，不创建文件导出/业务报告/数据库。输入仅手造数字、空值与字段。

冻结 logs/w16-gisis-numeric-impl-hashes-frozen.txt；旧冻结不变。本轮未运行浏览器、服务、容器、媒体/模型、安装或访问真实资料；不扩大报告试点授权。
