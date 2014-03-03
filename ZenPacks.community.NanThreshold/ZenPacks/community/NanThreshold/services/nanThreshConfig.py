import re
import logging

log = logging.getLogger('zen.zenhub.service.nanThresh')

import Globals
from DateTime import DateTime
from Products.ZenCollector.services.config import CollectorConfigService

from Products.PageTemplates.Expressions import getEngine
from Products.ZenUtils.ZenTales import talesCompile

from ZenPacks.community.NanThreshold.datasources.nanThreshDataSource import nanThreshDataSource

DSTYPE = nanThreshDataSource.sourcetype

def dotTraverse(base, path):
    path = path.split(".")
    while len(path) > 0:
        try:
            base = getattr(base, path.pop(0))
        except:
            return None
    return base 


varNameRe = re.compile(r"[A-Za-z][A-Za-z0-9_\.]*")
keywords = (',')

def getVarNames(dataPoints):
    names = varNameRe.findall(dataPoints)
    return [name for name in names if name not in keywords]

def getComponent(context, componentId, componentField=None):
    """Return localized component.
    """
    if componentField is None:
        return componentId
    if not componentField.startswith('string:') and \
            not componentField.startswith('python:'):
        componentField = 'string:%s' % componentField
    compiled = talesCompile(componentField)
    d = context
    environ = {'dev' : d,
               'device': d,
               'here' : context,
               'nothing' : None,
               'now' : DateTime() }
    res = compiled(getEngine().getContext(environ))
    if isinstance(res, Exception):
        raise res
    return res

class nanThreshConfig(CollectorConfigService):

    def _createDeviceProxy(self, device):
        proxy = CollectorConfigService._createDeviceProxy(self, device)

        # The event daemon keeps a persistent connection open, so this cycle
        # interval will only be used if the connection is lost... for now, it
        # doesn't need to be configurable.
        proxy.configCycleInterval =  5 * 60 # seconds

        proxy.datapoints = []
        proxy.thresholds = []

        for component in [device] + device.getMonitoredComponents():
            try:
                self._getDataPoints(proxy, component, component.device().id, component.id)
            except Exception, ex:
                log.warn("Skipping %s component %s because %s", device.id, component.id, str(ex))
                continue
            proxy.thresholds += component.getThresholdInstances(DSTYPE)

        if len(proxy.datapoints) > 0:
            return proxy

    def _getDataPoints(self, proxy, deviceOrComponent, deviceId, componentId):
        allDatapointNames = [d.id for d in deviceOrComponent.getRRDDataPoints()]
        for template in deviceOrComponent.getRRDTemplates():
            dataSources = [ds for ds
                           in template.getRRDDataSources(DSTYPE)
                           if ds.enabled]

            obj_attrs = {}
            rrd_paths = {}

            for ds in dataSources:
                for att in getVarNames(ds.dataPoints):
                    value = dotTraverse(deviceOrComponent, att)
                    if att in allDatapointNames:
                        rrd_paths[att] = deviceOrComponent.getRRDFileName(att)
                    elif value is not None:
                        obj_attrs[att] = value
                    else:
                        log.warn("Datapoint list %s references %s, which is not in %s" % (ds.dataPoints, att, allDatapointNames))
                        continue

                dp = ds.datapoints()[0]
                if dp == None: continue

                dpInfo = dict(
                    devId=deviceId,
                    compId=componentId,
                    dsId=ds.id,
                    dpId=dp.id,
                    dataPoints=ds.dataPoints,
                    obj_attrs=obj_attrs,
                    cycletime=dp.cycletime,
                    sev=ds.severity,
                    eclass=ds.eventClass,
                    comp=getComponent(context=deviceOrComponent, componentId=componentId, componentField=ds.component),
                    count=ds.count,
                    rrd_paths=rrd_paths,
                    path='/'.join((deviceOrComponent.rrdPath(), dp.name())),
                    rrdType=dp.rrdtype,
                    rrdCmd=dp.getRRDCreateCommand(deviceOrComponent.getPerformanceServer()),
                    minv=dp.rrdmin,
                    maxv=dp.rrdmax,
                    dsPath=ds.getPrimaryId(),
                )
                if not dpInfo['rrdCmd']:
                    dpInfo['rrdCmd'] = deviceOrComponent.perfServer().getDefaultRRDCreateCommand()

                proxy.datapoints.append(dpInfo)


if __name__ == '__main__':
    from Products.ZenHub.ServiceTester import ServiceTester
    from pprint import pprint

    tester = ServiceTester(nanThreshConfig)
    def printer(proxy):
        pprint(proxy.datapoints)
    tester.printDeviceProxy = printer
    tester.showDeviceInfo()
