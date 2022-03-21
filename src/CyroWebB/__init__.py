import select
import os,sys,socket,threading,multiprocessing,psutil,urllib.request
import inspect,brotli,ssl
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
    plugins = []
    processes = []

    def __init__(self,context,secure=False,production=False) -> None:
        self.context = context
        self.brotli = False
        self.secure = secure
        if secure:
            self.brotli = True
        self.production = production
        self.maxThreads = psutil.cpu_count() if production else 2


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
                ".ico": "image/vnd.microsoft.icon",
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

    def handle_socket(self, _sockets) -> None:
            CPUCount = psutil.cpu_count(logical=False) if self.production else 1
            self.workerQueue = multiprocessing.Manager().Queue(10000)
            self.messageQueue = multiprocessing.Manager().Queue(self.maxThreads*2)
            for _ in range(CPUCount):
                self.processes.append(Process(self,self.workerQueue,self.messageQueue))
            for process in self.processes:
                process.start()
            print("Server Ready")
            while True:
                socket_listener = select.select(_sockets, [], [], 0)[0]
                try:
                    if self.messageQueue.empty():
                        for sock in socket_listener:
                            if sock in _sockets:
                                client = sock.accept()
                                self.workerQueue.put((self,*client))
                    else:
                        message = self.messageQueue.get()
                        if message == "ServerShutdown":
                            self.kill()
                    #processes[-1].workers = [worker for worker in processes[-1].workers if not worker.is_alive()]
                except Exception as e:
                    for process in self.processes:
                        process.join()
                    print(e)
                    continue

    def run(self,host) -> None:
        if 'PROD' not in globals():
            self.SOCK.bind((host[0] if host[0] != "" else socket.gethostname(), host[1]))
            sockets = []
            if self.secure:
                print("https://" + host[0] if host[0] != "" else socket.gethostname(), host[1],sep=":")
                self.SOCK_ssl = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.SOCK_ssl.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                self.SOCK_ssl.bind((host[0] if host[0] != "" else socket.gethostname(), host[1]))
                self.ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLSv1_2)
                self.ssl_context.load_cert_chain(certfile=os.path.join(os.path.dirname(os.path.abspath(self.context)),"certificates/cert.crt"), keyfile=os.path.join(os.path.dirname(os.path.abspath(self.context)),"certificates/cert.key"))
                self.SOCK_ssl = self.ssl_context.wrap_socket(self.SOCK_ssl)
                self.SOCK_ssl.listen(5)
                sockets.append(self.SOCK_ssl)
            print("http://" + host[0] if host[0] != "" else socket.gethostname(), host[1],sep=":")
            self.SOCK = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.SOCK.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.SOCK.bind((host[0] if host[0] != "" else socket.gethostname(), host[1]))
            self.SOCK.listen(5)
            sockets.append(self.SOCK)

            self.handle_socket(sockets)

    def kill(self) -> None:
        self.workerQueue.put("ServerShutdown")
        for process in self.processes:
            process.terminate()
            process.join()
        self.SOCK.close()
        if self.secure:
            self.SOCK_ssl.close()
        print("Server Shutdown")
        quit()

    def get_external(self, resp, url, mimetype=None):
        FileType, noText = self.getFileType(url)
        if mimetype == None:
            resp.headers[b"Content-Type"] = FileType.encode()

        if (noText):
            resp.body = urllib.request.urlopen(url).read()
        else:
            try:
                resp.text = urllib.request.urlopen(url).read().decode()
            except AttributeError:
                resp.body = urllib.request.urlopen(url).read()
        
    def use_plugin(self,plugin):
        self.plugins.append(plugin(self))

class Process(multiprocessing.Process):
    def __init__(self, server, taskQueue, messageQueue):
        multiprocessing.Process.__init__(self)
        self.server = server
        self.taskQueue = taskQueue
        self.messageQueue = messageQueue

    def run(self):
        workers = []
        kill = False
        while True:
            if kill:
                ServerShutdown(self.messageQueue, KeyboardInterrupt)
            try:
                workers = [worker for worker in workers if worker.is_alive()]
                if len(workers) < self.server.maxThreads and self.taskQueue.qsize() > len(workers):
                    task = self.taskQueue.get()
                    if task == "ServerShutdown":
                        quit()
                    print(task)
                    workers.append(Worker(task))
                    workers[-1].start()
            except KeyboardInterrupt as e:
                for worker in workers:
                    worker.join()
                kill = True

class Worker(threading.Thread):
    def __init__(self, task) -> None:
        threading.Thread.__init__(self)
        self.task = task

    def run(self):
        try:
            task = self.task
            resp = Response.response()
            recv = self.task[1].recv(2 ** 10)
            req = Request.request(recv)
            handler, kwargs = self.task[0].find_handler(req)
            print(req.path, handler.__name__ if handler != None else ";", sep=": ")
            compress = True
            if handler is not None:
                if (inspect.isclass(handler)):
                    handler = getattr(handler(), req.method.lower(), None)
                    if handler is not None:
                        #if len(inspect.getfullargspec(handler).args)
                        try:
                            handler(req, resp, **kwargs)
                        except TypeError:
                            handler(resp, **kwargs)
                    else:
                        resp = Response.response()
                        resp.status_code = 405
                        resp.text = "405 Method Not Allowed"
                    self.task[1].send(resp.compile())
                else:            
                    try:
                        handler(req, resp, **kwargs)
                    except TypeError:
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
                    resp.body = open((os.path.join(os.path.dirname(os.path.abspath(task[0].context)),"static")) + req.path, "rb").read()
                    resp.headers[b"Cache-Control"] = ("max-age=" + str(task[0].StaticCacheAge)).encode()
                except FileNotFoundError:
                    resp = Response.response()
                    task[1].send(resp.compile())
            task[1].send(resp.compile())
            return True
        except Exception as e:
            print("********************")
            print(type(e))
            exc_type, exc_obj, exc_tb = sys.exc_info()
            fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
            print(exc_type, fname, exc_tb.tb_lineno)
            resp.text = "Well My Work Was Not Clean Enough, but...<br><b>Thats A Server Problem</b>"
            resp.status_code = 500
            task[1].send(resp.compile())
            return False

class ServerShutdown():
    def __init__(self, messageQueue, value):
        self.value = value
        messageQueue.put("ServerShutdown")
    
    def __str__(self):
        return "Server Shutdown: " + self.value