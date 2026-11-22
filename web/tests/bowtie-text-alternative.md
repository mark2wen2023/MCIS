# W15 同源文字替代（待独验）

固定基线 9e241dba94400cde9bddefb679a1c981a7fcc4ef。独立 candidate/bowtie-text-alternative，原候选不改。原 Diagram 只有 SVG/title 和编辑表单，无完整只读文字结构。

真实 Diagram 下增加原生 details/summary。按已有类型分组列完整节点名/ID，按原输入顺序列有向连线，升级因素显示输入绑定屏障。直接使用同一 model，不做遍历/因果推导/结构校验替代，不改变 SVG、业务模型、边、导出或来源选择。重复/缺失端点诚实显示，空类不暗示现实不存在。固定 ToBeVerified/Unknown 和整图来源限制保留；没有已复核/争议状态或 ECFC 映射。

web 目录，仅已有离线依赖：
```sh
bash tests/run-bowtie-svg-status.sh
./node_modules/.bin/esbuild tests/bowtie-text-alternative.test.tsx --bundle --platform=node --format=cjs --jsx=automatic --outfile=/tmp/bowtie-text-check.cjs --log-level=warning
node /tmp/bowtie-text-check.cjs
./node_modules/.bin/tsc -b --force
```
上述均退出0。实际 React SSR 检查完整文字、四条原连线、两种屏障Unknown、绑定、空输入、重复/缺端点、转义、输入不变。原SVG检查通过。没有浏览器、读屏、键盘/视觉或 AcciMap 验收；未启动服务/模型、未读真实资料、未改变权限、合同或持久化。旧冻结只对应旧提交，新freeze单列。
