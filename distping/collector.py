import json
import logging
import time
import random

import distping
import config
import monitor
import websocket
import collector

connections = {}
leader = False
lastAnalysisTime = 0

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
        else:
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
        if (counter > 100):
            logging.error('Not all observers sent their latest usage data. Process will continue without the data.')
            waitForData = False
    
    logging.debug('Group the data to start the analysis.')
    dataByTarget = groupDataByTarget()
    
    logging.debug('Analyze the grouped data.')
    analyzeData(dataByTarget)
    
    # TODO: Switch to a websocket manager object and broadcast the requests
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
        status = getStatusByObservers(statusValues, numberOfObservers)
        
        print(targetKey + ': STATUS: ' + status + ' (min: ' + str(minValue) + ', avg: ' + str(avgValue) + ', max: ' + str(maxValue) + ', loss: ' + str(lossValue) + '%)')
           
def getStatusByObservers(statusValues, numberOfObservers):
    statusCounted = {'online': 0, 'flapping': 0, 'offline': 0}
    for statusValue in statusValues:
        statusCounted[statusValue] = statusCounted[statusValue] + 1
    
    status = 'online'
    if (numberOfObservers > statusCounted['online']):
        down = statusCounted['flapping'] + statusCounted['offline']
        percentageDown = (100 / numberOfObservers) * down
        
        if (percentageDown > 33.333):
            status = 'offline'
        else:
            status = 'flapping'
        
    return status
    
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
    
    for name in collector.connections:
        connection = collector.connections[name]
        
        connection.send(setLeaderCommand)
        connection.send(setLastAnalysisCommand)
    
def getObserverRandomly():
    observers = config.getSharedConfigValue('observers')
    
    return random.choice(list(observers.keys()))

def startCollectorThread():
    time.sleep(2)
    
    analysisTimeInterval = config.getSharedConfigValue('check.analysisTimeInterval')
    observerName = config.getLocalConfigValue('observerName')
    
    while (not distping.exitApplication):
        try:
            checkConnections()
            
            if (collector.leader == observerName and (lastAnalysisTime + analysisTimeInterval) < time.time()): 
                logging.debug('It is time to analyse the data.')
                analyzeTargets()
                
            if (collector.leader == False):
                collector.leader = observerName
            
            time.sleep(15)
        except KeyboardInterrupt as err:
            return