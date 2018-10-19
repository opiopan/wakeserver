from BaseHTTPServer import HTTPServer
from BaseHTTPServer import BaseHTTPRequestHandler
import urlparse
import cgi
import json
import os

CONTENT_TYPES = {
    ".html": "text/html",
    ".htm": "text/html",
    ".css": "text/css",
    ".xml": "text/xml",
    ".js": "application/javascript",
    ".json": "application/json",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".gif": "image/gif",
    ".png": "image/png",
    ".svg": "image/svg+xml",
    ".ico": "image/x-icon",
}
GEN_CONTENT_TYPE = "application/octet-stream"

class Method:
    head = 'HEAD'
    get = 'GET'
    put = 'PUT'
    post = 'POST'
    delete = 'DELETE'        

class Request:
    def __init__(self, rfile, method, url, headers):
        self.rfile = rfile
        self.method = method
        self.headers = headers
        self.url = url
        parsed = urlparse.urlparse(self.url)
        self.path = parsed.path
        self.query = parsed.query
        self.params = urlparse.parse_qs(parsed.query)
        self.body = ''
        self.json = None

    def parseBody(self):
        self.body = ''
        self.json = None
        ctype, pdict = cgi.parse_header(self.headers['Content-Type'])
        if ctype == 'multipart/form-data':
            self.params = cgi.parse_multipart(self.rfile, pdict)
        else:
            length = int(self.headers['Content-Length'])
            self.body = self.rfile.read(length)
            if ctype == 'application/x-www-form-urlencoded':
                self.params = urlparse.parse_qs(self.body)
            elif ctype == 'application/json':
                self.json = json.loads(self.body)

class Response:
    class Phase:
        initial = 0
        header = 1
        done = 2
        
    def __init__(self, handler):
        self.handler = handler
        self.wfile = self.handler.wfile
        self.rcode = 200
        self.contentType = 'text/plain'
        self.headers = {}
        self.contentLength = -1
        self.body = ''
        self.phase = Response.Phase.initial

    def replyHeader(self):
        if self.phase != Response.Phase.initial:
            return
        self.handler.send_response(self.rcode)
        self.handler.send_header('Content-Type', self.contentType)
        for key in self.headers:
            self.handler.send_header(key, self.headers[key])
        if self.contentLength >= 0:
            self.handler.send_header('Content-Length', self.contentLength)
        self.handler.end_headers()
        self.phase = Response.Phase.header

    def close(self):
        if self.phase == Response.Phase.done:
            return
        self.contentLength = len(self.body)
        self.replyHeader()
        self.wfile.write(self.body)
        self.phase = Response.Phase.done
        
    def replyJson(self, obj):
        self.body = dumps(obj)
        self.contentType = 'application/json'
        self.close()

    def replyFile(self, path, onlyHeader = False):
        if os.path.isfile(path):
            base, ext = os.path.splitext(path)
            ext = ext.lower()
            self.contentType = CONTENT_TYPES[ext] if ext in CONTENT_TYPES \
                               else GEN_CONTENT_TYPE
            self.contentLength = os.path.getsize(path) if not onlyHeader else 0
            self.replyHeader()
            if onlyHeader:
                return
            with open(path) as f:
                while True:
                    data = f.read(8 * 1024)
                    if len(data) == 0:
                        break;
                    self.wfile.write(data)
            self.phase = Response.Phase.done
        else:
            self.replyError(404, 'Not found a file\r\n')

    def replyError(self, rcode, msg):
        self.rcode = rcode
        self.body = msg
        self.contentType = 'text/plain'
        self.close()

class RequestHandler(BaseHTTPRequestHandler):
    env = None

    def invokeHandler(self, method):
        req = Request(self.rfile, method, self.path, self.headers)
        resp = Response(self)
        handler = RequestHandler.env.findHandler(req.path)
        if handler != None:
            handler(req, resp)
            resp.close()
        elif (method == Method.get or \
              method == Method.head) and \
              RequestHandler.env.baseDir != None:
            path = 'index.html' if req.path == '/' else req.path
            resp.replyFile(RequestHandler.env.baseDir + '/' + path, \
                           method == Method.head)
        else:
            resp.replyError(404, 'Not found a file\r\n')

    def do_HEAD(self):
        self.invokeHandler(Method.head)

    def do_GET(self):
        self.invokeHandler(Method.get)
        
    def do_PUT(self):
        self.invokeHandler(Method.put)

    def do_POST(self):
        self.invokeHandler(Method.post)

    def do_DELETE(self):
        self.invokeHandler(Method.delete)
        
class Server:
    def __init__(self, port = 80, baseDir = None):
        self.port = int(port)
        self.baseDir = baseDir
        self.handlers = {}
        self.handlersForPrefix = {}

    def addHandler(self, path, handler, forPrefix = False):
        if forPrefix:
            self.handlersForPrefix[path] = handler
        else:
            self.handlers[path] = handler

    def findHandler(self, path):
        if path in self.handlers:
            return self.handlers[path]
        for key in self.handlersForPrefix:
            if path.startswith(key):
                return self.handlersForPrefix[key]
        return None

    def serveForever(self):
        RequestHandler.env = self
        server = HTTPServer(('', self.port), RequestHandler)
        server.serve_forever()
