# 离线例子
从 Skill 根目录运行以下命令，将输出写入安装目录外尚不存在的目录。
```sh
python scripts/reconstruct.py benchmarks/inputs/A --out ../demo-hull
python scripts/reconstruct.py benchmarks/inputs/B --profile benchmarks/witness-v2/B.json --out ../demo-reviewed
```
在 report.json 查看文件摘要和适用状态，在 offsets.json 查看各格文字及句柄，在 face-evidence.json 按三角面索引追溯。
