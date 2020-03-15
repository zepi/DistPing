import cherrypy
from cherrypy.lib import auth_basic
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
import time
import logging

import distping
import config
import collector
import template
import monitor
import utils
from websocket import DistPingServer

class DistPingFrontend(object):
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect('/status')
    
    @cherrypy.expose
    def status(self):
        statusNumbers = countTargetsByStatus()
        
        return template.renderTemplate(
            'pages/index.html',
            statusNumbers=statusNumbers,
            observerConnections=collector.getConnectionStatistics(), 
            targets=config.getSharedConfigValue('targets'), 
            latestValues=monitor.getLatestValues()
        )
    
    @cherrypy.expose
    def ws(self):
        handler = cherrypy.request.ws_handler

def validateUsernameAndPassword(realm, username, password):
    users = config.getLocalConfigValue('users')
    
    if username in users and users[username] == password:
         return True
   
    return False
    
def countTargetsByStatus():
    numbers = {
        'online': 0,
        'unstable': 0,
        'offline': 0
    }
    
    for data in monitor.getLatestValues().values():
        numbers[data['status']] = numbers[data['status']] + 1
    
    return numbers
    
def startFrontendThread():
    template.initializeTemplateSystem()
    
    cherrypy.config.update({
        'server.socket_host': config.getLocalConfigValue('server.ipAddress'), 
        'server.socket_port': config.getLocalConfigValue('server.port'),
        'log.screen': False,
        'log.access_file': '',
        'log.error_file': ''
    })
    cherrypy.engine.unsubscribe('graceful', cherrypy.log.reopen_files)
    
    distping.configureLogging()
    
    # Configure SSL
    if (config.getLocalConfigValue('server.ssl.enabled')):
        cherrypy.config.update({
            'server.ssl_certificate': config.getLocalConfigValue('server.ssl.certificate'),
            'server.ssl_private_key': config.getLocalConfigValue('server.ssl.privateKey')
        })
        
        if (config.getLocalConfigValue('server.ssl.certificateChain') != ''):
            cherrypy.config.update({
                'server.ssl_certificate_chain': config.getLocalConfigValue('server.ssl.certificateChain')
            })

    
    distPingFrontend = DistPingFrontend()
    
    WebSocketPlugin(cherrypy.engine).subscribe()
    cherrypy.tools.websocket = WebSocketTool()
    
    cherrypy.quickstart(distPingFrontend, '/', config={
        '/': {
            'tools.staticdir.on': True,
            'tools.staticdir.root': distping.getRootDirectory() + '/web',
            'tools.staticdir.dir': '',
            
            # Auth
            'tools.auth_basic.on': True,
            'tools.auth_basic.realm': 'DistPing',
            'tools.auth_basic.checkpassword': validateUsernameAndPassword
        },
        '/ws': {
            'tools.websocket.on': True,
            'tools.websocket.handler_cls': DistPingServer,
            
            # Auth
            'tools.auth_basic.on': False,
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': distping.getRootDirectory() + '/web/resources/img/favicon.ico'
        }
    })