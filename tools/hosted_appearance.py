"""Bind a hosted platter reveal to the prepared theme frame, not to a timer."""


def tab(s, rep):
    s = rep(s, '''    private func resetAdaptation() {
        adaptPending?.cancel()''', '''    private func resetAdaptation() {
        if ngUseHostPosition {
            let target: CGFloat = systemIsDark ? 1 : 0
            adaptDarkWeight = target
            adaptDarkTarget = target
        }
        adaptPending?.cancel()''')
    a = s.index('    public override func traitCollectionDidChange(')
    b = s.index('    private func updateAppearanceForCurrentMode()', a)
    part = s[a:b]
    part = rep(part, '''                updateAppearanceForCurrentMode()
                if !isDragging {''', '''                updateAppearanceForCurrentMode()
                if ngPalettePending && ngUseHostPosition && styleChanged {
                    backgroundGlassView.ngPreparePlatterAppearance(dark: systemIsDark)
                }
                if !isDragging {''')
    part = rep(part, '''        defer { ngAnimateAppearance = false }
        updateAppearanceForCurrentMode()
        if !isDragging { applyItemStates(selectedAt: selectedIndex, animated: ngAnimateAppearance) }''', '''        if ngAnimateAppearance { ngPaletteSettlesAt = CACurrentMediaTime() + NGTabPresentation.appearanceDuration }
        defer { ngAnimateAppearance = false }
        updateAppearanceForCurrentMode()
        if !isDragging { applyItemStates(selectedAt: selectedIndex, animated: ngAnimateAppearance) }''')
    s = s[:a] + part + s[b:]
    s = rep(s, '    private var ngPalettePending = false',
            '    private var ngPalettePending = false\n    private var ngPaletteSettlesAt: CFTimeInterval = 0')
    s = rep(s, '''    private func updateAdaptiveAppearance() {
        guard !ngPalettePending else { return }''', '''    private func updateAdaptiveAppearance() {
        guard !ngPalettePending, CACurrentMediaTime() >= ngPaletteSettlesAt else { return }''')
    return rep(s, '''        if isDragging || isCollapsingLens {
            let lensTint = vibrantTint(selectedTintColor, over: lensBackdropColor, plus: lensTintBrightening)''', '''        if !ngHostIsInteracting && CACurrentMediaTime() < ngPaletteSettlesAt { return }
        if isDragging || isCollapsingLens {
            let lensTint = vibrantTint(selectedTintColor, over: lensBackdropColor, plus: lensTintBrightening)''')


def surface(s, rep):
    s = rep(s, '    private var ngAppearanceEpoch: UInt64 = 0',
            '    private var ngAppearanceGate = NGTabAppearanceGate()')
    s = rep(s, '''            ngAppearanceEpoch &+= 1
            let epoch = ngAppearanceEpoch''', '''            let generation = ngAppearanceGate.begin()
            renderer.ngAppearanceTicket = nil
            renderer.ngVisiblePresent = nil''')
    s = rep(s, '''            ngAppearanceSnapshot = image
            ngAppearanceReveal = onReveal
            CATransaction.begin()''', '''            // Reversing a theme during the fade must not restore its cover to 100%.
            let shownOpacity = ngAppearanceImage.superlayer == nil ? 1
                : (ngAppearanceImage.presentation()?.opacity ?? ngAppearanceImage.opacity)
            let coverImage = ngAppearanceImage.superlayer == nil ? image : (ngAppearanceSnapshot ?? image)
            ngAppearanceSnapshot = coverImage
            ngAppearanceReveal = onReveal
            CATransaction.begin()''')
    s = rep(s, '''            ngAppearanceImage.contents = image
            ngAppearanceImage.opacity = 1''', '''            ngAppearanceImage.contents = coverImage
            ngAppearanceImage.opacity = shownOpacity''')
    s = rep(s, '''            renderer.ngVisiblePresent = { [weak self] in self?.ngFinishPlatterAppearance(epoch) }
            // The compositor can skip a presentation while an overlay is up.
            // Never leave a stale appearance image hanging on the screen.
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { [weak self] in
                self?.ngFinishPlatterAppearance(epoch)
            }''', '''            ngCheckPlatterAppearance(generation, retries: 2)''')
    s = rep(s, '''    private func ngFinishPlatterAppearance(_ epoch: UInt64) {
        guard ngAppearancePending, ngAppearanceEpoch == epoch else { return }
        ngAppearancePending = false
        renderer?.ngVisiblePresent = nil''', '''    // Called only after the tab bar has installed the new palette in its renderer.
    func ngPreparePlatterAppearance(dark: Bool) {
        guard ngAppearancePending, let renderer else { return }
        renderer.ngAppearanceTicket = ngAppearanceGate.prepare(dark: dark)
        renderer.ngVisiblePresent = { [weak self] shown in self?.ngFinishPlatterAppearance(shown) }
        renderer.setNeedsRender()
    }

    @objc private func ngPlatterBecameActive() {
        guard ngAppearancePending, window != nil else { return }
        renderer?.setNeedsRender()
        ngCheckPlatterAppearance(ngAppearanceGate.generation, retries: 2)
    }

    private func ngCheckPlatterAppearance(_ generation: UInt64, retries: Int) {
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.35) { [weak self] in
            guard let self, self.ngAppearancePending, self.ngAppearanceGate.generation == generation,
                  !self.ngBackdropHeld, UIApplication.shared.applicationState == .active else { return }
            self.renderer?.setNeedsRender()
            if retries > 0 {
                self.ngCheckPlatterAppearance(generation, retries: retries - 1)
            } else {
                // Lost drawable: use the existing real material fallback, not a
                // success callback for a frame that never reached display.
                self.ngPresented = false
                self.ngPrepareReplacement()
                self.ngClearPlatterAppearance()
            }
            // When inactive, the renderer requests a fresh frame on activation.
        }
    }

    private func ngFinishPlatterAppearance(_ ticket: NGTabAppearanceTicket) {
        guard UIApplication.shared.applicationState == .active,
              ngAppearancePending, ngAppearanceGate.accept(ticket) else { return }
        let generation = ticket.generation
        ngAppearancePending = false
        renderer?.ngAppearanceTicket = nil
        renderer?.ngVisiblePresent = nil''')
    s = rep(s, 'self.ngAppearanceEpoch == epoch', 'self.ngAppearanceGate.generation == generation')
    s = rep(s, '''        ngAppearanceImage.opacity = 0
        let fade = CABasicAnimation(keyPath: "opacity")
        fade.fromValue = 1''', '''        let visibleOpacity = ngAppearanceImage.presentation()?.opacity ?? ngAppearanceImage.opacity
        ngAppearanceImage.opacity = 0
        let fade = CABasicAnimation(keyPath: "opacity")
        fade.fromValue = visibleOpacity''')
    s = rep(s, '''        ngAppearanceEpoch &+= 1
        ngAppearancePending = false
        renderer?.ngVisiblePresent = nil''', '''        ngAppearanceGate.begin()
        ngAppearancePending = false
        renderer?.ngAppearanceTicket = nil
        renderer?.ngVisiblePresent = nil''')
    s = rep(s, '        if !held { renderer?.setNeedsRender() }', '''        if !held {
            renderer?.setNeedsRender()
            if ngAppearancePending { ngCheckPlatterAppearance(ngAppearanceGate.generation, retries: 2) }
        }''')
    return rep(s, '            name: TheseusSettings.settingsDidChangeNotification,\n            object: nil\n        )', '''            name: TheseusSettings.settingsDidChangeNotification,
            object: nil
        )
        NotificationCenter.default.addObserver(self, selector: #selector(ngPlatterBecameActive),
                                               name: UIApplication.didBecomeActiveNotification, object: nil)''')


def renderer(s, rep):
    s = rep(s, '    var ngVisiblePresent: (() -> Void)?', '''    var ngAppearanceTicket: NGTabAppearanceTicket?
    var ngVisiblePresent: ((NGTabAppearanceTicket) -> Void)?''')
    s = rep(s, '''        if let visiblePresent = ngVisiblePresent {
            drawable.addPresentedHandler { shown in
                guard shown.presentedTime > 0 else { return }
                DispatchQueue.main.async(execute: visiblePresent)
            }
        }''', '''        if let ticket = ngAppearanceTicket, let visiblePresent = ngVisiblePresent,
           let hostView, ticket.dark == (hostView.traitCollection.userInterfaceStyle == .dark) {
            // This ticket belongs to these encoded uniforms, not a later trait callback.
            drawable.addPresentedHandler { shown in
                guard shown.presentedTime > 0 else { return }
                DispatchQueue.main.async { visiblePresent(ticket) }
            }
        }''')
    return rep(s, '''        if let host = hostView, host.window == nil { return }
        startRendering()
    }

    private func encodeSnapshot''', '''        if let host = hostView, host.window == nil { return }
        startRendering()
        setNeedsRender()
    }

    private func encodeSnapshot''')
