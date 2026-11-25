# Chapter 04 — A blank row is still a row

Synthetic experiment only. Implementation 31322f2; regression tests ede1df3. Local Python 3.13.5 / pytest 9.0.2: 13 passed in 0.07 s. Seven algorithm source blobs and the test file matched GitHub hashes. Independent QA pending.

Input: reviewed CAD row anchors y=[30,20,10], columns x=[10,20], hull heights [2,1,0] m, stations [0,2] m, text in mm. First row [1000,1000], middle absent, last [1250,1250].
Actual legacy-mode output: 0 observations, 1 issue. Explicit row mapping: 6 observations, 2 null values, 0 issues. Adapter output in increasing height order: both sections [1.25,null,1.0] m. No mesh produced. Duplicate cells and overlapping row windows are rejected.

Remotion: reveal a table with an empty middle row; show text clustering returning only two rows and stopping; reveal the reviewed anchors, preserve all six cells, normalize to SI and keep the blank as null. Narration: 图纸上的一行，即使没有任何文字，也仍然是一行。只寻找数字，会丢失表格结构；而表格结构本身也是信息。我们先确定行的位置，再寻找其中的数据。我们保留空白，也保留它在世界中的位置。

Limitations: reviewed anchors must be supplied; no automatic CAD grid detection or real DWG execution here. Legacy mode remains for compatibility and cannot resolve missing-row/extra-text cancellation. No production authorization.
