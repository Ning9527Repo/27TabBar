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

    func ngPrepareReplacement() {
        backgroundGlassView.ngPrepareReplacement()
        selectionView.ngPrepareReplacement()
    }

    var ngHostIsInteracting: Bool { isDragging }

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
    s = replace(s, '        let contentWidth = min(bounds.width,', '        if ngUseHostPosition { return bounds }\n        let contentWidth = min(bounds.width,')
    s = replace(s, '        let size = pillSize\n', '        let base = pillSize\n        let size = CGSize(width: ngUseHostPosition ? max(base.width, itemFrame.width - 4) : base.width, height: base.height)\n')
    s = replace(s, '        let size = usesIOS26Look ? Self.iOS26LensSize : Self.lensSize\n', '        let base = usesIOS26Look ? Self.iOS26LensSize : Self.lensSize\n        let size = CGSize(width: ngUseHostPosition ? max(base.width, selectionFrame(for: itemFrame).width + 16) : base.width, height: base.height)\n')
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
    s = replace(s, '    public var onPresent: (() -> Void)? {\n        didSet { renderer?.onPresent = onPresent }\n    }', '''    private var ngWaitingForPresent = false
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
