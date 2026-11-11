# 仓库规则（给 Codex / 实现与验收代理）

详细背景、目录、测试命令、包状态和未关闭缺陷见 **[HANDOFF.md](HANDOFF.md)**。进度与流程以 **[ROADMAP.md](ROADMAP.md)** 为准。接口以 **[contracts/](contracts/)**（`CONTRACTS.md`、`openapi.yaml`、`schemas/`）为唯一真相源。缺陷与裁定在 `DEFECTS/<包>.md`，未入合同的提案在 `REQUESTS.md`。

## 必须遵守

- 服务只监听 `127.0.0.1`，不要改成 `0.0.0.0` 或公网地址。
- 不要打印、不要提交、不要外发任何密钥或 `.env`。发现密钥文件把它加入 `.gitignore` 并报告路径与类别，不写值。
- 不要 git push，除非仓库主人在本次任务里明确要求并授权。
- 不要修改 `/workspace/yuehai-*`（若本地还有这些目录）。
- 纯 C# 核心：C# 9、netstandard2.1，不得引用 `UnityEngine`。改接口先写 `REQUESTS.md`，不要擅自改已验收合同，除非有裁定。
- Lily/Mary 演示数据是虚构，必须标注。`reports/` 里上传的公开事故报告可以使用真实数据，须标明来源和【直接】/【推算】/【估计】。YANGZE 22 的 caseId 用 `CJK-2024-1230-YangZe22-VegaDream`。

## 工作包流程

1. 实现 + 自测通过。
2. 在 `ROADMAP.md` 追加「待测」行，附冻结哈希（文件清单 + sha256）。冻结期内不改这些文件。
3. 独立验收：`tests_acceptance/<包>/` + `DEFECTS/<包>.md`。验收不改实现。
4. 按裁定返工再测。断言与裁定冲突时**改写断言，不得删除用例**。
5. 已验收后才能推进依赖它的下游包。改其他包的已冻结文件，须先在 `REQUESTS.md` 登记。

新 CSS 放到 `web/src/styles/<包>.css` 再引入，不要把共享 `web/src/styles.css` 列入单包冻结清单。

## 常用命令

```bash
./run_dev.sh                          # 127.0.0.1:8765 + :5173
cd service && .venv/bin/pytest        # 用 service/.venv，不要用别的 venv
cd web && npm test && npm run test:w5 && npm run test:w16 && bash tests/run-analysis-w12.sh
~/.dotnet/dotnet test <对应 csproj>   # 见 HANDOFF.md §3.2
```
