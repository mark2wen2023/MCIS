# Chapter 12 — A reproducible chain, not isolated tools

Research orchestrator 2169e13, review mapping/scope binding 10dc65a, regression tests 7cd72a6. Local execution of 18 algorithm files and two test files, with Git blob hashes matching the remote source: 22 tests passed in 0.11 s. Python 3.13.5, pytest 9.0.2, ezdxf 1.4.4, trimesh 4.11.1. Not an independent QA or full service claim.

Actual synthetic DXF-to-GLB experiment:
| Input | Offset records | Nulls | Output vertices | Output faces | Result |
|---|---:|---:|---:|---:|---|
| Complete | 6 | 0 | 6 | 4 | written |
| Missing one cell | 6 | 1 | 4 | 2 | written |
| Entire row empty | 6 | 3 | null | null | rejected: no supported geometry |

Both written GLBs were independently read using trimesh, with face indices equal and coordinate errors zero for the deliberately simple integer-valued inputs. SHA-256 manifest verification passed; formal authorization false. Synthetic review records are provided by the experiment, not an automated approval mechanism. Exact files, JSON, reproduction program and hash list in the local synthetic experiment package.

Remotion: reveal actual synthetic table, animate reviewed mapping, build four triangles, delete one source cell, build two triangles, remove whole row and stop. Explain the difference between no geometry support and zero breadth. Show model and evidence fingerprint linkage.

Narration: 一次完成任务，并不意味着掌握了这种能力。我们把各个算法连接成同一条可复核的工作链。面对完整数据，它产生模型；面对缺失数据，它保留缺口；当没有足够的几何依据时，它拒绝输出三维资产。

No real vessel data. Caller-provided parsed records and review identities are not authenticated; the orchestrator consumes already parsed entities, and is not registered in the production runtime. No formal authorization.
