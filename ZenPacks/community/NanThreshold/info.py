from zope.interface import implements
from Products.Zuul.infos import ProxyProperty
from Products.Zuul.infos.template import RRDDataSourceInfo
from ZenPacks.community.NanThreshold.interfaces import InanThreshDataSourceInfo


class nanThreshDataSourceInfo(RRDDataSourceInfo):
    implements(InanThreshDataSourceInfo)

    dataPoints = ProxyProperty('dataPoints')
    cycletime = ProxyProperty('cycletime')
    severity = ProxyProperty('severity')

    @property
    def testable(self):
        """
        Tells the UI that we can test this datasource against a specific device
        """
        return False

