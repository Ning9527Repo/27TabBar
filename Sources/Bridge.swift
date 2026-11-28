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

    @MainActor init(_ item: UITabBarItem, _ control: UIControl, selected: Bool, previous: TabData?) {
        identity = ObjectIdentifier(item)
        // Keep only metadata from this exact item if UIKit is rebuilding its button.
        let native = NGTabPresentation.title(item.title) ?? NGTabPresentation.title(NGSystemTabButtonTitle(control, item.badgeValue))
        title = native ?? previous?.title ?? NGTabPresentation.shortLabel(item.accessibilityLabel)
            ?? NGTabPresentation.shortLabel(control.accessibilityLabel)
        let rendered = item.image != nil && item.selectedImage != nil ? nil : NGSystemTabButtonImage(control)
        icon = item.image ?? (selected ? nil : rendered) ?? previous?.icon
            ?? (rendered ?? item.selectedImage)?.withRenderingMode(.alwaysTemplate)
        selectedIcon = item.selectedImage ?? (selected ? rendered : nil) ?? previous?.selectedIcon
        accessibility = item.accessibilityLabel ?? control.accessibilityLabel
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
    private var metalPresented = false
    private var generation: UInt64 = 0

    init(_ bar: UITabBar) {
        native = bar
        nativeMask.backgroundColor = UIColor.clear.cgColor
        glass.autoresizingMask = []
        glass.barHeight = 63
        glass.ngUseHostPosition = true
        glass.ngActivateNative = { [weak self] index in self?.activate(index) }
    }

    deinit { timer?.invalidate() }

    func attach(to bar: UITabBar, in parent: UIView, at frame: CGRect) {
        generation &+= 1
        let mount = generation
        glass.ngExcludedBar = bar
        glass.ngApplyHostFrame(frame)
        glass.ngPrepareReplacement()
        glass.ngGlassDidPresent = { [weak self] in
            guard let self, self.generation == mount else { return }
            self.metalPresented = true
            self.glass.ngGlassDidPresent = nil
            NGSystemTabNote("replacement-metal-ready", self.native)
        }
        UIView.performWithoutAnimation {
            parent.insertSubview(glass, aboveSubview: bar)
            reveal(in: bar)
        }
        timer = Timer(timeInterval: 1.0 / 12, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let self, let bar = self.native, !self.glass.ngHostIsInteracting else { return }
                SystemTabsBridge.update(bar)
            }
        }
        if let timer {
            timer.tolerance = 0.02
            RunLoop.main.add(timer, forMode: .common)
        }
        DispatchQueue.main.asyncAfter(deadline: .now() + 2) { [weak self] in
            guard let self, self.generation == mount, !self.metalPresented else { return }
            NGSystemTabNote("replacement-using-own-material", self.native)
            // Keep our own bar and its library fallback. A slow GPU frame must
            // never remove the replacement and reveal the system bar.
        }
    }

    func reveal(in bar: UITabBar) {
        guard !isPresented else { return }
        isPresented = true
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        nativeMask.frame = bar.bounds
        bar.layer.mask = nativeMask
        glass.alpha = 1
        CATransaction.commit()
        glass.isUserInteractionEnabled = true
        glass.accessibilityElementsHidden = false
    }

    private func syncAppearance(from bar: UITabBar) {
        // A transient mismatch of inherited traits is not a native override.
        let style = bar.overrideUserInterfaceStyle
        if glass.overrideUserInterfaceStyle != style { glass.overrideUserInterfaceStyle = style }
    }

    func preserveReplacement(_ bar: UITabBar) {
        guard isPresented, glass.superview != nil else { return }
        syncAppearance(from: bar)
        if let parent = bar.superview, glass.superview === parent,
           let originalIndex = parent.subviews.firstIndex(where: { $0 === bar }),
           let replacementIndex = parent.subviews.firstIndex(where: { $0 === glass }),
           replacementIndex <= originalIndex {
            parent.insertSubview(glass, aboveSubview: bar)
        }
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        nativeMask.frame = bar.bounds
        if bar.layer.mask !== nativeMask { bar.layer.mask = nativeMask }
        glass.isHidden = bar.isHidden || bar.isCustomizing
        glass.alpha = bar.alpha
        CATransaction.commit()
        glass.isUserInteractionEnabled = !glass.isHidden && bar.isUserInteractionEnabled
    }

    func suspend() {
        glass.isHidden = true
        glass.isUserInteractionEnabled = false
    }

    func detach() {
        generation &+= 1
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
        syncAppearance(from: bar)
        if glass.selectedTintColor != bar.tintColor { glass.selectedTintColor = bar.tintColor }
        let unselected = bar.unselectedItemTintColor ?? TheseusTabBar.nativeUnselectedTint
        if glass.unselectedTintColor != unselected { glass.unselectedTintColor = unselected }
        if tabs != data {
            if data.map(\.identity) == tabs.map(\.identity) {
                glass.ngRefreshItems(tabs.map { $0.makeItem() }, changed: tabs.indices.filter { tabs[$0] != data[$0] })
            } else {
                glass.items = tabs.map { $0.makeItem() }
            }
            data = tabs
        }
        if !activationPending { glass.ngApplySelection(index) }
        // Sample while a scroll view behind the bar is moving. Update stable
        // content at a slower cadence (e.g. badges, asynchronously loaded cells).
        guard !glass.ngHostIsInteracting else { return }
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

    private func activate(_ index: Int) -> Int? {
        guard let bar = native, !activationPending, let items = bar.items, items.indices.contains(index),
              data.indices.contains(index), ObjectIdentifier(items[index]) == data[index].identity,
              let buttons = NGSystemTabControls(bar, items.count) else { return nil }
        activationPending = true
        defer {
            DispatchQueue.main.async { [weak self] in
                guard let self, let bar = self.native else { return }
                self.activationPending = false
                SystemTabsBridge.update(bar)
            }
        }
        guard items[index].isEnabled else { return nil }
        guard NGActivateSystemTabControl(bar, buttons[index]) else {
            NGSystemTabNote("native-action-rejected", bar)
            return nil
        }
        guard let selected = bar.selectedItem else { return nil }
        return data.firstIndex { $0.identity == ObjectIdentifier(selected) }
    }
}

@MainActor @objc(NGSystemTabsBridge) final class SystemTabsBridge: NSObject {
    private static let states = NSMapTable<UITabBar, SystemTabsState>.weakToStrongObjects()
    private static let observed = NSHashTable<UITabBar>.weakObjects()
    private static let lifecycle: [NSObjectProtocol] = [UIApplication.didBecomeActiveNotification,
        UIApplication.didEnterBackgroundNotification, UIApplication.protectedDataDidBecomeAvailableNotification,
        UIAccessibility.voiceOverStatusDidChangeNotification,
        UIAccessibility.reduceTransparencyStatusDidChangeNotification].map { name in
        NotificationCenter.default.addObserver(forName: name, object: nil, queue: .main) { _ in
            DispatchQueue.main.async {
                for bar in observed.allObjects { update(bar) }
            }
        }
    }

    @objc(suspend:) static func suspend(_ bar: UITabBar) {
        states.object(forKey: bar)?.suspend()
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
        let y = min(box.maxY, visibleBottom) - win.safeAreaInsets.bottom - 63
        let rect = CGRect(x: box.minX + 14, y: y, width: box.width - 28, height: 63)
        let result = parent.convert(rect, from: win)
        return result.width > 0 && result.height > 0 ? result : nil
    }

    @objc(update:) static func update(_ bar: UITabBar) {
        guard Thread.isMainThread, !NGSystemTabIsCapturing() else { return }
        observed.add(bar)
        _ = lifecycle
        let previous = states.object(forKey: bar)
        guard let win = bar.window, let parent = bar.superview else {
            previous?.suspend(); return
        }
        if let previous, previous.glass.superview !== parent {
            previous.glass.removeFromSuperview()
            parent.insertSubview(previous.glass, aboveSubview: bar)
        }
        previous?.preserveReplacement(bar)
        // Native selection can synchronously trigger layout. Reassert the mask,
        // but leave content/selection work to the already queued readback.
        if previous?.activationPending == true { return }
        // These conditions suppress updates, not the claimed replacement. Model
        // or presentation alpha during a tab transition never restores native UI.
        guard UIApplication.shared.applicationState != .background,
              !bar.isHidden, !bar.isCustomizing,
              bar.isUserInteractionEnabled else { return }
        guard previous != nil || (!UIAccessibility.isVoiceOverRunning && !UIAccessibility.isReduceTransparencyEnabled) else { return }
        guard let frame = layoutFrame(for: bar, in: win, parent: parent) else {
            NGSystemTabNote("geometry-update-deferred", bar); return
        }
        guard let items = bar.items, let selected = bar.selectedItem,
              let index = items.firstIndex(where: { $0 === selected }) else {
            NGSystemTabNote("selected-item-update-deferred", bar); return
        }
        guard let buttons = NGSystemTabControls(bar, items.count) else {
            NGSystemTabNote("native-buttons-update-deferred", bar); return
        }
        if !buttons[index].isSelected { NGSystemTabNote("native-selected-mismatch", bar) }
        guard previous != nil || Bundle.hasTabMetalResources else {
            NGSystemTabNote("resources-unavailable", bar); return
        }
        let oldData = previous?.data ?? []
        let tabs = items.indices.map { i in
            let item = items[i]
            return TabData(item, buttons[i], selected: i == index,
                           previous: oldData.first { $0.identity == ObjectIdentifier(item) })
        }
        guard tabs.allSatisfy({ $0.title != nil || $0.icon != nil || $0.selectedIcon != nil }) else {
            NGSystemTabNote("tab-content-update-deferred", bar); return
        }
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
            return
        }
        state.apply(tabs, index: index, bar: bar, frame: frame)
    }

    @objc(usesOverlay:) static func usesOverlay(_ bar: UITabBar) -> Bool {
        guard let state = states.object(forKey: bar) else { return false }
        return state.glass.superview != nil && bar.layer.mask === state.nativeMask
    }
}
