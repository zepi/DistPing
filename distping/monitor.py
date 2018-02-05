import time
import logging

import distping
import config
import fping

def getTargets():
    tree = config.getSharedConfigValue('targets')
    targets = []
    
    for group in tree:
        targets = targets + group['targets']
        
    return targets

def getLatestValues():
    result = {}
        
    for rec in (distping.database('time') > time.time() - (config.getSharedConfigValue('check.interval') * 1.2)):
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

def executeCheck():
    targets = getTargets()
    
    if (len(targets) == 0):
        logging.info('No targets available.')
        return
    
    results = fping.pingTargets(targets)

    # Save the results in the local database    
    for result in results:
        distping.database.insert(
            result['time'], 
            result['target'], 
            result['status'], 
            result['statistic']['sent'], 
            result['statistic']['received'], 
            result['statistic']['loss'], 
            result['timing']['min'], 
            result['timing']['avg'], 
            result['timing']['max']
        )
    
    distping.database.commit()

def startMonitorThread():
    lastCheck = 0
    
    while (not distping.exitApplication):
        try:
            if (lastCheck + config.getSharedConfigValue('check.interval') < time.time()):
                lastCheck = time.time()
                
                logging.info('Perform a check...')
                executeCheck()
            
            time.sleep(0.1)
        except KeyboardInterrupt as err:
            return