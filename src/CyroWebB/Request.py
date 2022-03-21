class request:
    def __init__(self, _str):
        self.method = _str.split(b"\r\n\r\n")[0].split(b"\r\n")[0].split(b" HTTP")[0].split(b" ")[0].decode("utf-8")
        self.path = _str.split(b"\r\n\r\n")[0].split(b"\r\n")[0].split(b" HTTP")[0].split(b" ")[1].decode("utf-8")
        self.headers = _str.split(b"\r\n\r\n")[0].split(b"\r\n")
        headerL = {}
        for header in self.headers:
            if(b": " in header):
                headerL[header.split(b": ")[0]] = header.split(b": ")[1]
            else:
                self.proto = header
        self.headers = headerL
        self.cookies = {}
        if b'Cookie' in self.headers:
            for cookie in self.headers[b'Cookie'].split(b";"):
                if cookie == "":
                    continue
                self.cookies[cookie.split(b"=")[0]] = cookie.split(b"=")[1]
        self.data = {}
        if(len(_str.split(b"\r\n\r\n")) == 2 and not _str.split(b"\r\n\r\n")[1] == b""):
            self.body = _str.split(b"\r\n\r\n")[1]
            self.headers[b"Content-Length"] = str(len(self.body)).encode()
            for post_data in self.body.split('\n').split(b"&"):
                if post_data == "":
                    continue
                self.data["POST"][post_data.split(b"=")[0]] = cookie.split(b"=")[1]
        if '?' in self.path:
            self.get_string = self.path.split('?')[1]
            self.path = self.path.split('?')[0]
            if '&' in self.get_string:
                self.get_string = self.get_string.split('&')
            else:
                self.get_string = [self.get_string]
            self.data["GET"] = {k: v for k, v in (x.split('=') for x in self.get_string)}
        else:
            self.body = None

    def compile(self):
        rv = b""
        rv += self.proto + b"\r\n"
        headers = {}
        for key in self.headers.keys():
            try:
                headers[key] = self.headers[key].encode()
            except:
                headers[key] = self.headers[key]
            try:
                headers[key.encode()] = self.headers[key]
                del headers[key]
            except:
                headers[key] = self.headers[key]
        self.headers = headers
        for key in self.headers.keys():
            rv += key
            rv += b": "
            rv += self.headers[key]
            rv += b"\r\n"
        rv += b"\r\n"
        if not self.body is None:
            rv += self.body
        return rv