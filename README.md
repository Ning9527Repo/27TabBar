# 系统底栏玻璃 · TheseusSystemTabs

把 iPhone 上符合条件的 UIKit `UITabBar` 换成 [Theseus 官方动图](https://github.com/valzevul/Theseus/blob/master/assets/tabBar.gif) 对应的底栏：Metal 玻璃底面、独立选中透镜、按压抬起、拖动拉伸和松手回弹。

- 恢复我们自己的完整 Theseus 底栏：复制原生标签的图标、文字、角标和启用状态，视觉和触摸统一交给 Theseus；原 `UITabBar` 只保留内部选择与 App 回调逻辑，整栏视觉持续由插件遮罩隐藏。
- 0.1.4 仅修复“切页时露回原生样式”和“选中胶囊过小”：转场、原按钮临时重建、GPU 首帧等待均保留现有替换；首次 GPU 帧前由原库自带的 UIKit 材质承接。胶囊按标签槽位宽度自适配，材质、底栏位置、图标和角标仍沿用自有方案。
- 0.1.5 将普通轻点和按住/拖动的透镜分开，轻点以 UIKit 实际选中结果触发一次原弹簧动画；选中胶囊在两端距外框 4 pt。标准底栏优先使用标签项及原生按钮的文字和图标，切页重建时保留同一标签的有效内容；原版 Metal 与模糊参数保持，采样透明缺口不再把未模糊页面直接叠进玻璃。
- 0.1.6 切页时淘汰旧纹理并用同轮廓的模糊层承接；拖动位置不等 Metal，透镜最多每秒采样 30 次。静止底板和选中胶囊减少清晰背景混合，拖动透镜的材质不改。
- 后续修订：切页不再整条换成带重阴影的备用磨砂，而是用各自的上一帧代表色（不带页面像素）短暂衔接新帧；首尾和中间的栏位统一等宽，图文和胶囊共用中心；恢复原版背景参数、按压拖动弹簧和渲染调度。保留系统底栏挂载、选中回读与文字图标恢复。
- 不再采用 0.1.3 的原按钮保留重排方案。不改导航控制器、safe area 或系统原栏 frame。
- 首版目标 iOS 16+。只接管 iPhone 标准贴底横向 `UITabBar`（2–5 个匹配的原生按钮）；iPad 顶栏、微信、桌面 Dock、自绘底栏、识别不出的样式保持原状。VoiceOver 开启时恢复原生栏。
- 背景取同一窗口的 UIKit 图层，在内存中渲染，不写屏幕截图、不联网。不保证 WebKit/视频/其他跨进程合成内容能出现在折射里。没有完成真机覆盖测试。
- 上游 Swift/Metal 及许可原样保存于 `Vendor/Theseus`，锁定 `71ca1c127a4e7fe3387361f160c4890dbd427f66`。构建时以 `tools/stage.py` 生成适配副本；shader 不改。

## 构建

需要完整 Xcode 和 iPhoneOS Metal 工具链。在 macOS 上运行：

```sh
python3 tests/check_source.py
python3 tools/build.py --targets roothide  # 或 rootless / both
```

GitHub Actions 仅 `workflow_dispatch` 启动。成品位于 `dist/`。RootHide 为 `iphoneos-arm64e`，普通无根为 `iphoneos-arm64`；二者分别编译和校验，不是改名转换。未将可安装包发布到软件源。

Theseus 原作：valzevul（Apache-2.0，见上游 LICENSE / NOTICE）。适配：Ning。
