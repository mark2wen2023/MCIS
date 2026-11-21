# W9 页面03 登记尺寸核对（待独立复验）

基线 main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`；候选 candidate/vessel-dimension-status。只改实际ShipsPage/VesselList只读展示，不接2D/3D、不改已有表单、API、权限或尺寸合同。

旧VesselList过滤undefined字段，缺总长/型宽时整个字段消失。新Dimensions组件逐项显示总长、型宽、首尾吃水：未登记、不填默认值；合法已登记数值；异常值不作为有效尺寸。现有读取解析器允许有限负数/零尺寸，故展示层不把它们冒充有效尺寸（录入正数/非负规则未改）。零吃水保留。现有parseVessels对null仍拒绝，组件null测试仅为防御，不代表新增服务合同支持。

每个有值字段来源标注“声明”“尚未核验”，包括Direct；缺失/空白来源明确说明。孤立来源标签不推出缺失数值。没有默认船体、可视放大倍数或姿态值；文案说明本页未提供模型比例，不能从画面大小反推实船尺寸、从吃水推断装载状态。其余字段继续原展示。

在web目录实跑，全部退出0：

```bash
node tests/vessel-dimensions.cjs
./node_modules/.bin/esbuild tests/vessel-entry-w91.test.tsx --bundle --platform=node --format=esm --packages=external --outfile=tests/.tmp-vessel-entry-w91.mjs --jsx=automatic --loader:.css=empty --log-level=warning
node tests/.tmp-vessel-entry-w91.mjs
./node_modules/.bin/tsc -b --force
./node_modules/.bin/vite build
```

新测试执行固定旧版及候选实际VesselList的React SSR，旧版缺字段反例成立；覆盖缺失、有值未验来源、Direct/Derived/Estimated、零吃水、非法长宽/负吃水、空白/孤立来源、转义、不改输入与空列表。其他页面依赖被替换，不执行effects、请求或保存。原W9.1 84项合成断言通过。TS与Vite8.3.8构建767模块，原大于1500kB警告保留。原回归首次全依赖ESM打包因Node动态require报错，改为现有外部包引用后通过；未安装依赖。

用户入口仍为页面03船舶参数 `#/ships?case=<现有案号>`；本轮未运行该地址。真实浏览器/视觉、Unity、服务、读取真实档案、实船尺寸认证、示意缩放与三维接线均未验。不改变默认功能开关、不合并或部署。
