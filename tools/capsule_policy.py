"""Keep the hosted capsule opaque without changing the platter or lens motion."""


def tab(s, rep):
    s = rep(s, '        selectionView.ngSetSolidSelectionTone(dark: dark, animated: animate)\n', '''        selectionView.ngSetSolidSelectionTone(dark: dark, animated: animate)
        theseusView?.ngCapsuleBackdrop = selectionView.renderedCenterColor
''')
    s = rep(s, '        glassView.ngNonblockingRendering = ngUseHostPosition\n', '''        glassView.ngNonblockingRendering = ngUseHostPosition
        if ngUseHostPosition {
            glassView.ngCapsuleBackdrop = selectionView.renderedCenterColor
        }
''')
    s = rep(s, '''    private func hideTheseus() {''', '''    private func ngPlaceOpaqueReleasePill(_ frame: CGRect) {
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
        if ngUseHostPosition { ngPlaceOpaqueReleasePill(releaseFrame) }
''')
    return rep(s, '''                // The settled pill only takes over once the lens is near the target.
                let share = min(max((progress - 0.72) / 0.28, 0), 1)
                self.selectionView.alpha = share
                glassView.alpha = 1 - share''', '''                self.ngPlaceOpaqueReleasePill(frame)
                glassView.alpha = 1 - min(max(progress, 0), 1)''')


def surface(s, rep):
    s = rep(s, '    var ngOpaqueBackdrop = false\n', '''    var ngOpaqueBackdrop = false
    var ngCapsuleBackdrop: UIColor? {
        didSet {
            guard oldValue != ngCapsuleBackdrop else { return }
            fallbackView?.ngCapsuleBackdrop = ngCapsuleBackdrop
            renderer?.setNeedsRender()
        }
    }
''')
    return rep(s, '            fallbackView?.ngFrostedPlatter = ngFrostedPlatter\n', '''            fallbackView?.ngFrostedPlatter = ngFrostedPlatter
            fallbackView?.ngCapsuleBackdrop = ngCapsuleBackdrop
''')


def renderer(s, rep):
    return rep(s, '                    limitCompensation: ngNonblockingRendering\n', '''                    limitCompensation: ngNonblockingRendering,
                    solidBackdrop: (hostView as? TheseusView)?.ngCapsuleBackdrop?.cgColor
''', count=2)


def capture(s, rect, rep):
    s = rep(s, '        limitCompensation: Bool = false\n', '''        limitCompensation: Bool = false,
        solidBackdrop: CGColor? = nil
''')
    # In opaque mode the lens gets a synthetic gradient, never page pixels.
    for start in ('        let hiddenStates = excludedViews.map', '        let previousVisibility = excludedViews.map'):
        if start in s:
            s = rep(s, start, '        let viewsToHide = solidBackdrop == nil ? excludedViews : []\n' + start.replace('excludedViews', 'viewsToHide'))
    s = rep(s, '        excludedViews.forEach { $0.isHidden = true }', '        viewsToHide.forEach { $0.isHidden = true }')
    s = rep(s, 'zip(excludedViews, ', 'zip(viewsToHide, ')
    s = rep(s, '        let compensation = CaptureCompensation.begin(in: sourceView, region: limitCompensation ? region : nil)',
            '        let compensation = solidBackdrop == nil\n            ? CaptureCompensation.begin(in: sourceView, region: limitCompensation ? region : nil) : []')
    opaqueFill = ('        if opaqueBackdrop {\n'
                  '            ctx.setFillColor(UIColor.systemBackground.resolvedColor(with: sourceView.traitCollection).cgColor)\n'
                  '            ctx.fill(' + rect + ')\n'
                  '        }\n')
    s = rep(s, opaqueFill, '''        if solidBackdrop == nil && opaqueBackdrop {
            ctx.setFillColor(UIColor.systemBackground.resolvedColor(with: sourceView.traitCollection).cgColor)
            ctx.fill(''' + rect + ''')
        }
''')
    gradient = '''        if let solidBackdrop {
            let components = solidBackdrop.components ?? [0.88, 0.88, 0.88, 1]
            let baseRed = components.count >= 4 ? components[0] : components[0]
            let baseGreen = components.count >= 4 ? components[1] : components[0]
            let baseBlue = components.count >= 4 ? components[2] : components[0]
            func neutralGlassColor(_ factor: CGFloat, _ bias: CGFloat) -> CGColor {
                func clamp(_ value: CGFloat) -> CGFloat { min(max(value, 0), 1) }
                return CGColor(red: clamp(baseRed * factor + bias),
                               green: clamp(baseGreen * factor + bias),
                               blue: clamp(baseBlue * factor + bias), alpha: 1)
            }
            let colors: [CGColor] = [
                neutralGlassColor(0.965, 0),
                neutralGlassColor(1.015, 0.006),
                neutralGlassColor(0.975, 0.002)
            ]
            let locations: [CGFloat] = [0, 0.54, 1]
            if let gradient = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(),
                                          colors: colors as CFArray, locations: locations) {
                ctx.saveGState()
                ctx.clip(to: region)
                ctx.drawLinearGradient(gradient,
                    start: CGPoint(x: region.minX, y: region.maxY),
                    end: CGPoint(x: region.maxX, y: region.minY), options: [])
                let highlight = CGGradient(colorsSpace: CGColorSpaceCreateDeviceRGB(),
                    colors: [UIColor.white.withAlphaComponent(0.10).cgColor,
                             UIColor.white.withAlphaComponent(0).cgColor] as CFArray,
                    locations: [0, 1])
                if let highlight {
                    ctx.saveGState()
                    ctx.translateBy(x: region.minX, y: region.minY)
                    ctx.scaleBy(x: region.width, y: region.height)
                    ctx.drawRadialGradient(highlight,
                        startCenter: CGPoint(x: 0.27, y: 0.24), startRadius: 0.01,
                        endCenter: CGPoint(x: 0.27, y: 0.24), endRadius: 0.70, options: [])
                    ctx.restoreGState()
                }
                ctx.restoreGState()
            } else {
                ctx.setFillColor(solidBackdrop)
                ctx.fill(region)
            }
        }
        if solidBackdrop == nil { sourceView.layer.render(in: ctx) }
'''
    return rep(s, '        sourceView.layer.render(in: ctx)\n', gradient)


def fallback(s, rep):
    return rep(s, '    private let blurView: UIVisualEffectView\n', '''    private let blurView: UIVisualEffectView
    var ngCapsuleBackdrop: UIColor? {
        didSet {
            blurView.isHidden = ngCapsuleBackdrop != nil
            backgroundColor = ngCapsuleBackdrop ?? .clear
        }
    }
''')
