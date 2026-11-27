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
    gradient = '''        if solidBackdrop != nil {
            ctx.saveGState()
            ctx.clip(to: region)
            ctx.translateBy(x: region.minX, y: region.minY)
            ctx.scaleBy(x: region.width, y: region.height)

            func drawSoftbox(center: CGPoint, radii: CGSize, color: UIColor, alpha: CGFloat) {
                guard let glow = CGGradient(
                    colorsSpace: CGColorSpaceCreateDeviceRGB(),
                    colors: [color.withAlphaComponent(alpha).cgColor,
                             color.withAlphaComponent(0).cgColor] as CFArray,
                    locations: [0, 1]) else { return }
                ctx.saveGState()
                ctx.translateBy(x: center.x, y: center.y)
                ctx.scaleBy(x: radii.width, y: radii.height)
                ctx.drawRadialGradient(glow, startCenter: .zero, startRadius: 0,
                                       endCenter: .zero, endRadius: 1, options: [])
                ctx.restoreGState()
            }

            drawSoftbox(center: CGPoint(x: 0.22, y: 0.16), radii: CGSize(width: 0.90, height: 0.82), color: UIColor(red: 0.58, green: 0.78, blue: 1.0, alpha: 1), alpha: 0.55)
            drawSoftbox(center: CGPoint(x: 0.78, y: 0.82), radii: CGSize(width: 0.88, height: 0.70), color: UIColor(red: 0.10, green: 0.80, blue: 0.92, alpha: 1), alpha: 0.30)
            drawSoftbox(center: CGPoint(x: 0.78, y: 0.18), radii: CGSize(width: 0.50, height: 0.48), color: .white, alpha: 0.25)
            ctx.restoreGState()
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
