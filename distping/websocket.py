import logging
from ws4py.client.threadedclient import WebSocketClient
from ws4py.websocket import WebSocket
from ws4py.manager import WebSocketManager
import time
import json

import distping
import config
import monitor
import collector
import websocket

manager = WebSocketManager()

class DistPingClient(WebSocketClient):
    def opened(self):
        self.send(json.dumps({
            'command': 'authenticate',
            'key': config.getSharedConfigValue('secretKey')
        }))
        
    def received_message(self, message):
        parsedMessage = json.loads(str(message))
        
        executeClientRequest(self, parsedMessage)

class DistPingServer(WebSocket):
    isAuthorized = False
    
    def received_message(self, message):
        parsedMessage = json.loads(str(message))
        
        if (parsedMessage['command'] == 'authenticate'):
            if (parsedMessage['key'] == config.getSharedConfigValue('secretKey')):
                self.isAuthorized = True
                websocket.manager.add(self)
                
                logging.info('Observer {} authenticated with secret key.'.format(self.peer_address[0]))
                
                self.send(json.dumps({
                    'response': 'welcome',
                    'leader': collector.leader
                }))
            else:
                self.isAuthorized = False
                
                logging.warning('Authorization with invalid secret key from {}.'.format(self.peer_address[0]))
                
                self.send(json.dumps({'response': 'secret_key_invalid'}))
                self.close(1000, 'Secret key invalid.')
        else:
            executeServerRequest(self, parsedMessage)
            
    def closed(self, code, message):
        websocket.manager.remove(self)
        
def executeServerRequest(socket, parsedMessage):
    if (parsedMessage['command'] == 'get_latest_config'):
        socket.send('config:def')
    elif (parsedMessage['command'] == 'get_latest_values'):
        logging.debug('Received request from the leader for the latest values.')
        latestValues = monitor.getLatestValues()

        socket.send(json.dumps({
            'response': 'latest_values',
            'observerName': config.getLocalConfigValue('observerName'),
            'data': latestValues
        }))
    elif (parsedMessage['command'] == 'set_leader'):
        collector.leader = parsedMessage['leader']
        
        socket.send(json.dumps({'response': 'leader_set'}))
    elif (parsedMessage['command'] == 'set_last_analysis'):
        collector.lastAnalysisTime = time.time() - parsedMessage['duration']
        
        socket.send(json.dumps({'response': 'last_analysis_set'}))
        
def executeClientRequest(socket, parsedMessage):
    if (parsedMessage['response'] == 'welcome'):
        if (parsedMessage['leader'] == False and collector.leader == False):
            collector.leader = collector.getObserverRandomly()
            
            sendCommandToSetNewLeader(collector.leader)
        elif (parsedMessage['leader'] == False and collector.leader != False):
            sendCommandToSetNewLeader(collector.leader)
        else:
            collector.leader = parsedMessage['leader']
    elif (parsedMessage['response'] == 'latest_values'):
        logging.debug('Received latest values from {}.'.format(parsedMessage['observerName']))
        collector.lastData[parsedMessage['observerName']] = parsedMessage['data']
    
def sendCommandToSetNewLeader(newLeader):
    websocket.manager.broadcast(json.dumps({
        'command': 'set_leader',
        'leader': newLeader
    }))