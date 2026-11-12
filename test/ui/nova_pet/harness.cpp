// Host harness for test/ui/check_nova_pet_frame.py. Not firmware. Built with g++ on the PC.
// Reads commands on stdin, drives the real NovaPetLink.h / NovaPetTee.h code, prints results.
#include "fake_mono.h"
#include "NovaPetLink.h"
#include "NovaPetTee.h"

int main() {
  FakeMono real, direct;           // real = behind the tee, direct = the same commands with no tee
  NovaPetLink::Link* link = new NovaPetLink::Link(NovaPetTee::formatOf(real));
  NovaPetTee* tee = nullptr;
  uint32_t now = 0;
  std::string line;
  while (std::getline(std::cin, line)) {
    std::istringstream in(line);
    std::string op; in >> op;
    if (op.empty() || op[0] == '#') continue;
    if (op == "REQ") { in >> now; link->request(now); }
    else if (op == "SCREEN") {      // SCREEN <w> <h> <colour 0|1> <eink 0|1>: another kind of screen, new link, same ops
      int w, h, c, e; in >> w >> h >> c >> e;
      delete tee; tee = nullptr; delete link;
      real = FakeMono(w, h, c != 0, e != 0); direct = FakeMono(w, h, c != 0, e != 0);
      link = new NovaPetLink::Link(NovaPetTee::formatOf(real));
      printf("SCREEN %d LINECAP %zu\n", link->ok() ? 1 : 0, link->lineCapacity());
    }
    else if (op == "NAMES") {       // NAMES <hex pet name | -> <hex radio name | ->: what UITask hands to Link::setNames()
      std::string a, b; in >> a >> b;
      auto x = unhex(a == "-" ? "" : a), y = unhex(b == "-" ? "" : b);
      std::string pn(x.begin(), x.end()), rn(y.begin(), y.end());
      link->setNames(pn.c_str(), rn.c_str());
    }
    else if (op == "F") {           // begin a frame at time now
      in >> now; delete tee; tee = new NovaPetTee(real, *link, now);
      tee->startFrame(); direct.startFrame();
    }
    else if (op == "E") {           // end the frame; print any line that is waiting, as the serial code would
      tee->endFrame(); direct.endFrame(); delete tee; tee = nullptr;
      while (link->pending()) {
        size_t n = link->pending();
        printf("LINE %.*s", (int)n, (const char*)link->pendingData());   // ends with its own newline
        link->consumed(n);
      }
      printf("ACTIVE %d SEQ %u\n", link->active(now) ? 1 : 0, (unsigned)link->sequence());
    }
    else if (op == "ENC") {         // ENC <seq> <hexfb> [<hexprev>]: the bare encoder
      unsigned seq; std::string fb, pv; in >> seq >> fb >> pv;
      auto f = unhex(fb), p = unhex(pv);
      static char buf[NovaPetLink::MAX_LINE];
      size_t n = NovaPetLink::encodeLine(f.data(), pv.empty() ? nullptr : p.data(), seq, buf, sizeof buf);
      printf("ENC %zu %s", n, n ? buf : "\n");
    }
    else if (op == "NAMEHEX") {     // NAMEHEX <hex of the name bytes>: what UITask hands to Link::setName()
      std::string h; in >> h; auto b = unhex(h); std::string nm(b.begin(), b.end());
      link->setName(nm.c_str());
    }
    else if (op == "ENCN") {        // ENCN <seq> <hexfb> <hexname> [<hexprev>]: the bare encoder with a name (key lines only carry it)
      unsigned seq; std::string fb, nh, pv; in >> seq >> fb >> nh >> pv;
      auto f = unhex(fb), p = unhex(pv), nb = unhex(nh);
      std::string nm(nb.begin(), nb.end());
      static char buf[NovaPetLink::MAX_LINE];
      size_t n = NovaPetLink::encodeLine(f.data(), pv.empty() ? nullptr : p.data(), seq, buf, sizeof buf, nm.c_str());
      printf("ENCN %zu %s", n, n ? buf : "\n");
    }
    else if (op == "ENCSMALL") {    // a buffer below MAX_LINE must be refused, not overrun
      std::vector<uint8_t> f(NovaPetLink::BYTES, 0x55); char buf[NovaPetLink::MAX_LINE - 1];
      printf("ENCSMALL %zu\n", NovaPetLink::encodeLine(f.data(), nullptr, 1, buf, sizeof buf));
    }
    else if (op == "DUMP") {        // the picture the tee drew so far, as hex
      for (size_t i = 0; i < link->canvas.bytes(); i++) printf("%02x", link->canvas.px[i]);
      printf("\n");
    }
    else if (op == "ADV") {         // ADV <num> <den>: the real screen's text is num/den columns a character (T096: 24 5 = 4.8)
      int n, d; in >> n >> d; real.advNum = direct.advNum = n; real.advDen = direct.advDen = d;
    }
    else if (op == "WAIT") { in >> now; printf("WAIT %d\n", link->waiting(now) ? 1 : 0); }
    else {                         // the same command, parsed afresh for each driver
      if (tee) apply(*tee, op, in);
      std::istringstream in2(line); std::string op2; in2 >> op2;
      apply(direct, op2, in2);
    }
  }
  printf("PASSTHROUGH %s %zu\n", real.log == direct.log ? "same" : "DIFFERENT", real.log.size());
  printf("SIZEOF_LINK %zu\n", sizeof(NovaPetLink::Link));
  return 0;
}
