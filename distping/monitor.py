import time
import logging

import distping
import fping

def findTargetsInConfig(childNodes = None):
    targets = []
    
    if (childNodes == None):
        childNodes = distping.getConfigValue('tree')
    
    for childNode in childNodes:
        if ('nodes' in childNode):
            targets = targets + findTargetsInConfig(childNode['nodes'])
        else:
            targets.append(childNode)

    return targets

def executeCheck():
    targets = findTargetsInConfig()
    
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
            if (lastCheck + distping.getConfigValue('check.interval') < time.time()):
                lastCheck = time.time()
                
                logging.info('Perform a check...')
                executeCheck()
            
            time.sleep(0.1)
        except KeyboardInterrupt as err:
            return