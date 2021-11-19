import os

class Plugin(object):
    def __init__(self,server) -> None:
        self.DataDir = os.path.join("\\".join(server.context.split("\\")[:-1]),"Plugins","".join(str(self.__class__).split(".")[-1:-3]))
        self.server = server
        self.LRUMaxLenght = 32
        self.lru_cache_list = []
        self.lru_cache = {}

    def __call__(self):
        return

    def intercept_request(self,request):
        return request

    def intercept_response(self,response):
        return response

    def from_lru_cache(self,key,source):
        if(key not in self.lru_cache_list):
            self.lru_cache[key] = source(key)
            if len(self.lru_cache_list) > self.LRUMaxLenght:
                del self.lru_cache[self.lru_cache_list[0]]
                self.lru_cache_list.pop(0)
        else:
            self.lru_cache_list.remove(key)
        self.lru_cache_list.append(key)
        return self.lru_cache[key]

    def to_lru_cache(self,key,value,target):
        self.lru_cache[key] = value
        self.lru_cache_list.append(key)
        if len(self.lru_cache_list) > self.LRUMaxLenght:
            del self.lru_cache[self.lru_cache_list[0]]
            self.lru_cache_list.pop(0)
        return target(key,value)