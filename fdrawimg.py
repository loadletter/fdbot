from PIL import Image, ImageDraw, ImageColor
import zlib
import StringIO
import base64

WIDTH = 800
HEIGHT = 480
TOOL_LIST = ['defaultBrush', 'brush', 'eraser', 'bucket', 'line', 'text']

def img2pil(img, w=WIDTH, h=HEIGHT):
    data = base64.b64decode(img)
    pixels = zlib.decompress(data)
    return Image.frombuffer("RGBA", (w, h), pixels, "raw", "ARGB", 0, 1).convert("RGB")


def img2png(img, w=WIDTH, h=HEIGHT):
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
    def __init__(self, img, w=WIDTH, h=HEIGHT):
        self.width = w
        self.height = h
        self.setSize('4')
        self.users = {}
        if isinstance(img, str):
            self.img = Image.open(img).convert('RGBA')
        else:
            self.fromBitmap()
     
    def fromBitmap(self, img):
        self.img = img2pil(img, self.width, self.height)
    
    def setSize(self, user, size):
        self.users[user]['size'] = int(size) * 2
    
    def setTool(self, user, tool):
        self.users[user]['tool'] = TOOL_LIST.index(tool)
    
    def setPosition(self, user, x, y):
        xy = (int(x), int(y))
        self.users[user]['xy'] = xy
        self.users[user]['move'].append(xy)
    
    def setColour(self, user, colour):
        self.users[user]['colour'] = colour
    
    def setHidden(self, user, hidden=True):
        self.users[user]['hidden'] = hidden
    
    def setKey(self, user, keydown=True):
        self.users[user]['keydown'] = keydown

    def setText(self, user, c):
        c = int(c)
        assert c < 127
        if c >= 32:
            self.users[user]['text'].append(chr(c))
        elif c == 8 and len(self.users[user]['text']) > 0:
            #backspace
            self.users[user]['text'].pop()
        
    def onFlush(self, user):
        if self.users[user]['keydown']:
            pass
        #   self.tool(user, user.move)
        #   user.move = []
        pass
    
    def addUser(self, user):
        self.users[user] = {'text' : [], 'move' : []}
    
    def removeUser(self, user):
        del self.users[user]
                 
