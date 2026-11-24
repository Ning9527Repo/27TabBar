import UIKit
import QuartzCore

extension Bundle {
    static let module: Bundle = resourceBundle ?? .main
    static let resourceBundle: Bundle? = {
        guard let path = NGTabResourceBundlePath() else { return nil }
        return Bundle(path: path)
    }()
    static let hasTabMetalResources = resourceBundle?.url(forResource: "default", withExtension: "metallib") != nil
}

@MainActor private final class NativeButtonGeometry {
    weak var button: UIControl?
    let nativeFrame: CGRect
    var appliedFrame: CGRect
    init(_ button: UIControl) {
        self.button = button
        nativeFrame = button.frame
        appliedFrame = button.frame
    }
    func restore() {
        guard let button, NGSystemTabFrameMatches(button.frame, appliedFrame) else { return }
        button.frame = nativeFrame
    }
}

@MainActor private final class NativeTabsState: NSObject, UIGestureRecognizerDelegate {
    weak var native: UITabBar?
    let glass = TheseusTabBar(frame: .zero)
    var busy = false
    var queued = false
    var stopRequested = false
    var failed = false
    private(set) var ready = false
    private(set) var active = false
    private var geometry: [NativeButtonGeometry] = []
    private let backgrounds = NSMapTable<UIView, NSNumber>.weakToStrongObjects()
    private var savedColor: UIColor?
    private var colorCaptured = false
    private var itemIDs: [ObjectIdentifier] = []
    private var itemEnabled: [Bool] = []
    private var refreshTimer: Timer?
    private var pan: UIPanGestureRecognizer?
    private var press: UILongPressGestureRecognizer?
    private var didPan = false
    private var generation: UInt64 = 0

    init(_ bar: UITabBar) {
        native = bar
        super.init()
        glass.ngUseHostPosition = true
        glass.ngExcludedBar = bar
        glass.barHeight = 63
        glass.preferredItemWidth = 66
        glass.isUserInteractionEnabled = false
        glass.accessibilityElementsHidden = true
        glass.onItemSelected = { [weak self] index in self?.commitDrag(index) }
    }

    deinit { refreshTimer?.invalidate() }

    func restoreGeometry() {
        UIView.performWithoutAnimation {
            for record in geometry { record.restore() }
            geometry.removeAll()
        }
    }

    private func hideNativeBackgrounds(_ bar: UITabBar, _ views: [UIView]) {
        for view in views {
            if backgrounds.object(forKey: view) == nil || view.layer.opacity != 0 {
                backgrounds.setObject(NSNumber(value: view.layer.opacity), forKey: view)
            }
            view.layer.opacity = 0
        }
        if !colorCaptured || bar.backgroundColor != .clear {
            savedColor = bar.backgroundColor
            colorCaptured = true
        }
        bar.backgroundColor = .clear
    }

    func apply(to bar: UITabBar, buttons: [UIControl], capsule: CGRect) {
        let isNew = glass.superview !== bar
        if isNew {
            generation &+= 1
            let mount = generation
            glass.alpha = 0.02
            glass.ngGlassDidPresent = { [weak self] in
                guard let self, self.generation == mount, !self.ready,
                      let bar = self.native, self.glass.superview === bar else { return }
                self.ready = true
                self.glass.ngGlassDidPresent = nil
                NGSystemTabNote("native-metal-first-frame", bar)
                bar.setNeedsLayout()
            }
            bar.insertSubview(glass, at: 0)
            installGestures(on: bar)
            refreshTimer = Timer(timeInterval: 1.0 / 15, repeats: true) { [weak self] _ in
                MainActor.assumeIsolated {
                    guard let self, self.active, let bar = self.native, bar.window != nil,
                          !bar.isHidden, bar.alpha > 0.01,
                          UIApplication.shared.applicationState == .active else { return }
                    // This timer refreshes only the backdrop; it never changes selection,
                    // destroys the mount, or evaluates transition opacity.
                    self.glass.invalidateBackground()
                }
            }
            if let refreshTimer { RunLoop.main.add(refreshTimer, forMode: .common) }
            DispatchQueue.main.asyncAfter(deadline: .now() + 3) { [weak self] in
                guard let self, self.generation == mount, !self.ready else { return }
                self.failed = true
                self.stop()
                NGSystemTabNote("native-metal-timeout", self.native)
            }
        }
        if !NGSystemTabFrameMatches(glass.ngHostFrame, capsule) { glass.ngApplyHostFrame(capsule) }
        let systemBackgrounds = NGSystemTabBackgrounds(bar)
        glass.ngBindNativeViews(buttons, backgrounds: systemBackgrounds)
        glass.overrideUserInterfaceStyle = bar.traitCollection.userInterfaceStyle
        glass.semanticContentAttribute = bar.effectiveUserInterfaceLayoutDirection == .rightToLeft ? .forceRightToLeft : .forceLeftToRight
        let items = bar.items ?? []
        let ids = items.map { ObjectIdentifier($0) }
        let enabled = items.map { $0.isEnabled }
        if ids != itemIDs || enabled != itemEnabled {
            itemIDs = ids
            itemEnabled = enabled
            // These hidden items supply only slot geometry. Actual icons, labels,
            // badges, accessibility and tap handling stay on the original controls.
            glass.items = items.map {
                var item = TheseusTabBarItem(icon: nil, title: nil)
                item.ngEnabled = $0.isEnabled
                return item
            }
        }
        glass.layoutIfNeeded()
        bar.sendSubviewToBack(glass)
        if ready {
            CATransaction.begin()
            CATransaction.setDisableActions(true)
            hideNativeBackgrounds(bar, systemBackgrounds)
            for (index, button) in buttons.enumerated() {
                let visual = bar.effectiveUserInterfaceLayoutDirection == .rightToLeft ? buttons.count - index - 1 : index
                let record = NativeButtonGeometry(button)
                button.frame = NGSystemTabSlot(capsule, buttons.count, visual)
                record.appliedFrame = button.frame
                geometry.append(record)
            }
            glass.alpha = 1
            CATransaction.commit()
            if !active { NGSystemTabNote("native-mount-active", bar) }
            active = true
        }
        syncSelection()
    }

    func syncSelection() {
        guard let bar = native, let items = bar.items, let selected = bar.selectedItem,
              let index = items.firstIndex(where: { $0 === selected }),
              !glass.ngHostIsInteracting else { return }
        if glass.selectedIndex != index { glass.selectedIndex = index }
    }

    private func installGestures(on bar: UITabBar) {
        let drag = UIPanGestureRecognizer(target: self, action: #selector(dragged(_:)))
        drag.delegate = self
        drag.cancelsTouchesInView = true
        drag.maximumNumberOfTouches = 1
        bar.addGestureRecognizer(drag)
        pan = drag
        let touch = UILongPressGestureRecognizer(target: self, action: #selector(pressed(_:)))
        touch.minimumPressDuration = 0
        touch.allowableMovement = .greatestFiniteMagnitude
        touch.cancelsTouchesInView = false
        touch.delaysTouchesBegan = false
        touch.delaysTouchesEnded = false
        touch.delegate = self
        bar.addGestureRecognizer(touch)
        press = touch
    }

    func gestureRecognizerShouldBegin(_ gesture: UIGestureRecognizer) -> Bool {
        guard active, let bar = native, !bar.isHidden, bar.alpha > 0.01,
              glass.bounds.contains(gesture.location(in: glass)) else { return false }
        if let drag = gesture as? UIPanGestureRecognizer {
            let velocity = drag.velocity(in: bar)
            return abs(velocity.x) > abs(velocity.y)
        }
        return true
    }

    func gestureRecognizer(_ gesture: UIGestureRecognizer, shouldRecognizeSimultaneouslyWith other: UIGestureRecognizer) -> Bool {
        if (gesture === pan && other === press) || (gesture === press && other === pan) { return true }
        // The passive press observer must not prevent UIKit's own button gestures.
        if gesture === press, let bar = native, let view = other.view { return view === bar || view.isDescendant(of: bar) }
        return false
    }

    @objc private func pressed(_ recognizer: UILongPressGestureRecognizer) {
        guard active else { return }
        switch recognizer.state {
        case .began:
            didPan = false
            glass.scriptedTouchBegan(at: recognizer.location(in: glass))
        case .ended:
            if !didPan {
                DispatchQueue.main.async { [weak self] in
                    guard let self, !self.didPan, let bar = self.native,
                          let selected = bar.selectedItem, let items = bar.items,
                          let index = items.firstIndex(where: { $0 === selected }) else { return }
                    self.glass.ngFinishNativePress(index)
                    self.syncSelection()
                }
            }
        case .cancelled, .failed:
            if !didPan { glass.ngCancelNativeInteraction(); syncSelection() }
        default: break
        }
    }

    @objc private func dragged(_ recognizer: UIPanGestureRecognizer) {
        guard active else { return }
        let location = recognizer.location(in: glass)
        switch recognizer.state {
        case .began:
            didPan = true
            if !glass.ngHostIsInteracting { glass.scriptedTouchBegan(at: location) }
            glass.scriptedTouchMoved(to: location, velocity: recognizer.velocity(in: glass))
        case .changed:
            glass.scriptedTouchMoved(to: location, velocity: recognizer.velocity(in: glass))
        case .ended:
            glass.scriptedTouchEnded(at: location)
            syncSelection()
        case .cancelled, .failed:
            glass.ngCancelNativeInteraction()
            syncSelection()
        default: break
        }
    }

    private func commitDrag(_ index: Int) {
        guard active, let bar = native, let items = bar.items, items.indices.contains(index),
              items[index].isEnabled, let buttons = NGSystemTabControls(bar, items.count) else { return }
        // Only a completed horizontal drag reaches this path. Simple taps never do.
        if !NGActivateSystemTabControl(bar, buttons[index]) { NGSystemTabNote("native-drag-rejected", bar) }
        DispatchQueue.main.async { [weak self] in self?.syncSelection() }
    }

    func stop() {
        generation &+= 1
        restoreGeometry()
        refreshTimer?.invalidate()
        refreshTimer = nil
        if let bar = native {
            if let pan { bar.removeGestureRecognizer(pan) }
            if let press { bar.removeGestureRecognizer(press) }
            CATransaction.begin()
            CATransaction.setDisableActions(true)
            for view in backgrounds.keyEnumerator().allObjects.compactMap({ $0 as? UIView }) {
                if view.layer.opacity == 0, let value = backgrounds.object(forKey: view) { view.layer.opacity = value.floatValue }
            }
            if colorCaptured, bar.backgroundColor == .clear { bar.backgroundColor = savedColor }
            CATransaction.commit()
        }
        backgrounds.removeAllObjects()
        savedColor = nil
        colorCaptured = false
        pan = nil
        press = nil
        active = false
        ready = false
        glass.ngGlassDidPresent = nil
        glass.ngCancelNativeInteraction()
        glass.removeFromSuperview()
    }
}

@MainActor @objc(NGSystemTabsBridge) final class SystemTabsBridge: NSObject {
    private static let states = NSMapTable<UITabBar, NativeTabsState>.weakToStrongObjects()

    @objc(beginLayout:) static func beginLayout(_ bar: UITabBar) -> Bool {
        guard !NGSystemTabIsCapturing() else { return false }
        let state: NativeTabsState
        if let previous = states.object(forKey: bar) { state = previous }
        else { state = NativeTabsState(bar); states.setObject(state, forKey: bar) }
        guard !state.busy else { return false }
        state.busy = true
        state.restoreGeometry()
        return true
    }

    @objc(endLayout:) static func endLayout(_ bar: UITabBar) {
        guard let state = states.object(forKey: bar), state.busy else { return }
        defer { state.busy = false }
        guard !state.stopRequested else { state.stopRequested = false; state.stop(); return }
        guard !state.failed, let win = bar.window, !bar.isCustomizing,
              win.traitCollection.userInterfaceIdiom == .phone,
              !UIAccessibility.isVoiceOverRunning, !UIAccessibility.isReduceTransparencyEnabled,
              bar.transform.isIdentity, bar.layer.mask == nil,
              let items = bar.items, (2...5).contains(items.count),
              let buttons = NGSystemTabControls(bar, items.count),
              !NGSystemTabBackgrounds(bar).isEmpty else {
            state.stop(); NGSystemTabNote("native-layout-gate", bar); return
        }
        let box = bar.convert(bar.bounds, to: win)
        let capsule = NGSystemTabCapsule(bar, items.count)
        guard !capsule.isEmpty, box.intersects(win.bounds), abs(box.maxY-win.bounds.maxY) <= 12,
              buttons.allSatisfy({ $0.transform.isIdentity && $0.frame.width >= 30 && $0.frame.height >= 32 }),
              Bundle.hasTabMetalResources, !TheseusSettings.shared.shouldUseFallback,
              UIApplication.shared.isProtectedDataAvailable, MetalContext.shared != nil else {
            state.stop(); NGSystemTabNote("native-geometry-metal-gate", bar); return
        }
        state.apply(to: bar, buttons: buttons, capsule: capsule)
    }

    @objc(detach:) static func detach(_ bar: UITabBar) {
        guard let state = states.object(forKey: bar) else { return }
        if state.busy { state.stopRequested = true; return }
        state.stop()
        states.removeObject(forKey: bar)
    }

    @objc(queueSelection:) static func queueSelection(_ bar: UITabBar) {
        guard let state = states.object(forKey: bar), !state.queued, !NGSystemTabIsCapturing() else { return }
        state.queued = true
        DispatchQueue.main.async { [weak bar, weak state] in
            guard let state else { return }
            state.queued = false
            guard let bar, states.object(forKey: bar) === state, bar.window != nil else { return }
            if state.busy { bar.setNeedsLayout(); return }
            state.syncSelection()
        }
    }
}
