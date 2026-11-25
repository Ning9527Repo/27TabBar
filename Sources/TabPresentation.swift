import Foundation
import CoreGraphics

// One recognizer owns an interaction, including its end or cancellation.
struct NGTabInteractionGate {
    private var active: ObjectIdentifier? = nil

    mutating func begin(_ owner: ObjectIdentifier) -> Bool {
        guard active == nil else { return false }
        active = owner
        return true
    }

    func accepts(_ owner: ObjectIdentifier) -> Bool { active == owner }

    mutating func end(_ owner: ObjectIdentifier) -> Bool {
        guard accepts(owner) else { return false }
        active = nil
        return true
    }

    mutating func clear() { active = nil }
}

// Preserve the initial press animation until the finger actually moves.
// Once tracking starts it stays direct, including on reversals and at rest.
struct NGTabDirectFollow {
    private var origin: CGFloat? = nil
    private(set) var isTracking = false

    mutating func update(_ x: CGFloat) -> Bool {
        guard x.isFinite else { return false }
        if let origin {
            if abs(x - origin) >= 1 { isTracking = true }
        } else {
            origin = x
        }
        return isTracking
    }

    mutating func reset() {
        origin = nil
        isTracking = false
    }
}

// Equal-width slots share one center for the icon, title and selection.
// Outer platter geometry stays fixed. Its ends receive the same 4 pt gap
// as the gap between adjacent capsule positions.
enum NGTabPresentation {
    static let appearanceDuration: TimeInterval = 0.15
    private static let gap: CGFloat = 4

    static func slotStrip(platter: CGRect) -> CGRect {
        guard platter.width > gap else { return platter }
        return platter.insetBy(dx: gap / 2, dy: 0)
    }

    static func capsule(slot: CGRect) -> CGRect {
        guard slot.width > gap, slot.height > 2 * gap else { return slot }
        return slot.insetBy(dx: gap / 2, dy: gap)
    }

    // Insets are unscaled shape coordinates. Recover the visible footprint
    // without changing the drawable's bounds or removing its transform.
    static func visibleLens(frame: CGRect, bounds: CGRect, inset: CGSize) -> CGRect? {
        guard frame.minX.isFinite, frame.minY.isFinite, frame.width.isFinite, frame.height.isFinite,
              bounds.width.isFinite, bounds.height.isFinite, inset.width.isFinite, inset.height.isFinite,
              frame.width > 0, frame.height > 0, bounds.width > 0, bounds.height > 0,
              bounds.width > 2 * inset.width, bounds.height > 2 * inset.height else { return nil }
        let visible = frame.insetBy(dx: inset.width * (frame.width / bounds.width),
                                    dy: inset.height * (frame.height / bounds.height))
        return visible.width.isFinite && visible.height.isFinite && !visible.isEmpty ? visible : nil
    }

    static func title(_ candidates: String?...) -> String? {
        for candidate in candidates {
            if let value = candidate?.trimmingCharacters(in: .whitespacesAndNewlines), !value.isEmpty {
                return value
            }
        }
        return nil
    }

    static func shortLabel(_ value: String?) -> String? {
        guard let text = title(value), text.count <= 32,
              text.rangeOfCharacter(from: .newlines) == nil,
              text.rangeOfCharacter(from: CharacterSet(charactersIn: ",，、;；")) == nil else { return nil }
        return text
    }
}
