import os,sys,socket,threading,multiprocessing,time,psutil
import webob,inspect,brotli,ssl
from parse import parse
from typing import Callable
from . import Response,Request
from .render import *

class Server(object):
    SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ActiveThreads = 0
    StaticCacheAge = 3600
    endpoints = {}

    def __init__(self,context,secure: None = False) -> None:
        self.context = context
        self.brotli = False
        if secure:
            self.brotli = True
            ssl.SSLContext(ssl.PROTOCOL_TLSv1).wrap_socket(self.SOCK, server_hostname=socket.gethostname())


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

            
    def find_handler(self, req):
        for path, handler in self.endpoints.items():
            parseOut = parse(path, req.path)
            if parseOut is not None:
                print(handler.__name__)
                return handler, parseOut.named

        return None, None

    def run(self,port) -> None:
        if 'PROD' not in globals():
            self.SOCK.bind((socket.gethostname(), port))
            self.SOCK.listen(5)
            CPUCount = psutil.cpu_count(logical=False)
            processes = []
            processes.append(Process())
            print("http://" + socket.gethostname(), port,sep=":")
            self.MaxThreads = psutil.cpu_count()
            while True:
                client = self.SOCK.accept()
                for process in processes:
                    if process == processes[-1]:
                        if len(process.workers) == self.MaxThreads:
                            if CPUCount == len(processes):
                                print("hit processer count")
                            else:
                                processes.append(Process())
                                processes[-1].start()
                                print("New Process!!!")
                        print(process.workers,len(processes[-1].workers),self.MaxThreads,len(processes[-1].workers) == self.MaxThreads)
                        worker = Worker(self,*client,len(processes),len(processes[-1].workers))
                        processes[-1].workers.append(worker)
                        processes[-1].workers[-1].start()
                    else:
                        pass
                    print(process.workers,process.workers == [worker for worker in process.workers if not worker.is_alive()])
                    process.workers = [worker for worker in process.workers if not worker.is_alive()]

            # while True:
            #     client = self.SOCK.accept()
            #     mp = multiprocessing.Process(target=self.handle, args=(*client, ))
            #     processL.append(mp)
            #     processL[-1].start()
            #     processL[-1].join()
        else:
            print("Ignoring Run Command; Global Variable Name PROD Present.")

class Process(multiprocessing.Process):
    def __init__(self):
        multiprocessing.Process.__init__(self)
        self.workers = []
        self.prevWorkerLen = 0

    def run(self):
        while True:
            if not self.prevWorkerLen == len(self.workers):
                print("New Worker Detected")
                self.workers[-1].start()
        self.workers[-1].start()

class Worker(threading.Thread):
    def __init__(self, server: Server, client: socket.socket, addr: tuple, processorID: int, threadID: int) -> None:
        threading.Thread.__init__(self)
        self.server = server
        self.client = client
        self.socket = socket
        self.addr = addr

    def run(self):
        try:
            resp = Response.response()
            recv = self.client.recv(2 ** 15)
            req = Request.request(recv)
            handler = self.server.find_handler(req)
            handler, kwargs = self.server.find_handler(req)
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
                    self.client.send(resp.compile())
                else:            
                    try:
                        handler(req, resp, **kwargs)
                    except:
                        handler(resp, **kwargs)
                if compress:
                    if self.server.brotli:
                        resp.body = brotli.compress(resp.text.encode())
                        resp.headers[b"Content-Encoding"] = b"br"
                    else:
                        pass
            else:
                try:
                    FileType, noText = self.server.getFileType(req.path)
                    resp.headers[b"Content-Type"] = FileType.encode()
                    if (noText):
                        resp.body = open((os.path.join(os.path.dirname(os.path.abspath(self.server.context)),"static")) + req.path, "rb").read()
                    else:
                        resp.text = open((os.path.join(os.path.dirname(os.path.abspath(self.server.context)),"static")) + req.path).read()
                    resp.headers[b"Cache-Control"] = ("max-age=" + str(self.server.StaticCacheAge)).encode()
                except Exception as e:
                    resp = Response.response()
                    self.client.send(resp.compile())
            self.client.send(resp.compile())
            return True
        except Exception as e:
            print("********************")
            print(e)
            resp.text = "Well My Work Was Not Clean Enough, but...<br><b>Thats A Server Problem</b>"
            resp.status_code = 500
            self.client.send(resp.compile())
            return False