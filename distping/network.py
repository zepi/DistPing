import p2py
import time
import logging

import distping
import config
import monitor
import collector
import status
import network
import websocket

node = None
observerMapping = {}

class DistpingNode(p2py.P2P_Node):
    def send_to_all(self, message):
        for connection in self.connections:
            connection.send_message(message)

    def event_new_peer_added_to_peer_book(self, address, UUID):
        websocket.sendObserverCountUpdate()

    def event_closed_connection(self, address, UUID=None):
        websocket.sendObserverCountUpdate()

def actionGetLatestValues(conn, message):
    logging.debug('Received request from the leader for the latest values.')
    latestValues = monitor.getLatestValues()

    conn.send_message({
        'type': 'SET_LATEST_VALUES',
        'observerName': config.getLocalConfigValue('observerName'),
        'data': latestValues
    })

def actionSetLeader(conn, message):
    collector.leader = message['leader']

def actionSetStatus(conn, message):
    status.statusData = message['data']

def actionSetLatestValues(conn, message):
    collector.lastData[message['observerName']] = message['data']

def actionSetLastAnalysis(conn, message):
    collector.lastAnalysisTime = time.time() - message['duration']

def sendToAllPeers(message):
    if node == None:
        return

    if not network.node.is_connected():
        return

    network.node.send_to_all(message)

def startNetworkThread():
    network.node = DistpingNode(port=config.getLocalConfigValue('server.networkPort'), host=config.getLocalConfigValue('server.networkIpAddress'))

    network.node.add_handler('GET_LATEST_VALUES', actionGetLatestValues)
    network.node.add_handler('SET_LEADER', actionSetLeader)
    network.node.add_handler('SET_STATUS', actionSetStatus)
    network.node.add_handler('SET_LATEST_VALUES', actionSetLatestValues)
    network.node.add_handler('SET_LAST_ANALYSIS', actionSetLastAnalysis)

    network.node.start()

    observerName = config.getLocalConfigValue('observerName')

    observers = config.getSharedConfigValue('observers')
    addresses = []
    for key, observer in observers.items():
        if key == observerName:
            continue

        network.observerMapping[observer['ipAddress'] + ':' + str(observer['port'])] = key
        addresses.append((observer['ipAddress'], int(observer['port'])))

    network.node.join_network(addresses)

    while not distping.exitApplication:
        try:
            time.sleep(1)
        except KeyboardInterrupt as err:
            return