import time
import logging

import distping
import config
import fping
import monitor

latestValues = {}
lastCheck = 0
nextCheck = 0

def getTargets():
    tree = config.getSharedConfigValue('targets')
    targets = []
    
    for group in tree:
        targets = targets + group['targets']
        
    return targets

def getLatestValues():
    if (len(monitor.latestValues) == 0):
        return {}
    
    return monitor.latestValues

def executeCheck():
    targets = getTargets()
    
    if (len(targets) == 0):
        logging.info('No targets available.')
        return
    
    results = fping.pingTargets(targets)

    # Save the results in the local database    
    for result in results:
        monitor.latestValues[result['target']] = {
            'host': result['target'],
            'status': result['status'],
            'time': result['time'],
            'sent': result['statistic']['sent'],
            'received': result['statistic']['received'],
            'loss': result['statistic']['loss'],
            'min': result['timing']['min'],
            'avg': result['timing']['avg'],
            'max': result['timing']['max']
        }

def getStatusForLossValue(lossAverage):
    status = 'online'
    
    if (lossAverage > float(config.getSharedConfigValue('analysis.thresholdDown'))):
        status = 'offline'
    elif (lossAverage > float(config.getSharedConfigValue('analysis.thresholdUnstable'))):
        status = 'unstable'
        
    return status

def startMonitorThread():
    while (not distping.exitApplication):
        try:
            if (monitor.nextCheck < time.time()):
                monitor.lastCheck = int(time.time())
                monitor.nextCheck = monitor.lastCheck + config.getSharedConfigValue('check.interval')
                
                logging.debug('Perform a check...')
                executeCheck()
            
            time.sleep(1)
        except KeyboardInterrupt as err:
            return
