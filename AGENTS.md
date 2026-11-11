# 仓库规则（给 Codex / 实现与验收代理）

**第一件事：先读 [docs/HANDOFF-STAGE1.md](docs/HANDOFF-STAGE1.md)**（阶段性交接：目标、架构、环境与测试命令、交接基线、全部包状态、接手顺序）。旧的 `HANDOFF.md` 只作历史。

进度与流程以 [ROADMAP.md](ROADMAP.md) 文末状态表为准（同一包以最后一行为准）。接口以 [contracts/](contracts/)（`CONTRACTS.md`、`openapi.yaml`、`schemas/`）为唯一真相源。缺陷与裁定在 `DEFECTS/<包>.md` 文末；合同外提案和跨包改动登记在 `REQUESTS.md`。

## 必须遵守

- 服务和前端只监听 `127.0.0.1`。
- 不打印、不提交、不外发任何密钥或 `.env`。
- 不 git push，除非仓库主人 Mark 在本次任务里明确要求。
- 不碰 `/workspace/yuehai-*`。
- 纯 C# 核心：C# 9、netstandard2.1，不得引用 `UnityEngine`。
- 合同先行：改接口先改 `contracts/` 或在 `REQUESTS.md` 提案。
- 阈值用 double，容差 `1e-6`；边界测试用 ±1e-7，明显超出用 ≥1e-5。CLI 领域错误退出码 4。
- 数据口径：`reports/` 里的公开事故报告可直接使用，每个值标来源和【直接】/【推算】/【估计】。Lily/Mary 是虚构，必须标「虚构」。YANGZE 22 的 caseId 是 `CJK-2024-1230-YangZe22-VegaDream`。

## 工作包流程

1. 实现 + 自测通过。
2. 在 `ROADMAP.md` 追加「待测」行，附冻结哈希（`logs/<包>-impl-hashes-frozen.txt`）。冻结后不改这些文件。
3. 在独立会话里验收：`tests_acceptance/<包>/` + `DEFECTS/<包>.md`。验收不改实现；还没修的用 KnownDefect 标注。
4. 按裁定返工再测。断言与裁定冲突时**改写断言，不删用例**。
5. 已验收后才推进下游。改别的包已冻结的文件，先在 `REQUESTS.md` 登记。
6. 共享入口 `web/src/main.tsx`、`routes.ts`、`styles.css` 不进单包冻结清单；新样式写 `web/src/styles/<包>.css`。

## 常用命令（详见 docs/HANDOFF-STAGE1.md §3）

```bash
./run_dev.sh                                   # 127.0.0.1:8765 + :5173
cd service && .venv/bin/pytest -q              # 只用 service/.venv
cd web && npx tsc -b --force && npm test && npm run test:w5 && npm run test:w16 && bash tests/run-analysis-w12.sh
~/.dotnet/dotnet test <对应 csproj>
```
