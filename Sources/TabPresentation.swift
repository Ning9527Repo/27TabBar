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

// A presentation can release the previous palette only after a frame encoded
// with this exact theme generation and prepared material has reached display.
struct NGTabAppearanceTicket: Equatable {
    let generation: UInt64
    let revision: UInt64
    let dark: Bool
}

struct NGTabAppearanceGate {
    private(set) var generation: UInt64 = 0
    private var revision: UInt64 = 0
    private(set) var expected: NGTabAppearanceTicket? = nil

    @discardableResult
    mutating func begin() -> UInt64 {
        generation &+= 1
        expected = nil
        return generation
    }

    mutating func prepare(dark: Bool) -> NGTabAppearanceTicket {
        revision &+= 1
        let ticket = NGTabAppearanceTicket(generation: generation, revision: revision, dark: dark)
        expected = ticket
        return ticket
    }

    mutating func accept(_ ticket: NGTabAppearanceTicket) -> Bool {
        guard expected == ticket else { return false }
        expected = nil
        return true
    }
}

// Equal-width slots share one center for the icon, title and selection.
// Outer platter geometry stays fixed. Its ends receive the same 4 pt gap
// as the gap between adjacent capsule positions.
enum NGTabPresentation {
    static let appearanceDuration: TimeInterval = 0.15
    private static let gap: CGFloat = 4

    static func pixelAligned(_ rect: CGRect, scale: CGFloat) -> CGRect {
        guard scale.isFinite, scale > 0, rect.minX.isFinite, rect.minY.isFinite,
              rect.width.isFinite, rect.height.isFinite, !rect.isNull else { return rect }
        let minX = (rect.minX * scale).rounded() / scale
        let minY = (rect.minY * scale).rounded() / scale
        let maxX = (rect.maxX * scale).rounded() / scale
        let maxY = (rect.maxY * scale).rounded() / scale
        return CGRect(x: minX, y: minY, width: max(0, maxX - minX), height: max(0, maxY - minY))
    }

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
