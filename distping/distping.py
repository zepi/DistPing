#!/usr/bin/env python3

import json
import sys
import os
import time
import logging
import threading
import signal
from pydblite import Base

import distping
import monitor
import frontend

exitApplication = False
config = False
database = None
threads = { 
    'threadMonitor': monitor.startMonitorThread,
    'threadFrontend': frontend.startFrontendThread
}
processes = {}

def getRootDirectory():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def loadConfig():
    path = os.path.join(getRootDirectory(), 'config', 'config.json')
    
    if (not os.path.isfile(path)):
        logging.error('Config file (' + path + ') not found.')
        return
    
    with open(path) as configData:
        distping.config = json.load(configData)
        
def getConfigValue(configPath):
    if (distping.config == False):
        return False
    
    config = distping.config
    
    pathParts = configPath.split('.')
    for pathPart in pathParts:
        if (pathPart not in config):
            raise KeyError('Key "' + pathPart + '" not found in configuration.')
        
        config = config[pathPart]
        
    return config

def startThreads():
    for threadName, threadFunction in threads.items():
        startThread(threadName, threadFunction)
        
def startThread(threadName, threadFunction):
    global processes
    
    processes[threadName] = threading.Thread(target=threadFunction, name=threadName, daemon=True)
    processes[threadName].start()  
    
def checkThreads():
    global processes
    
    for threadName, process in processes.items():
        if (not process.is_alive()):
            logging.warning('Thread "' + threadName + '" not alive anymore. Restart this thread.')
            startThread(threadName, threads[threadName])
            
def processSignal(signum, frame):
    distping.exitApplication = True
    logging.info('Received signal to stop the application.')

if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG, format='[%(asctime)s] [%(levelname)s]  %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    
    logging.debug('Load configuration file...')
    loadConfig()
    
    # Abort the execution if the config isn't loaded
    if (distping.config == False):
        sys.exit()
        
    # Signals
    signal.signal(signal.SIGINT, processSignal)
    signal.signal(signal.SIGTERM, processSignal)
        
    # Initialize database connection
    distping.database = Base(distping.getConfigValue('directory.data'))
    
    if (not distping.database.exists()):
        distping.database.create('time', 'host', 'status', 'sent', 'received', 'loss', 'min', 'avg', 'max')
    else:
        distping.database.open()
    
    startThreads()
    
    while (distping.exitApplication == False):
        if (distping.exitApplication):
            break
        
        checkThreads()
        
        time.sleep(1)
