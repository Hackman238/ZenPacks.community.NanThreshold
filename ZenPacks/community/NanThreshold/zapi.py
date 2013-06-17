import time
import os
import logging

import json
import urllib
import urllib2

import Globals

from Products.ZenUtils.GlobalConfig import getGlobalConfiguration

global_conf = getGlobalConfiguration()

destinationHost = global_conf.get('zenNanDestinationUrl', 'http://localhost:8080')
zenuser = global_conf.get('zenuser', 'admin')
zenpass = global_conf.get('zenpass', 'zenoss')

ROUTERS = {'EventsRouter': 'evconsole',}

class ZenossAPI():
    def __init__(self, debug=False):
        """
Initialize the API connection, log in, and store authentication cookie
"""
        # Use the HTTPCookieProcessor as urllib2 does not save cookies by default
        self.urlOpener = urllib2.build_opener(urllib2.HTTPCookieProcessor())
        if debug: self.urlOpener.add_handler(urllib2.HTTPHandler(debuglevel=1))
        self.reqCount = 1

        # Contruct POST params and submit login.
        loginParams = urllib.urlencode(dict(
                        __ac_name = zenuser,
                        __ac_password = zenpass,
                        submitted = 'true',
                        came_from = destinationHost + '/zport/dmd'))
        self.urlOpener.open(destinationHost + '/zport/acl_users/cookieAuthHelper/login',
                            loginParams)

    def _router_request(self, router, method, data=[]):
        if router not in ROUTERS:
            raise Exception('Router "' + router + '" not available.')

        # Contruct a standard URL request for API calls
        req = urllib2.Request(destinationHost + '/zport/dmd/' +
                              ROUTERS[router] + '_router')

        # NOTE: Content-type MUST be set to 'application/json' for these requests
        req.add_header('Content-type', 'application/json; charset=utf-8')

        # Convert the request parameters into JSON
        reqData = json.dumps([dict(
                    action=router,
                    method=method,
                    data=data,
                    type='rpc',
                    tid=self.reqCount)])

        # Increment the request count ('tid'). More important if sending multiple
        # calls in a single request
        self.reqCount += 1
        # Submit the request and convert the returned JSON to objects
        return json.loads(self.urlOpener.open(req, reqData).read())


    def createEvent(self, device, severity, summary, evclass):
        if severity not in ('Critical', 'Error', 'Warning', 'Info', 'Debug', 'Clear'):
            raise Exception('Severity "' + severity +'" is not valid.')

        data = dict(device=device, summary=summary, severity=severity,
                    component='', evclasskey='', evclass=evclass)
        return self._router_request('EventsRouter', 'add_event', [data])
