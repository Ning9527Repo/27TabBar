#import "Host.h"
#import "NativeGeometry.h"
#import <objc/runtime.h>
#import <dispatch/dispatch.h>
#import <dlfcn.h>
#import <math.h>
#import <objc/message.h>

// The implementation lives in Swift; this narrow ObjC interface avoids importing a
// generated Swift header into the bridging header's own module.
@interface NGSystemTabsBridge : NSObject
+ (BOOL)beginLayout:(UITabBar *)bar;
+ (void)endLayout:(UITabBar *)bar;
+ (void)detach:(UITabBar *)bar;
+ (void)queueSelection:(UITabBar *)bar;
@end

static NSUInteger NGTabCaptureDepth;
void NGSystemTabCaptureBegin(void) { NGTabCaptureDepth++; }
void NGSystemTabCaptureEnd(void) { if (NGTabCaptureDepth) NGTabCaptureDepth--; }
BOOL NGSystemTabIsCapturing(void) { return NGTabCaptureDepth != 0; }

static const UIControlEvents kNGPrimary = UIControlEventPrimaryActionTriggered;
static UIControlEvents NGActivationEvent(UIControl *control) {
    UIControlEvents events = control.allControlEvents;
    if (events & kNGPrimary) return kNGPrimary;
    if (events & UIControlEventTouchUpInside) return UIControlEventTouchUpInside;
    return 0;
}

void NGSystemTabNote(NSString *reason, UITabBar *bar) {
    static NSMutableDictionary<NSString *, NSNumber *> *counts;
    if (!NSThread.isMainThread) return;
    if (!counts) counts = [NSMutableDictionary dictionary];
    NSString *key = [NSString stringWithFormat:@"%@/%@", reason, bar ? NSStringFromClass(object_getClass(bar)) : @"process"];
    NSInteger count = [counts[key] integerValue];
    if (count >= 8) return;
    counts[key] = @(count + 1);
    NSString *line = [NSString stringWithFormat:@"%@ %@ bars=%lu selected=%@ view=%.0fx%.0f\n", [NSDate date], key, (unsigned long)bar.items.count, bar.selectedItem ? @"yes" : @"no", bar.bounds.size.width, bar.bounds.size.height];
    NSString *path = [NSHomeDirectory() stringByAppendingPathComponent:@"Library/Caches/TheseusSystemTabs.log"];
    NSFileManager *fm = NSFileManager.defaultManager;
    [fm createDirectoryAtPath:path.stringByDeletingLastPathComponent withIntermediateDirectories:YES attributes:nil error:nil];
    if (![fm fileExistsAtPath:path]) [fm createFileAtPath:path contents:nil attributes:nil];
    NSFileHandle *fd = [NSFileHandle fileHandleForWritingAtPath:path];
    @try { [fd seekToEndOfFile]; [fd writeData:[line dataUsingEncoding:NSUTF8StringEncoding]]; } @catch (NSException *e) { (void)e; }
    [fd closeFile];
}

NSArray<UIView *> *NGSystemTabBackgrounds(UITabBar *bar) {
    Class cls = NSClassFromString(@"_UIBarBackground");
    NSMutableArray *result = [NSMutableArray array];
    if (cls) for (UIView *view in bar.subviews) if ([view isKindOfClass:cls]) [result addObject:view];
    return result;
}

static NGNativeRect NGRect(CGRect r) { return (NGNativeRect){r.origin.x, r.origin.y, r.size.width, r.size.height}; }
static CGRect NGCG(NGNativeRect r) { return CGRectMake(r.x, r.y, r.width, r.height); }
CGRect NGSystemTabCapsule(UITabBar *bar, NSInteger count) { return count < 0 ? CGRectZero : NGCG(NGNativeCapsule(NGRect(bar.bounds), (size_t)count)); }
CGRect NGSystemTabSlot(CGRect capsule, NSInteger count, NSInteger visualIndex) { return count < 0 || visualIndex < 0 ? CGRectZero : NGCG(NGNativeButtonSlot(NGRect(capsule), (size_t)count, (size_t)visualIndex)); }
BOOL NGSystemTabFrameMatches(CGRect a, CGRect b) { return NGNativeRectMatches(NGRect(a), NGRect(b)); }

NSArray<UIControl *> *NGSystemTabControls(UITabBar *bar, NSInteger expectedCount) {
    if (expectedCount < 2 || expectedCount > 5 || !bar.window) return nil;
    NSUInteger count = (NSUInteger)expectedCount;
    Class button = NSClassFromString(@"UITabBarButton");
    if (!button) return nil;
    NSMutableArray<UIControl *> *controls = [NSMutableArray arrayWithCapacity:count];
    for (UIView *view in bar.subviews) {
        if (view.hidden || view.alpha <= 0.01 || view.layer.opacity <= 0.01) continue;
        if ([view isKindOfClass:button] && [view isKindOfClass:UIControl.class]) {
            if (CGRectIsEmpty(view.bounds)) return nil;
            [controls addObject:(UIControl *)view];
        }
        if (controls.count > count) return nil;
    }
    if (controls.count != count) return nil;
    [controls sortUsingComparator:^NSComparisonResult(UIControl *a, UIControl *b) {
        CGFloat x = [a convertPoint:CGPointMake(CGRectGetMidX(a.bounds), CGRectGetMidY(a.bounds)) toView:bar].x;
        CGFloat y = [b convertPoint:CGPointMake(CGRectGetMidX(b.bounds), CGRectGetMidY(b.bounds)) toView:bar].x;
        return x < y ? NSOrderedAscending : (x > y ? NSOrderedDescending : NSOrderedSame);
    }];
    if (bar.effectiveUserInterfaceLayoutDirection == UIUserInterfaceLayoutDirectionRightToLeft) {
        controls = [[controls.reverseObjectEnumerator allObjects] mutableCopy];
    }
    CGFloat last = NAN;
    for (UIControl *control in controls) {
        CGRect frame = [control convertRect:control.bounds toView:bar];
        CGFloat center = CGRectGetMidX(frame);
        if (!isfinite(center) || frame.size.width < 20 || !CGRectContainsPoint(bar.bounds, CGPointMake(center, CGRectGetMidY(frame))) || (isfinite(last) && fabs(last-center) < 15)) return nil;
        last = center;
    }
    return controls;
}

BOOL NGActivateSystemTabControl(UITabBar *bar, UIControl *control) {
    if (!bar || !control || !control.enabled || !control.window || !bar.window) return NO;
    // UIKit handles selection before dispatching its private control event.
    SEL buttonUp = NSSelectorFromString(@"_buttonUp:");
    Method method = class_getInstanceMethod(object_getClass(bar), buttonUp);
    if (method && method_getNumberOfArguments(method) == 3) {
        char ret[8] = {0}, arg[8] = {0};
        method_getReturnType(method, ret, sizeof(ret));
        method_getArgumentType(method, 2, arg, sizeof(arg));
        if (ret[0] == 'v' && arg[0] == '@') {
            ((void (*)(id, SEL, id))objc_msgSend)(bar, buttonUp, control);
            return YES;
        }
    }
    UIControlEvents event = NGActivationEvent(control);
    if (!event) { NGSystemTabNote(@"no-button-action", bar); return NO; }
    [control sendActionsForControlEvents:event];
    return YES;
}

NSString *NGTabResourceBundlePath(void) {
    Dl_info info = {0};
    if (!dladdr((const void *)&NGTabResourceBundlePath, &info) || !info.dli_fname) return nil;
    NSString *file = [NSFileManager.defaultManager stringWithFileSystemRepresentation:info.dli_fname length:strlen(info.dli_fname)];
    return [file.stringByDeletingLastPathComponent stringByAppendingPathComponent:@"TheseusSystemTabsResources.bundle"];
}

static BOOL NGIsBaseBar(UITabBar *bar) {
    return NSThread.isMainThread && [bar isKindOfClass:UITabBar.class];
}

static void (*NGOrigLayout)(UITabBar *, SEL);
static void (*NGOrigWindow)(UITabBar *, SEL);
static void (*NGOrigSelected)(UITabBar *, SEL, UITabBarItem *);
static void (*NGOrigItems)(UITabBar *, SEL, NSArray *, BOOL);
static void (*NGOrigTrait)(UITabBar *, SEL, UITraitCollection *);
static void (*NGOrigIndex)(UITabBarController *, SEL, NSUInteger);
static void (*NGOrigController)(UITabBarController *, SEL, UIViewController *);

static void NGLayout(UITabBar *bar, SEL cmd) {
    if (!NGIsBaseBar(bar) || NGSystemTabIsCapturing()) { NGOrigLayout(bar, cmd); return; }
    BOOL owned = [NGSystemTabsBridge beginLayout:bar];
    @try { NGOrigLayout(bar, cmd); }
    @finally { if (owned) [NGSystemTabsBridge endLayout:bar]; }
}

static void NGWindow(UITabBar *bar, SEL cmd) {
    NGOrigWindow(bar, cmd);
    if (NGIsBaseBar(bar)) {
        if (!bar.window) [NGSystemTabsBridge detach:bar];
        else [bar setNeedsLayout];
    }
}

static void NGSelected(UITabBar *bar, SEL cmd, UITabBarItem *item) {
    NGOrigSelected(bar, cmd, item);
    if (NGIsBaseBar(bar)) [NGSystemTabsBridge queueSelection:bar];
}

static void NGItems(UITabBar *bar, SEL cmd, NSArray *items, BOOL animated) {
    NGOrigItems(bar, cmd, items, animated);
    if (NGIsBaseBar(bar)) [bar setNeedsLayout];
}

static void NGTrait(UITabBar *bar, SEL cmd, UITraitCollection *trait) {
    NGOrigTrait(bar, cmd, trait);
    if (NGIsBaseBar(bar)) [bar setNeedsLayout];
}

static void NGIndex(UITabBarController *controller, SEL cmd, NSUInteger index) {
    NGOrigIndex(controller, cmd, index);
    if (NSThread.isMainThread && controller.isViewLoaded) [NGSystemTabsBridge queueSelection:controller.tabBar];
}

static void NGController(UITabBarController *controller, SEL cmd, UIViewController *selected) {
    NGOrigController(controller, cmd, selected);
    if (NSThread.isMainThread && controller.isViewLoaded) [NGSystemTabsBridge queueSelection:controller.tabBar];
}

static void NGInstall(Class cls, SEL sel, IMP replacement, IMP *original, unsigned nargs) {
    Method method = class_getInstanceMethod(cls, sel);
    if (*original || !method || method_getNumberOfArguments(method) != nargs) return;
    char ret[8] = {0};
    method_getReturnType(method, ret, sizeof(ret));
    if (ret[0] != 'v') return;
    if (nargs >= 3) {
        char arg[16] = {0};
        method_getArgumentType(method, 2, arg, sizeof(arg));
        if (sel == @selector(setSelectedIndex:)) {
            if (strcmp(arg, @encode(NSUInteger))) return;
        } else if (arg[0] != '@') return;
    }
    if (nargs == 4) {
        char arg[8] = {0};
        method_getArgumentType(method, 3, arg, sizeof(arg));
        if (strcmp(arg, @encode(BOOL))) return;
    }
    IMP impl = method_getImplementation(method);
    if (!impl || impl == replacement) return;
    *original = impl;
    // Do not alter an inherited implementation on UIView.
    if (!class_addMethod(cls, sel, replacement, method_getTypeEncoding(method))) {
        *original = method_setImplementation(method, replacement);
    }
}

__attribute__((constructor)) static void NGStart(void) {
    dispatch_async(dispatch_get_main_queue(), ^{ NGSystemTabNote(@"loaded", nil); });
    NSBundle *main = NSBundle.mainBundle;
    NSString *identifier = main.bundleIdentifier;
    if (![main.bundlePath.pathExtension isEqualToString:@"app"] || !identifier.length ||
        [identifier hasPrefix:@"com.tencent.xin"] || [identifier isEqualToString:@"com.apple.springboard"]) return;
    dispatch_async(dispatch_get_main_queue(), ^{
        Class cls = UITabBar.class;
        NGInstall(cls, @selector(layoutSubviews), (IMP)NGLayout, (IMP *)&NGOrigLayout, 2);
        NGInstall(cls, @selector(didMoveToWindow), (IMP)NGWindow, (IMP *)&NGOrigWindow, 2);
        NGInstall(cls, @selector(setSelectedItem:), (IMP)NGSelected, (IMP *)&NGOrigSelected, 3);
        NGInstall(cls, @selector(setItems:animated:), (IMP)NGItems, (IMP *)&NGOrigItems, 4);
        NGInstall(cls, @selector(traitCollectionDidChange:), (IMP)NGTrait, (IMP *)&NGOrigTrait, 3);
        NGInstall(UITabBarController.class, @selector(setSelectedIndex:), (IMP)NGIndex, (IMP *)&NGOrigIndex, 3);
        NGInstall(UITabBarController.class, @selector(setSelectedViewController:), (IMP)NGController, (IMP *)&NGOrigController, 3);
        NGSystemTabNote(NGOrigLayout ? @"native-mount-hooks-installed" : @"layout-hook-rejected", nil);
    });
}
