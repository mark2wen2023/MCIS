# PR99/100/101组合候选 — DO NOT MERGE / 待浏览器验收

2026-11-18开发方验证，不是独立验收或生产就绪证明。

## 固定输入与冲突处理

- main: 94d5e38c926fda232bb987b60fa9145e4bcf01a7
- PR99: 3d783392e7f3187457d1d5bfba1e6efcbb6d9064
- PR100: 73d1da7661311a68b8d75183991824c13d921653
- PR101: 1731de7217801d3e99af718a9cc0cc41c540f28a
- 第一次合并7024c1dbb9d7509c19cdbdf030a6ac992789e011保留PR99/100双父。
- 被测组合242b814bc44ba1c27d1226f9ee673abbb4a25a47，双父为7024c1d与PR101精确头；后续提交仅新增本记录。

两次合并均仅REQUESTS.md、ROADMAP.md末尾追加冲突。确认每个输入均以主线文件字节为前缀后，结果为主线原文+PR99完整后缀+PR100完整后缀+PR101完整后缀。未删改、重写或裁决历史说明，没有功能代码冲突。非共享改动文件逐字节等于所属输入；被测组合相对main的18个路径严格等于三个候选改动路径并集，未夹带其他候选。三个精确输入均是组合祖先。

## 限定验证

新建独立工作树，复制既有node_modules以隔离构建缓存，未安装依赖。Node24.22.1、esbuild0.28.2、TypeScript7.0.2、Vite8.3.8。下列六文件此前已完整静态审阅，本次核对其与对应精确候选字节一致：只有合成对象、纯函数和SSR，未调用服务/模型、未使用真实案件、未运行暂停节点或写入拒绝探测。没有使用全套测试脚本。

在web目录运行：

```bash
set -e
for test in interview-source-disclosure interview-render case-metadata-gaps case-metadata-w84 environment-origin-guidance environment-w92; do
 node_modules/.bin/esbuild "tests/$test.test.tsx" --bundle --platform=node --format=esm --packages=external --jsx=automatic --loader:.css=empty --define:__MCIS_API__='"http://127.0.0.1:8765"' --outfile="tests/.tmp-combined-$test.mjs"
 node "tests/.tmp-combined-$test.mjs"
done
node_modules/.bin/tsc -b --force
node_modules/.bin/vite build
```

六个脚本均退出0：笔录原渲染40项、W8.4模型/渲染96项、W9.2模型/渲染103项断言通过；另三份来源披露/缺项/环境来源SSR脚本通过但没有断言总数。上述数值不是239个独立测试用例，不与以前各分支测试数相加。

TypeScript强制构建退出0；Vite退出0，769模块，JS1860.30kB，CSS76.01kB。保留>1500kB分块警告，没有调整阈值。所选命令无失败/跳过，不代表完整CI/全仓通过。

## 未验与范围

仅组合三个只读提示功能，未改权限、业务写入或归档支持。来源字段不证明原件已核验；五项有字不证明全案完整；来源类型不证明真实性。各原候选限制保持。

SSR/纯函数不是浏览器。CSS在测试打包时置空，不验证视觉；真实页面点击/展开/布局、完整HTTP联动、原件、真实模型、可信身份、干净安装及CI均未验。未重试浏览器沙箱失败或其他受限操作。组合未独验，不合并主线、不关闭原PR、不部署。
