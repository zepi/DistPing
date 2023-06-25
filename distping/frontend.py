import cherrypy
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
import bcrypt

import distping
import config
import collector
import template
import monitor
from websocket import DistPingFrontendServer

class DistPingFrontend(object):
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect('/status')
    
    @cherrypy.expose
    def status(self):
        statusNumbers = countTargetsByStatus()
        
        return template.renderTemplate(
            'pages/index.html',
            pageTitle='Status',
            statusNumbers=statusNumbers,
            observerConnections=collector.getConnectionStatistics(), 
            targets=config.getSharedConfigValue('targets'), 
            latestValues=monitor.getLatestValues(),
            webIpAddress=config.getLocalConfigValue('server.webIpAddress'),
            webPort=config.getLocalConfigValue('server.webPort')
        )
    
    @cherrypy.expose
    def ws(self):
        handler = cherrypy.request.ws_handler

    @cherrypy.expose
    def ws_frontend(self):
        handler = cherrypy.request.ws_handler

def validateUsernameAndPassword(realm, username, password):
    users = config.getLocalConfigValue('users')
    
    if username in users and bcrypt.checkpw(password.encode('UTF-8'), users[username].encode('UTF-8')):
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
        'server.socket_host': config.getLocalConfigValue('server.webIpAddress'),
        'server.socket_port': config.getLocalConfigValue('server.webPort'),
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
            'tools.websocket.handler_cls': DistPingFrontendServer,

            # Auth
            'tools.auth_basic.on': False,
        },
        '/favicon.ico': {
            'tools.staticfile.on': True,
            'tools.staticfile.filename': distping.getRootDirectory() + '/web/resources/img/favicon.ico'
        }
    })