#include "../Sources/NativeGeometry.h"
#include <assert.h>
#include <stdio.h>
int main(void) {
    unsigned checks = 0;
    for (size_t n = 2; n <= 5; n++) {
        for (int w = 320; w <= 1024; w += 8) {
            for (int h = 65; h <= 112; h++) {
                NGNativeRect bounds = {0,0,w,h};
                NGNativeRect bar = NGNativeCapsule(bounds,n);
                assert(NGNativeRectFinite(bar));
                assert(fabs(bar.width-fmin(w-28,n*66.0)) < 0.001);
                assert(fabs((bar.x+bar.width/2)-w/2.0) < 0.001);
                assert(bar.y >= 0 && bar.y+bar.height <= h);
                for (size_t i=0;i<n;i++) {
                    NGNativeRect slot = NGNativeButtonSlot(bar,n,i);
                    assert(NGNativeRectFinite(slot) && slot.width >= 44);
                    assert(slot.x >= bar.x && slot.x+slot.width <= bar.x+bar.width);
                    assert(slot.y >= bar.y && slot.y+slot.height <= bar.y+bar.height);
                    NGNativeRect applied=slot, external=slot;
                    assert(NGNativeRectMatches(applied,slot));
                    external.x += 1;assert(!NGNativeRectMatches(external,applied));
                    external=slot;external.width+=1;assert(!NGNativeRectMatches(external,applied));
                    external=slot;external.height+=1;assert(!NGNativeRectMatches(external,applied));
                    external=slot;external.y+=1;assert(!NGNativeRectMatches(external,applied));
                    checks++;
                }
            }
        }
    }
    NGNativeRect bad={0,0,NAN,83};assert(!NGNativeRectFinite(NGNativeCapsule(bad,4)));
    bad=(NGNativeRect){0,0,430,83};
    assert(!NGNativeRectFinite(NGNativeCapsule(bad,1)));
    assert(!NGNativeRectFinite(NGNativeCapsule(bad,6)));
    assert(!NGNativeRectFinite(NGNativeButtonSlot(bad,4,4)));
    printf("native_geometry_ok cases=%u\n",checks);
}
