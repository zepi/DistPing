import cherrypy
from cherrypy.lib import auth_basic
import time

import distping

class DistPingFrontend(object):
    @cherrypy.expose
    def index(self):
        raise cherrypy.HTTPRedirect('/index.html')

class DistPingDataFrontend(object):
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_targets(self):
        result = distping.getConfigValue('tree')
       
        return result
    
    @cherrypy.expose
    @cherrypy.tools.json_out()
    def get_latest_values(self):
        result = {}
        
        for rec in (distping.database('time') > time.time() - 45):
            result[rec['host']] = {
                'host': rec['host'],
                'status': rec['status'],
                'time': rec['time'],
                'sent': rec['sent'],
                'received': rec['received'],
                'loss': rec['loss'],
                'min': rec['min'],
                'avg': rec['avg'],
                'max': rec['max']
            }
            
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
            
        return result

def validateUsernameAndPassword(realm, username, password):
    users = distping.getConfigValue('users')
    
    if username in users and users[username] == password:
         return True
   
    return False
    
def startFrontendThread():
    cherrypy.config.update({
        'server.socket_host': distping.getConfigValue('host.web.ipAddress'), 
        'server.socket_port': distping.getConfigValue('host.web.port') 
    })
    
    distPingFrontend = DistPingFrontend()
    distPingFrontend.data = DistPingDataFrontend()
    
    cherrypy.quickstart(distPingFrontend, '/', config={
        '/': {
            'tools.staticdir.debug': True,
            'tools.staticdir.on': True,
            'tools.staticdir.root': distping.getRootDirectory() + '/web',
            'tools.staticdir.dir': '',
            'log.screen': True,
            
            # Auth
            'tools.auth_basic.on': True,
            'tools.auth_basic.realm': 'DistPing',
            'tools.auth_basic.checkpassword': validateUsernameAndPassword
        }
    })