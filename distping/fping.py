import subprocess
import os
import time
from distutils import spawn

import distping
import config

def pingTargets(targets):
    fpingBinary = ''
    try:
        fpingBinary = config.getSharedConfigValue('check.fpingBinary')
    except KeyError as err:
        fpingBinary = ''
        
    if (fpingBinary == '' or not os.path.isfile(fpingBinary) or not os.access(fpingBinary, os.X_OK)):
        fpingBinary = searchFpingBinary()
        
    hosts = []
    for target in targets:
        hosts.append(target['host'])
        
    # Ping the targets
    result = subprocess.run([fpingBinary, '-t', '1000', '-i', '200', '-c', str(config.getSharedConfigValue('check.numberOfPackets')), '-q'] + hosts, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    # Parse the raw results
    pingResults = parseRawResult(result.stdout.decode('utf-8'))
    
    return pingResults
    
def searchFpingBinary():
    if not spawn.find_executable('fping'):
        raise SystemError('Executable fping file not found.')
    else:
        return spawn.find_executable('fping')
    
def parseRawResult(rawResult):
    pingResults = []
    
    for line in rawResult.split('\n'):
        if (line.strip() == ''):
            continue
        
        splittedLine = line.split(' : ')
        
        key = splittedLine[0].strip()
        splittedData = splittedLine[1].strip().split(', ')

        statisticValues = getDataValues(splittedData[0].strip())
        pingResult = {
            'target': key,
            'time': int(time.time()),
            'statistic': {
                'sent': int(statisticValues[0]),
                'received': int(statisticValues[1]),
                'loss': int(statisticValues[2].strip('%'))
            },
            'timing': {
                'min': 0,
                'avg': 0,
                'max': 0
            }
        }
        
        if (pingResult['statistic']['received'] == 0):
            pingResult['status'] = 'offline'
        elif (pingResult['statistic']['sent'] != pingResult['statistic']['received']):
            pingResult['status'] = 'unstable'
        else:
            pingResult['status'] = 'online'
        
        if (len(splittedData) == 2):
            timingValues = getDataValues(splittedData[1].strip())
            
            pingResult['timing'] = {
                'min': timingValues[0],
                'avg': timingValues[1],
                'max': timingValues[2]
            }
        
        pingResults.append(pingResult)
        
    return pingResults
        
def getDataValues(dataPart):
    splittedDataPart = dataPart.split(' = ')
    
    return splittedDataPart[1].split('/')