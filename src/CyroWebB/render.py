import os
from jinja2 import Environment, FileSystemLoader

class Template:
    def __init__(self, f="templates"):
        self.templates_env = Environment(loader=FileSystemLoader(os.path.abspath(f)))

    def __call__(self, file, data=None):
        if data is None:
            data = {}
            
        return self.templates_env.get_template(file).render(**data)

        with open(file) as f:
            return f.read()