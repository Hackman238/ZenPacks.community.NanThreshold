from AccessControl import ClassSecurityInfo
from Products.ZenModel.BasicDataSource import BasicDataSource
from Products.ZenModel import RRDDataSource
from Products.ZenModel.ZenPackPersistence import ZenPackPersistence

class nanThreshDataSource(BasicDataSource, ZenPackPersistence):
    ZENPACKID = 'ZenPacks.community.nanThreshold'

    sourcetypes = ('Nan Monitor',)
    sourcetype = 'Nan Monitor'

    eventClass = '/Status'

    dataPoints = 'sysUpTime,'
    cycletime = 60

    _properties = BasicDataSource._properties + (
         {'id':'dataPoints', 'type':'string', 'mode':'w'},
         {'id':'cycletime', 'type':'int', 'mode':'w'},
        )

    security = ClassSecurityInfo()

    def addDataPoints(self):
        """
        Overrides method definded in BasicDataSource.
        """
        
        RRDDataSource.SimpleRRDDataSource.addDataPoints(self)

    def getDescription(self):
        return self.dataPoints
