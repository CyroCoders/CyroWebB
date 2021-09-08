class response:
    def __init__(self):
        self.proto = b"HTTP/1.1"
        self.status_code = 200
        self.headers = {}
        self.body = None
        self.text = ""
        self.headers[b"Server"] = b"CyroWebB"

    def compile(self):
        if self.body is None: self.headers[b"Content-Length"] = str(len(self.text)).encode("utf-8")
        else: self.headers[b"Content-Length"] = str(len(self.body)).encode("utf-8")
        rv = b""
        rv += self.proto + b" " + str(self.status_code).encode("utf-8") + b"\r\n"
        for key in self.headers.keys():
            rv += key
            rv += b": "
            rv += self.headers[key]
            rv += b"\r\n"
        rv += b"\r\n"
        if self.body is None: rv += self.text.encode("utf-8")
        else: rv += self.body
        return rv