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
    var ngUseHostPosition = false
    var ngHostFrame = CGRect.zero
    var ngGlassDidPresent: (() -> Void)? {
        didSet { backgroundGlassView.onPresent = ngGlassDidPresent }
    }
    private let ngNativeButtons = NSHashTable<UIView>.weakObjects()
    private let ngNativeBackgrounds = NSHashTable<UIView>.weakObjects()
    private var ngNativeBitmaps: [(view: UIView, image: UIImage, hidden: Bool)] = []
    var ngHostIsInteracting: Bool { isDragging }

    func ngBindNativeViews(_ buttons: [UIView], backgrounds: [UIView]) {
        ngNativeButtons.removeAllObjects()
        ngNativeBackgrounds.removeAllObjects()
        buttons.forEach { ngNativeButtons.add($0) }
        backgrounds.forEach { ngNativeBackgrounds.add($0) }
        let excluded: [UIView] = [self] + buttons + backgrounds + [theseusView].compactMap { $0 }
        backgroundGlassView.setCaptureExcludedViews(excluded)
        selectionView.setCaptureExcludedViews(excluded)
        theseusView?.setCaptureExcludedViews(buttons)
        itemsContainerView?.isHidden = true
        accessibilityElements = []
    }

    func ngCancelNativeInteraction() { endDragImmediately() }

    func ngFinishNativePress(_ nativeIndex: Int) {
        guard isDragging, nativeIndex >= 0, nativeIndex < slotFrames.count else { return }
        let callback = onItemSelected
        onItemSelected = nil
        defer { onItemSelected = callback }
        // UIKit already handled the tap. Collapse the original lens without
        // synthesizing another button action.
        finishInteraction(rawX: slotFrame(at: nativeIndex).midX - fingerAnchorOffset)
    }

    private func ngNativeCapture(_ begin: Bool) {
        if begin {
            guard ngNativeBitmaps.isEmpty else { return }
            for button in ngNativeButtons.allObjects where !button.isHidden && !button.bounds.isEmpty {
                let format = UIGraphicsImageRendererFormat()
                format.scale = button.window?.screen.scale ?? UIScreen.main.scale
                format.opaque = false
                let image = UIGraphicsImageRenderer(size: button.bounds.size, format: format).image { output in
                    output.cgContext.translateBy(x: -button.bounds.minX, y: -button.bounds.minY)
                    button.layer.render(in: output.cgContext)
                }
                ngNativeBitmaps.append((button, image, button.isHidden))
                button.isHidden = true
            }
        } else {
            for entry in ngNativeBitmaps { entry.view.isHidden = entry.hidden }
            ngNativeBitmaps.removeAll()
        }
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
    # Keep the upstream compact capsule; host positioning changes only the outer frame.
    s = replace(s, '        super.layoutSubviews()\n\n        contentView.bounds = bounds', '''        super.layoutSubviews()

        let buttons = ngNativeButtons.allObjects
        let exclusions: [UIView] = [self] + buttons + ngNativeBackgrounds.allObjects + [theseusView].compactMap { $0 }
        backgroundGlassView.setCaptureExcludedViews(exclusions)
        selectionView.setCaptureExcludedViews(exclusions)
        theseusView?.setCaptureExcludedViews(buttons)
        itemsContainerView?.isHidden = ngUseHostPosition
        contentView.bounds = bounds''')
    s = replace(s, '            CGRect(x: barFrame.minX + CGFloat(index) * itemWidth, y: 0, width: itemWidth, height: itemHeight)', '''            let rtl = ngUseHostPosition && effectiveUserInterfaceLayoutDirection == .rightToLeft
            let slot = rtl ? itemViews.count - index - 1 : index
            return CGRect(x: barFrame.minX + CGFloat(slot) * itemWidth, y: 0, width: itemWidth, height: itemHeight)''')
    s = replace(s, '        theseusSourceView?.superview\n', '        ngUseHostPosition ? ngExcludedBar : theseusSourceView?.superview\n')
    s = replace(s, '        glassView.sourceView = sourceView\n        glassView.isHidden', '        glassView.sourceView = sourceView\n        glassView.setCaptureExcludedViews(ngNativeButtons.allObjects)\n        glassView.isHidden')
    s = replace(s, '            self?.showCaptureTint(true)', '            if self?.ngUseHostPosition == true { self?.ngNativeCapture(true) }\n            else { self?.showCaptureTint(true) }')
    s = replace(s, '            self?.showCaptureTint(false)', '            if self?.ngUseHostPosition == true { self?.ngNativeCapture(false) }\n            else { self?.showCaptureTint(false) }')
    s = replace(s, '        guard itemsHiddenForCapture else { return }\n        Self.render', '''        if ngUseHostPosition {
            for entry in ngNativeBitmaps {
                let transform = Self.affineTransform(from: entry.view, to: sourceView)
                context.saveGState()
                context.concatenate(transform)
                entry.image.draw(in: entry.view.bounds)
                context.restoreGState()
            }
            return
        }
        guard itemsHiddenForCapture else { return }
        Self.render''')
    s = replace(s, '        glassView.resumeRendering()\n', '        if ngUseHostPosition { container.bringSubviewToFront(glassView) }\n        glassView.resumeRendering()\n')
    s = replace(s, '        theseusView = glassView\n        applyAdaptiveOverride()', '''        theseusView = glassView
        if ngUseHostPosition {
            let excluded: [UIView] = [self, glassView] + ngNativeButtons.allObjects + ngNativeBackgrounds.allObjects
            backgroundGlassView.setCaptureExcludedViews(excluded)
            selectionView.setCaptureExcludedViews(excluded)
        }
        applyAdaptiveOverride()''')
    s = replace(s, '        guard !isDragging, isUserInteractionEnabled else { return }', '        guard !isDragging, isUserInteractionEnabled || ngUseHostPosition else { return }')
    s = replace(s, '        contentView.bringSubviewToFront(container)\n        if captureTwinRow', '        if ngUseHostPosition { container.isHidden = true; accessibilityElements = [] }\n        contentView.bringSubviewToFront(container)\n        if captureTwinRow')
    s = replace(s, '''        guard index != selectedIndex else { return }
        selectedIndex = index
        onItemSelected?(index)''', '''        guard items.indices.contains(index), items[index].ngEnabled else { return }
        guard index != selectedIndex || ngUseHostPosition else { return }
        selectedIndex = index
        onItemSelected?(index)''')
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
            let shouldSend = landingIndex != selectedIndex || ngUseHostPosition
            isCommittingDrag = true
            selectedIndex = landingIndex
            isCommittingDrag = false
            if shouldSend { onItemSelected?(landingIndex) }
        }''')
    s = replace(s, '''            if landingIndex < self.slotFrames.count {
                animator?.retarget(to: self.convertToTheseusContainer(self.selectionFrame(for: self.slotFrame(at: landingIndex))))
            }''', '''            let current = self.selectedIndex
            if current >= 0 && current < self.slotFrames.count {
                animator?.retarget(to: self.convertToTheseusContainer(self.selectionFrame(for: self.slotFrame(at: current))))
            }''')
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
    s = replace(s, '        willCapture?()\n        defer { didCapture?() }', '        NGSystemTabCaptureBegin()\n        willCapture?()\n        defer { didCapture?(); NGSystemTabCaptureEnd() }')
    return replace(s, '            commandBuffer.addCompletedHandler { _ in\n                DispatchQueue.main.async(execute: onPresent)', '            commandBuffer.addCompletedHandler { buffer in\n                guard buffer.status == .completed else { return }\n                DispatchQueue.main.async(execute: onPresent)')


def surface(s):
    # Match drawable geometry to the padded Metal texture. Keep the shader's
    # logical host bounds and account for padding exactly once in capture.
    s = replace(s, '        return (metalLayerView?.frame ?? bounds).insetBy(dx: -padding.x, dy: -padding.y)', '        return bounds.insetBy(dx: -padding.x, dy: -padding.y)')
    s = replace(s, '        metalLayer.contentsGravity = .center', '        metalLayer.contentsGravity = .resize')
    return replace(s, '        let paddingX = padding.x * scale\n', '        metalLayerView?.frame = bounds.insetBy(dx: -padding.x, dy: -padding.y)\n        let paddingX = padding.x * scale\n')


def compensation(s):
    return replace(s, '                glass.backgroundColor = glass.captureVeilColor', '''                let layer = CALayer()
                layer.frame = glass.bounds.insetBy(dx: glass.shape.widthInset, dy: glass.shape.heightInset)
                layer.cornerRadius = min(glass.shape.cornerRadius, min(layer.bounds.width, layer.bounds.height) / 2)
                layer.backgroundColor = glass.captureVeilColor.cgColor
                glass.layer.insertSublayer(layer, above: host.layer)
                entry.snapshotLayer = layer''')


def stage(dst):
    verify_vendor()
    patches = {'TheseusTabBar.swift':tabbar,'TheseusRenderer.swift':renderer,
               'TheseusView.swift':surface,'CaptureCompensation.swift':compensation}
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
