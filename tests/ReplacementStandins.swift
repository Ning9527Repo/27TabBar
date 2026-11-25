import Foundation
import CoreGraphics

struct AutoMask: OptionSet { let rawValue: Int }
class UIColor: NSObject { static let clear = UIColor(); static let blue = UIColor() }
class UIImage: NSObject { enum Mode { case alwaysTemplate }; func withRenderingMode(_ mode: Mode) -> UIImage { self } }
class CALayer: NSObject {
    var mask: CALayer?
    var frame = CGRect.zero
    var backgroundColor: NSObject?
}
extension UIColor { var cgColor: NSObject { self } }
enum CATransaction {
    static func begin() {}
    static func commit() {}
    static func setDisableActions(_ v: Bool) {}
}
enum Direction { case leftToRight, rightToLeft }
enum Style { case unspecified, light, dark }
enum Semantic { case unspecified, forceLeftToRight, forceRightToLeft }
enum Idiom { case phone, pad }
class Traits { var userInterfaceIdiom = Idiom.phone; var userInterfaceStyle = Style.light }
class UIView: NSObject {
    var frame = CGRect.zero
    var bounds = CGRect.zero
    var alpha: CGFloat = 1
    var isHidden = false
    var isUserInteractionEnabled = true
    var accessibilityElementsHidden = false
    var autoresizingMask: AutoMask = []
    var layer = CALayer()
    weak var superview: UIView?
    weak var window: UIWindow?
    var subviews: [UIView] = []
    var traitCollection = Traits()
    var effectiveUserInterfaceLayoutDirection = Direction.leftToRight
    var overrideUserInterfaceStyle = Style.unspecified
    var semanticContentAttribute = Semantic.unspecified
    var tintColor: UIColor! = .blue
    func insertSubview(_ view: UIView, aboveSubview sibling: UIView) {
        view.removeFromSuperview()
        let i = subviews.firstIndex(where: { $0 === sibling }) ?? subviews.count-1
        subviews.insert(view, at: min(i+1, subviews.count)); view.superview = self; view.window = window
    }
    func removeFromSuperview() { superview?.subviews.removeAll(where: { $0 === self }); superview = nil; window = nil }
    func convert(_ p: CGPoint, to v: UIView?) -> CGPoint { p }
    func convert(_ r: CGRect, to v: UIView?) -> CGRect { r.offsetBy(dx: frame.minX, dy: frame.minY) }
    func convert(_ r: CGRect, from v: UIView?) -> CGRect { r }
    static func performWithoutAnimation(_ block: () -> Void) { block() }
}
class UIViewController { var viewIfLoaded: UIView? }
class UIWindow: UIView { var rootViewController: UIViewController?; var safeAreaInsets = (bottom: CGFloat(34), top: CGFloat(0)) }
class UIScrollView: UIView { var contentOffset = CGPoint.zero }
class UIControl: UIView { var isEnabled = true; var isSelected = false; var nativeTitle: String?; var nativeImage: UIImage?; var accessibilityLabel: String? }
class UITabBarItem: NSObject {
    var title: String?; var image: UIImage?; var selectedImage: UIImage?; var accessibilityLabel: String?
    var badgeValue: String?; var badgeColor: UIColor?; var isEnabled = true
}
class UITabBar: UIView {
    var items: [UITabBarItem]?; var selectedItem: UITabBarItem?; var isCustomizing = false
    var unselectedItemTintColor: UIColor?; var controls: [UIControl]?
}
struct TheseusTabBarItem {
    var icon: UIImage?; var selectedIcon: UIImage?; var title: String?
    var ngLabel: String?; var ngBadge: String?; var ngBadgeColor: UIColor?; var ngEnabled = true
    init(icon: UIImage?, selectedIcon: UIImage?, title: String?) { self.icon = icon; self.selectedIcon = selectedIcon; self.title = title }
}
class TheseusTabBar: UIView {
    weak var ngExcludedBar: UITabBar?
    var ngUseHostPosition = false; var ngHostFrame = CGRect.zero
    var ngGlassDidPresent: (() -> Void)?; var ngActivateNative: ((Int) -> Int?)?
    var items: [TheseusTabBarItem] = []; var selectedIndex = 0
    var barHeight: CGFloat = 63; var preferredItemWidth: CGFloat = 66
    var selectedTintColor = UIColor.blue; var unselectedTintColor = UIColor.clear
    static let nativeUnselectedTint = UIColor.clear
    var prepared = 0; var invalidations = 0
    init(frame: CGRect) { super.init(); self.frame = frame; bounds = CGRect(origin: .zero, size: frame.size) }
    func ngApplyHostFrame(_ f: CGRect) { ngHostFrame = f; frame = f; bounds = CGRect(origin: .zero, size: f.size) }
    func ngPrepareReplacement() { prepared += 1 }
    func ngRefreshItems(_ newItems: [TheseusTabBarItem], changed: [Int]) { items = newItems }
    func ngApplySelection(_ index: Int) { if selectedIndex != index { selectedIndex = index } }
    func invalidateBackground() { invalidations += 1 }
}
class UIApplication {
    static let shared = UIApplication()
    enum State { case active, background }
    var applicationState = State.active
    static let didBecomeActiveNotification = Notification.Name("active")
    static let didEnterBackgroundNotification = Notification.Name("background")
    static let protectedDataDidBecomeAvailableNotification = Notification.Name("unlock")
}
enum UIAccessibility {
    static var isVoiceOverRunning = false
    static var isReduceTransparencyEnabled = false
    static let voiceOverStatusDidChangeNotification = Notification.Name("voiceover")
    static let reduceTransparencyStatusDidChangeNotification = Notification.Name("transparency")
}
func NGTabResourceBundlePath() -> String? { CommandLine.arguments[1] }
func NGSystemTabControls(_ bar: UITabBar, _ count: Int) -> [UIControl]? { bar.controls }
func NGSystemTabButtonTitle(_ control: UIControl, _ badge: String?) -> String? { control.nativeTitle == badge ? nil : control.nativeTitle }
func NGSystemTabButtonImage(_ control: UIControl) -> UIImage? { control.nativeImage }
var nativeActivations = 0
var nativeAllowsSelection = true
func NGActivateSystemTabControl(_ bar: UITabBar, _ control: UIControl) -> Bool {
    nativeActivations += 1
    if nativeAllowsSelection, let index = bar.controls?.firstIndex(where: { $0 === control }) {
        bar.selectedItem = bar.items?[index]
        SystemTabsBridge.update(bar) // Synchronous native layout must not re-enter selection.
    }
    return true
}
func NGSystemTabNote(_ reason: String, _ bar: UITabBar?) {}
func NGSystemTabIsCapturing() -> Bool { false }
