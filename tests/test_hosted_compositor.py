#!/usr/bin/env python3
"""Run actual generated event methods with Swift stand-ins, not UIKit/Metal."""
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from test_replacement import ROOT, method, stage

STANDINS = r'''
import Foundation
#if canImport(CoreGraphics)
import CoreGraphics
#endif
struct Transform: Equatable { var m41: CGFloat = 0; var m42: CGFloat = 0 }
let CATransform3DIdentity = Transform()
func CACurrentMediaTime() -> TimeInterval { 100 }
final class Layer {
    var frame = CGRect.zero, transform = CATransform3DIdentity
    func removeAllAnimations() {}
}
final class Glass {
    let layer = Layer()
    var isHidden = true, continuousUpdate = false
    var alpha: CGFloat = 1
    func pauseRendering() { continuousUpdate = false }
}
final class Driver { func stop() {} }
final class LensMorphAnimator {
    var isRunning = false
    func retarget(to: CGRect) {}
    func cancel() { isRunning = false }
}
struct LensMorph { static func transform(mapping: CGRect, onto: CGRect) -> Transform { Transform() } }
struct FlexGlow { static let spotTravel: CGFloat = 10 }
final class SelectionAnimator {
    var frameForCenterX: ((CGFloat) -> CGRect?)?
    var onFrameChanged: ((CGRect) -> Void)?
    var active = false
    func rest(at: CGFloat, immediate: Bool) { active = true }
    func cancel() { active = false }
    func follow(x: CGFloat, at: TimeInterval, direct: Bool) {
        guard active, let frame = frameForCenterX?(x) else { return }
        onFrameChanged?(frame)
    }
}
struct Item { var ngEnabled = true }
final class Harness {
    let ngUseHostPosition = true
    var isDragging = false, isCollapsingLens = false, isCommittingDrag = false
    var isUserInteractionEnabled = true, isPillFading = false, flexSpreadStarted = false
    var selectedIndex = 0, hoveredIndex = -1
    var slotFrames = (0..<4).map { CGRect(x: CGFloat($0) * 100,y:0,width:100,height:63) }
    var items = Array(repeating:Item(),count:4)
    var selectionAnimator: SelectionAnimator?, lensMorphAnimator: LensMorphAnimator?, theseusView: Glass? = Glass()
    var ngGestureGate = NGTabInteractionGate()
    var ngFollowFrame: CGRect?, flexSpotCenter: CGPoint?
    var flexTouchStartX: CGFloat?, flexTouchY: CGFloat?
    var fingerAnchorOffset: CGFloat = 0, touchDownX: CGFloat = 0, barFollow: CGFloat = 0
    var currentDragVelocity = CGPoint.zero
    var flexReleaseScale: CGFloat = 1, flexSpread: CGFloat = 0
    var pillRestFrame = CGRect.zero
    var ngActivateNative: ((Int) -> Int?)?, onItemSelected: ((Int) -> Void)?
    let selectionView = Glass(), liftDriver = Driver(), bodyGainDriver = Driver()
    let pillFadeDriver = Driver(), flexSpreadDriver = Driver()
    var opens = 0, closes = 0, refreshes = 0, calls: [Int] = []
    var accept = true
    init() {
        ngActivateNative = { [weak self] index in
            guard let self else { return nil }
            self.calls.append(index); return self.accept ? index : self.selectedIndex
        }
    }
    func slotFrame(at index: Int) -> CGRect { slotFrames[index] }
    func glassFrame(for frame: CGRect) -> CGRect { frame }
    func calculateInterpolatedFrame(for point: CGPoint) -> CGRect? {
        CGRect(x: point.x-50,y:0,width:100,height:63)
    }
    func convertToTheseusContainer(_ r: CGRect) -> CGRect { r }
    func convertFromTheseusContainer(_ r: CGRect) -> CGRect { r }
    func placeLens(at r: CGRect) { theseusView?.layer.frame = r }
    func showTheseus() {
        opens += 1; theseusView?.isHidden = false
        selectionAnimator?.cancel() // same cancellation order as production show
    }
    func hideTheseus() { closes += 1; isCollapsingLens = true }
    func ngInvalidatePageFrames() { refreshes += 1 }
    func resetFlexGlow() {}
    func updateHoveredItem(lensCenterX: CGFloat) {}
    func updateFlexGlow() {}
    func applyBarTransform() {}
    func startLensActivity() {}
    func stopLensActivity() {}
    func startFlexSpread() { flexSpreadStarted = true }
    func stopLensStretch() {}
    func setLensFill(_ fill: CGFloat, rim: CGFloat) {}
    func setLensItemProgress(_ progress: CGFloat) {}
    func setLensRefraction(_ scale: CGFloat) {}
    func applyBarLift(_ scale: CGFloat) {}
    func applyBarBodyGain(progress: CGFloat) {}
    func updateItemColors() {}
    func applyItemTints(selectedAt: Int, animated: Bool) {}
    func updateSelectionViewFrame(animated: Bool) {
        if slotFrames.indices.contains(selectedIndex) {
            selectionView.layer.frame = NGTabPresentation.capsule(slot: slotFrames[selectedIndex])
        }
    }
'''
TEST = r'''
var cases = 0
for rtl in [false,true] {
 for accept in [false,true] {
  for initial in 0..<4 {
   for pressed in 0..<4 {
    for landing in 0..<4 {
     let h = Harness(); h.selectedIndex = initial; h.accept = accept
     if rtl { h.slotFrames.reverse() }
     let frames = h.slotFrames
     let x = frames[pressed].midX, y = frames[landing].midX
     h.beginInteraction(at: CGPoint(x:x,y:20), rawX:x)
     precondition(h.opens == 1 && h.isDragging && h.selectionAnimator?.active == true)
     h.followFinger(at: CGPoint(x:y,y:20))
     precondition(h.theseusView?.layer.frame.midX == y)
     h.finishInteraction(rawX:y); h.finishInteraction(rawX:y)
     precondition(!h.isDragging && h.closes == 1 && h.calls == [landing])
     precondition(h.selectedIndex == (accept ? landing : initial) && h.slotFrames == frames)
     h.endDragImmediately()
     precondition(h.calls == [landing] && !h.isCollapsingLens && h.theseusView?.isHidden == true)
     precondition(h.selectionView.alpha == 1 && !h.selectionView.isHidden)
     precondition(h.selectionView.layer.frame == NGTabPresentation.capsule(slot: frames[h.selectedIndex]))
     cases += 1
    }
   }
  }
 }
}
let h = Harness(); h.items[1].ngEnabled = false
h.beginInteraction(at: CGPoint(x:150,y:0), rawX:150)
h.beginInteraction(at: .zero, rawX:CGFloat.nan)
precondition(h.opens == 0 && !h.isDragging)
h.beginInteraction(at: CGPoint(x:50,y:0), rawX:50)
let before = h.theseusView?.layer.frame
h.followFinger(at: CGPoint(x: CGFloat.nan,y:0))
precondition(h.theseusView?.layer.frame == before)
h.finishInteraction(rawX:CGFloat.nan)
precondition(h.opens == 1 && h.closes == 0 && h.calls.isEmpty && h.theseusView?.isHidden == true)
print("hosted_production_gestures_ok cases=\(cases) rtl_rejection_cancel=ok")
'''

with tempfile.TemporaryDirectory(prefix='hosted-gestures-') as temp:
    d = Path(temp)
    stage(d/'staged')
    tab = (d/'staged/TheseusTabBar.swift').read_text()
    signatures = ('beginInteraction(', 'followFinger(', 'finishInteraction(', 'endDragImmediately()', 'findClosestItemIndex(')
    model = (ROOT/'Sources/TabPresentation.swift').read_text().replace('import CoreGraphics\n', '')
    source = d/'main.swift'
    source.write_text(STANDINS + '\n'.join(method(tab, name) for name in signatures) + '\n}\n' + model + TEST)
    if '--emit' in sys.argv:
        Path(sys.argv[sys.argv.index('--emit')+1]).write_bytes(source.read_bytes())
    else:
        compiler = ['xcrun', 'swiftc'] if shutil.which('xcrun') else ['swiftc']
        subprocess.run([*compiler, '-swift-version', '5', str(source), '-o', str(d/'test')], check=True)
        subprocess.run([str(d/'test')], check=True)
