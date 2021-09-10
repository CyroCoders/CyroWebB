import os
from jinja2 import Environment, FileSystemLoader

class Template:
    def __init__(self,server,f="templates"):
        self.templates_env = Environment(loader=FileSystemLoader(os.path.join(os.path.dirname(os.path.abspath(server.context)),f)))

    def __call__(self, file, data=None):
        if data is None:
            data = {}
            
        return self.templates_env.get_template(file).render(**data)