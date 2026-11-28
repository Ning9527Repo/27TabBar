"""Antialias the hosted platter rim without resizing its blur or layout."""


def tab(s, rep):
    s = rep(s, '''        let frame = rect.insetBy(dx: -margin, dy: -margin)
        barEdgeShadeLayer.frame = frame
        barEdgeGlowLayer.frame = frame
        guard !ngPalettePending else { return }
        let scale = traitCollection.displayScale > 0 ? traitCollection.displayScale : UIScreen.main.scale
        let amplitude = usesIOS26Look ? iOS26RimAmplitude() : nil
        let key = [rect.width, rect.height, isDarkAppearance ? 1 : 0] + (amplitude ?? [])''', '''        let scale = traitCollection.displayScale > 0 ? traitCollection.displayScale : UIScreen.main.scale
        let rawFrame = rect.insetBy(dx: -margin, dy: -margin)
        var frame = rawFrame
        if ngUseHostPosition, let window {
            let inWindow = backgroundView.convert(rawFrame, to: window)
            // Snap the image's canvas, not the capsule's outline.
            if abs(inWindow.width - rawFrame.width) < 0.01, abs(inWindow.height - rawFrame.height) < 0.01 {
                let minX = floor(inWindow.minX * scale) / scale
                let minY = floor(inWindow.minY * scale) / scale
                let maxX = ceil(inWindow.maxX * scale) / scale
                let maxY = ceil(inWindow.maxY * scale) / scale
                frame = CGRect(x: rawFrame.minX + (minX - inWindow.minX),
                               y: rawFrame.minY + (minY - inWindow.minY), width: maxX - minX, height: maxY - minY)
            }
        }
        barEdgeShadeLayer.frame = frame
        barEdgeGlowLayer.frame = frame
        guard !ngPalettePending else { return }
        let origin = ngUseHostPosition ? CGPoint(x: -frame.minX, y: -frame.minY) : CGPoint(x: margin, y: margin)
        let amplitude = usesIOS26Look ? iOS26RimAmplitude() : nil
        var key: [CGFloat] = [rect.width, rect.height, frame.width, frame.height, origin.x, origin.y, scale,
                              ngUseHostPosition ? 1 : 0, isDarkAppearance ? 1 : 0]
        if let amplitude { key += amplitude }''')
    s = rep(s, 'outline: rect.offsetBy(dx: margin, dy: margin), scale: scale, isDark: isDarkAppearance, amplitude: amplitude)',
            'outline: rect.offsetBy(dx: origin.x, dy: origin.y), scale: scale, isDark: isDarkAppearance, amplitude: amplitude, antialias: ngUseHostPosition)')
    s = rep(s, '.offsetBy(dx: margin, dy: margin)\n            images = Self.edgeImages(size: frame.size, body: body, scale: scale, isDark: isDarkAppearance)',
            '.offsetBy(dx: origin.x, dy: origin.y)\n            images = Self.edgeImages(size: frame.size, body: body, scale: scale, isDark: isDarkAppearance, antialias: ngUseHostPosition)')
    s = rep(s, '    static func iOS26RimImage(size: CGSize, outline: CGRect, scale: CGFloat, isDark: Bool, amplitude: [CGFloat]) -> CGImage? {', '''    /// Area of a unit pixel covered by the tangent half-plane at this signed distance.
    static func ngRimCoverage(_ distance: CGFloat, normalX: CGFloat, normalY: CGFloat) -> CGFloat {
        let major = max(abs(normalX), abs(normalY))
        let minor = min(abs(normalX), abs(normalY))
        let outer = (major + minor) / 2
        let offset = abs(distance)
        if offset >= outer { return distance < 0 ? 1 : 0 }
        if offset <= (major - minor) / 2 || minor < 0.0001 {
            return min(max(0.5 - distance / major, 0), 1)
        }
        let tail = outer - offset
        let area = tail * tail / (2 * major * minor)
        return distance < 0 ? 1 - area : area
    }

    static func iOS26RimImage(size: CGSize, outline: CGRect, scale: CGFloat, isDark: Bool, amplitude: [CGFloat], antialias: Bool = false) -> CGImage? {''')
    s = rep(s, '''                depth -= CapsuleEnds.inset(along: qx, radius: radius)
                guard depth > 0, depth < CGFloat(table[0].count) else { continue }''', '''                let coverage: CGFloat
                let limit = CGFloat(table[0].count)
                if antialias {
                    // Match the circular UIVisualEffectView clip, including the cap tangents.
                    coverage = ngRimCoverage(-depth, normalX: normalX, normalY: normalY)
                        - ngRimCoverage(limit - depth, normalX: normalX, normalY: normalY)
                    guard coverage > 0 else { continue }
                    depth = max(depth, 0)
                } else {
                    depth -= CapsuleEnds.inset(along: qx, radius: radius)
                    guard depth > 0, depth < limit else { continue }
                    coverage = 1
                }''')
    s = rep(s, 'amplitude[channel] * strength, 0', 'amplitude[channel] * strength * coverage, 0')
    s = rep(s, 'private static func edgeImages(size: CGSize, body: CGRect, scale: CGFloat, isDark: Bool)',
            'private static func edgeImages(size: CGSize, body: CGRect, scale: CGFloat, isDark: Bool, antialias: Bool = false)')
    s = rep(s, '                distance += CapsuleEnds.inset(along: qx, radius: radius)\n                let side',
            '                if !antialias { distance += CapsuleEnds.inset(along: qx, radius: radius) }\n                let side')
    return rep(s, '''                if distance >= 0 {
                    if distance < 1 {''', '''                if antialias {
                    let inside = ngRimCoverage(distance, normalX: normalX, normalY: normalY)
                    let near = ngRimCoverage(distance - 1, normalX: normalX, normalY: normalY)
                    let far = ngRimCoverage(distance - 2, normalX: normalX, normalY: normalY)
                    shadeAlpha = (near - inside) * (isDark ? 0.70 * side : 0.12 + 0.23 * side)
                        + (far - near) * (isDark ? 0.34 * side : 0.06 + 0.11 * side)
                    if inside > 0 {
                        let depth = max(-distance, 0)
                        glowLevel = profile(glowProfile, at: depth) * vertical * inside
                        if normalY < 0 {
                            shadeAlpha += 0.016 * exp(-pow((depth - 33) / 18, 2)) * normalY * normalY * inside
                        }
                        shadeAlpha += 0.021 * exp(-pow(depth / 35, 2)) * normalX * normalX * inside
                    }
                } else if distance >= 0 {
                    if distance < 1 {''')
