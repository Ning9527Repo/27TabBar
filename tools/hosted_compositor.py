"""Hosted tab bars use one persistent blur and one opaque, movable pill."""


def tab(s, rep):
    s = rep(s, '    private func ngSyncPlatterHold() {\n        if ngUseHostPosition { backgroundGlassView.ngHoldBackdrop(ngHostIsInteracting) }\n    }', '''    private lazy var ngHostedPlatter = UIVisualEffectView(effect: UIBlurEffect(style: .systemChromeMaterialLight))
    private var ngHostedDragTarget = CGRect.zero
    private var ngHostedPressX: CGFloat = 0
    private var ngHostedDirectDrag = false

    private func ngInstallHostedChrome() {
        // Use one fixed light blur plus an independently tinted surface. The
        // blur is never rebuilt or retargeted when the host's traits change.
        backgroundGlassView.snapshotDidUpdate = nil
        backgroundGlassView.providesCaptureSnapshot = false
        backgroundGlassView.pauseRendering()
        backgroundGlassView.removeFromSuperview()
        resetAdaptation()
        contentView.overrideUserInterfaceStyle = .unspecified
        selectionView.ngEnableSolidSelection()
        pillShadeLayer.removeFromSuperlayer()
        ngHostedPlatter.overrideUserInterfaceStyle = .light
        ngHostedPlatter.isUserInteractionEnabled = false
        ngHostedPlatter.clipsToBounds = true
        backgroundView.insertSubview(ngHostedPlatter, at: 0)
        ngApplyHostedAppearance(animated: false)
    }

    private func ngSetHostedColor(_ color: CGColor, on target: CALayer, key: String, animated: Bool) {
        let old: CGColor? = key == "borderColor" ? target.borderColor : target.backgroundColor
        guard old != color else { return }
        let live = target.presentation()
        let shown = (key == "borderColor" ? live?.borderColor : live?.backgroundColor) ?? old
        target.removeAnimation(forKey: "ngHosted." + key)
        if key == "borderColor" { target.borderColor = color }
        else { target.backgroundColor = color }
        if animated, let shown {
            let fade = CABasicAnimation(keyPath: key)
            fade.fromValue = shown
            fade.toValue = color
            fade.duration = NGTabPresentation.appearanceDuration
            fade.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            target.add(fade, forKey: "ngHosted." + key)
        }
    }

    private func ngApplyHostedAppearance(animated: Bool) {
        let dark = systemIsDark
        let reduce = UIAccessibility.isReduceTransparencyEnabled
        let tint = UIColor(white: dark ? 0.04 : 1, alpha: reduce ? 1 : (dark ? 0.76 : 0.22))
        let animate = animated && window != nil && !UIAccessibility.isReduceMotionEnabled
            && TheseusSettings.shared.areMorphAnimationsEnabled
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        ngAnimateAppearance = animate
        adaptDarkWeight = dark ? 1 : 0
        adaptDarkTarget = adaptDarkWeight
        ngSetHostedColor(tint.cgColor, on: ngHostedPlatter.contentView.layer, key: "backgroundColor", animated: animate)
        selectionView.ngSetSolidSelectionTone(dark: dark, animated: animate)
        // Keep one opaque selection surface; the old simultaneous lens/pill
        // compositing and its second outline are not used in hosted gestures.
        selectionView.layer.borderWidth = 0
        selectionView.layer.borderColor = nil
        updateEdgeLayers(rebuildCapture: false)
        updateBarShadow()
        applyItemTints(selectedAt: selectedIndex, animated: animate)
        ngAnimateAppearance = false
        CATransaction.commit()
    }

    private func ngPlaceHostedPill(_ rect: CGRect) {
        guard rect.width > 0, rect.height > 0, rect.midX.isFinite, rect.midY.isFinite else { return }
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        selectionView.bounds = CGRect(origin: .zero, size: rect.size)
        selectionView.center = CGPoint(x: rect.midX, y: rect.midY)
        let radius = min(rect.width, rect.height) / 2
        if selectionView.shape.cornerRadius != radius { selectionView.shape.cornerRadius = radius }
        selectionView.layer.cornerRadius = radius
        CATransaction.commit()
    }

    private func ngStopHostedPillMotion() {
        lensMorphAnimator?.cancel()
        for key in ["position", "position.x", "position.y", "bounds", "bounds.size", "transform"] {
            selectionView.layer.removeAnimation(forKey: key)
        }
    }

    private func ngBeginHostedDrag(at x: CGFloat) {
        guard !isDragging, isUserInteractionEnabled, x.isFinite, slotFrames.indices.contains(selectedIndex) else { return }
        let pressed = findClosestItemIndex(to: CGPoint(x: x, y: 0))
        guard slotFrames.indices.contains(pressed), items.indices.contains(pressed), items[pressed].ngEnabled else { return }
        let shown = selectionView.layer.presentation()?.frame ?? selectionView.frame
        let target = glassFrame(for: slotFrames[pressed])
        let from = shown.isEmpty ? selectionFrame(for: slotFrames[selectedIndex]) : shown
        ngStopHostedPillMotion()
        isCollapsingLens = false
        isDragging = true
        ngHostedDragTarget = target
        ngHostedPressX = x
        ngHostedDirectDrag = false
        fingerAnchorOffset = target.midX - x
        ngPlaceHostedPill(from)
        if UIAccessibility.isReduceMotionEnabled {
            ngPlaceHostedPill(target)
            return
        }
        let animator = LensMorphAnimator()
        lensMorphAnimator = animator
        animator.morph(from: from, to: target, spring: Self.lensGrowSpring, onTick: { [weak self] rect, _ in
            guard let self, self.isDragging else { return }
            let center = self.ngHostedDragTarget.midX
            self.ngPlaceHostedPill(self.ngHostedDirectDrag ? rect.offsetBy(dx: center - rect.midX, dy: 0) : rect)
        }, onComplete: { [weak self] in
            guard let self, self.isDragging else { return }
            self.ngPlaceHostedPill(self.ngHostedDragTarget)
        })
    }

    private func ngMoveHostedDrag(to x: CGFloat) {
        guard isDragging, x.isFinite,
              let left = slotFrames.map(\\.midX).min(), let right = slotFrames.map(\\.midX).max() else { return }
        if abs(x - ngHostedPressX) >= 0.5 { ngHostedDirectDrag = true }
        guard ngHostedDirectDrag else { return }
        let center = min(max(x + fingerAnchorOffset, left - Self.lensOverrun), right + Self.lensOverrun)
        ngHostedDragTarget.origin.x = center - ngHostedDragTarget.width / 2
        let rect = selectionView.frame
        ngPlaceHostedPill(rect.offsetBy(dx: center - rect.midX, dy: 0))
    }

    private func ngFinishHostedDrag(at x: CGFloat) {
        guard isDragging else { return }
        ngMoveHostedDrag(to: x)
        let shown = selectionView.frame
        ngStopHostedPillMotion()
        isCollapsingLens = true
        isDragging = false
        let target = findClosestItemIndex(to: CGPoint(x: ngHostedDragTarget.midX, y: 0))
        if items.indices.contains(target), items[target].ngEnabled,
           let confirmed = ngActivateNative?(target), items.indices.contains(confirmed), confirmed != selectedIndex {
            isCommittingDrag = true
            selectedIndex = confirmed
            isCommittingDrag = false
            applyItemTints(selectedAt: confirmed, animated: false)
        }
        guard slotFrames.indices.contains(selectedIndex) else { isCollapsingLens = false; return }
        let landing = selectionFrame(for: slotFrames[selectedIndex])
        if UIAccessibility.isReduceMotionEnabled {
            ngPlaceHostedPill(landing)
            isCollapsingLens = false
            return
        }
        let animator = LensMorphAnimator()
        lensMorphAnimator = animator
        animator.morph(from: shown, to: landing, spring: Self.lensShrinkSpring, onTick: { [weak self] rect, _ in
            self?.ngPlaceHostedPill(rect)
        }, onComplete: { [weak self] in
            guard let self else { return }
            self.ngPlaceHostedPill(landing)
            self.isCollapsingLens = false
        })
    }

    private func ngCancelHostedDrag(restore: Bool = true) {
        ngStopHostedPillMotion()
        ngGestureGate.clear()
        isDragging = false
        isCollapsingLens = false
        if restore, slotFrames.indices.contains(selectedIndex) {
            ngPlaceHostedPill(selectionFrame(for: slotFrames[selectedIndex]))
        }
    }''')
    # Keep the upstream renderer available for a non-hosted bar, but the
    # installed system-bar replacement never enters those render paths.
    # Only the pill may grow/translate. Do not start the old whole-bar
    # lift driver or its background gain animation for a hosted gesture.
    for signature in ('setBarLifted(_ lifted: Bool)', 'applyBarBodyGain(progress: CGFloat)'):
        header = '    private func ' + signature + ' {\n'
        s = rep(s, header, header + '        guard !ngUseHostPosition else { return }\n')
    for state in ('isDragging: Bool', 'isCollapsingLens'):
        old = f'    private var {state} = false {{\n        didSet {{ if oldValue != {state.split(":")[0]} {{ ngSyncPlatterHold() }} }}\n    }}'
        if old in s:
            s = s.replace(old, f'    private var {state} = false')
    s = rep(s, '''            backgroundGlassView.ngFrostedPlatter = ngUseHostPosition
            var chrome = backgroundGlassView.configuration
            chrome.blur.radius = ngUseHostPosition ? 26 : 18
            chrome.blur.sigma = ngUseHostPosition ? 9 : nil
            chrome.refraction.interiorSharpness = ngUseHostPosition ? 0 : Self.chromeDetailLight
            backgroundGlassView.configuration = chrome
            backgroundGlassView.ngOpaqueBackdrop = ngUseHostPosition
            if ngUseHostPosition { selectionView.ngEnableSolidSelection() }''',
                '            if ngUseHostPosition && !oldValue { ngInstallHostedChrome() }')
    s = rep(s, '''        backgroundGlassView.ngPrepareReplacement()
        if !ngUseHostPosition { selectionView.ngPrepareReplacement() }''', '''        if ngUseHostPosition { return }
        backgroundGlassView.ngPrepareReplacement()
        selectionView.ngPrepareReplacement()''')
    s = rep(s, '    private func ngInvalidatePageFrames() {\n',
                '    private func ngInvalidatePageFrames() {\n        guard !ngUseHostPosition else { return }\n')
    s = rep(s, '    public func invalidateBackground() {\n',
                '    public func invalidateBackground() {\n        guard !ngUseHostPosition else { return }\n')
    s = rep(s, '''        if isDragging || isCollapsingLens {
            let shown = theseusView.flatMap { $0.isHidden ? nil : ngVisibleLensFrame($0) }''', '''        if ngUseHostPosition && ngHostIsInteracting {
            let shown = selectionView.layer.presentation()?.frame ?? selectionView.frame
            ngCancelHostedDrag(restore: false)
            ngPlaceHostedPill(shown)
        } else if isDragging || isCollapsingLens {
            let shown = theseusView.flatMap { $0.isHidden ? nil : ngVisibleLensFrame($0) }''')
    s = rep(s, '''        let exclusions = [self, ngExcludedBar].compactMap { $0 }
        backgroundGlassView.setCaptureExcludedViews(exclusions)
        selectionView.setCaptureExcludedViews(exclusions)
        if let bar = ngExcludedBar { theseusView?.setCaptureExcludedViews([bar]) }
        contentView.bounds = bounds''', '''        contentView.bounds = bounds''')
    a = s.index('        backgroundGlassView.frame = bodyFrame\n')
    b = s.index('        updateBarShadow()', a)
    old = s[a:b]
    legacy = '''        let exclusions = [self, ngExcludedBar].compactMap { $0 }
        backgroundGlassView.setCaptureExcludedViews(exclusions)
        selectionView.setCaptureExcludedViews(exclusions)
        if let bar = ngExcludedBar { theseusView?.setCaptureExcludedViews([bar]) }
''' + old
    s = s[:a] + '''        if ngUseHostPosition {
            CATransaction.begin()
            CATransaction.setDisableActions(true)
            ngHostedPlatter.frame = bodyFrame
            ngHostedPlatter.layer.cornerRadius = bodyFrame.height / 2
            CATransaction.commit()
            updateEdgeLayers(rebuildCapture: false)
        } else {
''' + ''.join('    ' + line if line.strip() else line for line in legacy.splitlines(keepends=True)) + '        }\n' + s[b:]
    s = rep(s, '''        super.traitCollectionDidChange(previousTraitCollection)
        if #available(iOS 13.0, *) {''', '''        super.traitCollectionDidChange(previousTraitCollection)
        if ngUseHostPosition {
            if traitCollection.hasDifferentColorAppearance(comparedTo: previousTraitCollection) {
                ngApplyHostedAppearance(animated: previousTraitCollection != nil)
            }
            return
        }
        if #available(iOS 13.0, *) {''')
    s = rep(s, '    private func updateAppearanceForCurrentMode() {\n', '''    private func updateAppearanceForCurrentMode() {
        if ngUseHostPosition { ngApplyHostedAppearance(animated: false); return }
''')
    s = rep(s, '    private func updatePillShade(size: CGSize) {\n',
                '    private func updatePillShade(size: CGSize) {\n        guard !ngUseHostPosition else { return }\n')
    s = rep(s, '''        if isDragging {
            endDragImmediately()
        }
        contentView.bringSubviewToFront(container)''', '''        if isDragging || (ngUseHostPosition && isCollapsingLens) { endDragImmediately() }
        contentView.bringSubviewToFront(container)''')
    s = rep(s, 'showsSelectedIcon: isSelected && !isDragging,',
                'showsSelectedIcon: isSelected && (ngUseHostPosition || !isDragging),')
    s = rep(s, '    private func updateTheseusFrame() {\n',
                '    private func updateTheseusFrame() {\n        guard !ngUseHostPosition else { return }\n')
    s = rep(s, '    private func setupTheseus() {\n',
                '    private func setupTheseus() {\n        guard !ngUseHostPosition else { return }\n')
    s = rep(s, '    private func endDragImmediately() {\n',
                '    private func endDragImmediately() {\n        if ngUseHostPosition { ngCancelHostedDrag(); return }\n')
    s = rep(s, '    private func applyBarTransform() {\n',
                '    private func applyBarTransform() {\n        guard !ngUseHostPosition else { return }\n')
    s = rep(s, '    @objc private func theseusSettingsDidChange() {\n', '''    @objc private func theseusSettingsDidChange() {
        if ngUseHostPosition {
            if ngHostIsInteracting { ngCancelHostedDrag() }
            ngApplyHostedAppearance(animated: false)
            invalidateIntrinsicContentSize()
            setNeedsLayout()
            return
        }
''')
    s = rep(s, '    private func beginInteraction(at location: CGPoint, rawX: CGFloat, time: TimeInterval = CACurrentMediaTime()) {\n',
                '    private func beginInteraction(at location: CGPoint, rawX: CGFloat, time: TimeInterval = CACurrentMediaTime()) {\n        if ngUseHostPosition { ngBeginHostedDrag(at: location.x); return }\n')
    s = rep(s, '    private func followFinger(at location: CGPoint, time: TimeInterval = CACurrentMediaTime()) {\n',
                '    private func followFinger(at location: CGPoint, time: TimeInterval = CACurrentMediaTime()) {\n        if ngUseHostPosition { ngMoveHostedDrag(to: convert(location, to: contentView).x); return }\n')
    s = rep(s, '    private func finishInteraction(rawX: CGFloat) {\n',
                '    private func finishInteraction(rawX: CGFloat) {\n        if ngUseHostPosition { ngFinishHostedDrag(at: convert(CGPoint(x: rawX, y: 0), to: contentView).x); return }\n')
    return rep(s, '''        super.didMoveToWindow()
        if window == nil {
            teardownTheseus()''', '''        super.didMoveToWindow()
        if ngUseHostPosition {
            if window == nil { ngCancelHostedDrag() }
            else { ngApplyHostedAppearance(animated: false) }
            return
        }
        if window == nil {
            teardownTheseus()''')
