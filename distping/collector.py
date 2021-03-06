import json
import logging
import time
import random

import distping
import config
import monitor
import websocket
import collector
import status
import actions

connections = {}
leader = False
lastAnalysisTime = 0

def getConnectionStatistics():
    return {
        'total': len(config.getSharedConfigValue('observers')),
        'connected': len(collector.connections) + 1 # Add 1 for this process because we are also an observer connection
    }

def checkConnections():
    for name, observerData in config.getSharedConfigValue('observers').items():
        if (name == config.getLocalConfigValue('observerName')):
            continue
        
        if (name in collector.connections):
            connection = collector.connections[name]
            
            if (not connection.terminated):
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
    
    for name, observerData in observers.items():
        if (name == config.getLocalConfigValue('observerName')):
            collector.lastData[name] = monitor.getLatestValues()
        elif (name in collector.connections):
            connection = collector.connections[name]
            connection.send(json.dumps({
                'command': 'get_latest_values'
            }))

    waitForData = True
    complete = False
    counter = 0
    while (waitForData):
        if (len(collector.lastData) == len(observers)):
            logging.debug('Got all data responses from observers.')
            
            complete = True
            waitForData = False
        
        time.sleep(0.2)
        counter = counter + 1
        
        if (counter > 50):
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
            if (targetKey not in dataByTarget):
                dataByTarget[targetKey] = {}
            
            dataByTarget[targetKey][observerName] = values
            
    return dataByTarget

def analyzeData(dataByTarget):
    for targetKey, observerValues in dataByTarget.items():
        minValues = []
        avgValues = []
        maxValues = []
        lossValues = []
        statusValues = []
        
        for observerName, data in observerValues.items():
            minValues.append(float(data['min']))
            avgValues.append(float(data['avg']))
            maxValues.append(float(data['max']))
            lossValues.append(float(data['loss']))
            statusValues.append(data['status'])
            
        numberOfObservers = len(observerValues)
        minValue = round(sum(minValues) / numberOfObservers, 2)
        avgValue = round(sum(avgValues) / numberOfObservers, 2)
        maxValue = round(sum(maxValues) / numberOfObservers, 2)
        lossValue = round(sum(lossValues) / numberOfObservers, 2)
        targetStatus = monitor.getStatusForLossValue(lossValue)
        
        status.setStatus(targetKey, targetStatus, {
            'min': minValue,
            'avg': avgValue,
            'max': maxValue,
            'loss': lossValue,
            'observerData': observerValues
        })
        
        actions.executeActions('target-analysis-finished', {
            'targetKey': targetKey,
            'time': time.time(),
            'status': targetStatus,
            'min': minValue,
            'avg': avgValue,
            'max': maxValue,
            'loss': lossValue,
            'values': observerValues
        })
    
def switchLeader(startTime):
    duration = time.time() - startTime
    
    collector.leader = getObserverRandomly()
    collector.lastAnalysisTime = time.time() - duration
    
    logging.debug('New leader: {}'.format(collector.leader))
    
    setLeaderCommand = json.dumps({
        'command': 'set_leader',
        'leader': collector.leader
    })
    setLastAnalysisCommand = json.dumps({
        'command': 'set_last_analysis',
        'duration': duration
    })
    
    if (status.statusChanged):
        setStatusCommand = json.dumps({
            'command': 'set_status',
            'data': status.statusData
        })
    
    for name in collector.connections:
        connection = collector.connections[name]
        
        connection.send(setLastAnalysisCommand)
        
        if (status.statusChanged):
            connection.send(setStatusCommand)
            
        connection.send(setLeaderCommand)
    
def getObserverRandomly():
    connectedObservers = connections.keys()
    
    if len(connectedObservers) == 0:
        return config.getLocalConfigValue('observerName')
    
    return random.choice(list(connectedObservers))

def startCollectorThread():
    time.sleep(2)
    
    analysisTimeInterval = config.getSharedConfigValue('analysis.timeInterval')
    observerName = config.getLocalConfigValue('observerName')
    
    while (not distping.exitApplication):
        try:
            checkConnections()
            
            if (collector.leader == observerName and (lastAnalysisTime + analysisTimeInterval) < time.time()): 
                logging.debug('Start analysis...')
                analyzeTargets()
                
            if (collector.leader != observerName and (lastAnalysisTime + (2 * analysisTimeInterval)) < time.time()):
                logging.debug('Leader did not collect the information. Taking control...')
                switchLeader(time.time() - analysisTimeInterval)
                
            if (collector.leader == False):
                collector.leader = observerName
            
            time.sleep(15)
        except KeyboardInterrupt as err:
            return