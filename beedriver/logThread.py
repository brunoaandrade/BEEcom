#!/usr/bin/env python

import threading
import time
import os
import usb
import math
import re
from beedriver import logger

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


class LogThread(threading.Thread):
    r"""
        DebugThread Class

        This class provides the methods to debug and log printer actions


    """


    # *************************************************************************
    #                        __init__ Method
    # *************************************************************************
    def __init__(self, connection):
        r"""
        __init__ Method

        Initializes this class

        """

        super(LogThread, self).__init__()


        return

    # *************************************************************************
    #                        run Method
    # *************************************************************************
    def run(self):

        super(LogThread, self).run()


        logger.info('Exiting transfer thread')

        return


