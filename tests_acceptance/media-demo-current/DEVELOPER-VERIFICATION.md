# 图音合成演示普通回归（开发侧，2026-11-18）

被测精确头1450bb2829a6c2ca0db9b83861c16aa8201ed0a2。仅验证现有候选，不改运行时。
静态审查三个节点及其fixture/helper后，在仓库根目录运行：

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=.:service "$MCIS_DEMO_PY" -m pytest -q \
 service/tests/test_media_demo_no_role_header.py::test_synthetic_prepare_and_readback_without_role_header \
 service/tests/test_media_demo_launch.py::test_prepared_manifest_metadata_and_disabled_app \
 service/tests/test_media_review_demo.py::test_same_app_edits_audit_and_reopen_preserve_both_histories
```

MCIS_DEMO_PY指向已有获准服务虚拟环境Python，本轮未安装依赖。实际3 passed in 2.06s，无失败/跳过。

覆盖：全新合成材料准备；不附加角色头的运行读取及下载响应摘要头；显式root/manifest关联预检；模型关闭的应用构造；同应用图音修订、审计链与重新构造应用后的修订重读，初始机器草稿保留。仅临时数据库及合成材料，TestClient进程内ASGI调用，不是实际网络服务或浏览器，不证明原件完整性全面验收/真实人工听校。

未选取同文件其他节点，没有运行导出拒绝、写入拒绝探测、暂停测试、真实资料或模型。没有重新启动浏览器、服务或安装依赖。现有指南docs/MEDIA-DEMO.md已给出固定完整SHA、准备/预检/回环8766及停止命令，并注明未认证、模式初始化可能写入、非原子预检与仅自有临时目录。

仍缺：支持沙箱的真实浏览器环境、页面交互/声音输出/人工审核、干净安装、完整客户端到服务流程和可靠停止日志；本次应用重开不是进程崩溃恢复。正式媒体归档/恢复继续关闭，不合并不部署。本记录不能称独立验收。
