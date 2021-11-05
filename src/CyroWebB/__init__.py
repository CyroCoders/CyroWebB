import os,sys,socket,threading,multiprocessing,time,psutil,urllib.request
from traceback import print_tb
import webob,inspect,brotli,ssl
from parse import parse
from typing import Callable
from . import Response,Request
from .render import *
from .frontend_endpoints import *

class Server(object):
    SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    ActiveThreads = 0
    StaticCacheAge = 3600
    endpoints = {}

    def __init__(self,context,secure=False) -> None:
        self.context = context
        self.brotli = False
        self.secure = secure
        if secure:
            self.brotli = True


    def create_endpoint(self, path: str) -> Callable:
        def wrapper(handler):
            if(not(self.endpoints.__contains__(path))):
                self.endpoints[path] = handler
                return handler
            else:
                raise AssertionError(f"Endpoint {path}:{handler} Already Exists!")#self.error["urlcatcherexists"])
        return wrapper

    def getFileType(self, f: str) -> list:
            self.extList = {
                ".css": "text/css",
                ".html": "text/html",
                ".htm": "text/html",
                ".ico": "image/vnd.microsoft.icon",
                ".js": "text/javascript",
                ".svg": "image/svg+xml",
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
                return handler, parseOut.named

        return None, None

    def handle_socket(self,_socket) -> None:
            workerQueue = multiprocessing.Manager().Queue(10000)
            _socket.listen(5)
            CPUCount = psutil.cpu_count(logical=False)
            processes = []
            for _ in range(CPUCount):
                processes.append(Process(workerQueue))
            for process in processes:
                process.start()
            self.MaxThreads = psutil.cpu_count()
            while True:
                try:
                    client = _socket.accept()
                    workerQueue.put((self,*client))
                    #processes[-1].workers = [worker for worker in processes[-1].workers if not worker.is_alive()]
                except Exception as e:
                    print(e)
                    for process in processes:
                        process.join()
                    continue

    def run(self,host) -> None:
        if 'PROD' not in globals():
            self.SOCK.bind((host[0] if host[0] != "" else socket.gethostname(), host[1]))
            if self.secure:
                print("https://" + host[0] if host[0] != "" else socket.gethostname(), host[1],sep=":")
                self.SOCK_ssl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.SOCK_ssl.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.SOCK_ssl.bind((host[0] if host[0] != "" else socket.gethostname(), host[1]))
                self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                self.ssl_context.load_cert_chain(certfile=os.path.join(os.path.dirname(os.path.abspath(self.context)),"certificates/cert.crt"), keyfile=os.path.join(os.path.dirname(os.path.abspath(self.context)),"certificates/cert.key"))
                self.SOCK_ssl = self.ssl_context.wrap_socket(self.SOCK_ssl)
                self.handle_socket(self.SOCK_ssl)
            else:
                print("http://" + host[0] if host[0] != "" else socket.gethostname(), host[1],sep=":")
                self.SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.SOCK.bind((host[0] if host[0] != "" else socket.gethostname(), host[1]))
                self.handle_socket(self.SOCK)

    def get_external(self, resp, url, mimetype=None):
        FileType, noText = self.getFileType(url)
        if mimetype == None:
            resp.headers[b"Content-Type"] = FileType.encode()

        if (noText):
            resp.body = urllib.request.urlopen(url).read()
        else:
            try:
                resp.text = urllib.request.urlopen(url).read().decode()
            except:
                resp.body = urllib.request.urlopen(url).read()

class Process(multiprocessing.Process):
    def __init__(self, taskQueue):
        multiprocessing.Process.__init__(self)
        self.taskQueue = taskQueue

    def run(self):
        MaxThreads = psutil.cpu_count()
        workers = []
        try:
            print(len(workers) < MaxThreads)
            while True:
                workers = [worker for worker in workers if worker.is_alive()]
                while len(workers) < MaxThreads:
                    print(workers)
                    workers.append(Worker(self.taskQueue))
                    workers[-1].start()
        except:
            for worker in workers:
                worker.join()

class Worker(threading.Thread):
    def __init__(self, taskQueue) -> None:
        threading.Thread.__init__(self)
        self.taskQueue = taskQueue

    def run(self):
        try:
            task = self.taskQueue.get()
            resp = Response.response()
            recv = task[1].recv(2 ** 10)
            req = Request.request(recv)
            handler, kwargs = task[0].find_handler(req)
            print(req.path, handler.__name__ if handler != None else ";", sep=": ")
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
                    task[1].send(resp.compile())
                else:            
                    try:
                        handler(req, resp, **kwargs)
                    except:
                        handler(resp, **kwargs)
                if compress:
                    if task[0].brotli:
                        resp.body = brotli.compress(resp.text.encode())
                        resp.headers[b"Content-Encoding"] = b"br"
                    else:
                        pass
            else:
                try:
                    FileType, noText = task[0].getFileType(req.path)
                    resp.headers[b"Content-Type"] = FileType.encode()
                    if (noText):
                        resp.body = open((os.path.join(os.path.dirname(os.path.abspath(task[0].context)),"static")) + req.path, "rb").read()
                    else:
                        resp.text = open((os.path.join(os.path.dirname(os.path.abspath(task[0].context)),"static")) + req.path).read()
                    resp.headers[b"Cache-Control"] = ("max-age=" + str(task[0].StaticCacheAge)).encode()
                except Exception as e:
                    resp = Response.response()
                    task[1].send(resp.compile())
            task[1].send(resp.compile())
            return True
        except Exception as e:
            print("********************")
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            resp.text = "Well My Work Was Not Clean Enough, but...<br><b>Thats A Server Problem</b>"
            resp.status_code = 500
            task[1].send(resp.compile())
            return False