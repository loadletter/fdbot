import sys
import time
import socket
import random
import datetime

from fdrawimg import img2png, png2img, colour_int2hex

DefaultServer = "flockdraw.com"
DefaultPort = 443
BuffSize = 4096

class FlockDrawConnection:

    def __init__(self,
                 whiteboard,
                 username,
                 server=DefaultServer,
                 port=DefaultPort):
        self.users = []
        self.bufferIn = ""
        self.bufferOut = []
        assert "/" not in server
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverport = server, port
        print "Connecting to ", serverport
        self.sock.connect(serverport)
        print "Connected to ", serverport
        self.server = server
        self.port = port
        self.whiteboard = whiteboard
        self.initialize(server, whiteboard, username)
        self.hadUsers = False
        self.oweBitmap = []
        self.didCreate = False

    def sendLine(self, data):
        self.bufferOut.append(data)
        self.bufferOut.append("\n")

    def initialize(self, server, whiteboard, username):
        self.sendLine("C whiteboard-http://%s/%s %s %d" % (
            server,
            whiteboard,
            username,
            3
        ))

    def deliver(self, user, data):
        self.sendLine("D %s %s" % (user, data))

    def broadcast(self, data):
        self.sendLine("B %s" % data)

    def deliverCommands(self, user, commands):
        self.deliver(user, self.formatCommands(commands))

    def broadcastCommands(self, commands):
        self.broadcast(self.formatCommands(commands))

    def warnWith(self, warning, data):
        limit = 60
        printLine = repr(data)
        if len(printLine) > limit:
            printLine = repr(line[:limit] + "...")
        print >>sys.stderr, "warning:", warning % data

    def formatCommands(self, commands):
        return "\t".join(commands)

    def handleAdd(self, username):
        assert " " not in username
        self.users.append(username)
        print "New peer:", username
        self.hadUsers = True

    def handleRemove(self, username):
        if username in self.users:
            self.users.remove(username)
            print "Peer leaving:", username
        else:
            self.warnWith("unknown peer %s leaving", username)

    def handleMessage(self, data):
        try:
            sender, message = data.split(" ", 1)
        except ValueError:
            self.warnWith("received message %s without sender", username)
            return
        for command in self.parseCommands(message):
            self.handleCommand(sender, command)

    def tryObtainBitmap(self, noAsk=[]):
        try:
            user = random.choice([user for user in self.users if user not in noAsk])
        except IndexError:
            return False
        self.warnWith("attempting to obtain bitmap from %s", user)
        self.deliver(user, "Rq")
        return True

    def handleRequest(self, origin, args):
        # This is the one that needs to be handled to avoid messing up
        # state for non-bots. Since we can't keep bitmap state ourselves,
        # it's a hard one. We try to obtain the bitmap from another peer.
        self.warnWith("%s requested bitmap", origin)
        self.oweBitmap.append(origin)
        if not self.tryObtainBitmap(noAsk=[origin]):
            self.warnWith("unable to obtain bitmap for %s", origin)

    def handleNew(self, args):
        print "Created new whiteboard"
        self.didCreate = True

    def handleKeypress(self, origin, args):
        print "Event:", origin, "keypress", args

    def handlePointerMove(self, origin, args):
        print "Event:", origin, "move", args

    def handlePointerSize(self, origin, args):
        print "Event:", origin, "size", args

    def handlePointerDown(self, origin, args):
        print "Event:", origin, "down", args

    def handlePointerUp(self, origin, args):
        print "Event:", origin, "up", args

    def handlePointerHide(self, origin, args):
        print "Event:", origin, "hide", args

    def handlePointerShow(self, origin, args):
        print "Event:", origin, "show", args

    def handleBrushChange(self, origin, args):
        print "Event:", origin, "tool", args

    def handleColourChange(self, origin, args):
        print "Event:", origin, "colour", args, "=", colour_int2hex(int(args))

    def handleFlush(self, origin, args):
        print "Event:", origin, "flush", args

    def handleChat(self, origin, args):
        print "Event:", origin, "chat", args

    def debugSavePng(self, filename, b64coded):
        with open(filename, "wb") as f:
            f.write(img2png(b64coded))

    def handleBitmap(self, origin, data):
        for user in self.oweBitmap:
            self.warnWith("relaying bitmap to %s", user)
            self.deliver(user, "Bo " + data)
        self.oweBitmap = []

        debugName = "flockdrawdump-%s-%s-%s.png" % (
            origin,
            self.whiteboard,
            str(datetime.datetime.now())
        )
        self.debugSavePng(debugName, data)

    def handleCommand(self, origin, command):
        if " " in command:
            command, args = command.split(" ", 1)
        else:
            args = None
        try:
            f = {
                'Kp': self.handleKeypress,
                'Rq': self.handleRequest,
                'Pm': self.handlePointerMove,
                'Ps': self.handlePointerSize,
                'Pd': self.handlePointerDown,
                'Pu': self.handlePointerUp,
                'Phi': self.handlePointerHide,
                'Psh': self.handlePointerShow,
                'Bch': self.handleBrushChange,
                'Cch': self.handleColourChange,
                'F': self.handleFlush,
                'Bo': self.handleBitmap,
                'C': self.handleChat,
            }[command]
        except KeyError:
            self.warnWith("ignoring command %s", command)
            if args:
                self.warnWith("...with arguments %s", args)
            self.warnWith("...from %s", origin)
        f(origin, args)

    def parseCommands(self, data):
        return data.split("\t")

    def handleLine(self, line):
        try:
            if len(line) == 1:
                letter, rest = line, None
            else:
                letter, rest = line.split(" ", 1)
        except ValueError:
            self.warnWith("ignoring line %s (no prefix)", line)
            return
        try:
            f = {
                'A': self.handleAdd,
                'R': self.handleRemove,
                'M': self.handleMessage,
                'N': self.handleNew,
            }[letter]
        except KeyError:
            self.warnWith("ignoring line %s (unknown prefix)", line)
            return
        f(rest)

    def trySend(self):
        while self.bufferOut:
            data = self.bufferOut.pop(0)
            len = self.sock.send(data)
            rest = data[len:]
            if rest:
                self.bufferOut.insert(0, rest)
                break

    def tryHandle(self):
        incoming = self.sock.recv(BuffSize)
        if incoming:
            self.bufferIn += incoming
            while True:
                elements = self.bufferIn.split("\n", 1)
                if len(elements) < 2:
                    self.bufferIn = elements[0]
                    break
                line, self.bufferIn = elements
                line = line
                self.handleLine(line)
        return incoming

    def isAbandoned(self):
        if not self.hadUsers:
            return False
        if self.users:
            return False
        return True

    def flush(self):
        while self.bufferOut:
            self.trySend()

    def shutdown(self):
        self.flush()
        self.sock.shutdown(socket.SHUT_WR)
        self.sock.close()

    def debugPutPixel(self, x, y, colour):
        commands = []
        commands.append("Bch brush")
        commands.append("Ps 1")
        commands.append("Cch %d" % colour)
        commands.append("Pd %d %d" % (x, y))
        commands.append("Pu %d %d" % (x, y))
        commands.append("F")
        self.broadcastCommands(commands)

    def debugFloodFill(self, x, y, colour):
        commands = []
        commands.append("Bch bucket")
        commands.append("Cch %d" % colour)
        commands.append("Pd %d %d" % (x, y))
        commands.append("Pu %d %d" % (x, y))
        commands.append("F")
        self.broadcastCommands(commands)


class FlockDrawPNGServer(FlockDrawConnection):

    def __init__(self,
                 whiteboard,
                 username,
                 pngfile=None,
                 server=DefaultServer,
                 port=DefaultPort):
        if pngfile:
            self.imagedata = png2img(open(pngfile, "rb").read())
        FlockDrawConnection.__init__(self, whiteboard, username, server, port)

    def handleRequest(self, origin, args):
        self.deliverCommands(origin, ["Bo " + self.imagedata])

    def obtainBitmap(self):
        self.tryObtainBitmap()
        self.obtainedBitmap = False
        while not self.obtainedBitmap:
            self.trySend()
            if not self.bufferOut:
                self.tryHandle()

    def handleBitmap(self, origin, data):
        self.debugSavePng("last.png", data)
        self.obtainedBitmap = True
        print "Image saved as last.png."

if __name__ == '__main__':
    conn = FlockDrawPNGServer("testone", "observer", pngfile="blank.png")
    try:
        while True:
            conn.trySend()
            if not conn.bufferOut:
                conn.tryHandle()
    except KeyboardInterrupt:
        conn.obtainBitmap()
        print "Leaving after keyboard interrupt."
    conn.shutdown()
