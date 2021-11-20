from . import base
import json, os, hashlib,datetime

class Database(base.Plugin):
    def __init__(self,server) -> None:
        super().__init__(server)
        parent = self
        @server.create_endpoint("/api/db/{path}")
        class dbAPI():
            def get(self,res,path):
                res.text = parent.from_lru_cache(path,self.from_json)
                return res.text

            def put(self,req,res,path):
                a = parent.to_lru_cache(path,req.body,self.to_json)
                res.status = 201
                res.headers[b"Content-Location"] = f"/api/db/{path}".encode()
                res.text = f"Added Data To {path}:\n{a}"
                return res.text

            def post(self,req,res,path):
                hash  = hashlib.md5()
                hash.update(datetime.datetime.now().strftime('%Y%m%d%H%M%S%f').encode())
                key = hash.hexdigest()[:10]
                path = os.path.join(path,key)
                print(key)
                a = parent.to_lru_cache(path,req.body,self.to_json)
                res.status = 201
                res.headers[b"Content-Location"] = f"/api/db/{path}".encode()
                res.text = f"Added Data To {path}:\n{a}"
                return res.text

            def delete(self,res,path):
                res.text = str({"data": "String-Data"})
                return res.text

            def from_json(self,key):
                os.makedirs(parent.DataDir, exist_ok=True)
                with open(os.path.join(parent.DataDir,"db.json"),"r+") as file:
                    data = json.load(file)
                    for _key in key.split("/"):
                        data = data[_key]
                    return data

            def to_json(self,key,value):
                os.makedirs(parent.DataDir, exist_ok=True)
                with open(os.path.join(parent.DataDir,"db.json"),"a+") as file:
                    file.seek(0)
                    keys = key.split("/")
                    keys.reverse()
                    keys = [key for key in keys if key!=""]
                    data = {keys[0]: value.decode()}
                    if len(keys) > 1:
                        for _key in keys[1:]:
                            data = {_key: data}
                    try:
                        db_data = json.load(file)
                    except json.JSONDecodeError:
                        db_data = {}
                    self.recursive_update(db_data,data)
                    print(db_data, data)
                    file.truncate(0)
                    json.dump(db_data, file)
                    
                return data

            def recursive_update(self,source,update): #source: https://gist.github.com/angstwad/bf22d1822c38a92ec0a9
                for k, v in update.items():
                    if (k in source and isinstance(source[k], dict)
                            and isinstance(update[k], dict)):
                        self.recursive_update(source[k], update[k])
                    else:
                        source[k] = update[k]

        self.api = dbAPI