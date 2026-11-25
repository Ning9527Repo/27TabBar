#!/usr/bin/env python3
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
VENDOR = ROOT / 'Vendor/Theseus'


def verify_vendor():
    expected = json.loads((ROOT/'Vendor/manifest.json').read_text())['files']
    actual = {str(p.relative_to(VENDOR)):hashlib.sha256(p.read_bytes()).hexdigest()
              for p in sorted(VENDOR.rglob('*')) if p.is_file()}
    if actual != expected:
        raise SystemExit('Theseus vendor manifest mismatch')


def replace(text, old, new, count=1):
    if text.count(old) != count:
        raise SystemExit(f'Patch anchor mismatch: {old!r}')
    return text.replace(old, new)


def tabbar(s):
    s = replace(s, '    public var selectedIndex: Int = 0 {', '''    weak var ngExcludedBar: UIView?
    private weak var ngPress: UILongPressGestureRecognizer?
    private weak var ngPan: UIPanGestureRecognizer?
    private lazy var ngTap = UITapGestureRecognizer(target: self, action: #selector(ngHandleTap(_:)))
    var ngActivateNative: ((Int) -> Int?)?
    var ngUseHostPosition = false {
        didSet {
            ngTap.isEnabled = ngUseHostPosition
            ngPress?.minimumPressDuration = ngUseHostPosition ? 0.15 : 0
            ngPress?.allowableMovement = ngUseHostPosition ? 10 : .greatestFiniteMagnitude
            backgroundGlassView.ngOpaqueBackdrop = ngUseHostPosition
            selectionView.ngOpaqueBackdrop = ngUseHostPosition
        }
    }

    @objc private func ngHandleTap(_ gesture: UITapGestureRecognizer) {
        guard gesture.state == .ended, !slotFrames.isEmpty else { return }
        selectItem(at: findClosestItemIndex(to: gesture.location(in: contentView)))
    }

    var ngHostFrame = CGRect.zero
    var ngGlassDidPresent: (() -> Void)? {
        didSet { backgroundGlassView.onPresent = ngGlassDidPresent }
    }

    func ngPrepareReplacement() {
        backgroundGlassView.ngPrepareReplacement()
        selectionView.ngPrepareReplacement()
    }

    var ngHostIsInteracting: Bool { isDragging || isCollapsingLens }

    private var ngRefreshingItems = false

    func ngRefreshItems(_ refreshed: [TheseusTabBarItem], changed: [Int]) {
        guard itemViews.count == refreshed.count else { items = refreshed; return }
        ngRefreshingItems = true
        items = refreshed
        ngRefreshingItems = false
        for i in changed {
            let selected = i == selectedIndex
            itemViews[i].configure(with: items[i], isSelected: selected)
            itemViews[i].tintColor = selected ? (appliedRestingTint ?? selectedTintColor) : unselectedTint()
        }
    }

    func ngApplySelection(_ index: Int) {
        guard index != selectedIndex else { return }
        if isCollapsingLens { endDragImmediately() }
        selectedIndex = index
    }

    func ngApplyHostFrame(_ next: CGRect) {
        if isDragging { endDragImmediately() }
        ngHostFrame = next
        frame = next
        setNeedsLayout()
        invalidateBackground()
    }

    public var selectedIndex: Int = 0 {''')
    s = replace(s, '    public var title: String?\n', '''    public var title: String?
    var ngBadge: String?
    var ngBadgeColor: UIColor?
    var ngLabel: String?
    var ngEnabled = true
''')
    s = replace(s, '            rebuildItemViews()\n            setNeedsLayout()', '            guard !ngRefreshingItems else { return }\n            rebuildItemViews()\n            setNeedsLayout()')
    s = replace(s, '        let contentWidth = min(bounds.width,', '        if ngUseHostPosition { return bounds }\n        let contentWidth = min(bounds.width,')
    s = replace(s, '        let size = pillSize\n', '''        if ngUseHostPosition {
            return NGTabPresentation.capsule(slot: itemFrame, platter: backgroundView.frame,
                                             itemInset: barContentInset)
        }
        let size = pillSize
''')
    s = replace(s, '        let size = usesIOS26Look ? Self.iOS26LensSize : Self.lensSize\n', '''        let base = usesIOS26Look ? Self.iOS26LensSize : Self.lensSize
        let size = CGSize(width: ngUseHostPosition ? max(base.width, max(pillSize.width, itemFrame.width - 4) + 16) : base.width,
                          height: base.height)
''')
    s = replace(s, '        pressGesture.minimumPressDuration = 0', '        pressGesture.minimumPressDuration = 0\n        ngPress = pressGesture')
    s = replace(s, '        addGestureRecognizer(panGesture)', '''        addGestureRecognizer(panGesture)
        ngPan = panGesture
        ngTap.isEnabled = ngUseHostPosition
        ngTap.delegate = self
        ngTap.require(toFail: pressGesture)
        ngTap.require(toFail: panGesture)
        addGestureRecognizer(ngTap)
''')
    s = replace(s, '            UIView.animate(withDuration: 0.22, delay: 0, usingSpringWithDamping: 0.88, initialSpringVelocity: 0.75) {', '''            let options: UIView.AnimationOptions = ngUseHostPosition ? [.beginFromCurrentState, .allowUserInteraction] : []
            UIView.animate(withDuration: 0.22, delay: 0, usingSpringWithDamping: 0.88,
                           initialSpringVelocity: 0.75, options: options) {
'''.rstrip('\n'))
    s = replace(s, '    private func selectItem(at index: Int) {\n', '''    private func selectItem(at index: Int) {
        if ngUseHostPosition {
            guard items.indices.contains(index), items[index].ngEnabled,
                  let confirmed = ngActivateNative?(index), items.indices.contains(confirmed) else { return }
            if isCollapsingLens, confirmed != selectedIndex { endDragImmediately() }
            selectedIndex = confirmed
            return
        }
''')
    s = replace(s, '        guard index != selectedIndex else { return }\n        selectedIndex = index', '        guard items.indices.contains(index), items[index].ngEnabled, index != selectedIndex else { return }\n        selectedIndex = index')
    s = replace(s, '        guard let pan = gestureRecognizer as? UIPanGestureRecognizer,', '''        if ngUseHostPosition, gestureRecognizer === ngTap { return !slotFrames.isEmpty && !isDragging }
        if ngUseHostPosition, let pan = gestureRecognizer as? UIPanGestureRecognizer, pan === ngPan {
            let velocity = pan.velocity(in: self)
            return !slotFrames.isEmpty && abs(velocity.x) > abs(velocity.y)
        }
        guard let pan = gestureRecognizer as? UIPanGestureRecognizer,
'''.rstrip('\n'))
    s = replace(s, '        super.layoutSubviews()\n\n        contentView.bounds = bounds', '''        super.layoutSubviews()

        let exclusions = [self, ngExcludedBar].compactMap { $0 }
        backgroundGlassView.setCaptureExcludedViews(exclusions)
        selectionView.setCaptureExcludedViews(exclusions)
        if let bar = ngExcludedBar { theseusView?.setCaptureExcludedViews([bar]) }
        contentView.bounds = bounds''')
    s = replace(s, '            CGRect(x: barFrame.minX + CGFloat(index) * itemWidth, y: 0, width: itemWidth, height: itemHeight)', '''            let rtl = ngUseHostPosition && effectiveUserInterfaceLayoutDirection == .rightToLeft
            let slot = rtl ? itemViews.count - index - 1 : index
            return CGRect(x: barFrame.minX + CGFloat(slot) * itemWidth, y: 0, width: itemWidth, height: itemHeight)''')
    s = replace(s, '        theseusSourceView?.superview\n', '        ngUseHostPosition ? self : theseusSourceView?.superview\n')
    s = replace(s, '        glassView.sourceView = sourceView\n        glassView.isHidden', '        glassView.sourceView = sourceView\n        if let bar = ngExcludedBar { glassView.setCaptureExcludedViews([bar]) }\n        glassView.isHidden')
    s = replace(s, '        case .ended, .cancelled, .failed:\n            finishInteraction(rawX: gesture.location(in: self).x)', '''        case .ended:
            finishInteraction(rawX: gesture.location(in: self).x)
        case .cancelled, .failed:
            if isDragging { endDragImmediately() }''')
    s = replace(s, '        case .ended, .cancelled:\n            finishInteraction(rawX: gesture.location(in: self).x)', '''        case .ended:
            finishInteraction(rawX: gesture.location(in: self).x)
        case .cancelled, .failed:
            if isDragging { endDragImmediately() }''')
    s = replace(s, '''        if landingIndex != selectedIndex {
            isCommittingDrag = true
            selectedIndex = landingIndex
            isCommittingDrag = false
            onItemSelected?(landingIndex)
        }''', '''        if items.indices.contains(landingIndex), items[landingIndex].ngEnabled {
            if ngUseHostPosition {
                if let confirmed = ngActivateNative?(landingIndex), items.indices.contains(confirmed) {
                    isCommittingDrag = true
                    selectedIndex = confirmed
                    isCommittingDrag = false
                }
            } else if landingIndex != selectedIndex {
                isCommittingDrag = true
                selectedIndex = landingIndex
                isCommittingDrag = false
                onItemSelected?(landingIndex)
            }
        }''')
    s = replace(s, '            currentDragVelocity = gesture.velocity(in: self)\n', '''            currentDragVelocity = gesture.velocity(in: self)
            if ngUseHostPosition { followFinger(at: gesture.location(in: self)) }
''')
    s = replace(s, '        gestureRecognizer.view === self && otherGestureRecognizer.view === self',
                '        !ngUseHostPosition && gestureRecognizer.view === self && otherGestureRecognizer.view === self')
    s = replace(s, '        glassView.layer.transform = CATransform3DIdentity\n        let releaseFrame = glassView.frame.insetBy(dx: glassView.shape.widthInset, dy: glassView.shape.heightInset)', '''        let displayedFrame = glassView.layer.frame
        let scaleX = displayedFrame.width / max(glassView.bounds.width, 1)
        let scaleY = displayedFrame.height / max(glassView.bounds.height, 1)
        let releaseFrame = displayedFrame.insetBy(dx: glassView.shape.widthInset * scaleX,
                                                  dy: glassView.shape.heightInset * scaleY)
        glassView.layer.transform = CATransform3DIdentity''')
    s = replace(s, '        if glassView.shape.widthInset != 0 || glassView.shape.heightInset != 0 {\n            glassView.frame = releaseFrame',
                '        if glassView.frame != releaseFrame || glassView.shape.widthInset != 0 || glassView.shape.heightInset != 0 {\n            glassView.frame = releaseFrame')
    s = replace(s, '            if landingIndex < self.slotFrames.count {\n                animator?.retarget(to: self.convertToTheseusContainer(self.selectionFrame(for: self.slotFrame(at: landingIndex))))', '''            let target = self.ngUseHostPosition ? self.selectedIndex : landingIndex
            if self.slotFrames.indices.contains(target) {
                animator?.retarget(to: self.convertToTheseusContainer(self.selectionFrame(for: self.slotFrame(at: target))))''')
    s = replace(s, '        NSLayoutConstraint.activate([\n            stackView.centerXAnchor', '        NSLayoutConstraint.activate([\n            stackView.widthAnchor.constraint(lessThanOrEqualTo: widthAnchor, constant: -4),\n            stackView.centerXAnchor')
    s = replace(s, '    private let captureTitleView = UIImageView()', '''    private let captureTitleView = UIImageView()
    private let ngBadgeLabel = UILabel()
    private let ngTwinBadge = UILabel()

    private func ngLayoutBadge(_ label: UILabel, beside icon: CGRect, width: CGFloat) {
        guard !label.isHidden else { return }
        let textWidth: CGFloat = label.sizeThatFits(CGSize(width: CGFloat.greatestFiniteMagnitude, height: CGFloat(16))).width
        let w: CGFloat = min(max(16, textWidth + 8), max(16, width - 4))
        let end: CGFloat = min(width - 1, icon.midX + 9 + w / 2)
        label.frame = CGRect(x: max(0, end - w), y: max(0, icon.minY - 2), width: w, height: 16)
    }''')
    s = replace(s, '        captureTwin.addSubview(captureTitleView)', '''        captureTwin.addSubview(captureTitleView)
        for label in [ngBadgeLabel, ngTwinBadge] {
            label.font = .systemFont(ofSize: 10, weight: .semibold)
            label.textAlignment = .center
            label.textColor = .white
            label.layer.cornerRadius = 8
            label.clipsToBounds = true
            label.isHidden = true
            label.isAccessibilityElement = false
        }
        addSubview(ngBadgeLabel)
        captureTwin.addSubview(ngTwinBadge)''')
    s = replace(s, '        iconImageView.transform = transform\n', '        iconImageView.transform = transform\n        ngLayoutBadge(ngBadgeLabel, beside: iconImageView.frame, width: bounds.width)\n')
    s = replace(s, '        accessibilityLabel = item.title ?? item.icon?.accessibilityLabel', '''        accessibilityLabel = item.ngLabel ?? item.title ?? item.icon?.accessibilityLabel
        accessibilityValue = item.ngBadge
        let hasBadge = item.ngBadge?.isEmpty == false
        for label in [ngBadgeLabel, ngTwinBadge] {
            label.text = item.ngBadge
            label.backgroundColor = item.ngBadgeColor ?? .systemRed
            label.isHidden = !hasBadge
        }
        alpha = item.ngEnabled ? 1 : 0.48''')
    s = replace(s, '        captureTitleView.isHidden = titleLabel.isHidden\n', '''        captureTitleView.isHidden = titleLabel.isHidden
        ngLayoutBadge(ngTwinBadge, beside: captureIconView.frame, width: captureTwin.bounds.width)
''')
    s = replace(s, '        return image.withRenderingMode(.alwaysTemplate)\n', '        return image.renderingMode == .alwaysOriginal ? image : image.withRenderingMode(.alwaysTemplate)\n')
    s = replace(s, '        let bitmap = UIGraphicsImageRenderer(size: image.size, format: format).image { _ in\n', '        if image.renderingMode == .alwaysOriginal { return image }\n        let bitmap = UIGraphicsImageRenderer(size: image.size, format: format).image { _ in\n')
    return s


def renderer(s):
    s = replace(s, '        let viewFrame = metalLayer.frame\n', '        let viewFrame = hostView?.bounds ?? metalLayer.frame\n')
    s = replace(s, '              let superlayer = metalLayer.superlayer else {',
                '              let superlayer = hostView?.layer ?? metalLayer.superlayer else {')
    s = replace(s, '                    excludedViews: excludedViews\n', '''                    excludedViews: excludedViews,\n                    opaqueBackdrop: (hostView as? TheseusView)?.ngOpaqueBackdrop == true\n'''.rstrip('\n') + '\n', count=2)
    s = replace(s, '        willCapture?()\n        defer { didCapture?() }', '        NGSystemTabCaptureBegin()\n        willCapture?()\n        defer { didCapture?(); NGSystemTabCaptureEnd() }')
    return replace(s, '            commandBuffer.addCompletedHandler { _ in\n                DispatchQueue.main.async(execute: onPresent)', '            commandBuffer.addCompletedHandler { buffer in\n                guard buffer.status == .completed else { return }\n                DispatchQueue.main.async(execute: onPresent)')


def surface(s):
    s = replace(s, '    public var onPresent: (() -> Void)? {\n        didSet { renderer?.onPresent = onPresent }\n    }', '''    var ngOpaqueBackdrop = false
    private var ngWaitingForPresent = false
    private var ngPresented = false

    func ngPrepareReplacement() {
        ngWaitingForPresent = !ngPresented
        guard ngWaitingForPresent else { return }
        if fallbackView == nil {
            let fallback = VisualEffectFallbackView()
            fallback.isUserInteractionEnabled = false
            fallback.autoresizingMask = [.flexibleWidth, .flexibleHeight]
            fallback.frame = bounds
            insertSubview(fallback, at: 0)
            fallbackView = fallback
        }
        fallbackView?.configure(with: configuration)
        fallbackView?.updateForTraitCollection(traitCollection)
        fallbackView?.isHidden = false
        ngConfigurePresentCallback()
    }

    private func ngConfigurePresentCallback() {
        if ngWaitingForPresent || onPresent != nil {
            renderer?.onPresent = { [weak self] in self?.ngFramePresented() }
        } else { renderer?.onPresent = nil }
    }

    private func ngFramePresented() {
        ngPresented = true
        ngWaitingForPresent = false
        if !isUsingFallback { fallbackView?.isHidden = true }
        onPresent?()
        ngConfigurePresentCallback()
    }

    public var onPresent: (() -> Void)? {
        didSet { ngConfigurePresentCallback() }
    }''')
    s = replace(s, '        renderer?.onPresent = onPresent\n', '        ngConfigurePresentCallback()\n')
    s = replace(s, '            fallbackView?.isHidden = true\n\n            metalLayerView?.isHidden = false', '            fallbackView?.isHidden = !ngWaitingForPresent\n\n            metalLayerView?.isHidden = false')
    # Match drawable geometry to the padded Metal texture. Keep the shader's
    # logical host bounds and account for padding exactly once in capture.
    s = replace(s, '        return (metalLayerView?.frame ?? bounds).insetBy(dx: -padding.x, dy: -padding.y)', '        return bounds.insetBy(dx: -padding.x, dy: -padding.y)')
    s = replace(s, '        metalLayer.contentsGravity = .center', '        metalLayer.contentsGravity = .resize')
    return replace(s, '        let paddingX = padding.x * scale\n', '        metalLayerView?.frame = bounds.insetBy(dx: -padding.x, dy: -padding.y)\n        let paddingX = padding.x * scale\n')


def opaque_capture(s, rect):
    s = replace(s, '        excludedViews: [UIView] = []\n',
                '        excludedViews: [UIView] = [],\n        opaqueBackdrop: Bool = false\n')
    line = '        ctx.clear(' + rect + ')\n'
    return replace(s, line, line + '''        if opaqueBackdrop {
            ctx.setFillColor(UIColor.systemBackground.resolvedColor(with: sourceView.traitCollection).cgColor)
            ctx.fill(''' + rect + ''')
        }
''')


def compensation(s):
    return replace(s, '                glass.backgroundColor = glass.captureVeilColor', '''                let layer = CALayer()
                layer.frame = glass.bounds.insetBy(dx: glass.shape.widthInset, dy: glass.shape.heightInset)
                layer.cornerRadius = min(glass.shape.cornerRadius, min(layer.bounds.width, layer.bounds.height) / 2)
                layer.backgroundColor = glass.captureVeilColor.cgColor
                glass.layer.insertSublayer(layer, above: host.layer)
                entry.snapshotLayer = layer''')


def tab_frame_policy(s):
    s = replace(s, '            backgroundGlassView.ngOpaqueBackdrop = ngUseHostPosition\n            selectionView.ngOpaqueBackdrop = ngUseHostPosition', '''            backgroundGlassView.ngOpaqueBackdrop = ngUseHostPosition
            selectionView.ngOpaqueBackdrop = ngUseHostPosition
            backgroundGlassView.refraction.interiorSharpness = ngChromeDetail
            selectionView.refraction.interiorSharpness = ngUseHostPosition ? 0.06 : Self.pillDetail''')
    s = replace(s, '    var ngHostIsInteracting: Bool { isDragging || isCollapsingLens }', '''    var ngHostIsInteracting: Bool { isDragging || isCollapsingLens }
    private var ngFollowStart: CGFloat?
    private var ngFingerFrame: CGRect?

    private var ngChromeDetail: CGFloat {
        if ngUseHostPosition { return isDarkAppearance ? 0.08 : 0.10 }
        return isDarkAppearance ? Self.chromeDetailDark : Self.chromeDetailLight
    }

    private func ngInvalidatePageFrames(after delay: TimeInterval) {
        backgroundGlassView.ngInvalidateBackdrop(after: delay)
        selectionView.ngInvalidateBackdrop(after: delay)
        if let lens = theseusView, !lens.isHidden {
            lens.ngInvalidateBackdrop(after: 0.04)
        }
    }''')
    s = replace(s, '        if isCollapsingLens { endDragImmediately() }\n        selectedIndex = index', '''        if isCollapsingLens { endDragImmediately() }
        ngInvalidatePageFrames(after: 0.24)
        selectedIndex = index''')
    s = replace(s, '            if isCollapsingLens, confirmed != selectedIndex { endDragImmediately() }\n            selectedIndex = confirmed', '            ngApplySelection(confirmed)')
    s = replace(s, '                    isCommittingDrag = true\n                    selectedIndex = confirmed', '''                    if confirmed != selectedIndex { ngInvalidatePageFrames(after: 0.15) }
                    isCommittingDrag = true
                    selectedIndex = confirmed''')
    s = replace(s, 'backgroundGlassView.configuration.refraction.interiorSharpness = isDark ? Self.chromeDetailDark : Self.chromeDetailLight',
                'backgroundGlassView.configuration.refraction.interiorSharpness = ngChromeDetail')
    s = replace(s, '        glassView.sourceView = sourceView\n        if let bar = ngExcludedBar', '''        glassView.sourceView = sourceView
        glassView.ngInteractiveLens = ngUseHostPosition
        if let bar = ngExcludedBar''')
    s = replace(s, '        if let sourceView = theseusSourceView, sourceView.bounds.width > 0 {',
                '        if let sourceView = theseusSourceView, sourceView.bounds.width > 0, glassView.sourceView !== sourceView {')
    s = replace(s, '        var lastFrame = startFrame', '''        var lastFrame = startFrame
        if ngUseHostPosition { glassView.ngInvalidateBackdrop(after: 0) }''')
    s = replace(s, '            lastFrame = frame\n            glassView.layer.transform = self.stretched', '''            var frame = frame
            if let finger = self.ngFingerFrame {
                let target = self.convertToTheseusContainer(finger)
                frame = frame.offsetBy(dx: target.midX - frame.midX, dy: target.midY - frame.midY)
            }
            lastFrame = frame
            glassView.layer.transform = self.stretched''')
    s = replace(s, '        showTheseus()\n        startLensActivity()', '''        ngFollowStart = nil
        ngFingerFrame = nil
        showTheseus()
        startLensActivity()''')
    s = replace(s, '        selectionAnimator?.follow(x: location.x + fingerAnchorOffset, at: time)', '''        if ngUseHostPosition {
            guard isDragging, let frame = calculateInterpolatedFrame(for: CGPoint(x: location.x + fingerAnchorOffset, y: 0)) else { return }
            if ngFollowStart == nil {
                ngFollowStart = location.x
                lensMorphAnimator?.retarget(to: convertToTheseusContainer(frame))
            } else if ngFingerFrame != nil || abs(location.x - (ngFollowStart ?? location.x)) >= 1 {
                ngFingerFrame = frame
                // The grow animation owns size; the finger owns the center independently.
                if lensMorphAnimator?.isRunning == true, let lens = theseusView {
                    var transform = lens.layer.transform
                    let target = convertToTheseusContainer(frame)
                    transform.m41 += target.midX - lens.layer.frame.midX
                    transform.m42 += target.midY - lens.layer.frame.midY
                    lens.layer.transform = transform
                }
                selectionAnimator?.onFrameChanged?(frame)
            }
        } else {
            selectionAnimator?.follow(x: location.x + fingerAnchorOffset, at: time)
        }''')
    s = replace(s, '        isDragging = false\n        hoveredIndex = -1\n        currentDragVelocity = .zero\n        flexSpreadDriver.stop()',
                '        isDragging = false\n        ngFingerFrame = nil\n        hoveredIndex = -1\n        currentDragVelocity = .zero\n        flexSpreadDriver.stop()')
    s = replace(s, '        if changed {\n            backgroundGlassView.invalidateBackground()\n        }',
                '        if changed && !(ngUseHostPosition && isDragging) {\n            backgroundGlassView.invalidateBackground()\n        }')
    return s


def renderer_frame_policy(s):
    s = replace(s, '    var continuousUpdate: Bool = false {', '''    var ngInteractiveLens = false
    var ngCaptureNotBefore: CFTimeInterval = 0
    private var ngLastCapture: CFTimeInterval = -.infinity

    var continuousUpdate: Bool = false {''')
    s = replace(s, 'metalLayer?.presentsWithTransaction = continuousUpdate',
                'metalLayer?.presentsWithTransaction = continuousUpdate && !ngInteractiveLens')
    s = replace(s, '        guard shouldRender() else { return }', '''        guard shouldRender() else { return }
        let now = CACurrentMediaTime()
        guard now >= ngCaptureNotBefore,
              !ngInteractiveLens || now - ngLastCapture >= 1.0 / 30.0 - 0.001 else { return }''')
    s = replace(s, '        frameCounter += 1', '        ngLastCapture = now\n        frameCounter += 1')
    s = replace(s, '        let renderScale = currentRefractionQuality.renderScale',
                '        let renderScale = ngInteractiveLens ? min(currentRefractionQuality.renderScale, 0.5) : currentRefractionQuality.renderScale')
    s = replace(s, 'guard framesInFlight < Self.maxFramesInFlight else { return }',
                'guard framesInFlight < (ngInteractiveLens ? 1 : Self.maxFramesInFlight) else { return }')
    s = replace(s, '        isRendering = true\n        markAllFramesCompleted()',
                '        isRendering = true\n        if !ngInteractiveLens { markAllFramesCompleted() }')
    s = replace(s, '        waitForGPUCompletion()\n        markAllFramesCompleted()', '''        // A lens can be reopened while its prior frame drains. Keep that frame
        // counted so the next session cannot reuse textures still on the GPU.
        if !ngInteractiveLens {
            waitForGPUCompletion()
            markAllFramesCompleted()
        }''')
    s = replace(s, 'set { frameCounterLock.withLock { _lastCompletedFrame = newValue } }',
                'set { frameCounterLock.withLock { _lastCompletedFrame = max(_lastCompletedFrame, newValue) } }')
    return replace(s, '        commandBuffer.addCompletedHandler { [weak self] _ in\n            guard let image = Self.image(from: snapshot) else { return }\n            DispatchQueue.main.async { self?.onSnapshot?(image) }', '''        let onSnapshot = self.onSnapshot
        commandBuffer.addCompletedHandler { buffer in
            guard buffer.status == .completed, let image = Self.image(from: snapshot) else { return }
            DispatchQueue.main.async { onSnapshot?(image) }''')


def surface_frame_policy(s):
    s = replace(s, '    private var ngPresented = false', '''    private var ngPresented = false
    private var ngBackdropEpoch: UInt64 = 0
    private var ngCaptureNotBefore: CFTimeInterval = 0
    var ngInteractiveLens = false

    func ngInvalidateBackdrop(after delay: TimeInterval) {
        ngBackdropEpoch &+= 1
        ngCaptureNotBefore = CACurrentMediaTime() + delay
        ngPresented = false
        captureSnapshot = nil
        captureSnapshotOverride = nil
        ngPrepareReplacement()
        renderer?.ngCaptureNotBefore = ngCaptureNotBefore
        applySnapshotSetting()
        renderer?.setNeedsRender()
    }''')
    s = replace(s, '        fallbackView?.isHidden = false\n        ngConfigurePresentCallback()', '''        fallbackView?.isHidden = false
        // Keep acquiring drawables while masking the stale texture on screen.
        if ngOpaqueBackdrop || ngInteractiveLens {
            metalLayerView?.alpha = 0
            fallbackView?.ngSetBackdropBlur()
        }
        ngConfigurePresentCallback()''')
    s = replace(s, '            renderer?.onPresent = { [weak self] in self?.ngFramePresented() }', '''            let epoch = ngBackdropEpoch
            renderer?.onPresent = { [weak self] in
                guard let self, self.ngBackdropEpoch == epoch, !self.isUsingFallback else { return }
                self.ngFramePresented()
            }''')
    s = replace(s, '        if !isUsingFallback { fallbackView?.isHidden = true }', '''        if !isUsingFallback {
            UIView.performWithoutAnimation {
                metalLayerView?.alpha = 1
                fallbackView?.isHidden = true
            }
        }''')
    s = replace(s, '        renderer?.onSnapshot = providesCaptureSnapshot ? { [weak self] image in\n            self?.captureSnapshot = image\n            self?.snapshotDidUpdate?()', '''        let epoch = ngBackdropEpoch
        renderer?.onSnapshot = providesCaptureSnapshot ? { [weak self] image in
            guard let self, self.ngBackdropEpoch == epoch else { return }
            self.captureSnapshot = image
            self.snapshotDidUpdate?()''')
    s = replace(s, '        renderer?.hostView = self\n        renderer?.configuration', '''        renderer?.hostView = self
        renderer?.ngInteractiveLens = ngInteractiveLens
        renderer?.ngCaptureNotBefore = ngCaptureNotBefore
        renderer?.configuration''')
    s = replace(s, '            fallbackView?.configure(with: configuration)\n            fallbackView?.updateForTraitCollection(traitCollection)', '''            fallbackView?.configure(with: configuration)
            if ngOpaqueBackdrop || ngInteractiveLens { fallbackView?.ngSetBackdropBlur() }
            fallbackView?.updateForTraitCollection(traitCollection)''')
    return s


def fallback_frame_policy(s):
    s = replace(s, '    private var lastConfiguration: TheseusConfiguration?', '''    func ngSetBackdropBlur() { blurView.alpha = 1 }

    private var lastConfiguration: TheseusConfiguration?''')
    return replace(s, '        cornerRadius = config.shape.cornerRadius', '        cornerRadius = abs(config.shape.cornerRadius)')


def stage(dst):
    verify_vendor()
    patches = {'TheseusTabBar.swift':lambda s: tab_frame_policy(tabbar(s)),
               'TheseusRenderer.swift':lambda s: renderer_frame_policy(renderer(s)),
               'TheseusView.swift':lambda s: surface_frame_policy(surface(s)),
               'VisualEffectFallback.swift':fallback_frame_policy,'CaptureCompensation.swift':compensation,
               'BackgroundCaptureDraw.swift':lambda s: opaque_capture(s, 'CGRect(x: 0, y: 0, width: width, height: height)'),
               'ViewLayerCapture.swift':lambda s: opaque_capture(s, 'CGRect(x: 0, y: 0, width: pixelWidth, height: pixelHeight)')}
    dst.mkdir(parents=True,exist_ok=True)
    for p in sorted((VENDOR/'Sources/Theseus').rglob('*.swift')):
        s = p.read_text()
        if p.name in patches:
            s = patches[p.name](s)
        (dst/p.name).write_text(s)
    if len(list(dst.glob('*.swift'))) != 33:
        raise SystemExit('Unexpected Swift source count')


if __name__ == '__main__':
    stage(Path(sys.argv[1]))
