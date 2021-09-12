def create(server):
    @server.create_endpoint("/icon/{name}.svg")
    def icons(req,res,name):
        server.get_external(res,f"https://cdn.jsdelivr.net/gh/CyroCoders/CyroWebF/icon/{name}.svg")