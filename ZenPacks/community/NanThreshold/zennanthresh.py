import logging
import os.path

from twisted.internet import defer

import Globals
from zope.interface import implements
import zope.component

from Products.ZenCollector.daemon import CollectorDaemon
from Products.ZenCollector.interfaces import ICollectorPreferences,\
                                             IEventService,\
                                             IScheduledTask,\
                                             ICollector, \
                                             IDataService
from Products.ZenCollector.tasks import SimpleTaskFactory,\
                                        SimpleTaskSplitter,\
                                        TaskStates

from Products.ZenUtils.observable import ObservableMixin
from Products.ZenUtils.Utils import unused, zenPath

from Products.ZenCollector.services.config import DeviceProxy
unused(DeviceProxy)

from ZenPacks.community.NanThreshold.services.nanThreshConfig import getVarNames

from ZenPacks.community.NanThreshold.zapi import ZenossAPI

COLLECTOR_NAME = "zennanthersh"

log = logging.getLogger("zen.%s" % COLLECTOR_NAME)

class SimpleObject(object):
    """
    Simple class that can have arbitrary attributes assigned to it.
    """


def createDeviceDictionary(deviceProxy):
    """
    Returns a dictionary of simple objects suitable for passing into eval().
    """
    vars = {}

    for dp in deviceProxy.datapoints:
        for key, value in dp['obj_attrs'].items():
            parts = key.split(".")
            base = vars[parts[0]] = SimpleObject()
            for part in parts[1:-1]:
                if not hasattr(base, part):
                    setattr(base, part, SimpleObject())
                base = getattr(base, part)
            setattr(base, parts[-1], value)

    return vars


class nanThreshPrefs(object):
    implements(ICollectorPreferences)

    def __init__(self):
        self.collectorName = COLLECTOR_NAME
        self.defaultRRDCreateCommand = None
        self.configCycleInterval = 60 # minutes
        self.cycleInterval = 60 # 1 minute

        self.configurationService = 'ZenPacks.community.NanThreshold.services.nanThreshConfig'

        # No more than maxTasks models will take place at once
        self.maxTasks = 100

        self.options = None

    def buildOptions(self, parser):
        pass

    def postStartup(self):
        pass


class nanThreshCollectionTask(ObservableMixin):
    implements(IScheduledTask)

    STATE_CONNECTING = 'CONNECTING'
    STATE_FETCH_MODEL = 'FETCH_MODEL_DATA'
    STATE_PROCESS_MODEL = 'FETCH_PROCESS_MODEL_DATA'
    STATE_APPLY_DATAMAPS = 'FETCH_APPLY_MODEL_DATA'

    def __init__(self, deviceId, taskName, scheduledIntervalSeconds, taskConfig):
        super(nanThreshCollectionTask, self).__init__()
        self.name = taskName
        self.configId = deviceId
        self.state = TaskStates.STATE_IDLE
        self.interval = 60
        
        self._device = taskConfig
        self._devId = deviceId
        self._manageIp = self._device.manageIp

        self._dataService = zope.component.queryUtility(IDataService)
        self._eventService = zope.component.queryUtility(IEventService)
        self._preferences = zope.component.queryUtility(ICollectorPreferences, COLLECTOR_NAME)

        self._collector = zope.component.queryUtility(ICollector)
        self._lastErrorMsg = ''

    def doTask(self):
        for datapoint in self._device.datapoints:
            dataPoints = datapoint['dataPoints']
            component = datapoint['comp']
            severity = datapoint['sev']
            count = datapoint['count']
            obj_attrs = datapoint['obj_attrs']

            rrd_paths = datapoint['rrd_paths']
            varNames = getVarNames(dataPoints)

            rrdNames = [varName for varName in varNames
                if varName not in obj_attrs.keys()]

            self._fetchRrdValues(rrdNames, rrd_paths, component, severity)

            log.debug("Datapoint dump: %s", str(datapoint))

        return defer.succeed("Gathered datapoint information")

    def _fetchRrdValues(self, rrdNames, rrd_paths, component, severity):
        rrdStart = 'now-600s'
        rrdEnd = 'now'
        perfDir = zenPath('perf')

        log.debug("Datapoints to check: %s", rrdNames)
        for rrdName in rrdNames:
            try:
                filePath = os.path.join(perfDir, rrd_paths[rrdName])
                values = self._dataService.readRRD(filePath,
                                       'AVERAGE',
                                       "-s " + rrdStart,
                                       "-e " + rrdEnd)[2]
            except Exception, e:
                log.debug("Unable to read RRD for dataPoint: %s", e)
                continue

            for value in reversed(values):
                value = value[0]
                if value is not None:
                    break

            value = None
            if value is None:
                value = -1
                message = "NAN for dataPoint %s on device %s!" % (rrdName, self._devId)
                log.warn("%s", message)
                evt = dict(device = self._devId, summary = message, component = component, severity = severity)
                self._eventService.sendEvent(evt)
            log.debug("Datapoint %s value: %s", rrdName, value)


    def cleanup(self):
        pass

    def displayStatistics(self):
        """
        Called by the collector framework scheduler, and allows us to
        see how each task is doing.
        """
        display = ''
        if self._lastErrorMsg:
            display += "%s\n" % self._lastErrorMsg
        return display


if __name__ == '__main__':
    myPreferences = nanThreshPrefs()
    myTaskFactory = SimpleTaskFactory(nanThreshCollectionTask)
    myTaskSplitter = SimpleTaskSplitter(myTaskFactory)
    daemon = CollectorDaemon(myPreferences, myTaskSplitter)
    daemon.run()
