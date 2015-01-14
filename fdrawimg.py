from PIL import Image
import zlib
import StringIO
import base64

Width = 800
Height = 480

def img2png(img, w=Width, h=Height):
    data = base64.b64decode(img)
    pixels = zlib.decompress(data)
    pilim = Image.frombuffer("RGBA", (w, h), pixels, "raw", "ARGB", 0, 1).convert("RGB")
    f = StringIO.StringIO()
    pilim.save(f, "png")
    return f.getvalue()


def png2img(png):
    pilim = Image.open(StringIO.StringIO(png)).convert("RGBA")
    data = zlib.compress("".join([chr(a) + chr(r) + chr(g) + chr(b) for r, g, b, a in pilim.getdata()]))
    return base64.b64encode(data)


def colour_int2hex(num):
    h = hex(num).replace("0x", "#")
    return h.replace("#", ''.join(("#", "0" * (7 - len(h)))))
