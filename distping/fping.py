import subprocess
import os
import time
import shutil

import distping
import config
import monitor
import utils

def pingTargets(targets):
    fpingBinary = ''
    try:
        fpingBinary = config.getSharedConfigValue('check.fpingBinary')
    except KeyError as err:
        fpingBinary = ''
        
    if (fpingBinary == None or fpingBinary == '' or not os.path.isfile(fpingBinary) or not os.access(fpingBinary, os.X_OK)):
        fpingBinary = searchFpingBinary()

    if (fpingBinary == None):
        raise SystemError('Executable fping file not found.')

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
    return shutil.which('fping')
    
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
            'data': {
                'sent': int(statisticValues[0]),
                'received': int(statisticValues[1]),
                'loss': int(statisticValues[2].strip('%')),
                'min': 0,
                'avg': 0,
                'max': 0
            }
        }
        
        pingResult['status'] = monitor.getStatusForPingLossValue(pingResult['data']['loss'])
        
        if (len(splittedData) == 2):
            timingValues = getDataValues(splittedData[1].strip())
            
            pingResult['data']['min'] = utils.roundTime(timingValues[0])
            pingResult['data']['avg'] = utils.roundTime(timingValues[1])
            pingResult['data']['max'] = utils.roundTime(timingValues[2])

        pingResults.append(pingResult)
        
    return pingResults
        
def getDataValues(dataPart):
    splittedDataPart = dataPart.split(' = ')
    
    return splittedDataPart[1].split('/')
