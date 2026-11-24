import UIKit
import QuartzCore

extension Bundle {
    static let module: Bundle = {
        resourceBundle ?? .main
    }()
    static let resourceBundle: Bundle? = {
        guard let path = NGTabResourceBundlePath() else { return nil }
        return Bundle(path: path)
    }()
    static let hasTabMetalResources = resourceBundle?.url(forResource: "default", withExtension: "metallib") != nil
}

private struct TabData: Equatable {
    let identity: ObjectIdentifier
    let title: String?
    let icon: UIImage?
    let selectedIcon: UIImage?
    let accessibility: String?
    let badge: String?
    let badgeColor: UIColor?
    let enabled: Bool

    @MainActor init(_ item: UITabBarItem, _ control: UIControl) {
        identity = ObjectIdentifier(item)
        title = item.title
        icon = item.image
        selectedIcon = item.selectedImage
        accessibility = item.accessibilityLabel
        badge = item.badgeValue
        badgeColor = item.badgeColor
        enabled = item.isEnabled && control.isEnabled
    }

    func makeItem() -> TheseusTabBarItem {
        var item = TheseusTabBarItem(icon: icon, selectedIcon: selectedIcon, title: title)
        item.ngLabel = accessibility
        item.ngBadge = badge
        item.ngBadgeColor = badgeColor
        item.ngEnabled = enabled
        return item
    }
}

@MainActor private final class SystemTabsState {
    weak var native: UITabBar?
    let glass = TheseusTabBar(frame: .zero)
    let nativeMask = CALayer()
    var data: [TabData] = []
    var timer: Timer?
    var scrollSample: [ObjectIdentifier: CGPoint] = [:]
    var activationPending = false
    var refreshTick = 0
    private(set) var isPresented = false

    init(_ bar: UITabBar) {
        native = bar
        nativeMask.backgroundColor = UIColor.clear.cgColor
        glass.autoresizingMask = []
        glass.barHeight = 63
        glass.ngUseHostPosition = true
        glass.onItemSelected = { [weak self] index in self?.activate(index) }
    }

    deinit { timer?.invalidate() }

    func attach(to bar: UITabBar, in parent: UIView, at frame: CGRect) {
        glass.ngExcludedBar = bar
        glass.ngApplyHostFrame(frame)
        glass.alpha = 0.02
        glass.isUserInteractionEnabled = false
        glass.accessibilityElementsHidden = true
        glass.ngGlassDidPresent = { [weak self] in
            guard let self, let bar = self.native else { return }
            SystemTabsBridge.present(self, for: bar)
        }
        parent.insertSubview(glass, aboveSubview: bar)
        timer = Timer(timeInterval: 1.0 / 12, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self, let bar = self.native else { return }
                SystemTabsBridge.update(bar)
            }
        }
        if let timer {
            timer.tolerance = 0.02
            RunLoop.main.add(timer, forMode: .common)
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
            guard let self, let bar = self.native, !self.isPresented else { return }
            SystemTabsBridge.expire(self, for: bar)
        }
    }

    func reveal(in bar: UITabBar) {
        guard !isPresented else { return }
        isPresented = true
        glass.ngGlassDidPresent = nil
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        nativeMask.frame = bar.bounds
        bar.layer.mask = nativeMask
        glass.alpha = 1
        CATransaction.commit()
        glass.isUserInteractionEnabled = true
        glass.accessibilityElementsHidden = false
    }

    func detach() {
        timer?.invalidate()
        timer = nil
        glass.ngGlassDidPresent = nil
        if let bar = native, bar.layer.mask === nativeMask {
            CATransaction.begin()
            CATransaction.setDisableActions(true)
            bar.layer.mask = nil
            CATransaction.commit()
        }
        glass.removeFromSuperview()
    }

    func apply(_ tabs: [TabData], index: Int, bar: UITabBar, frame: CGRect) {
        // Do not write geometry during Theseus's press / stretch transform.
        if glass.ngHostFrame != frame { glass.ngApplyHostFrame(frame) }
        if nativeMask.frame != bar.bounds {
            CATransaction.begin()
            CATransaction.setDisableActions(true)
            nativeMask.frame = bar.bounds
            CATransaction.commit()
        }
        if glass.effectiveUserInterfaceLayoutDirection != bar.effectiveUserInterfaceLayoutDirection {
            glass.semanticContentAttribute = bar.effectiveUserInterfaceLayoutDirection == .rightToLeft ? .forceRightToLeft : .forceLeftToRight
        }
        if glass.overrideUserInterfaceStyle != bar.traitCollection.userInterfaceStyle {
            glass.overrideUserInterfaceStyle = bar.traitCollection.userInterfaceStyle
        }
        if glass.selectedTintColor != bar.tintColor { glass.selectedTintColor = bar.tintColor }
        let unselected = bar.unselectedItemTintColor ?? TheseusTabBar.nativeUnselectedTint
        if glass.unselectedTintColor != unselected { glass.unselectedTintColor = unselected }
        if tabs != data {
            data = tabs
            glass.items = tabs.map { $0.makeItem() }
        }
        if !activationPending, glass.selectedIndex != index { glass.selectedIndex = index }
        // Sample while a scroll view behind the bar is moving. Update stable
        // content at a slower cadence (e.g. badges, asynchronously loaded cells).
        refreshTick = (refreshTick + 1) % 8
        let scroll = sampleScroll(in: bar)
        if scroll != scrollSample || refreshTick == 0 {
            scrollSample = scroll
            glass.invalidateBackground()
        }
    }

    private func sampleScroll(in bar: UITabBar) -> [ObjectIdentifier: CGPoint] {
        guard let win = bar.window, let root = win.rootViewController?.viewIfLoaded else { return [:] }
        let box = glass.convert(glass.bounds, to: win).insetBy(dx: -20, dy: -60)
        var queue: [UIView] = [root]
        var visited = 0
        var result: [ObjectIdentifier: CGPoint] = [:]
        while let view = queue.popLast(), visited < 128 {
            visited += 1
            guard view !== bar, view !== glass, !view.isHidden, view.alpha > 0.02,
                  view.convert(view.bounds, to: win).intersects(box) else { continue }
            if let scroll = view as? UIScrollView { result[ObjectIdentifier(scroll)] = scroll.contentOffset }
            queue.append(contentsOf: view.subviews.prefix(32))
        }
        return result
    }

    private func activate(_ index: Int) {
        guard let bar = native, !activationPending, let items = bar.items, items.indices.contains(index),
              data.indices.contains(index), ObjectIdentifier(items[index]) == data[index].identity,
              let buttons = NGSystemTabControls(bar, items.count) else { return }
        activationPending = true
        defer {
            DispatchQueue.main.async { [weak self] in
                guard let self, let bar = self.native else { return }
                self.activationPending = false
                SystemTabsBridge.update(bar)
            }
        }
        guard items[index].isEnabled else { return }
        if !NGActivateSystemTabControl(bar, buttons[index]) {
            NGSystemTabNote("native-action-rejected", bar)
        }
    }
}

@MainActor @objc(NGSystemTabsBridge) final class SystemTabsBridge: NSObject {
    private static let states = NSMapTable<UITabBar, SystemTabsState>.weakToStrongObjects()
    private static let observed = NSHashTable<UITabBar>.weakObjects()
    private static let failed = NSHashTable<UITabBar>.weakObjects()
    private static let lifecycle: [NSObjectProtocol] = [UIApplication.didBecomeActiveNotification,
        UIApplication.didEnterBackgroundNotification, UIApplication.protectedDataDidBecomeAvailableNotification,
        UIAccessibility.voiceOverStatusDidChangeNotification,
        UIAccessibility.reduceTransparencyStatusDidChangeNotification].map { name in
        NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { _ in
            DispatchQueue.main.async {
                failed.removeAllObjects()
                for bar in observed.allObjects { update(bar) }
            }
        }
    }

    fileprivate static func present(_ state: SystemTabsState, for bar: UITabBar) {
        guard states.object(forKey: bar) === state else { return }
        update(bar)
        guard states.object(forKey: bar) === state, state.glass.superview === bar.superview,
              state.glass.window != nil, bar.layer.mask == nil else { return }
        state.reveal(in: bar)
        NGSystemTabNote("glass-presented", bar)
    }

    fileprivate static func expire(_ state: SystemTabsState, for bar: UITabBar) {
        guard states.object(forKey: bar) === state, !state.isPresented else { return }
        failed.add(bar)
        NGSystemTabNote("metal-first-frame-timeout", bar)
        detach(bar)
    }

    @objc(detach:) static func detach(_ bar: UITabBar) {
        states.object(forKey: bar)?.detach()
        states.removeObject(forKey: bar)
    }

    private static func layoutFrame(for bar: UITabBar, in win: UIWindow, parent: UIView) -> CGRect? {
        let box = bar.convert(bar.bounds, to: win)
        let visibleBottom = win.bounds.maxY
        guard win.traitCollection.userInterfaceIdiom == .phone,
              box.width.isFinite, box.height.isFinite, box.minX.isFinite, box.minY.isFinite,
              box.width >= 260, box.width >= win.bounds.width * 0.90,
              box.height >= 40, box.height <= 112,
              box.intersects(win.bounds), abs(box.maxY - visibleBottom) <= 12 else { return nil }
        let y = min(box.maxY, visibleBottom) - win.safeAreaInsets.bottom - 5 - 63
        let rect = CGRect(x: box.minX + 14, y: y, width: box.width - 28, height: 63)
        let result = parent.convert(rect, from: win)
        return result.width > 0 && result.height > 0 ? result : nil
    }

    private static func visible(_ bar: UITabBar, through window: UIWindow) -> Bool {
        var cursor: UIView? = bar
        for _ in 0..<25 {
            guard let view = cursor, !view.isHidden, view.alpha >= 0.95 else { return false }
            if let layer = view.layer.presentation(), layer.opacity < 0.94 { return false }
            if view === window { return true }
            cursor = view.superview
        }
        return false
    }

    @objc(update:) static func update(_ bar: UITabBar) {
        guard Thread.isMainThread else { return }
        observed.add(bar)
        _ = lifecycle
        let previous = states.object(forKey: bar)
        guard !failed.contains(bar), !UIAccessibility.isVoiceOverRunning,
              !UIAccessibility.isReduceTransparencyEnabled,
              UIApplication.shared.applicationState != .background,
              let win = bar.window, let parent = bar.superview, visible(bar, through: win),
              bar.isUserInteractionEnabled, !bar.isCustomizing,
              bar.layer.mask == nil || bar.layer.mask === previous?.nativeMask
        else { NGSystemTabNote("visibility-gate", bar); detach(bar); return }
        guard let frame = layoutFrame(for: bar, in: win, parent: parent) else {
            NGSystemTabNote("geometry-gate", bar); detach(bar); return
        }
        guard let items = bar.items, let selected = bar.selectedItem,
              let index = items.firstIndex(where: { $0 === selected }) else {
            NGSystemTabNote("selected-item-gate", bar); detach(bar); return
        }
        guard let buttons = NGSystemTabControls(bar, items.count), buttons[index].isSelected else {
            NGSystemTabNote("native-buttons-gate", bar); detach(bar); return
        }
        guard Bundle.hasTabMetalResources, !TheseusSettings.shared.shouldUseFallback,
              UIApplication.shared.isProtectedDataAvailable,
              MetalContext.shared != nil else {
            NGSystemTabNote("metal-gate", bar); detach(bar); return
        }
        let tabs = zip(items, buttons).map { TabData($0.0, $0.1) }
        let state: SystemTabsState
        if let previous, previous.glass.superview === parent {
            state = previous
        } else {
            detach(bar)
            state = SystemTabsState(bar)
            states.setObject(state, forKey: bar)
            state.glass.selectedIndex = index
            state.glass.preferredItemWidth = 66
            state.glass.ngHostFrame = frame
            state.apply(tabs, index: index, bar: bar, frame: frame)
            state.attach(to: bar, in: parent, at: frame)
        }
        state.apply(tabs, index: index, bar: bar, frame: frame)
    }

    @objc(usesOverlay:) static func usesOverlay(_ bar: UITabBar) -> Bool {
        guard let state = states.object(forKey: bar) else { return false }
        return state.glass.superview != nil && bar.layer.mask === state.nativeMask
    }
}
