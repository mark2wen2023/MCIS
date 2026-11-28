# 研究装配查看器

模板使用 Unity 6000.6、glTFast 6.21、内置渲染管线和旧版输入接口。将 HullViewer.cs、Editor 和 Resources 放入 Unity 项目的 Assets。启用 IMGUI、Physics、ScreenCapture、ImageConversion 模块。

在 Assets/StreamingAssets 放入 assembly、patches、brackets 三组同名 GLB 与 JSON。它们分别对应候选装配、原图约束局部片和未完成安装定位的局部构件。每份 JSON 填写 mode（依次为 demo、strict、unregistered_local_demo）、GLB 的 sha256、items 和 tracks。items 的 id 对应场景节点，另外记录 title、group、source、grade、installation、parameters。完整装配的 tracks 来自 s6_equipment.runtime.rotation_samples。每条轨迹提供 node、kind、min、max 和单位四元数采样 rotations，后两组 tracks 为空数组。

macOS Apple Silicon 构建时指定 MCIS_VIEWER_OUT 为目标 .app 的完整路径，通过编辑器批处理执行 HullBuild.Build。双击程序，右键拖动、滚轮缩放，点击网格查看证据。运动范围为演示设置。在有图形显示的会话用 --verify-viewer 启动程序，可复核文件指纹、运行时加载、运动节点与固定节点隔离、拾取及视图切换。设置 MCIS_CAPTURE_DIR 为已有本地目录可留存运行和剖切截图。
