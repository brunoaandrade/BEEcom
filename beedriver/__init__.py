#!/usr/bin/env python

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
import logging
import parsers
import time
from PyQt4 import QtCore

__all__ = ["commands", "connection", "transferThread", "printStatusThread", "logThread"]

class ConsoleLogHandler(logging.StreamHandler):
    """
    This class serves the purpose of redirecting logging messages to the Control Panel console.
    """

    _form = None

    @staticmethod
    def set_form(form):
        """
        Set the widget that contains the console to which the message shall be sent.

        Args:
            form: the widget that will be used to emit the signal containing the message

        """
        ConsoleLogHandler._form = form

    def emit(self, record):
        """
        Override of the emit(record) method of StreamHandler. Sends the message to the console.

        Args:
            record: message to be sent

        """
        msg = self.format(record)
        ConsoleLogHandler._form.emit(QtCore.SIGNAL("append_console_log"), msg)


class DebugFileHandler(logging.FileHandler):
    def __init__(self, filename, mode='a', encoding=None, delay=False):
        logging.FileHandler.__init__(self, filename, mode, encoding, delay)

    def emit(self, record):
        if not record.levelno == logging.DEBUG:
            return
        logging.FileHandler.emit(self, record)


def write_to_print_log(log_line):
    if log_line is not None:
        current_milli_time = str(int(round(time.time() * 1000)))
        print_logger.debug(current_milli_time + "," + log_line)


# Logger configuration
logger = logging.getLogger('beecom')
logger.setLevel(logging.DEBUG)

# create file handler which logs even debug messages
# fh = logging.FileHandler('bee_console.log')
# fh.setLevel(logging.DEBUG)

# create file handler that logs only debug messages
fh = DebugFileHandler('beemelt.log')
fh.setLevel(logging.DEBUG)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# create formatter and add it to the handlers
formatter = logging.Formatter('%(asctime)s - %(message)s')
fh.setFormatter(formatter)

# add the handlers to logger
logger.addHandler(ch)
logger.addHandler(fh)

# temp logger
temp_logger = logging.getLogger('temp')
temp_logger.setLevel(logging.DEBUG)
fh = logging.FileHandler('debugging.log')
fh.setLevel(logging.DEBUG)
temp_logger.addHandler(fh)

# print logger
print_logger_parent_path = "./logs/"
print_logger_child_path = None
print_logger = logging.getLogger('print_logger')
print_logger.setLevel(logging.DEBUG)
