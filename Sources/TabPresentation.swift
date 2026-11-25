import Foundation
import CoreGraphics

// Equal-width slots share one center for the icon, title and selection.
// Outer platter geometry stays fixed. Its ends receive the same 4 pt gap
// as the gap between adjacent capsule positions.
enum NGTabPresentation {
    private static let gap: CGFloat = 4

    static func slotStrip(platter: CGRect) -> CGRect {
        guard platter.width > gap else { return platter }
        return platter.insetBy(dx: gap / 2, dy: 0)
    }

    static func capsule(slot: CGRect) -> CGRect {
        guard slot.width > gap, slot.height > 2 * gap else { return slot }
        return slot.insetBy(dx: gap / 2, dy: gap)
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
