import argparse
import numpy as np
import sys
from decode import Decoder
from PIL import Image, ImageChops

parser = argparse.ArgumentParser("Test decoding with a reference image")
parser.add_argument("--qoi", "-q", required=True)
parser.add_argument("--ref", "-r", required=True)
args = parser.parse_args()

with open(args.qoi, "rb") as f:
   dec_im = Image.fromarray(np.array(Decoder(f.read(), False).decode()).astype(np.uint8))
ref_im = Image.open(args.ref)

diff = ImageChops.difference(dec_im, ref_im)
if diff.getbbox():
   print("\u001b[31m{} isn't decoded properly.\u001b[0m".format(args.qoi))
   print(diff.getbbox())
   sys.exit(1)
else:
   print("\u001b[32m{} is decoded properly.\u001b[0m".format(args.qoi))
