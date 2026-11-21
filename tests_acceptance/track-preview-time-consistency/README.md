# 页面05 / W10 CSV预览时间一致性（待独立复验）

固定基线 main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`；独立候选 candidate/track-preview-time-consistency。不改变已有候选、共享合同或后端。

## 现有能力和选定接缝

TrackPage 是存量检查＋首次输入，不是已有观测编辑器。TrackInputPanel 只给尚无航迹的已登记单船首次导入；服务端 tracks_import/parser.py 已逐行拒绝含糊UTC、重复/倒序时间和不明确数值状态，HDG缺省/unavailable为null，不复制COG。commit_sync拒绝已有点；track_history的LocalReceipt只追加登记定位，现有router只有历史读取，不是点级修订/版本发布接口。

本轮不发明手工编辑或新CSV。实际接缝是 TrackInputPanel.showPreview → parsePreview → setPreview/setBody → 人工确认保存。旧parsePreview仅检查UTC为字符串、相对秒为有限数，纯合成的重复UTC或错纪元响应仍可成为canCommit=true预览。测试固定旧代码复现，**不是声称现有正常服务实际输出了这些响应**。

新增校验复用 tracks/model.ts:validUtc：完整真实日期Z、样例UTC与纪元/相对秒一致、时间范围一致；仅canCommit=true要求严格样例顺序、首端点一致、全样例在范围内、少于等于100行时末端点相符。超过100行只核前100样例，不能以此代替服务端全文件预检。误差容限1e-6秒。

反例现在在接受预览前失败，不能让该响应进入确认保存状态；不修改任何输入或文件，不排序、删点、清洗、猜时间、把未知变零或COG补HDG。canCommit=false的有效诊断预览继续展示，范围不必被误判为可保存排序。

## 实跑命令与结果

在 web 目录，使用现有离线依赖，无安装：

```bash
node tests/track-preview-time.cjs
./node_modules/.bin/esbuild tests/track-input-w102.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/mcis-track-input-test.cjs --jsx=automatic --loader:.css=empty --log-level=warning
node /tmp/mcis-track-input-test.cjs
./node_modules/.bin/esbuild tests/track-inspection-w101.test.tsx --bundle --platform=node --format=cjs --outfile=/tmp/mcis-track-inspection-test.cjs --jsx=automatic --loader:.css=empty --log-level=warning
node /tmp/mcis-track-inspection-test.cjs
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

全部退出0。新增20项纯合成解析检查含旧头反例、含糊/非法日期、重复等价UTC、乱序、错误纪元/相对秒/范围、±容限、负秒、null/0艏向、诊断及101行边界。原W10.2 45项、W10.1 117项分别通过：已有React SSR、纯解析和内存fetch替身，不是网络。Vite8.3.8、766模块，既有大于1500kB提示保留。

本轮没有真实CSV文件、真实服务/HTTP、数据库/ORM、浏览器、媒体、4A或模型运行。原件与回执后端、审计和权限未改；没有实际commit调用或写入。

## 下一实际依赖

这只增强首次导入预览的接纳边界；不能为页面08提供新旧轨迹版本关系。后续须先确认生产修订实体/父版本/原件关联与授权审计职责，才能做保留原始观测的修订保存和分析失效。现有历史读取与首次导入回执不能冒充该接口。未新增开放写路由或另造输入规范。
