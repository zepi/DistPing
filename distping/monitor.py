import time
import logging

import distping
import config
import fping
import monitor
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
            
    print(pingableTargets)
    print(otherTargets)
        
    return (pingableTargets, otherTargets)

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
            'sent': result['statistic']['sent'],
            'received': result['statistic']['received'],
            'loss': result['statistic']['loss'],
            'min': result['timing']['min'],
            'avg': result['timing']['avg'],
            'max': result['timing']['max']
        }
        
def executeOtherChecks(targets):
    results = False

def getStatusForLossValue(lossAverage):
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
