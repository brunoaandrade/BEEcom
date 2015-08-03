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

__author__ = "BVC Electronic Systems"
__license__ = ""

import time

import usb
import usb.core
import usb.util
from beedriver.commands import BeeCmd
from beedriver import logger


class Conn:
    r"""
        Connection Class

        This class provides the methods to manage and control communication with the
        BeeTheFirst 3D printer

        __init__()              Initializes current class
        findBEE()               Searches for connected printers and establishes connection
        write(message,timeout)  Writes data to the communication buffer
        read()                  Read data from the communication buffer
        dispatch(message)       Writes data to the buffer and reads the response
        sendCmd(cmd,wait,to)    Sends a command to the 3D printer
        close()                 Closes active communication with the printer
        isConnected()           Returns the current state of the printer connection
        getCommandIntf()        Returns the BeeCmd object with the command interface for higher level operations
        reconnect()             Closes and re-establishes the connection with the printer
    """

    dev = None
    endpoint = None
    ep_in = None
    ep_out = None
    cfg = None
    intf = None

    READ_TIMEOUT = 2000
    DEFAULT_READ_LENGTH = 512

    queryInterval = 0.5

    connected = None

    backend = None

    command_intf = None     # Commands interface

    # *************************************************************************
    #                            Init Method
    # *************************************************************************
    def __init__(self):
        r"""
        Init Method

        Initializes this class

        receives as argument the BeeConnection object ans verifies the
        connection status

        """

        self.findBEE()

        if self.isConnected():
            self.command_intf = BeeCmd(self)

        return

    # *************************************************************************
    #                        findBEE Method
    # *************************************************************************
    def findBEE(self):
        r"""
        findBE-E method

        searches for connected printers and tries to connect to the first one.
        """

        self.connected = False

        # find our device
        #self.dev = usb.core.find(idVendor=0xffff, idProduct=0x014e,backend=libusb1.get_backend())
        #self.dev = usb.core.find(idVendor=0xffff, idProduct=0x014e,backend=libusb0.get_backend())
        #self.dev = usb.core.find(idVendor=0xffff, idProduct=0x014e,backend=openusb.get_backend())
        self.dev = usb.core.find(idVendor=0xffff, idProduct=0x014e)

        if self.dev is not None:
            logger.info("BTF Old Connected")

        # was it found? no, try the other device
        if self.dev is None:
            #self.dev = usb.core.find(idVendor=0x29c9, idProduct=0x0001,backend=libusb1.get_backend())
            self.dev = usb.core.find(idVendor=0x29c9, idProduct=0x0001)
            if self.dev is not None:
                logger.info("BEETHEFIRST Printer Connected")

        if self.dev is None:
            #self.dev = usb.core.find(idVendor=0x29c9, idProduct=0x0002,backend=libusb1.get_backend())
            self.dev = usb.core.find(idVendor=0x29c9, idProduct=0x0002)
            if self.dev is not None:
                logger.info("BEETHEFIRST+ Printer Connected")

        if self.dev is None:
            #self.dev = usb.core.find(idVendor=0x29c9, idProduct=0x0003,backend=libusb1.get_backend())
            self.dev = usb.core.find(idVendor=0x29c9, idProduct=0x0003)
            if self.dev is not None:
                logger.info("BEEME Printer Connected")

        if self.dev is None:
            #self.dev = usb.core.find(idVendor=0x29c9, idProduct=0x0004,backend=libusb1.get_backend())
            self.dev = usb.core.find(idVendor=0x29c9, idProduct=0x0004)
            if self.dev is not None:
                logger.info("BEEINSCHOOL Printer Connected")

        elif self.dev is None:
            raise ValueError('Device not found')

        if self.dev is None:
            logger.debug("Can't Find Printer")
            return

        # set the active configuration. With no arguments, the first
        # configuration will be the active one
        try:
            self.dev.set_configuration()
            self.dev.reset()
            time.sleep(0.5)
            #self.dev.set_configuration()
            self.cfg = self.dev.get_active_configuration()
            self.intf = self.cfg[(0, 0)]
            logger.debug("reconnect")

        except usb.core.USBError as e:
            logger.error("Could not set configuration: %s" % str(e))
            return

        # self.endpoint = self.dev[0][(0,0)][0]

        self.ep_out = usb.util.find_descriptor(
            self.intf,
            # match the first OUT endpoint
            custom_match=lambda lb: usb.util.endpoint_direction(lb.bEndpointAddress) == usb.util.ENDPOINT_OUT)

        self.ep_in = usb.util.find_descriptor(
            self.intf,
            # match the first in endpoint
            custom_match=lambda lb: usb.util.endpoint_direction(lb.bEndpointAddress) == usb.util.ENDPOINT_IN)

        # Verify that the end points exist
        assert self.ep_out is not None
        assert self.ep_in is not None

        self.connected = True

        return

    # *************************************************************************
    #                        write Method
    # *************************************************************************
    def write(self, message, timeout=500):
        r"""
        write method

        writes a message to the communication buffer

        arguments:
            message - data to be writen
            timeout - optional communication timeout (default = 500ms)

        returns:
            bytesWriten - bytes writen to the buffer
        """
        bytesWriten = 0

        if message == "dummy":
            pass
        else:
            try:
                bytesWriten = self.ep_out.write(message, timeout)
            except usb.core.USBError, e:
                print str(e)

        return bytesWriten

    # *************************************************************************
    #                        read Method
    # *************************************************************************
    def read(self, timeout=2000, readLen=512):
        r"""
        read method

        reads existing data from the communication buffer

        arguments:
            timeout - optional communication timeout (default = 500ms)

        returns:
            sret - string with data read from the buffer
        """

        resp = ""

        try:
            self.write("")
            ret = self.ep_in.read(readLen, timeout)
            resp = ''.join([chr(x) for x in ret])
        except usb.core.USBError, e:
            logger.error("USB read data exception: %s", str(e))

        return resp

    # *************************************************************************
    #                        dispatch Method
    # *************************************************************************
    def dispatch(self, message):
        r"""
        dispatch method

        writes data to the communication buffers and read existing data

        arguments:
            message - data to be writen

        returns:
            sret - string with data read from the buffer
        """

        timeout = self.READ_TIMEOUT
        resp = "No response"
        try:
            if message == "dummy":
                pass
            else:
                time.sleep(0.009)
                self.ep_out.write(message)
                time.sleep(0.009)

        except usb.core.USBError, e:
            logger.error("USB dispatch (write) data exception: %s", str(e))

        try:
            ret = self.ep_in.read(self.DEFAULT_READ_LENGTH, timeout)
            resp = ''.join([chr(x) for x in ret])

        except usb.core.USBError, e:
            logger.error("USB dispatch (read) data exception: %s", str(e))

        return resp

    # *************************************************************************
    #                        sendCmd Method
    # *************************************************************************
    def sendCmd(self, cmd, wait=None, timeout=None):
        r"""
        sendCmd method

        sends command to the printer

        arguments:
            cmd - command to send
            wait - optional wait for reply
            timeout - optional communication timeout

        returns:
            resp - string with data read from the buffer
        """
        cmdStr = cmd + "\n"

        if wait is None:
            resp = self.dispatch(cmdStr)
        else:
            if wait.isdigit():
                resp = self._waitForStatus(cmdStr, wait, timeout)
            else:
                resp = self._waitFor(cmdStr, wait, timeout)

        return resp

    # *************************************************************************
    #                        waitFor Method
    # *************************************************************************
    def _waitFor(self, cmd, s, timeout=None):
        r"""
        waitFor method

        writes command to the printer and waits for the response

        arguments:
            cmd - commmand to send
            s - string to be found in the response
            timeout - optional communication timeout (seconds)

        returns:
            resp - string with data read from the buffer
        """
        c_time = time.time()

        self.write(cmd)

        resp = ""
        while s not in resp:
            resp += self.read()

            # Checks timeout
            if timeout is not None:
                e_time = time.time()
                if e_time-c_time > timeout:
                    break

        return resp

    # *************************************************************************
    #                        waitForStatus Method
    # *************************************************************************
    def _waitForStatus(self, cmd, s, timeout=None):
        r"""
        waitForStatus method

        writes command to the printer and waits for status the response

        arguments:
            cmd - commmand to send
            s - string to be found in the response
            timeout - optional communication timeout (seconds)

        returns:
            resp - string with data read from the buffer
        """
        c_time = time.time()

        self.write(cmd)

        str2find = "S:" + str(s)

        resp = ""
        while "ok" not in resp:

            resp += self.read()

            # Checks timeout
            if timeout is not None:
                e_time = time.time()
                if e_time-c_time > timeout:
                    break

        while str2find not in resp:
            try:
                self.write("M625\n")
                time.sleep(0.5)
                resp += self.read()
            except Exception, ex:
                logger.error("Exception while waiting for %s response: %s", str2find, str(ex))

        return resp

    # *************************************************************************
    #                        close Method
    # *************************************************************************
    def close(self):
        r"""
        close method

        closes active connection with printer
        """
        if self.dev is not None:
            try:
                # release the device
                usb.util.dispose_resources(self.dev)
                #usb.util.release_interface(self.dev, self.intf)    #not needed after dispose
            except usb.core.USBError, e:
                logger.error("USB exception while closing connection to printer: %s", str(e))

        return

    # *************************************************************************
    #                        isConnected Method
    # *************************************************************************
    def isConnected(self):
        r"""
        isConnected method

        returns the connection state

        returns:
            True if connected
            False if disconnected
        """

        return self.connected

    # *************************************************************************
    #                        getCommandIntf Method
    # *************************************************************************
    def getCommandIntf(self):
        r"""
        getCommandIntf method

        returns Comm object which contains the printer commands interface

        returns:
            Comm if connected
            None if disconnected
        """

        return self.command_intf

    # *************************************************************************
    #                        reconnect Method
    # *************************************************************************
    def reconnect(self):
        r"""
        reconnect method

        tries to reconnect to the printer

        returns:
            True if connected
            False if disconnected
        """

        if self.connected is False:
            self.findBEE()
        else:
            self.close()
            self.findBEE()

        return self.connected
