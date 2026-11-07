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
// Native habitat coordinates leave sprite-sized clearance above the floor and
// below the header. Legacy choreography and assets are never magnified.
inline int habitatY(int y,int height,bool bottom=false) {
#ifdef LORAGOTCHI_NATIVE_UI
  if(height>64) return bottom ? height-30 : 34+(std::max(18,std::min(42,y))-18)*(height-68)/24;
#endif
  return y+bodyOffset(height);
}
inline int sidebarWidth(int) { return 0; }
// Distribute page anchors, not glyph pixels. A 64px page keeps its exact old
// geometry; larger panels gain row spacing and edge-anchored headings/hints.
inline int pageY(int y,int height) {
  if(height<=64 || y<=15) return y;
  if(y>56) return height-(64-y);
  return 16+(y-16)*(height-24)/40;
}
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
class Page : public Region {
public:
  Page(DisplayDriver& d):Region(d,0,0,d.width(),d.height()) {}
  void setCursor(int x,int y) override { Region::setCursor(x,pageY(y,height())); }
  void fillRect(int x,int y,int w,int h) override {
    Region::fillRect(x,pageY(y,height()),w,std::max(1,pageY(y+h,height())-pageY(y,height())));
  }
  void drawRect(int x,int y,int w,int h) override {
    Region::drawRect(x,pageY(y,height()),w,std::max(1,pageY(y+h,height())-pageY(y,height())));
  }
  void drawXbm(int x,int y,const uint8_t* b,int w,int h) override {
    // Region's clipped bitmap fallback dispatches virtual fillRect; decode
    // here so a clipped native page bitmap cannot map its row twice.
    if(!b || w<=0 || h<=0) return;
    const int top=pageY(y,height()),stride=(w+7)/8;
    for(int j=0;j<h;++j) for(int i=0;i<w;++i)
      if(b[j*stride+i/8] & (0x80>>(i&7))) Region::fillRect(x+i,top+j,1,1);
  }
};
} // namespace LoRaFishLayout
