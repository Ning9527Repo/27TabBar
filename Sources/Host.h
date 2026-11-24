#import <UIKit/UIKit.h>

NS_ASSUME_NONNULL_BEGIN
NSArray<UIControl *> * _Nullable NGSystemTabControls(UITabBar *bar, NSInteger expectedCount);
NSArray<UIView *> *NGSystemTabBackgrounds(UITabBar *bar);
CGRect NGSystemTabCapsule(UITabBar *bar, NSInteger count);
CGRect NGSystemTabSlot(CGRect capsule, NSInteger count, NSInteger visualIndex);
BOOL NGSystemTabFrameMatches(CGRect a, CGRect b);
void NGSystemTabCaptureBegin(void);
void NGSystemTabCaptureEnd(void);
BOOL NGSystemTabIsCapturing(void);
BOOL NGActivateSystemTabControl(UITabBar *bar, UIControl *control);
void NGSystemTabNote(NSString *reason, UITabBar * _Nullable bar);
NSString * _Nullable NGTabResourceBundlePath(void);
NS_ASSUME_NONNULL_END
