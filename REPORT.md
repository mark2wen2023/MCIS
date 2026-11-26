# W19 关键词最小对照 — 官方验收记录

- 底版：origin/main `94d5e38c926fda232bb987b60fa9145e4bcf01a7`
- 父候选：`eeb7a2a152f95274346f07884fbe6f3b77c299b1`；本提交：`a3a593fe4d9362c9210d455c1ffc0836c424d841`
- 只新增 `keyword_control.py`；`run.py` 固定校验未改（SHA-256 `e7959f56cffc316f2bf0bb921f1b8b4a143213e94704513f6e6fe5196efbce09`）
- 无等价现成原件可直接引用：W191/test_http.py 虽是 94d5e38 上真实 127.0.0.1 HTTP，但夹具不同，大小写查询只断言 total，没有卡 id/出处字节级比对，也没有先对夹具全文排除探测词的记录。eeb7a2a 官方跑始终使用同一大小写的词。
- 官方运行（Asia/Shanghai）：2026-11-27 06:45:15–06:45:18 CST，退出码 0
- `timeout --signal=TERM --kill-after=10s 150s unshare -r -n`，仅监听 127.0.0.1:18768
- HTTP 不是浏览器；不是向量检索；不是 W19 整包；未重复生命周期验收

查询：
- A：`syn-w19-retr-7F3A9C`（原词 `SYN-W19-RETR-7f3a9c` 的 swapcase），HTTP 200，total=1，卡 id 与同进程原对照相同，`content.source` 与原对照及先前官方出处字节级一致（excerpt=`SYN-W19-RETR-SRC-PUB`）。
- B：`ZXQ-ABSENT-W19-9K2M`（先断言不在任何夹具字符串中），HTTP 200，items=[]，total=0。
