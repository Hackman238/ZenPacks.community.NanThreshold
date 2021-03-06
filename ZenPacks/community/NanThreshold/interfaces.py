######################################################################
#
# Copyright 2011 Zenoss, Inc.  All Rights Reserved.
#
######################################################################

from Products.Zuul.interfaces import IRRDDataSourceInfo
from Products.Zuul.form import schema
from Products.Zuul.utils import ZuulMessageFactory as _t


class InanThreshDataSourceInfo(IRRDDataSourceInfo):
    dataPoints = schema.Text(title=_t(u'dataPoints'), group=_t('Detail'), xtype='twocolumntextarea')
    cycletime = schema.Int(title=_t(u'Cycle Time (seconds)'))
    severity = schema.Int(title=_t(u'Severity'))
