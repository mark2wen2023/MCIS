# 图片逐行OCR核对：隔离候选 v1

显式工厂 `mcis_service.image_review.app.create_image_review_app(settings)`，默认应用不挂载、不建新表。只在临时库和127.0.0.1运行。既有W4.2保持opaque上传和下载、不内嵌执行；候选页面提供授权下载在本地查看。本片不修改PR69/97或EvidencePage。

输入：同案已登记PDF、页图、原始OCR输出、候选JSON四份W4.2回执摘要。候选仅接既有`mcis.offline-ocr-candidate/v0.1`逐行结果，无表格。导入读取已登记候选字节，对PDF/页图实际读取摘要绑定；保存候选完整内容及登记ID/摘要、识别器、页码、坐标、原始输出摘要、导入角色/操作人/UTC。原始OCR输出亦登记并核对实际字节摘要；不自动证明候选逐行结果确由该识别器产生。PDF页码和图像渲染来源是人工声明，不验证页数/渲染关系；raw_page_index=null照原样保留。不得称自动PDF跳页、原件真实性或已运行OCR。

POST `/api/v1/cases/{caseId}/image-reviews`：`bindings:{pdf,image,raw,candidate}`及`acknowledgeArchiveBlocked:true`。201含runId/revision=0及initial/reviews。无自动幂等重试；超时结果未知，保留运行记录，须通过同案GET集合列出运行ID/UTC再逐项读取核查，而非盲重发。列表不核验来源字节，不返回识别内容。
GET `.../{runId}`：重新执行原登记权限和四份回执字节检查，返回完整原识别与追加历史。该检查不是Access下载记录或人的已读证明。
POST `.../{runId}/reviews`：expectedRevision/lineIndex/text/decision/reason。decision仅pending/transcription-checked/unreadable；文字核对不是事故事实确认。事务内compare-and-set，旧版本412；不自动覆盖、重试。所有前值通过只追加记录保留；无旧数据迁移或补造。

导入与核对沿用W4.2 authorize写权；查看沿用读权；同案load_receipt绑定，默认请求头仍非生产身份认证。记录与既有audit同SQLite事务；追加表UPDATE/DELETE触发器，非抗管理员篡改承诺。复用既有下载POST及SHA检查，不新增原件接口。不改变现有权限/锁或旧入口安全实现。

新表`image_ocr_review_records`不进入归档白名单。因四份来源必须是W4.2登记，既有has_history走工作记录归档，既有未知非空表检查拒绝整包；导入前必须明确同意该限制。不承诺备份恢复，禁止在正式案件启用。生产接线前须完成归档合同与独立权限/并发/浏览器验收。

页面只存内存输入，无自动保存，失败/412保留当前输入；刷新/离开提示可能被浏览器抑制。该独立页面不读取现有工作台身份状态，不能冒充已完成工作台集成。没有外部OCR/API、模型执行、私案资料。PaddleOCR历史输出导入与重新运行必须分别报告。

## 隔离页图预览增量（dc0538之后）
本候选页面现在可显式点击载入PNG，并排显示页图、逐行OCR和人工修订输入；选行显示声明框及局部原图。不改变W4.2的opaque下载协议：调用已有授权下载并记录访问，浏览器检查返回摘要后仅在canvas解码PNG，不执行附件。PNG头声明尺寸须匹配OCR尺寸，最大8192单边/2500万像素，再核对解码尺寸；拒绝或清除不自动重试。按浏览器比例显示，不改变原文件。此增量取代本文此前“仅下载、不内嵌”的候选UI说明，默认产品应用仍不启用。
换案件/运行输入、重新读取或离开页面清除已载入像素；异步迟到结果不重新绘制。逐行框选不提交核对，不改用户草稿。PDF仍仅下载，不实现跳页；没有自动OCR、PDF页码/渲染关系核验或事实确认。浏览器实际显示与解码未验。
