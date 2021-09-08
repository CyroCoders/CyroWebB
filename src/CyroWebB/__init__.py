import os,sys,socket,multiprocessing
import webob,inspect,brotli,ssl
from parse import parse
from typing import Callable
from . import Response,Request
from _thread import *

class Server(object):
    SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ActiveThreads = 0
    endpoints = {}

    def __init__(self,context) -> None:
        self.context = context

    def create_endpoint(self, path: str) -> Callable:
        def wrapper(handler):
            if(not(self.endpoints.__contains__(path))):
                self.endpoints[path] = handler
                return handler
            else:
                raise AssertionError(self.error["urlcatcherexists"])
                return self.error["urlcatcherexists"]
        return wrapper

    def getFileType(self, f: str) -> list:
            self.extList = {
                ".css": "text/css",
                ".html": "text/html",
                ".htm": "text/html",
                ".ico": "image/vnd.microsoft.icon",
                ".js": "text/javascript",
                ".svg": "image/svg",
                ".xml": "text/xml",
                ".jp2": "image/x-jp2",
                ".jpg": "image/jpeg",
                ".jpeg": "image/jpeg",
                ".json": "text/json",
                ".png": "image/png",
                ".txt": "text/plain",
                ".map": "application/json",
                ".webp": "image/webp",
            }
            self.noText = {
                ".ico": "image/ico",
                ".jp2": "image/x-jp2",
                ".jpg": "image/jpg",
                ".jpeg": "image/jpeg",
                ".png": "image/png",
                ".webp": "image/webp",
            }
            fileType = self.extList[os.path.splitext(f)[1]]

            return fileType, fileType in self.noText.values()

    def handle(self,client: socket.socket,addr: tuple) -> bool:
        try:
            resp = Response.response()
            recv = client.recv(2 ** 15)
            req = Request.request(recv)
            handler = self.find_handler(req)
            handler, kwargs = self.find_handler(req)
            compress = True
            if handler is not None:
                if (inspect.isclass(handler)):
                    handler = getattr(handler(), req.method.lower(), None)
                    if handler is not None:
                        #if len(inspect.getfullargspec(handler).args)
                        try:
                            handler(req, resp, **kwargs)
                        except:
                            handler(resp, **kwargs)
                    else:
                        resp = Response.response()
                        resp.status_code = 405
                        resp.text = "405 Method Not Allowed"
                        client.send(resp.compile())
                else:            
                    try:
                        handler(req, resp, **kwargs)
                    except:
                        handler(resp, **kwargs)
                if compress:
                    if self.brotli:
                        resp.body = brotli.compress(resp.text.encode())
                        resp.headers[b"Content-Encoding"] = b"br"
                    else:
                        pass
            else:
                try:
                    FileType, noText = self.getFileType(req.path)
                    resp.headers[b"Content-Type"] = FileType.encode()
                    if (noText):
                        resp.body = open(os.path.dirname(os.path.abspath(self.context)) + "/static" + req.path, "rb").read()
                    else:
                        resp.text = open(os.path.dirname(os.path.abspath(self.context)) + "/static" + req.path).read()

                    resp.headers[b"cache_control"] = ("max-age=" + str(self.staticCache)).encode()
                except Exception as e:
                    resp = Response.response()
                    resp.text = "404"
                    client.send(resp.compile())
            client.send(resp.compile())
            return True
        except Exception as e:
            print(e)
            resp.text = "Well My Work Was Not Clean Enough, but...<br><b>Thats A Server Problem</b>"
            resp.status_code = 500
            client.send(resp.compile())
            return False
            
    def find_handler(self, req):
        for path, handler in self.endpoints.items():
            parseOut = parse(path, req.path)
            if parseOut is not None:
                return handler, parseOut.named

        return None, None

    def run(self,port) -> None:
        self.SOCK.bind((socket.gethostname(), port))
        self.SOCK.listen(5)
        processL = []
        print("http://"+ socket.gethostname(), port,sep=":")
        while True:
            client = self.SOCK.accept()
            mp = multiprocessing.Process(target=self.handle, args=(*client, ))
            processL.append(mp)
            processL[-1].start()
            processL[-1].join()