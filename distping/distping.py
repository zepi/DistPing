#!/usr/bin/env python3

import json
import sys
import os
import time
import logging
import logging.config
import threading
import signal
import argparse
from pydblite import Base

import distping
import config
import monitor
import frontend
import collector

arguments = False
exitApplication = False
database = None
threads = { 
    'threadMonitor': monitor.startMonitorThread,
    'threadFrontend': frontend.startFrontendThread,
    'threadCollector': collector.startCollectorThread
}
processes = {}

def getRootDirectory():
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def configureLogging():
    loggingConfig = {
        'version': 1,
        'formatters': {
            'void': {
                'format': '[%(asctime)s] [%(levelname)s]\t%(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
            'standard': {
                'format': '[%(asctime)s] [%(levelname)s] %(name)s:\t%(message)s',
                'datefmt': '%Y-%m-%d %H:%M:%S'
            },
        },
        'handlers': {},
        'loggers': {}
    }

    if (config.getLocalConfigValue('server.logs.coreLogFile') != ''):
        loggingConfig['handlers']['default'] = {
            'level':'DEBUG',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'void',
            'filename': config.getLocalConfigValue('server.logs.coreLogFile'),
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': 'utf8'
        }
    else:
        loggingConfig['handlers']['default'] = {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'void',
        }
        
    loggingConfig['loggers'][''] = {
        'handlers': ['default'],
        'level': config.getLocalConfigValue('server.logs.coreLogLevel')
    }
        
    if (config.getLocalConfigValue('server.logs.accessLogFile') != ''):
        loggingConfig['handlers']['cherrypy_access'] = {
            'level':'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'standard',
            'filename': config.getLocalConfigValue('server.logs.accessLogFile'),
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': 'utf8'
        }
        
        loggingConfig['loggers']['cherrypy.access'] = {
            'handlers': ['cherrypy_access'],
            'level': 'INFO',
            'propagate': False
        }
    
    if (config.getLocalConfigValue('server.logs.errorLogFile') != ''):
        loggingConfig['handlers']['cherrypy_error'] = {
            'level': 'INFO',
            'class': 'logging.handlers.RotatingFileHandler',
            'formatter': 'void',
            'filename': config.getLocalConfigValue('server.logs.errorLogFile'),
            'maxBytes': 10485760,
            'backupCount': 20,
            'encoding': 'utf8'
        }
        
        loggingConfig['loggers']['cherrypy.error'] = {
            'handlers': ['cherrypy_error'],
            'level': 'INFO',
            'propagate': False
        }
        
    logging.config.dictConfig(loggingConfig)
    logging.debug('Logging configured')


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
    parser = argparse.ArgumentParser(description='Distributed ping tool.')
    parser.add_argument('--config-dir', help='Set the config directory')
    distping.arguments = parser.parse_args()

    #configureLogging()
    
    logging.info('DistPing started.')
    logging.debug('Load configuration file...')
    config.loadConfigs()
    
    # Abort the execution if the config isn't loaded
    if (distping.config == False):
        sys.exit()
        
    # Signals
    signal.signal(signal.SIGINT, processSignal)
    signal.signal(signal.SIGTERM, processSignal)
        
    # Initialize database connection
    distping.database = Base(config.getLocalConfigValue('directory.data'))
    
    if (not distping.database.exists()):
        distping.database.create('time', 'host', 'status', 'sent', 'received', 'loss', 'min', 'avg', 'max')
    else:
        distping.database.open()
        
    logging.info('Start the threads.')
    startThreads()
    
    while (distping.exitApplication == False):
        if (distping.exitApplication):
            break
        
        checkThreads()
        
        time.sleep(1)
