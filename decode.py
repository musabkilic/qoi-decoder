import argparse
import sys
import struct


class Decoder:
   def __init__(self, im, v):
      self.im = im
      self.i = 0
      self.j = 0
      self.n = len(im)
      self.v = v
      self.darr = []

   def read(self, x=1):
      buffer = self.im[self.i:self.i+x]
      self.i += x
      return buffer

   def readc(self, x=1):
      return b"".join(struct.unpack("s"*x, self.read(x))).decode()

   def readu8(self):
      return struct.unpack("b", self.read())[0]

   def readu32(self):
      return struct.unpack(">I", self.read(4))[0]

   def readi(self):
      return self.read()[0]

   def log(self, *args, **kwargs):
      if self.v:
         text = " ".join(map(str, args))
         print(f"{hex(self.j)[2:]:0>5}", text)
         self.j += kwargs.get("move", 0)

   def prev_pixel(self):
      return self.darr[-1] if self.darr else ([0, 0, 0] if self.ch == 3 else [0, 0, 0, 255])

   def push_pixel(self, pix):
      self.darr.append(pix)
      r, g, b = pix[:3]
      a = 255 if self.ch == 3 else pix[3]
      ind = (r * 3 + g * 5 + b * 7 + a * 11) % 64
      self.carr[ind] = pix

   def qoi_op_rgb(self):
      # QOI_OP_RGB
      self.log(":QOI_OP_RGB", move=4)
      r = self.readi()
      g = self.readi()
      b = self.readi()
      pix = [r, g, b]
      if self.ch == 4:
         pix.append(self.prev_pixel()[3])
      self.push_pixel(pix)

   def qoi_op_rgba(self):
      # QOI_OP_RGBA
      self.log(":QOI_OP_RGBA", move=5)
      r = self.readi()
      g = self.readi()
      b = self.readi()
      a = self.readi()
      self.push_pixel([r, g, b, a])

   def qoi_op_index(self, inf):
      # QOI_OP_INDEX
      self.log(":QOI_OP_INDEX", inf, move=1)
      self.push_pixel(self.carr[inf])

   def qoi_op_diff(self, inf):
      # QOI_OP_DIFF
      self.log(":QOI_OP_DIFF", move=1)
      dr = (inf >> 4) - 2
      dg = ((inf >> 2) & 0x03) - 2
      db = (inf & 0x03) - 2
      r = (self.prev_pixel()[0] + dr) % 0x100
      g = (self.prev_pixel()[1] + dg) % 0x100
      b = (self.prev_pixel()[2] + db) % 0x100
      pix = [r, g, b]
      if self.ch == 4:
         pix.append(self.prev_pixel()[3])
      self.push_pixel(pix)

   def qoi_op_luma(self, inf):
      # QOI_OP_LUMA
      self.log(":QOI_OP_LUMA", move=2)
      dg = inf - 0x20
      rb = self.readi()
      dr, db = (rb >> 4) - 8, (rb & 0x0F) - 8
      r = (self.prev_pixel()[0] + dg + dr) % 0x100
      g = (self.prev_pixel()[1] + dg) % 0x100
      b = (self.prev_pixel()[2] + dg + db) % 0x100
      pix = [r, g, b]
      if self.ch == 4:
         pix.append(self.prev_pixel()[3])
      self.push_pixel(pix)

   def qoi_op_run(self, inf):
      # QOI_OP_RUN
      tim = inf + 1
      self.log(":QOI_OP_RUN", tim, move=1)
      for i in range(tim):
         self.push_pixel(self.prev_pixel())

   def magic(self):
      self.log(":HEADER")
      self.log(":MAGIC", self.readc(4), move=4)
      self.w = self.readu32()
      self.h = self.readu32()
      self.log(":WIDTH", self.w, move=4)
      self.log(":HEIGHT", self.h, move=4)
      self.ch = self.readu8()
      self.log(":CHANNELS", {3:"RGB", 4:"RGBA"}[self.ch], move=1)
      self.log(":COLORSCAPE", {0:"sRGB and linear alpha", 1:"all linear"}[self.readu8()], move=1)

      self.carr = [[0] * self.ch for i in range(64)]

   def decode(self):
      self.magic()
      self.log()

      while self.i < self.n:
         tag = self.readi()
         if tag == 0xFE:
            self.qoi_op_rgb()
         elif tag == 0xFF:
            self.qoi_op_rgba()
         else:
            tag, inf = tag >> 6, tag & 0x3F
            if tag == 0x00:
               self.qoi_op_index(inf)
            elif tag == 0x01:
               self.qoi_op_diff(inf)
            elif tag == 0x02:
               self.qoi_op_luma(inf)
            elif tag == 0x03:
               self.qoi_op_run(inf)
            else:
               assert False, "DON'T KNOW {}".format(hex(tag))
      assert self.w * self.h + 8 == len(self.darr), "WRONG LENGTH"

      im_arr = []
      for y in range(self.h):
         im_arr.append([])
         for x in range(self.w):
            pix = self.darr[y * self.w + x]
            assert len(pix) == self.ch, "WRONG PIXEL SIZE"
            assert 0 <= pix[0] <= 255, "RED MUST BE BETWEEN 0 AND 255"
            assert 0 <= pix[1] <= 255, "GREEN MUST BE BETWEEN 0 AND 255"
            assert 0 <= pix[2] <= 255, "RED MUST BE BETWEEN 0 and 255"
            assert self.ch == 3 or 0 <= pix[3] <= 255, "ALPHA MUST BE BETWEEN 0 and 255"
            im_arr[-1].append(pix)
      return im_arr

if __name__ == "__main__":
   import numpy as np
   from PIL import Image
   parser = argparse.ArgumentParser(description="Decode a QOI file")
   parser.add_argument("--file", "-i", help="file to decode", required=True)
   parser.add_argument("--show", "-s", help="show image", default=True)
   parser.add_argument("--verbose", "-v", default=True)
   parser.add_argument("--output", "-o", help="output as")
   args = parser.parse_args()
   with open(args.file, "rb") as f:
      im_arr = Decoder(f.read(), args.verbose).decode()
      im = Image.fromarray(np.array(im_arr).astype(np.uint8))
      if args.show:
         im.show()
      if args.output:
         im.save(args.output)
