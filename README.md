# 系统底栏玻璃 · TheseusSystemTabs

把 iPhone 上符合条件的 UIKit `UITabBar` 换成 [Theseus 官方动图](https://github.com/valzevul/Theseus/blob/master/assets/tabBar.gif) 对应的底栏：Metal 玻璃底面、独立选中透镜、按压抬起、拖动拉伸和松手回弹。

- 接入原生底栏的图标、标题、选中图、角标和启用状态。点击/拖动只向匹配的 UIKit 原生按钮派发已有的动作，由 App 决定是否切页；不伪造 delegate 回调，不改导航控制器或 safe area。
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
