"""Render hosted drag optics from tab items and a constant, opaque backdrop."""


def tab(s, rep):
    s = rep(s, '    private var isDragging: Bool = false', '''    private var isDragging: Bool = false {
        didSet { if oldValue != isDragging { ngSyncPlatterHold() } }
    }''')
    s = rep(s, '    private var isCollapsingLens = false', '''    private var isCollapsingLens = false {
        didSet { if oldValue != isCollapsingLens { ngSyncPlatterHold() } }
    }''')
    s = rep(s, '    private func ngLensShapeFrame(_ glass: TheseusView, frame: CGRect, bounds: CGRect) -> CGRect? {', '''    private func ngSyncPlatterHold() {
        if ngUseHostPosition { backgroundGlassView.ngHoldBackdrop(ngHostIsInteracting) }
    }

    private func ngTrackedLensFrame(_ frame: CGRect) -> CGRect {
        let converted = convertToTheseusContainer(frame)
        if ngUseHostPosition, selectionAnimator?.ngIsTrackingDirect == true {
            return converted.offsetBy(dx: frame.midX - converted.midX, dy: 0)
        }
        return converted
    }

    // The same opaque pill moves on the compositor below the live icons,
    // even before Metal has a frame or when it misses a frame. No page can
    // show through the lens when the two surfaces hand off on release.
    private func ngSyncDragPill(_ lens: TheseusView) {
        guard ngUseHostPosition, !pillRestFrame.isEmpty,
              let footprint = ngLensShapeFrame(lens, frame: lens.layer.frame, bounds: lens.layer.bounds) else { return }
        let visible = convertFromTheseusContainer(footprint)
        guard !visible.isEmpty else { return }
        selectionView.layer.transform = LensMorph.transform(mapping: pillRestFrame, onto: visible)
    }

    private func ngLensShapeFrame(_ glass: TheseusView, frame: CGRect, bounds: CGRect) -> CGRect? {''')
    s = rep(s, '''        guard let container = theseusContainer,
              let sourceView = theseusSourceView else { return }

        var config = TheseusConfiguration.lens''', '''        guard let container = theseusContainer,
              let sourceView = ngUseHostPosition ? self : theseusSourceView else { return }

        var config = TheseusConfiguration.lens''')
    s = rep(s, '        glassView.ngNonblockingRendering = ngUseHostPosition', '''        glassView.ngHierarchyCapture = ngUseHostPosition
        glassView.ngNonblockingRendering = ngUseHostPosition
        glassView.ngHostedDragLens = false
        config.edgeFeather = ngUseHostPosition ? 1.0 : TheseusTabBar.pillFeather''')
    s = rep(s, '''        glassView.captureWillBegin = { [weak self] in
            self?.showCaptureTint(true)
        }
        glassView.captureDidEnd = { [weak self] in
            self?.showCaptureTint(false)
        }
        glassView.captureItemLayer = { [weak self] context, sourceView in
            self?.drawLensItems(in: context, from: sourceView)
        }''', '''        glassView.captureWillBegin = { [weak self] in self?.showCaptureTint(true) }
        glassView.captureDidEnd = { [weak self] in self?.showCaptureTint(false) }
        glassView.captureItemLayer = { [weak self] context, sourceView in
            self?.drawLensItems(in: context, from: sourceView)
        }''')
    s = rep(s, '        if let sourceView = theseusSourceView, sourceView.bounds.width > 0, glassView.sourceView !== sourceView {',
            '        if !ngUseHostPosition, let sourceView = theseusSourceView, sourceView.bounds.width > 0, glassView.sourceView !== sourceView {')
    s = rep(s, '        theseusView?.sourceView = theseusSourceView', '        theseusView?.sourceView = ngUseHostPosition ? self : theseusSourceView')
    s = rep(s, '        fadePill(to: 0, spring: Self.pillFadeOutSpring)', '''        if ngUseHostPosition {
            pillFadeDriver.stop()
            isPillFading = false
            selectionView.alpha = 1
            ngSyncDragPill(glassView)
        } else { fadePill(to: 0, spring: Self.pillFadeOutSpring) }''')
    s = rep(s, '            self.selectionView.layer.transform = LensMorph.transform(mapping: pillLocal, onto: localFrame)', '''            if self.ngUseHostPosition { self.ngSyncDragPill(glassView) }
            else { self.selectionView.layer.transform = LensMorph.transform(mapping: pillLocal, onto: localFrame) }''')
    s = rep(s, '            self.placeLens(at: body)\n            self.setLensItemProgress(1)',
            '            self.placeLens(at: body)\n            self.ngSyncDragPill(glassView)\n            self.setLensItemProgress(1)')
    s = rep(s, '''        selectionView.layer.transform = CATransform3DIdentity
        if ngUseHostPosition {
            pillFadeDriver.stop()
            isPillFading = false
            selectionView.isHidden = false
            selectionView.alpha = 0
        } else {
            selectionView.isHidden = false''', '''        if ngUseHostPosition {
            pillFadeDriver.stop()
            isPillFading = false
            selectionView.isHidden = false
            selectionView.alpha = 1
        } else {
            selectionView.layer.transform = CATransform3DIdentity
            selectionView.isHidden = false''')
    s = rep(s, '''                // The settled pill only takes over once the lens is near the target.
                let share = min(max((progress - 0.72) / 0.28, 0), 1)
                self.selectionView.alpha = share
                glassView.alpha = 1 - share''', '''                self.ngSyncDragPill(glassView)
                let share = min(max((progress - 0.72) / 0.28, 0), 1)
                glassView.alpha = 1 - share''')
    s = rep(s, '''            if self.ngUseHostPosition {
                self.updateSelectionViewFrame(animated: false)
                self.selectionView.alpha = 1
            }''', '''            if self.ngUseHostPosition {
                self.selectionView.layer.transform = CATransform3DIdentity
                self.updateSelectionViewFrame(animated: false)
                self.selectionView.alpha = 1
            }''')
    s = rep(s, '''        selectionView.layer.removeAllAnimations()
        updateSelectionViewFrame(animated: false)
        hideTheseus()''', '''        if !ngUseHostPosition {
            selectionView.layer.removeAllAnimations()
            updateSelectionViewFrame(animated: false)
        }
        hideTheseus()''')
    s = rep(s, '''            selectionView.isHidden = false
            selectionView.alpha = 1
            return
        }

        let shown =''', '''            selectionView.isHidden = false
            selectionView.alpha = 1
            if ngUseHostPosition {
                selectionView.layer.transform = CATransform3DIdentity
                updateSelectionViewFrame(animated: false)
            }
            return
        }

        let shown =''')
    s = rep(s, '''        if !isCollapsingLens, !isPillFading, !(lensMorphAnimator?.isRunning ?? false) {''',
            '''        if !ngUseHostPosition, !isCollapsingLens, !isPillFading, !(lensMorphAnimator?.isRunning ?? false) {''', count=2)
    s = rep(s, '''                            lens.layer.transform = transform
                        }
                    } else { morph.retarget(to: containerFrame) }
                } else {
                    self.placeLens(at: containerFrame)
                    if self.isPillFading, !self.selectionView.isHidden {''', '''                            lens.layer.transform = transform
                            self.ngSyncDragPill(lens)
                        }
                    } else { morph.retarget(to: containerFrame) }
                } else {
                    self.placeLens(at: containerFrame)
                    if self.ngUseHostPosition, let lens = self.theseusView { self.ngSyncDragPill(lens) }
                    else if self.isPillFading, !self.selectionView.isHidden {''')
    s = rep(s, '''        glassView.layer.transform = stretched(CATransform3DIdentity)
    }

    private func stopLensStretch()''', '''        glassView.layer.transform = stretched(CATransform3DIdentity)
        if isDragging { ngSyncDragPill(glassView) }
    }

    private func stopLensStretch()''')
    s = rep(s, 'let target = self.convertToTheseusContainer(follow)', 'let target = self.ngTrackedLensFrame(follow)')
    s = rep(s, 'let containerFrame = self.convertToTheseusContainer(frame)', 'let containerFrame = self.ngTrackedLensFrame(frame)')
    s = rep(s, '    private var ngDragCenter = NGTabDirectFollow()',
            '    private var ngDragCenter = NGTabDirectFollow()\n    var ngIsTrackingDirect: Bool { ngDragCenter.isTracking }')
    return rep(s, '''        selectionView.isHidden = false
        selectionView.alpha = 1
        isDragging = false
        ngGestureGate.clear()''', '''        selectionView.isHidden = false
        selectionView.alpha = 1
        if ngUseHostPosition { selectionView.layer.transform = CATransform3DIdentity }
        isDragging = false
        ngGestureGate.clear()''')

def renderer(s, rep):
    s = rep(s, '    var ngNonblockingRendering = false', '''    var ngNonblockingRendering = false
    var ngHierarchyCapture = false
    var ngBackdropHeld = false
    var ngHostedDragLens = false

    private lazy var ngLightLensBackdrop = ngMakeLensBackdrop(236)
    private lazy var ngDarkLensBackdrop = ngMakeLensBackdrop(65)

    private func ngMakeLensBackdrop(_ tone: UInt8) -> MTLTexture? {
        let desc = MTLTextureDescriptor.texture2DDescriptor(pixelFormat: .bgra8Unorm,
                                                            width: 1, height: 1, mipmapped: false)
        desc.usage = .shaderRead
        desc.storageMode = .shared
        guard let texture = context.device.makeTexture(descriptor: desc) else { return nil }
        var pixel = UInt32(tone) * 0x00010101 | 0xff000000
        texture.replace(region: MTLRegionMake2D(0, 0, 1, 1), mipmapLevel: 0, withBytes: &pixel, bytesPerRow: 4)
        return texture
    }

    private func ngRenderHostedLens(to drawable: CAMetalDrawable, from bar: UIView,
                                    region: CGRect, renderScale: CGFloat, frameValue: UInt64) -> Bool {
        guard let dark = hostView?.traitCollection.userInterfaceStyle,
              let plate = (dark == .dark ? ngDarkLensBackdrop : ngLightLensBackdrop),
              let draw = drawItemLayer,
              let command = context.commandQueue.makeCommandBuffer() else { return false }
        let size = CGSize(width: CGFloat(drawable.texture.width) * renderScale,
                          height: CGFloat(drawable.texture.height) * renderScale)
        let slot = itemLayerTextureIndex
        guard let items = renderItemLayer(region: region, scale: renderScale, fixedSize: size,
                                          sourceView: bar, draw: draw) else { return false }
        let output = SIMD2<Float>(Float(drawable.texture.width), Float(drawable.texture.height))
        // A constant texture is already its own Gaussian blur. The only live
        // texture in this path is the transparent tab-item layer.
        guard encodeRefractionCompositePass(commandBuffer: command, blurredTexture: plate,
                                            originalSourceTexture: plate, itemTexture: items, frostTextures: nil,
                                            destinationTexture: drawable.texture, viewSize: output) else {
            itemLayerTextureIndex = slot
            return false
        }
        command.addCompletedHandler { [weak self] _ in self?.lastCompletedFrame = frameValue }
        command.present(drawable)
        command.commit()
        return true
    }''')
    s = rep(s, 'renderItemLayer(region: CGRect, scale: CGFloat, sourceView:',
            'renderItemLayer(region: CGRect, scale: CGFloat, fixedSize: CGSize? = nil, sourceView:')
    a = s.index('    private func renderItemLayer(')
    b = s.index('    private func performRender(', a)
    item = s[a:b]
    item = rep(item, '''        let width = Int(ceil(region.width * renderScale - 0.001))
        let height = Int(ceil(region.height * renderScale - 0.001))''', '''        guard !region.isEmpty, region.width.isFinite, region.height.isFinite else { return nil }
        let width = Int(ceil((fixedSize?.width ?? region.width * renderScale) - 0.001))
        let height = Int(ceil((fixedSize?.height ?? region.height * renderScale) - 0.001))''')
    item = rep(item, '        ctx.scaleBy(x: renderScale, y: -renderScale)', '''        let sx = fixedSize == nil ? renderScale : CGFloat(width) / region.width
        let sy = fixedSize == nil ? renderScale : CGFloat(height) / region.height
        ctx.scaleBy(x: sx, y: -sy)''')
    s = s[:a] + item + s[b:]
    a = s.index('    private func encodeRefractionCompositePass(')
    b = s.index('    private func applyFlexGlow(', a)
    composite = s[a:b]
    composite = rep(composite, '    ) {\n', '    ) -> Bool {\n')
    composite = rep(composite, '            return\n', '            return false\n')
    composite = rep(composite, '        encoder.endEncoding()\n', '        encoder.endEncoding()\n        return true\n')
    s = s[:a] + composite + s[b:]
    s = rep(s, '        encodeRefractionCompositePass(\n            commandBuffer: commandBuffer,',
            '        guard encodeRefractionCompositePass(\n            commandBuffer: commandBuffer,')
    s = rep(s, '            viewSize: outputSize\n        )\n\n        if keepsSnapshot', '''            viewSize: outputSize
        ) else {
            texturePool.checkin(intermediateTexture1)
            texturePool.checkin(intermediateTexture2)
            for texture in frostTextures?.pooled ?? [] { texturePool.checkin(texture) }
            if let capturedSurface { viewLayerCapture?.recycleSurface(capturedSurface) }
            return false
        }

        if keepsSnapshot''')
    # Do not stop or hide the frosted platter; freeze its most recent frame
    # while the press/drag/release is active, then catch up in one render.
    s = rep(s, '        guard !isShuttingDown else { return }',
            '        guard !isShuttingDown, !ngBackdropHeld else { return }')
    return rep(s, '''        let renderScale = currentRefractionQuality.renderScale

        let sourceTexture: MTLTexture''', '''        let renderScale = currentRefractionQuality.renderScale

        let sourceTexture: MTLTexture''')


def surface(s, rep):
    s = rep(s, '    var ngNonblockingRendering = false', '''    var ngNonblockingRendering = false
    var ngHostedDragLens = false
    private var ngBackdropHeld = false

    func ngHoldBackdrop(_ held: Bool) {
        guard ngBackdropHeld != held else { return }
        ngBackdropHeld = held
        renderer?.ngBackdropHeld = held
        if !held { renderer?.setNeedsRender() }
    }''')
    s = rep(s, '        renderer?.ngNonblockingRendering = ngNonblockingRendering', '''        renderer?.ngNonblockingRendering = ngNonblockingRendering
        renderer?.ngHostedDragLens = ngHostedDragLens
        renderer?.ngBackdropHeld = ngBackdropHeld''')
    return rep(s, '''        isUsingFallback = shouldUseFallback

        if shouldUseFallback {''', '''        isUsingFallback = shouldUseFallback

        // Reduced transparency or an unavailable Metal backend uses the
        // opaque moving pill below, not a page-sampling UIKit blur here.
        if ngHostedDragLens && shouldUseFallback {
            renderer?.stopRendering()
            renderer = nil
            metalLayerView?.isHidden = true
            fallbackView?.isHidden = true
            return
        }

        if shouldUseFallback {''')
