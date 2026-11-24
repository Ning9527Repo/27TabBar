# 系统底栏玻璃 · TheseusSystemTabs

把 iPhone 上符合条件的 UIKit `UITabBar` 换成 [Theseus 官方动图](https://github.com/valzevul/Theseus/blob/master/assets/tabBar.gif) 对应的底栏：Metal 玻璃底面、独立选中透镜、按压抬起、拖动拉伸和松手回弹。

- 玻璃底板作为原生 `UITabBar` 内部的最底层子视图；原 `UITabBarButton` 不复制、不重新挂到玻璃里，图标、文字、角标和辅助功能均由原控件显示。普通点击沿用真实系统触摸；水平拖动松手才转发系统选择入口，由 App 决定是否切页。
- 每轮布局采用“有条件还原上轮按钮坐标 → UIKit 原布局 → 重新记录并重排按钮”，只隐藏原 `_UIBarBackground`；无整栏透明遮罩、无 hitTest 截断、无定时轮询切页。不修改原栏 frame、导航控制器或 safe area。
- 参考 `com.banshengnianhua.theseustabbar` 的原生栏内挂载、条件几何恢复和事件合并方法，独立源码实现；未复制其动态库或材质。玻璃及透镜继续使用锁定的原版 Theseus Metal。
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
