#!/bin/bash
# 用法: run_module.sh <模型id> <日志名> <提示>
cd /workspace/maritime-sim-design
export PATH=$HOME/.dotnet:$PATH DOTNET_CLI_TELEMETRY_OPTOUT=1 DOTNET_NOLOGO=1
COMMON="通用规则：先读 ./P1_TASK_A.md（总体约束、C# 9 兼容、命名空间规范）和 ./ARCHITECTURE.md 中对应章节/接口签名；查看 ./unity/Assets/_Project/Scripts 下已有类型并复用，不得重复定义。测试工程已搭好：./unity/DotnetTests/Mcis.Pure.csproj（glob 引入 Core/Primitives、Domain/**、Simulation/Clock/**、Simulation/Cpa/**）与 ./unity/DotnetTests/Tests/Mcis.Pure.Tests.csproj（xUnit，net8.0），测试文件放 ./unity/DotnetTests/Tests/ 下。dotnet 命令：~/.dotnet/dotnet。本次只做下面这一个模块，写完后运行 'cd unity/DotnetTests/Tests && ~/.dotnet/dotnet test' 修到全部通过，然后在 ./unity/PROGRESS.md 表格中更新该模块一行（状态=完成、模型=agy 当前模型、测试=通过数/总数）。每次写入文件不超过约 200 行，分多个文件，保持持续输出。只允许在 /workspace/maritime-sim-design/unity 内写文件；不要 git 操作。严格范围：只创建/修改本模块说明中明确列出的路径；绝对不要实现 ARCHITECTURE.md 中其他模块（Data/CasePackage、Damage、Ecfc、Environment、Export、Analysis 等都不属于 P1），不要新增 asmdef（除非本模块明确要求）。"
agy --model "$1" -p "$COMMON

本次模块：$3" --dangerously-skip-permissions < /dev/null > "logs/$2.txt" 2>&1
echo "EXIT $?" >> "logs/$2.txt"
