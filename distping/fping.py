import subprocess
import os
import time
from distutils import spawn

import distping
import config
import monitor

def pingTargets(targets):
    fpingBinary = ''
    try:
        fpingBinary = config.getSharedConfigValue('check.fpingBinary')
    except KeyError as err:
        fpingBinary = ''
        
    if (fpingBinary == '' or not os.path.isfile(fpingBinary) or not os.access(fpingBinary, os.X_OK)):
        fpingBinary = searchFpingBinary()
        
    hosts = []
    addressTranslationTable = {}
    for path, target in targets.items():
        if ('address' in target):
            hosts.append(target['address'])
            addressTranslationTable[target['address']] = target['path']
        else:
            hosts.append(target['host'])
            addressTranslationTable[target['host']] = target['path']
        
    # Ping the targets
    result = subprocess.run([
        fpingBinary, 
        '-t', str(config.getSharedConfigValue('ping.initialTimeout')), 
        '-i', str(config.getSharedConfigValue('ping.packetInterval')), 
        '-c', str(config.getSharedConfigValue('ping.numberOfPackets')), 
        '-q'
    ] + hosts, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
    # Parse the raw results
    pingResults = parseRawResult(result.stdout.decode('utf-8'), addressTranslationTable)
    
    return pingResults
    
def searchFpingBinary():
    if not spawn.find_executable('fping'):
        raise SystemError('Executable fping file not found.')
    else:
        return spawn.find_executable('fping')
    
def parseRawResult(rawResult, addressTranslationTable):
    pingResults = []
    
    for line in rawResult.split('\n'):
        if (line.strip() == ''):
            continue
        
        splittedLine = line.split(' : ')
        
        key = splittedLine[0].strip()
        if key in addressTranslationTable:
            key = addressTranslationTable[key]
        
        splittedData = splittedLine[1].strip().split(', ')

        statisticValues = getDataValues(splittedData[0].strip())
        pingResult = {
            'path': key,
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
        print(pingResult)
        
        pingResult['status'] = monitor.getStatusForLossValue(pingResult['statistic']['loss'])
        
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
