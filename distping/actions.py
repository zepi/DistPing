import json
import requests
import logging
import time
import subprocess
import os

import distping
import config

def executeActions(eventName, data):
    actions = config.getSharedConfigValue('actions')
    
    data['sender'] = config.getLocalConfigValue('observerName')
    data['sendTime'] = time.time()
    
    for action in actions:
        if (action['event'] == eventName):
            logging.debug('Execute action {} for event {}.'.format(action['name'], eventName))
            
            executeAction(action, data)
            
def executeAction(action, data):
    if (action['type'] == 'webhook'):
        if (action['contentType'] == 'json'):
            requests.post(action['url'], json=data)
    elif (action['type'] == 'script'):
        actionEnv = os.environ.copy()
        actionEnv['EVENT'] = json.dumps(data)
        
        commandRaw = action['command']
        command = commandRaw.split(' ')
        
        subprocess.call(command, env=actionEnv)
        