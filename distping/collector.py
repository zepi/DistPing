import json
import logging
import time
import random

import distping
import config
import monitor
import websocket
import collector
import network
import status
import actions

connections = {}
leader = False
lastAnalysisTime = 0
lastData = None

def getConnectionStatistics():
    return {
        'total': len(config.getSharedConfigValue('observers')),
        'connected': len(collector.connections) + 1 # Add 1 for this process because we are also an observer connection
    }

def checkConnections():
    for name, observerData in config.getSharedConfigValue('observers').items():
        if name == config.getLocalConfigValue('observerName'):
            continue
        
        if name in collector.connections:
            connection = collector.connections[name]
            
            if not connection.terminated:
                continue
            else:
                connection.close()
                del connections[name]
        
        try:
            connection = websocket.DistPingClient(observerData['url'])
            connection.connect()
        
            collector.connections[name] = connection
        except OSError as err:
            logging.error('Cannot connect to "{}" ({}). Error message: {}'.format(name, observerData['url'], str(err)))
        
def analyzeTargets():
    collector.lastData = {}
    observers = config.getSharedConfigValue('observers')
    startTime = time.time()

    collector.lastData[config.getLocalConfigValue('observerName')] = monitor.getLatestValues()
    network.sendToAllPeers({
        'type': 'GET_LATEST_VALUES'
    })

    waitForData = True
    counter = 0
    while waitForData:
        if len(collector.lastData) == len(observers):
            logging.debug('Got all data responses from observers.')
            
            waitForData = False
        
        time.sleep(0.2)
        counter = counter + 1
        
        if counter > 50:
            logging.error('Not all observers sent their latest usage data. Process will continue without the data.')
            waitForData = False
    
    logging.debug('Group the data to start the analysis.')
    dataByTarget = groupDataByTarget()
    
    logging.debug('Analyze the grouped data.')
    analyzeData(dataByTarget)
    
    switchLeader(startTime)
    
def groupDataByTarget():
    dataByTarget = {}
    
    for observerName, data in collector.lastData.items():

        for targetKey, values in data.items():
            if targetKey not in dataByTarget:
                dataByTarget[targetKey] = {}
            
            dataByTarget[targetKey][observerName] = values
            
    return dataByTarget

def analyzeData(dataByTarget):
    targets = monitor.getAllTargets(config.getSharedConfigValue('targets'))

    for targetKey, observerValues in dataByTarget.items():
        numberOfObservers = len(observerValues)
        targetStatus = 'offline'

        targetData = []
        statusValues = []

        target = targets[targetKey]

        if target['type'] == 'ping':
            minValues = []
            avgValues = []
            maxValues = []
            lossValues = []

            for observerName, data in observerValues.items():
                minValues.append(float(data['data']['min']))
                avgValues.append(float(data['data']['avg']))
                maxValues.append(float(data['data']['max']))
                lossValues.append(float(data['data']['loss']))
                statusValues.append(data['status'])

            minValue = round(sum(minValues) / numberOfObservers, 2)
            avgValue = round(sum(avgValues) / numberOfObservers, 2)
            maxValue = round(sum(maxValues) / numberOfObservers, 2)
            lossValue = round(sum(lossValues) / numberOfObservers, 2)
            targetStatus = monitor.getStatusForPingLossValue(lossValue)

            targetData = {
                'min': minValue,
                'avg': avgValue,
                'max': maxValue,
                'loss': lossValue
            }
        else:
            for observerName, data in observerValues.items():
                statusValues.append(data['status'])
                targetData = data['data']

            statusList = list(statusValues)

            numberOfOnline = statusList.count('online')
            numberOfOffline = statusList.count('offline')

            if numberOfOnline > numberOfOffline:
                targetStatus = 'online'
            else:
                targetStatus = 'offline'

        status.setStatus(targetKey, targetStatus, {
            'data': targetData,
            'observerData': observerValues
        })
        
        actions.executeActions('target-analysis-finished', {
            'targetKey': targetKey,
            'time': time.time(),
            'status': targetStatus,
            'data': targetData,
            'values': observerValues
        })
    
def switchLeader(startTime):
    duration = time.time() - startTime
    
    collector.leader = getObserverRandomly()
    collector.lastAnalysisTime = time.time() - duration
    
    logging.debug('New leader: {}'.format(collector.leader))

    network.sendToAllPeers({
        'type': 'SET_LAST_ANALYSIS',
        'duration': duration
    })

    if status.statusChanged:
        network.sendToAllPeers({
            'type': 'SET_STATUS',
            'data': status.statusData
        })

    network.sendToAllPeers({
        'type': 'SET_LEADER',
        'leader': collector.leader
    })

    
def getObserverRandomly():
    connections = network.node.connections
    
    if len(connections) == 0:
        return config.getLocalConfigValue('observerName')

    selectedConnection = random.choice(list(connections))

    key = "{0}:{1}".format(selectedConnection.connection_address[0], selectedConnection.connection_address[1])

    return network.observerMapping[key]

def startCollectorThread():
    time.sleep(2)
    
    analysisTimeInterval = config.getSharedConfigValue('analysis.timeInterval')
    observerName = config.getLocalConfigValue('observerName')
    
    while not distping.exitApplication:
        try:
            if collector.leader == observerName and (lastAnalysisTime + analysisTimeInterval) < time.time():
                logging.debug('Start analysis...')
                analyzeTargets()
                
            if collector.leader != observerName and (lastAnalysisTime + (2 * analysisTimeInterval)) < time.time():
                logging.debug('Leader did not collect the information. Taking control...')
                switchLeader(time.time() - analysisTimeInterval)
                
            if not collector.leader:
                collector.leader = observerName
            
            time.sleep(15)
        except KeyboardInterrupt as err:
            return
