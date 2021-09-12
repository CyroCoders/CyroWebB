def create(server):
    @server.create_endpoint("/icon/{name}.svg")
    def icons(res,name):
        server.get_external(res,f"https://cdn.jsdelivr.net/gh/CyroCoders/CyroWebF/icon/{name}.svg")