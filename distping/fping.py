import subprocess
import distping
import os
import time
from distutils import spawn

def pingTargets(targets):
    fpingBinary = ''
    try:
        fpingBinary = distping.getConfigValue('check.fpingBinary')
    except KeyError as err:
        fpingBinary = ''
        
    if (fpingBinary == '' or not os.path.isfile(fpingBinary) or not os.access(fpingBinary, os.X_OK)):
        fpingBinary = searchFpingBinary()
        
    hosts = []
    for target in targets:
        hosts.append(target['host'])
        
    # Ping the targets
    result = subprocess.run([fpingBinary, '-c', str(distping.getConfigValue('check.numberOfPackets')), '-q'] + hosts, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    
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
                'sent': statisticValues[0],
                'received': statisticValues[1],
                'loss': statisticValues[2]
            },
            'timing': {
                'min': 0,
                'avg': 0,
                'max': 0
            }
        }
        
        if (pingResult['statistic']['sent'] != pingResult['statistic']['received']):
            pingResult['status'] = 'offline'
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