import sys
import time
import socket
import requests
from contextlib import closing

import distping
import config
import monitor
import utils


def checkTargets(targets):
    checkResults = []

    for path, target in targets.items():
        checkResult = None

        if (target['type'] == 'port'):
            checkResult = checkPortTarget(target)
        elif (target['type'] == 'http'):
            checkResult = checkHttpTarget(target)

        checkResults.append(checkResult)

    return checkResults

def checkPortTarget(checkData):
    startTime = time.perf_counter()
    with closing(socket.socket(socket.AF_INET, socket.SOCK_STREAM)) as sock:
        sock.settimeout(config.getSharedConfigValue('port.timeout'))
        if sock.connect_ex((checkData['host'], checkData['port'])) == 0:
            status = 'online'
        else:
            status = 'offline'

    endTime = time.perf_counter()

    result = {
        'path': checkData['path'],
        'time': int(time.time()),
        'status': status,
        'data': {
            'time': utils.roundTime(round(endTime - startTime, 5) * 1000)
        }
    }

    return result

def checkHttpTarget(checkData):
    try:
        data = requests.get(checkData['url'], timeout=config.getSharedConfigValue('http.timeout'), headers={
            'User-Agent': 'DistPing/' + distping.version
        })
        responseCode = data.status_code
        responseData = data.text
        responseTime = data.elapsed
    except:
        responseCode = 500
        responseData = ''
        responseTime = 0

    if responseCode == 200:
        result = {
            'path': checkData['path'],
            'time': int(time.time()),
            'status': 'offline',
            'data': {
                'statusCode': responseCode,
                'size': len(responseData),
                'time': utils.roundTime(responseTime.total_seconds() * 1000)
            }
        }

        if 'keyword' in checkData:
            if 'inversed' in checkData and checkData['inversed']:
                if not checkData['keyword'] in responseData:
                    result['status'] = 'online'
            else:
                if checkData['keyword'] in responseData:
                    result['status'] = 'online'
        else:
            result['status'] = 'online'

        return result
    else:
        return {
            'path': checkData['path'],
            'time': int(time.time()),
            'status': 'offline',
            'data': {
                'statusCode': responseCode,
                'size': 0,
                'time': 0
            }
        }

