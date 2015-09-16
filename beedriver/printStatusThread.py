#!/usr/bin/env python

import threading
import time

"""
* Copyright (c) 2015 BEEVC - Electronic Systems This file is part of BEESOFT
* software: you can redistribute it and/or modify it under the terms of the GNU
* General Public License as published by the Free Software Foundation, either
* version 3 of the License, or (at your option) any later version. BEESOFT is
* distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
* without even the implied warranty of MERCHANTABILITY or FITNESS FOR A
* PARTICULAR PURPOSE. See the GNU General Public License for more details. You
* should have received a copy of the GNU General Public License along with
* BEESOFT. If not, see <http://www.gnu.org/licenses/>.
"""

__author__ = "BVC Electronic Systems"
__license__ = ""


class PrintStatusThread(threading.Thread):
    r"""
        StatusThread Class

        This class monitors the current status of a printing operation
    """
    
    _responseCallback = None
    _beeConn = None
    _running = True

    # *************************************************************************
    #                        __init__ Method
    # *************************************************************************
    def __init__(self, connection, responseCallback):
        r"""
        __init__ Method

        Initializes this class

        """
        super(PrintStatusThread, self).__init__()
        self._responseCallback = responseCallback
        self._beeConn = connection

        return
    
    def run(self):

        commands = self._beeConn.getCommandIntf()
        while self._running:

            printVars = commands.getPrintVariables()

            self._responseCallback(printVars)

            if 'Lines' in printVars and \
                'Executed Lines' in printVars and \
                    printVars['Lines'] is not None and \
                    printVars['Lines'] == printVars['Executed Lines']:
                # the print has finished
                break

            time.sleep(10)

    def stopStatusMonitor(self):
        """
        Forces the Status thread monitor to stop
        :return:
        """
        self._running = False
