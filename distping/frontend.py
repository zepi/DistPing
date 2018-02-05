import cherrypy
from cherrypy.lib import auth_basic
from ws4py.server.cherrypyserver import WebSocketPlugin, WebSocketTool
import time
import logging

import distping
import config
import monitor
from websocket import DistPingServer

class DistPingFrontend(object):
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect('/index.html')
    
    @cherrypy.expose
    def ws(self):
        handler = cherrypy.request.ws_handler

class DistPingDataFrontend(object):
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_targets(self):
        result = config.getSharedConfigValue('targets')
       
        return result
    
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_latest_values(self):
        return monitor.getLatestValues()
    
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_latest_history(self, duration=900):
        result = {}
        
        for rec in (distping.database('time') > time.time() - int(duration)):
            key = rec['host']
            if (key not in result):
                result[key] = []
            
            result[rec['host']].append({
                'host': rec['host'],
                'status': rec['status'],
                'time': rec['time'],
                'sent': rec['sent'],
                'received': rec['received'],
                'loss': rec['loss'],
                'min': rec['min'],
                'avg': rec['avg'],
                'max': rec['max']
            })
            
        for key in result:
            result[key] = sorted(result[key], key=sortByTime)
            
        return result
    
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_history(self, host, duration=3600):
        result = []
        
        for rec in (distping.database('time') > time.time() - int(duration)) & (distping.database('host') == host):
            result.append({
                'host': rec['host'],
                'status': rec['status'],
                'time': rec['time'],
                'sent': rec['sent'],
                'received': rec['received'],
                'loss': rec['loss'],
                'min': rec['min'],
                'avg': rec['avg'],
                'max': rec['max']
            })
            
        return sorted(result, key=lambda entry: entry['time'])
    
def sortByTime(element):
    return element['time']

def validateUsernameAndPassword(realm, username, password):
    users = config.getLocalConfigValue('users')
    
    if username in users and users[username] == password:
         return True
   
    return False
    
def startFrontendThread():
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
    distPingFrontend.data = DistPingDataFrontend()
    
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
    })