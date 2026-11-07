#pragma once
#include <helpers/ui/DisplayDriver.h>
#include <algorithm>

// Layout, not magnification: native assets keep their pixel dimensions. A region
// owns only translation/clipping; presentation, rotation and update policy stay
// on the actual driver. It never starts/ends frames or allocates a framebuffer.
namespace LoRaFishLayout {
inline int bodyOffset(int height) {
#ifdef LORAGOTCHI_NATIVE_UI
  return std::max(0, height - 64) / 2;
#else
  (void)height; return 0; // Preserve the independent T-Watch tall-tank mapping.
#endif
}
inline int sidebarWidth(int width) { return width >= 288 ? 112 : 0; }
class Region : public DisplayDriver {
  DisplayDriver& out;
  int ox, oy, cx = 0, cy = 0, textSize = 1;
  void rect(int x,int y,int w,int h) {
    const int x0=std::max(0,x), y0=std::max(0,y);
    const int x1=std::min(width(),x+w), y1=std::min(height(),y+h);
    if(x1>x0 && y1>y0) out.fillRect(ox+x0,oy+y0,x1-x0,y1-y0);
  }
public:
  Region(DisplayDriver& target,int x,int y,int w,int h):DisplayDriver(w,h),out(target),ox(x),oy(y) {}
  bool isOn() override { return out.isOn(); }
  bool supportsColor() const override { return out.supportsColor(); }
  void turnOn() override {} void turnOff() override {} void clear() override {}
  void startFrame(ColorVal) override {} void endFrame() override {}
  void setTextSize(int s) override { textSize=std::max(1,s);out.setTextSize(s); }
  void setColor(ColorVal c) override { out.setColor(c); }
  void setCursor(int x,int y) override { cx=x;cy=y;out.setCursor(ox+x,oy+y); }
  void print(const char* s) override {
    // All region callers place full glyph rows. Clip strings before the edge,
    // rather than relying on panel wrapping into a neighbouring semantic region.
    if(cx<0 || cy<0 || cy+8*textSize>height()) return;
    char text[256]; size_t n=std::min(strlen(s),sizeof(text)-1);
    memcpy(text,s,n);text[n]=0;
    while(n && getTextWidth(text)>width()-cx) text[--n]=0;
    out.setCursor(ox+cx,oy+cy);out.print(text); cx+=getTextWidth(text);
  }
  uint16_t getTextWidth(const char* s) override { return out.getTextWidth(s); }
  void fillRect(int x,int y,int w,int h) override { rect(x,y,w,h); }
  void drawRect(int x,int y,int w,int h) override {
    if(w<=0 || h<=0) return;
    rect(x,y,w,1);rect(x,y+h-1,w,1);rect(x,y,1,h);rect(x+w-1,y,1,h);
  }
  void drawXbm(int x,int y,const uint8_t* bits,int w,int h) override {
    if(!bits || w<=0 || h<=0) return;
    if(x>=0 && y>=0 && x+w<=width() && y+h<=height()) {
      out.drawXbm(ox+x,oy+y,bits,w,h);return;
    }
    // XBM here follows the existing driver contract (MSB first).
    const int stride=(w+7)/8;
    for(int j=std::max(0,-y);j<std::min(h,height()-y);++j)
      for(int i=std::max(0,-x);i<std::min(w,width()-x);++i)
        if(bits[j*stride+i/8] & (0x80>>(i&7))) rect(x+i,y+j,1,1);
  }
};
} // namespace LoRaFishLayout
