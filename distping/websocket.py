from ws4py.websocket import WebSocket
from ws4py.messaging import TextMessage
import cherrypy
import json

import config
import monitor
import network
import utils

class DistPingFrontendServer(WebSocket):
    def received_message(self, message):
        parsedMessage = json.loads(str(message))

        if (parsedMessage['command'] == 'get_status'):
            targets = config.getSharedConfigValue('targets')
            latestValues = monitor.getLatestValues()

            for category in targets:
                for target in category['targets']:
                    path = utils.getPath(category, target)
                    if path in latestValues:
                        val = latestValues[path]
                        status = val['status']
                        data = val['data']
                    else:
                        status = 'offline'
                        data = {}

                    self.send(json.dumps({
                        'type': 'status-update',
                        'path': path,
                        'status': status,
                        'data': data,
                    }))

        sendObserverCountUpdate()

def broadcastMessage(message):
    cherrypy.engine.publish('websocket-broadcast', TextMessage(json.dumps(message)))

def sendObserverCountUpdate():
    broadcastMessage({
        'type': 'observer-count-update',
        'numberOfConnectedObservers': len(network.node.connections) + 1,
        'numberOfTotalObservers': len(network.observerMapping) + 1,
    })