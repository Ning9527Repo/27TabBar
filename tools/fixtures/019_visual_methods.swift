    private func setupTheseus() {
        guard theseusView == nil else { return }
        guard let container = theseusContainer,
              let sourceView = theseusSourceView else { return }

        var config = TheseusConfiguration.lens
        // Covers the rim and shadow outside the shape, no more: capture cost follows the area.
        config.shape.padding = CGPoint(x: 18, y: 18)
        config.lensChain = TheseusConfiguration.LensChain()
        config.edgeFeather = TheseusTabBar.pillFeather
        config.captureMethod = TheseusCapability.isDeviceSupported ? .layerRendering : .surfaceBased
        config.refraction.magnificationCenterY = 0
        config.refraction.intensity = 1.1
        config.edgeEffects.rimGlow = 0
        config.edgeEffects.glareIntensity = 0
        config.theme.tintColor = glassTint
        config.theme.tintOpacity = glassTintIntensity
        apply(lensMaterial, activity: 0, to: &config)

        let glassView = TheseusView(configuration: config)
        glassView.sourceView = sourceView
        glassView.ngNonblockingRendering = ngUseHostPosition
        if let bar = ngExcludedBar { glassView.setCaptureExcludedViews([bar]) }
        glassView.isHidden = true
        glassView.alpha = 0
        glassView.isUserInteractionEnabled = false

        container.addSubview(glassView)
        theseusView = glassView
        applyAdaptiveOverride()
        glassView.captureWillBegin = { [weak self] in
            self?.showCaptureTint(true)
        }
        glassView.captureDidEnd = { [weak self] in
            self?.showCaptureTint(false)
        }
        glassView.captureItemLayer = { [weak self] context, sourceView in
            self?.drawLensItems(in: context, from: sourceView)
        }
    }

    private func showTheseus() {
        setupTheseus()

        guard let glassView = theseusView,
              let container = theseusContainer else { return }

        if glassView.superview !== container {
            glassView.removeFromSuperview()
            container.addSubview(glassView)
        }
        if let sourceView = theseusSourceView, sourceView.bounds.width > 0, glassView.sourceView !== sourceView {
            glassView.sourceView = sourceView
        }
        glassView.resumeRendering()
        glassView.continuousUpdate = true
        glassView.invalidateBackground()

        lensMorphAnimator?.cancel()
        selectionAnimator?.cancel()
        isCollapsingLens = false

        setBarLifted(liftsBar)

        guard selectedIndex >= 0, selectedIndex < slotFrames.count else { return }
        let itemFrame = slotFrame(at: selectedIndex)
        let pillFrame = convertToTheseusContainer(selectionFrame(for: itemFrame))
        let lensFrame = convertToTheseusContainer(glassFrame(for: itemFrame))

        let startFrame: CGRect
        let startProgress: CGFloat
        if glassView.isHidden {
            let visiblePill = selectionView.layer.presentation()?.frame ?? selectionView.layer.frame
            startFrame = ngUseHostPosition && !visiblePill.isEmpty
                ? convertToTheseusContainer(visiblePill) : pillFrame
            startProgress = 0
        } else {
            startFrame = (ngUseHostPosition ? ngVisibleLensFrame(glassView) : nil) ?? glassView.frame
            startProgress = lensItemProgress
        }
        // A transform about a fixed frame, not a drawable resize every tick.
        setLensFill(0, rim: startProgress)
        setLensRefraction(startProgress)
        glassView.layer.transform = CATransform3DIdentity
        let lifted = glassFrame(for: itemFrame).size.applying(CGAffineTransform(scaleX: Self.liftScale, y: Self.liftScale))
        let hostFrame = CGRect(x: lensFrame.midX - lifted.width / 2, y: lensFrame.midY - lifted.height / 2, width: lifted.width, height: lifted.height)
        glassView.frame = hostFrame
        var lensShape = glassView.shape
        lensShape.widthInset = -lensOutset
        lensShape.heightInset = -lensOutset
        lensShape.cornerRadius = lensCornerRadius(forHeight: hostFrame.height + 2 * lensOutset)
        glassView.shape = lensShape
        let morphBase = ngUseHostPosition
            ? hostFrame.insetBy(dx: lensShape.widthInset, dy: lensShape.heightInset) : hostFrame
        let growthTarget = ngUseHostPosition ? lensFrame.insetBy(dx: -lensOutset, dy: -lensOutset) : lensFrame
        glassView.layer.transform = LensMorph.transform(mapping: morphBase, onto: startFrame)
        glassView.alpha = 1
        glassView.isHidden = false
        let pillLocal = selectionFrame(for: itemFrame)
        pillRestFrame = pillLocal
        selectionView.layer.transform = CATransform3DIdentity
        selectionView.bounds = CGRect(origin: .zero, size: pillLocal.size)
        selectionView.center = CGPoint(x: pillLocal.midX, y: pillLocal.midY)
        selectionView.shape.cornerRadius = (ngUseHostPosition ? min(pillLocal.width, pillLocal.height) : pillLocal.height) / 2
        updatePillShade(size: pillLocal.size)
        selectionView.isHidden = false
        fadePill(to: 0, spring: Self.pillFadeOutSpring)
        setLensItemProgress(startProgress)
        if startProgress == 0, TheseusSettings.shared.areMorphAnimationsEnabled {
            startLensStretch()
        }
        var lastFrame = startFrame

        let animator = lensMorphAnimator ?? LensMorphAnimator()
        lensMorphAnimator = animator
        animator.morph(from: startFrame, to: growthTarget, spring: Self.lensGrowSpring, onTick: { [weak self, weak glassView] frame, progress in
            guard let self = self, let glassView = glassView else { return }
            var placed = frame
            if let follow = self.ngFollowFrame {
                let target = self.convertToTheseusContainer(follow)
                placed = frame.offsetBy(dx: target.midX - frame.midX, dy: target.midY - frame.midY)
            }
            lastFrame = placed
            glassView.layer.transform = self.stretched(LensMorph.transform(mapping: morphBase, onto: placed))
            let localFrame = self.convertFromTheseusContainer(placed)
            self.selectionView.layer.transform = LensMorph.transform(mapping: pillLocal, onto: localFrame)
            self.updateHoveredItem(lensCenterX: localFrame.midX)
            let grown = startProgress + (1 - startProgress) * progress
            self.setLensItemProgress(grown)
            self.setLensFill(0, rim: min(max(grown, 0), 1))
            self.setLensRefraction(min(max(grown, 0), 1))
        }, onComplete: { [weak self, weak glassView] in
            guard let self = self, let glassView = glassView else { return }
            self.ngFollowFrame = nil
            glassView.layer.transform = self.stretched(CATransform3DIdentity)
            // placeLens adds the rim outset itself; lastFrame already includes it.
            let body = self.ngUseHostPosition ? lastFrame.insetBy(dx: self.lensOutset, dy: self.lensOutset) : lastFrame
            self.placeLens(at: body)
            self.setLensItemProgress(1)
            self.setLensFill(0, rim: 1)
            self.setLensRefraction(1)
        })

    }

    private func hideTheseus() {
        guard let glassView = theseusView, !glassView.isHidden else {
            pillFadeDriver.stop()
            isPillFading = false
            selectionView.isHidden = false
            selectionView.alpha = 1
            return
        }

        let shown = ngUseHostPosition ? ngVisibleLensFrame(glassView) : nil
        ngFollowFrame = nil
        selectionAnimator?.cancel()
        lensMorphAnimator?.cancel()
        stopLensStretch()

        setBarLifted(false)

        guard selectedIndex >= 0, selectedIndex < slotFrames.count else {
            glassView.isHidden = true
            glassView.continuousUpdate = false
            glassView.pauseRendering()
            setLensFill(0, rim: -1)
            pillFadeDriver.stop()
            isPillFading = false
            selectionView.isHidden = false
            selectionView.alpha = 1
            return
        }

        isCollapsingLens = true
        glassView.continuousUpdate = true
        let landingIndex = selectedIndex
        let pillFrame = convertToTheseusContainer(selectionFrame(for: slotFrame(at: landingIndex)))
        let startRim = max(glassView.configuration.lensRimScale, 0)
        let startRefraction = glassView.configuration.lensRefractionScale
        let startProgress = lensItemProgress
        selectionView.layer.transform = CATransform3DIdentity
        if ngUseHostPosition {
            pillFadeDriver.stop()
            isPillFading = false
            selectionView.isHidden = false
            selectionView.alpha = 0
        } else {
            selectionView.isHidden = false
            fadePill(to: 1, spring: Self.pillFadeInSpring)
        }
        let size = glassView.bounds.size
        let modelFrame = CGRect(x: glassView.center.x - size.width / 2, y: glassView.center.y - size.height / 2,
                                width: size.width, height: size.height)
        let releaseFrame: CGRect
        let animationBase: CGRect
        if let shown, let base = ngLensShapeFrame(glassView, frame: modelFrame, bounds: glassView.bounds) {
            releaseFrame = shown
            animationBase = base
        } else {
            glassView.layer.transform = CATransform3DIdentity
            releaseFrame = glassView.frame.insetBy(dx: glassView.shape.widthInset, dy: glassView.shape.heightInset)
            animationBase = releaseFrame
            if glassView.shape.widthInset != 0 || glassView.shape.heightInset != 0 {
                glassView.frame = releaseFrame
                var shape = glassView.shape
                shape.widthInset = 0
                shape.heightInset = 0
                shape.cornerRadius = lensCornerRadius(forHeight: releaseFrame.height)
                glassView.shape = shape
            }
        }
        guard !releaseFrame.isEmpty, !animationBase.isEmpty else { endDragImmediately(); return }

        let animator = lensMorphAnimator ?? LensMorphAnimator()
        lensMorphAnimator = animator
        animator.morph(from: releaseFrame, to: pillFrame, spring: Self.lensShrinkSpring, onTick: { [weak self, weak glassView, weak animator] frame, progress in
            guard let self = self, let glassView = glassView else { return }
            glassView.layer.transform = LensMorph.transform(mapping: animationBase, onto: frame)
            if self.ngUseHostPosition {
                // The settled pill only takes over once the lens is near the target.
                let share = min(max((progress - 0.72) / 0.28, 0), 1)
                self.selectionView.alpha = share
                glassView.alpha = 1 - share
            }
            let target = self.ngUseHostPosition ? self.selectedIndex : landingIndex
            if self.slotFrames.indices.contains(target) {
                animator?.retarget(to: self.convertToTheseusContainer(self.selectionFrame(for: self.slotFrame(at: target))))
            }
            let remaining = min(max(1 - progress, 0), 1)
            self.setLensFill(0, rim: startRim * remaining)
            self.setLensRefraction(startRefraction * remaining)
            self.setLensItemProgress(startProgress * remaining)
        }, onComplete: { [weak self, weak glassView] in
            guard let self = self else { return }
            self.isCollapsingLens = false
            if self.ngUseHostPosition {
                self.updateSelectionViewFrame(animated: false)
                self.selectionView.alpha = 1
            }
            self.selectionView.isHidden = false
            self.setLensItemProgress(0)
            self.applyItemStates(selectedAt: self.selectedIndex, animated: false)
            if let glassView = glassView {
                glassView.isHidden = true
                glassView.layer.transform = CATransform3DIdentity
                glassView.continuousUpdate = false
                glassView.pauseRendering()
            }
            self.setLensFill(0, rim: -1)
            self.setLensRefraction(1)
        })
    }

    private func placeLens(at containerFrame: CGRect) {
        guard let glassView = theseusView else { return }
        let resting = (slotFrames.first.map { glassFrame(for: $0).size } ?? containerFrame.size).applying(CGAffineTransform(scaleX: Self.liftScale, y: Self.liftScale))
        glassView.bounds = CGRect(origin: .zero, size: resting)
        glassView.center = CGPoint(x: containerFrame.midX, y: containerFrame.midY)
        var shape = glassView.shape
        let outset = lensOutset
        shape.widthInset = (resting.width - containerFrame.width) / 2 - outset
        shape.heightInset = (resting.height - containerFrame.height) / 2 - outset
        shape.cornerRadius = lensCornerRadius(forHeight: containerFrame.height + 2 * outset)
        glassView.shape = shape
    }

    private func updateSelectionViewFrame(animated: Bool) {
        guard selectedIndex >= 0, selectedIndex < slotFrames.count else { return }

        let frame = selectionFrame(for: slotFrame(at: selectedIndex))
        let radius = ngUseHostPosition ? min(frame.width, frame.height) / 2 : frame.height / 2
        if selectionView.shape.cornerRadius != radius {
            selectionView.shape.cornerRadius = radius
        }

        let bounds = CGRect(origin: .zero, size: frame.size)
        let center = CGPoint(x: frame.midX, y: frame.midY)
        updatePillShade(size: frame.size)
        guard selectionView.bounds != bounds || selectionView.center != center else { return }
        if animated && TheseusSettings.shared.areMorphAnimationsEnabled {
            let options: UIView.AnimationOptions = ngUseHostPosition ? [.beginFromCurrentState, .allowUserInteraction] : []
            UIView.animate(withDuration: 0.22, delay: 0, usingSpringWithDamping: 0.88,
                           initialSpringVelocity: 0.75, options: options) {
                self.selectionView.bounds = bounds
                self.selectionView.center = center
            }
        } else {
            selectionView.bounds = bounds
            selectionView.center = center
        }
        selectionView.invalidateBackground()
    }

    private func updatePillShade(size: CGSize) {
        let frame = CGRect(origin: .zero, size: size)
        if pillShadeLayer.frame != frame {
            pillShadeLayer.frame = frame
            pillShadeLayer.cornerRadius = (ngUseHostPosition ? min(size.width, size.height) : size.height) / 2
        }
        let colors: [CGColor]
        let locations: [NSNumber]
        if usesIOS26Look {
            colors = [UIColor.clear.cgColor, UIColor.clear.cgColor]
            locations = [0, 1]
        } else if isDarkAppearance {
            colors = [UIColor(white: 1, alpha: 0.008).cgColor, UIColor(white: 1, alpha: 0).cgColor]
            locations = [0, 0.5]
        } else {
            colors = [UIColor(white: 0, alpha: 0.025).cgColor, UIColor(white: 0, alpha: 0.025).cgColor, UIColor(white: 0, alpha: 0).cgColor]
            locations = [0, 0.19, 0.3]
        }
        if pillShadeLayer.locations != locations { pillShadeLayer.locations = locations }
        if (pillShadeLayer.colors as? [CGColor]) != colors { pillShadeLayer.colors = colors }
    }
