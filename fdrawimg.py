from PIL import Image
import zlib
import StringIO
import base64

Width = 800
Height = 480

def img2pil(img, w=Width, h=Height):
    data = base64.b64decode(img)
    pixels = zlib.decompress(data)
    return Image.frombuffer("RGBA", (w, h), pixels, "raw", "ARGB", 0, 1).convert("RGB")


def img2png(img, w=Width, h=Height):
    pilim = img2pil(img, w, h)
    f = StringIO.StringIO()
    pilim.save(f, "png")
    return f.getvalue()


def png2img(png):
    pilim = Image.open(StringIO.StringIO(png)).convert("RGBA")
    data = zlib.compress("".join([chr(a) + chr(r) + chr(g) + chr(b) for r, g, b, a in pilim.getdata()]))
    return base64.b64encode(data)


def colour_int2hex(num):
    h = hex(num)
    return h.replace("0x", ''.join(("#", "0" * (7 - len(h)))))
    
class LocalWhiteboard:
    def __init__(self, img, w=Width, h=Height):
        self.width = w
        self.height = h
        if isinstance(img, str):
            self.img = Image.open(img).convert('RGBA')
        else:
            self.fromBitmap()
     
    def fromBitmap(self, img):
        self.img = img2pil(img, self.width, self.height)
        
                 
