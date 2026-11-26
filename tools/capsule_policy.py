"""Hosted capsule optics live here; the platter and gesture geometry stay separate."""


def tab(s, rep):
    s = rep(s, '        glassView.ngNonblockingRendering = ngUseHostPosition\n', '''        glassView.ngNonblockingRendering = ngUseHostPosition
        glassView.ngFrostedLens = ngUseHostPosition
        glassView.ngOpaqueBackdrop = ngUseHostPosition
''')
    s = rep(s, '        glassView.resumeRendering()\n', '''        if glassView.isHidden { glassView.ngPrepareFrostedLensPresentation() }
        glassView.resumeRendering()
''')
    s = rep(s, '        // Keep one opaque selection surface; the old simultaneous lens/pill\n        // compositing and its second outline are not used in hosted gestures.\n', '')
    s = s.replace('ngEnableSolidSelection', 'ngEnableFrostedSelection').replace('ngSetSolidSelectionTone', 'ngSetFrostedSelectionTone')
    s = rep(s, '''    private func hideTheseus() {''', '''    private func ngPlaceReleasePill(_ frame: CGRect) {
        let pill = convertFromTheseusContainer(frame)
        guard !pill.isEmpty else { return }
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        selectionView.bounds = CGRect(origin: .zero, size: pill.size)
        selectionView.center = CGPoint(x: pill.midX, y: pill.midY)
        let radius = min(pill.width, pill.height) / 2
        if selectionView.shape.cornerRadius != radius { selectionView.shape.cornerRadius = radius }
        selectionView.alpha = 1
        selectionView.isHidden = false
        CATransaction.commit()
    }

    private func hideTheseus() {''')
    s = rep(s, '''            pillFadeDriver.stop()
            isPillFading = false
            selectionView.isHidden = false
            selectionView.alpha = 0
        } else {''', '''            pillFadeDriver.stop()
            isPillFading = false
        } else {''')
    s = rep(s, '''        guard !releaseFrame.isEmpty, !animationBase.isEmpty else { endDragImmediately(); return }
''', '''        guard !releaseFrame.isEmpty, !animationBase.isEmpty else { endDragImmediately(); return }
        if ngUseHostPosition { ngPlaceReleasePill(releaseFrame) }
''')
    return rep(s, '''                // The settled pill only takes over once the lens is near the target.
                let share = min(max((progress - 0.72) / 0.28, 0), 1)
                self.selectionView.alpha = share
                glassView.alpha = 1 - share''', '''                self.ngPlaceReleasePill(frame)
                glassView.alpha = 1 - min(max(progress, 0), 1)''')


def surface(s, rep):
    start = s.index('    private var ngSolidSelection = false')
    end = s.index('    var ngNonblockingRendering', start)
    s = s[:start] + '''    private var ngFrostedSelection = false
    private var ngSelectionMaterial: UIVisualEffectView?
    private var ngSelectionDark: Bool?
    var ngFrostedLens = false

    func ngEnableFrostedSelection() {
        guard !ngFrostedSelection else { return }
        ngFrostedSelection = true
        ngBackdropEpoch &+= 1
        ngWaitingForPresent = false
        renderer?.stopRendering()
        renderer = nil
        providesCaptureSnapshot = false
        captureSnapshot = nil
        captureSnapshotOverride = nil
        sourceView = nil
        fallbackView?.isHidden = true
        metalLayerView?.isHidden = true
        layer.cornerCurve = .continuous
        layer.cornerRadius = shape.cornerRadius
        clipsToBounds = true
        isOpaque = false
        layer.isOpaque = false
        backgroundColor = .clear
        let material = UIVisualEffectView(effect: nil)
        material.isUserInteractionEnabled = false
        material.frame = bounds
        material.autoresizingMask = [.flexibleWidth, .flexibleHeight]
        insertSubview(material, at: 0)
        ngSelectionMaterial = material
        ngSetFrostedSelectionTone(dark: traitCollection.userInterfaceStyle == .dark, animated: false)
    }

    func ngSetFrostedSelectionTone(dark: Bool, animated: Bool) {
        guard let material = ngSelectionMaterial, ngSelectionDark != dark else { return }
        ngSelectionDark = dark
        material.effect = UIBlurEffect(style: dark ? .systemThickMaterialDark : .systemThickMaterialLight)
        let layer = material.contentView.layer
        let previous = layer.presentation()?.backgroundColor ?? layer.backgroundColor
        let tint = UIColor(white: dark ? 1 : 0, alpha: dark ? 0.12 : 0.095).cgColor
        CATransaction.begin()
        CATransaction.setDisableActions(true)
        layer.backgroundColor = tint
        if let previous, animated, window != nil {
            let fade = CABasicAnimation(keyPath: "backgroundColor")
            fade.fromValue = previous
            fade.toValue = tint
            fade.duration = NGTabPresentation.appearanceDuration
            fade.timingFunction = CAMediaTimingFunction(name: .easeInEaseOut)
            layer.add(fade, forKey: "ngPillAppearance")
        }
        CATransaction.commit()
    }

''' + s[end:]
    s = rep(s, '            if ngSolidSelection { ngUpdateSolidSelection(); return }', '''            if ngFrostedSelection {
                if oldValue.shape.cornerRadius != configuration.shape.cornerRadius {
                    layer.cornerRadius = configuration.shape.cornerRadius
                }
                return
            }''')
    s = rep(s, '        if ngSolidSelection { ngUpdateSolidSelection(); return }', '        if ngFrostedSelection { return }')
    s = rep(s, '        if ngSolidSelection { return backgroundColor }\n', '')
    s = s.replace('ngSolidSelection', 'ngFrostedSelection')
    s = rep(s, '    func ngPrepareReplacement() {', '''    func ngPrepareFrostedLensPresentation() {
        guard ngFrostedLens, !isUsingFallback else { return }
        ngBackdropEpoch &+= 1
        ngPresented = false
        ngPrepareReplacement()
    }

    func ngPrepareReplacement() {''')
    s = rep(s, 'fallbackView?.ngFrostedPlatter = ngFrostedPlatter',
            'fallbackView?.ngFrostedPlatter = ngFrostedPlatter || ngFrostedLens', count=2)
    return rep(s, '            fallbackView?.isHidden = !ngWaitingForPresent\n', '''            if ngFrostedLens { ngPrepareFrostedLensPresentation() }
            fallbackView?.isHidden = !ngWaitingForPresent
''')


def renderer(s, rep):
    s = rep(s, '        let renderScale = currentRefractionQuality.renderScale\n', '''        let frostedLens = (hostView as? TheseusView)?.ngFrostedLens == true
        let screenScale = sourceView.window?.screen.scale ?? UIScreen.main.scale
        // Only the backdrop is low resolution; the drawable retains native rim fidelity.
        let renderScale: CGFloat = frostedLens ? 0.5 / screenScale : currentRefractionQuality.renderScale
''')
    s = rep(s, '''        let effectiveRadius = detailSigma.map { min(Int(($0 * 3).rounded(.up)), currentQuality.maxBlurRadius) }
            ?? configuration.effectiveBlurRadius(for: currentQuality, pixelsPerPoint: pixelsPerPoint)
        let effectiveSigma = Float(min(detailSigma ?? configuration.effectiveSigma * pixelsPerPoint, CGFloat(effectiveRadius) * 0.5))''', '''        let ordinaryRadius = detailSigma.map { min(Int(($0 * 3).rounded(.up)), currentQuality.maxBlurRadius) }
            ?? configuration.effectiveBlurRadius(for: currentQuality, pixelsPerPoint: pixelsPerPoint)
        let effectiveRadius = frostedLens ? 33 : ordinaryRadius
        let effectiveSigma: Float = frostedLens ? 11 : Float(min(detailSigma ?? configuration.effectiveSigma * pixelsPerPoint, CGFloat(effectiveRadius) * 0.5))''')
    return rep(s, '            originalSourceTexture: sourceTexture,', '''            // Both lens styles can tap the nominal raw input, including at the rim.
            originalSourceTexture: frostedLens ? intermediateTexture2 : sourceTexture,''')
