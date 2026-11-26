# 陌生合成工程图独立验收
fixture/inputs 是按工况隔离的输入，fixture/truth.json 只供独立评分。s2-freeze.json 记录全部冻结输入、真值和首轮前已登记的评分器。先使用 Git 归档的指定实现运行 CLI，再由独立程序复算原生曲线参数及各控制点的留一误差。保留每轮名和全部失败案例。

从可写的基准目录执行下列命令，生成的 runs/ 在本机保留。
```sh
python run_suite.py /path/to/checkout 7dd34bbe282dabb3c2b71748fb8aa1e4ee2d559c review-1
python independent.py review-1
```

首次试验是盲测，研发方看到首轮错误后的执行属于固定回归。没有布局关联依据的米制值属于资料未定。不得调整真值来满足模型输出。
