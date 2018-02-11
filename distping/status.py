import time
import json

import distping
import config
import status
import actions

statusData = {}
statusChanged = False

def setStatus(targetKey, newStatus, values):
    if (targetKey in status.statusData and status.statusData[targetKey]['status'] == newStatus):
        return
    
    oldStatus = ''
    oldStatusTime = ''
    if (targetKey in status.statusData):
        oldStatus = status.statusData[targetKey]['status']
        oldStatusTime = status.statusData[targetKey]['statusSince']
    
    status.statusData[targetKey] = {
        'status': newStatus,
        'statusSince': time.time()
    }
    status.statusChanged = True
    
    if (oldStatus == ''):
        return
    
    actions.executeActions('status-changed', {
        'targetKey': targetKey,
        'oldStatus': oldStatus,
        'newStatus': newStatus,
        'time': status.statusData[targetKey]['statusSince'],
        'oldStatusTime': oldStatusTime,
        'values': values
    })
