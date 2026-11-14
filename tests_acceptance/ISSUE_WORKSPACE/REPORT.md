# 问题研判工作区 UI：独立验收

## 结论

最终产品版本独立29项检查通过，测试脚本退出0。未发现本切片剩余阻断项。产品未由独立审查者修改，未推送/部署/合并。

测试：web/tests/issue-workspace-independent.tsx；esbuild platform=node、format=esm、jsx=automatic打包，使用现有HappyDOM执行React交互。MCIS_HAPPY_DOM_PATH指定现有happy-dom/lib/index.js。最终测试在全部assert通过、React unmount和HappyDOM abort/close后显式process.exit(0)；首轮已输出通过但存在Node残留句柄，不能把首轮称自然退出成功。最终重跑退出0。

## 检查范围

默认断连、外部port无contextKey禁用；错误保存内容不显示/不误报已保存；读响应倒退隐藏历史、禁止新建；读失败后再读仍保持旧基线，不能接纳相同倒退；同版本改写拒绝；错误详情隐藏；保存结果未知冻结表单并同operationId/同payload重试；只有一个历史事件；切换context后旧响应忽略且旧表单清除；内存演练限固定虚构案件；无local/sessionStorage写入。内存port验证相同操作幂等、改变payload/旧revision冲突、返回副本不改原历史、跨案读封套拒绝。

已有卡入口新增后复跑29项全部通过：已有issueId初始隐藏且禁追加，读取成功恢复历史与追加；切到不存在的issueId读取失败仍禁用，不误建新卡。

## 审查发现与修正

静态审查指出保存回包需逐项核对提交entry，refresh应拒revision倒退及旧prefix改写，读失败隐藏历史时仍需保留一致性基线；卸载应使异步epoch失效。实现者随后完成这些修正。独立测试在产品修正后执行通过，不声称运行了旧代码失败复现。

已静态核对当前effect cleanup会递增epoch并清除pending，context变化清理display与基线。实际DOM覆盖context切换迟到响应；没有单独证明卸载后React内部setState不可达或浏览器网络取消。

## 诚实边界

这是HappyDOM和内存模拟port，不是浏览器视觉/E2E、真实服务保存、会话认证、CI或LLM。外部port仅为业务接口契约，不证明提供者已认证；无URL、token、旧身份桥接。人工输入的核实/讨论仍是未审核意见，不是事实、责任认定或专家共识。来源ID仅历史引用，不证明当前原件有效。无附件录入、后端持久化或真实登录完成声明。

## 冻结 SHA-256

- IssueWorkspace.tsx: 96a4463d4f25d6b5e5df42d57ffe6706fe6368c53514bfe32b78b1367e23c121
- model.ts: 839871446b982d4df26af7ac570bb8b77fdf151ee99a3a657c5d943078a490ee

最终所有三个按钮显式type="button"，避免嵌入表单时隐式提交。静态核对后独立29项再次通过、退出0；未单独执行外层form提交事件测试。
