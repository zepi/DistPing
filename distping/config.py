import json
import os
import time
import logging

import distping
import config

local = False
shared = False

def getConfigDirectory():
    if (distping.arguments.config_dir != None):
        configPath = distping.arguments.config_dir
    else:
        configPath = os.path.join(distping.getRootDirectory(), 'config')
    
    if (not os.path.isdir(configPath)):
        raise RuntimeError('Config path "{}" is not existing.'.format(configPath))
    
    return configPath

def loadConfigFile(fileName):
    path = os.path.join(getConfigDirectory(), fileName)
    
    if (not os.path.isfile(path)):
        logging.error('Config file "{}" not found.'.format(path))
        return
    
    with open(path) as configData:
        return json.load(configData)
        
def loadLocalConfig():
    config.local = loadConfigFile('local.json')
    
def loadSharedConfig():
    config.shared = loadConfigFile('shared.json')
    
    # Sort the targets
    config.shared['targets'] = sorted(config.shared['targets'], key=lambda group: group['name'])
    
    for group in config.shared['targets']:
        group['targets'] = sorted(group['targets'], key=lambda target: target['name'])

def getLocalConfigValue(configPath):
    if (config.local == False):
        return False
    
    return getConfigValue('local', configPath)
        
def getSharedConfigValue(configPath):
    if (config.shared == False):
        return False
    
    return getConfigValue('shared', configPath)
    
def getConfigValue(location, configPath):
    if (location == 'local'):
        configDict = config.local
    elif (location == 'shared'):
        configDict = config.shared
    
    pathParts = configPath.split('.')
    for pathPart in pathParts:
        if (pathPart not in configDict):
            raise KeyError('Key "{}" not found in configuration.'.format(pathPart))
        
        configDict = configDict[pathPart]
        
    return configDict

def loadConfigs():
    loadLocalConfig()
    loadSharedConfig()