import Foundation
import CoreGraphics

// Only the selection shape changes: icon slots, platter and bar placement stay fixed.
enum NGTabPresentation {
    static func capsule(slot: CGRect, platter: CGRect, itemInset: CGFloat) -> CGRect {
        guard !slot.isEmpty, !platter.isEmpty else { return slot }
        let gap: CGFloat = 4
        let first = abs(slot.minX - (platter.minX + itemInset)) < 1
        let last = abs(slot.maxX - (platter.maxX - itemInset)) < 1
        let left = first ? platter.minX + gap : slot.minX + gap / 2
        let right = last ? platter.maxX - gap : slot.maxX - gap / 2
        return CGRect(x: left, y: platter.minY + gap,
                      width: max(0, right - left), height: max(0, platter.height - 2 * gap))
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
