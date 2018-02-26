from mako.template import Template
from mako.lookup import TemplateLookup
import os

import distping
import template

lookup = None

def initializeTemplateSystem():
    template.lookup = TemplateLookup(directories=[os.path.join(distping.getRootDirectory(), 'templates')])
    
def renderTemplate(templateName, **kwargs):
    templateFile = template.lookup.get_template(templateName)
    
    return templateFile.render(**kwargs)