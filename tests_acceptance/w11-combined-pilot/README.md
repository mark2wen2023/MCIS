# W11 组合试点：同一轮门槛核对与接口断点（合成）

本目录只做只读核对与接口盘点，不改产品、不开新接口、不用假核心、不直写生产表。不是 W11 整包。

核对照的两钉：

- 真实 .NET 验收：`875ccc50b049fb24b82f6b0663f3f9476db1880e`
- 单边原文试点（含 `tests_acceptance/ECFCNEW/http_real.py`）：`41eb599f5a42eb2d0938ad4212936a0949a1cef5`（是上一钉的祖先）

本候选从 **875ccc50** 分出，因为该提交已同时包含 `w11-real-core` 与 `41eb599`/`b40a6ca` 的单边原文工装，且是已复核的真实 .NET 验收钉。不重跑那两轮已有官方验收。

若已有**同一轮**原件满足全部组合门槛，脚本只回固定证据 SHA 并退出 0。否则记录首个接口断点并退出 3，不临时开接口或改产品，不把先前两轮分开的证据说成同一轮组合通过。

```sh
timeout --signal=TERM --kill-after=10s 150s python3 tests_acceptance/w11-combined-pilot/run.py \
  --source /path/to/this-checkout \
  --dotnet /home/box/.dotnet/dotnet \
  --out /path/to/empty-out
```
