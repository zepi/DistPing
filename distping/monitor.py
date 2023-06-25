import time
import logging

import distping
import config
import fping
import monitor
import websocket
import checks
import utils

latestValues = {}

def groupTargets(tree):
    pingableTargets = {}
    otherTargets = {}
    
    observerName = config.getLocalConfigValue('observerName')
    
    for group in tree:
        for target in group['targets']:
            if 'observers' in target and observerName not in target['observers']:
                continue
            
            path = utils.getPath(group, target)
            
            if target['type'] == 'ping':
                pingableTargets[path] = {
                    **target,
                    'path': path
                }
            else:
                otherTargets[path] = {
                    **target,
                    'path': path
                }
            
    return (pingableTargets, otherTargets)

def getAllTargets(tree):
    targets = {}

    observerName = config.getLocalConfigValue('observerName')

    for group in tree:
        for target in group['targets']:
            if 'observers' in target and observerName not in target['observers']:
                continue

            path = utils.getPath(group, target)

            targets[path] = {
                **target,
                'path': path
            }

    return targets

def getLatestValues():
    if (len(monitor.latestValues) == 0):
        return {}
    
    return monitor.latestValues

def executePingChecks(targets):
    results = fping.pingTargets(targets)

    # Save the results in the local database    
    for result in results:
        target = targets[result['path']]
        
        monitor.latestValues[result['path']] = {
            'host': target['host'],
            'status': result['status'],
            'time': result['time'],
            'data': result['data']
        }
        websocket.broadcastMessage({
            'type': 'status-update',
            'path': result['path'],
            'status': result['status'],
            'data': result['data']
        })
        
def executeOtherChecks(targets):
    results = checks.checkTargets(targets)

    # Save the results in the local database
    for result in results:
        target = targets[result['path']]

        if (target['type'] == 'port'):
            host = target['host']
        else:
            host = target['url']

        monitor.latestValues[result['path']] = {
            'host': host,
            'status': result['status'],
            'time': result['time'],
            'data': result['data']
        }
        websocket.broadcastMessage({
            'type': 'status-update',
            'path': result['path'],
            'status': result['status'],
            'data': result['data']
        })

def getStatusForPingLossValue(lossAverage):
    status = 'online'
    
    if (lossAverage > float(config.getSharedConfigValue('analysis.thresholdDown'))):
        status = 'offline'
    elif (lossAverage > float(config.getSharedConfigValue('analysis.thresholdUnstable'))):
        status = 'unstable'
        
    return status

def startMonitorThread():
    lastCheck = 0
    
    tree = config.getSharedConfigValue('targets')
    pingableTargets, otherTargets = groupTargets(tree)
    
    while (not distping.exitApplication):
        try:
            if (lastCheck + config.getSharedConfigValue('check.interval') < time.time()):
                lastCheck = time.time()
                
                logging.debug('Perform a check...')
                
                if (len(pingableTargets) > 0):
                    executePingChecks(pingableTargets)
                    
                if (len(otherTargets) > 0):
                    executeOtherChecks(otherTargets)
            
            time.sleep(1)
        except KeyboardInterrupt as err:
            return
