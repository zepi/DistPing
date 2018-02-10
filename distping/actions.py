import json
import requests
import logging

import distping
import config

def executeActions(eventName, data):
    actions = config.getSharedConfigValue('actions')
    
    for action in actions:
        if (action['event'] == eventName):
            logging.debug('Execute action {} for event {}.'.format(action['name'], eventName))
            
            executeAction(action, data)
            
def executeAction(action, data):
    if (action['type'] == 'webhook'):
        if (action['contentType'] == 'json'):
            requests.post(action['url'], json=data)