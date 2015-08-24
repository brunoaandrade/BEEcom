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
from beedriver.commands import BeeCmd
from beedriver import logger
import threading

class Conn:
    r"""
        Connection Class

        This class provides the methods to manage and control communication with the
        BeeTheFirst 3D printer

        __init__()                                              Initializes current class
        GetPrinterList()                                        Returns a Dictionary list of the printers.
        ConnectToPrinter(selectedPrinter)                       Establishes Connection to selected printer
        ConnectToPrinterWithSN(serialNumber)                    Establishes Connection to printer by serial number
        Write(message,timeout)                                  Writes data to the communication buffer
        Read()                                                  Read data from the communication buffer
        Dispatch(message)                                       Writes data to the buffer and reads the response
        SendCmd(cmd,wait,to)                                    Sends a command to the 3D printer
        waitFor(cmd, s, timeout)                                Writes command to the printer and waits for the response
        _waitForStatus(cmd, s, timeout)                         Writes command to the printer and waits for status the response
        Close()                                                 Closes active communication with the printer
        isConnected()                                           Returns the current state of the printer connection
        getCommandIntf()                                        Returns the BeeCmd object with the command interface for higher level operations
        Reconnect()                                             Closes and re-establishes the connection with the printer
    """

    dev = None
    
    ep_in = None
    ep_out = None
    
    cfg = None
    intf = None

    READ_TIMEOUT = 2000
    DEFAULT_READ_LENGTH = 512

    queryInterval = 0.5

    connected = None

    backend = None
    
    printerList = None
    connectedPrinter = None

    command_intf = None     # Commands interface

    # *************************************************************************
    #                            Init Method
    # *************************************************************************
    def __init__(self):
        r"""
        Init Method

        Initializes this class

        receives as argument the BeeConnection object and verifies the
        connection status

        """

        self.transfering = False
        self.fileSize = 0
        self.bytesTransferred = 0

        if self.isConnected():
            self.command_intf = BeeCmd(self)

        return
    
    
    # *************************************************************************
    #                        GetPrinterLit Method
    # *************************************************************************
    def GetPrinterList(self):
        r"""
        GetPrinterLit method

        Returns a Dictionary list of the printers.
        """
        
        #self.connected = False
        
        dev_list = []
        for dev in usb.core.find(idVendor=0xffff, idProduct=0x014e, find_all=True):
            dev_list.append(dev)
                            
        for dev in usb.core.find(idVendor=0x29c9, find_all=True):
            dev_list.append(dev)
            
        #Smoothiboard
        for dev in usb.core.find(idVendor=0x1d50, find_all=True):
            dev_list.append(dev)
        
        
        self.printerList = []
        for dev in dev_list:
            printer = {}
            printer['VendorID'] = str(dev.idVendor)
            printer['ProductID'] = str(dev.idProduct)
            printer['Manufacturer'] = dev.manufacturer
            printer['Product'] = dev.product
            printer['Serial Number'] = dev.serial_number
            printer['Interfaces'] = []
            for config in dev:
                for intf in config:
                    interface = {}
                    interface['Class'] = intf.bInterfaceClass
                    #endPoints = intf.endpoints()
                    interface['EP Out'] =  usb.util.find_descriptor(intf,
                                                                    # match the first OUT endpoint
                                                                    custom_match=lambda lb: usb.util.endpoint_direction(lb.bEndpointAddress) == usb.util.ENDPOINT_OUT)
                    interface['EP In'] =  usb.util.find_descriptor(intf,
                                                                    # match the first OUT endpoint
                                                                    custom_match=lambda lb: usb.util.endpoint_direction(lb.bEndpointAddress) == usb.util.ENDPOINT_IN)
                    printer['Interfaces'].append(interface)
            self.printerList.append(printer)
        
        #logger.info('Found %d Printers.' % len(self.printerList))
        
        return self.printerList
    
    # *************************************************************************
    #                        ConnectToPrinter Method
    # *************************************************************************
    def ConnectToPrinter(self,selectedPrinter):
        r"""
        ConnectToPrinter method

        Establishes Connection to selected printer
        
        returns False if connection fails
        """
        
        self.connectedPrinter = selectedPrinter
        
        logger.info('\n...Connecting to %s with serial number %s',str(selectedPrinter['Product']),str(selectedPrinter['Serial Number']))
        
        self.ep_out = self.connectedPrinter['Interfaces'][0]['EP Out']
        self.ep_in = self.connectedPrinter['Interfaces'][0]['EP In']
        
        # Verify that the end points exist
        assert self.ep_out is not None
        assert self.ep_in is not None
        
        self.dev = self.ep_out.device
        self.dev.set_configuration()
        self.dev.reset()
        time.sleep(0.5)
        #self.dev.set_configuration()
        self.cfg = self.dev.get_active_configuration()
        self.intf = self.cfg[(0,0)]
        
        
        self.connected = True
        
        return True
    
    # *************************************************************************
    #                        ConnectToPrinterWithSN Method
    # *************************************************************************
    def ConnectToPrinterWithSN(self,serialNumber):
        r"""
        ConnectToPrinterWithSN method

        Establishes Connection to printer by serial number
        
        returns False if connection fails
        """
        
        for printer in self.printerList:
            SN = str(printer['Serial Number'])
            if SN == serialNumber:
                self.ConnectToPrinter(printer)
                return True
            
        return False

    # *************************************************************************
    #                        Write Method
    # *************************************************************************
    def Write(self, message, timeout=500):
        r"""
        Write method

        Writes a message to the communication buffer

        arguments:
            message - data to be Writen
            timeout - optional communication timeout (default = 500ms)

        returns:
            bytesWriten - bytes Writen to the buffer
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
    #                        Read Method
    # *************************************************************************
    def Read(self, timeout=2000, readLen=512):
        r"""
        Read method

        reads existing data from the communication buffer

        arguments:
            timeout - optional communication timeout (default = 500ms)

        returns:
            sret - string with data read from the buffer
        """

        resp = ""

        try:
            self.Write("")
            ret = self.ep_in.read(readLen, timeout)
            resp = ''.join([chr(x) for x in ret])
        except usb.core.USBError, e:
            logger.error("USB read data exception: %s", str(e))

        return resp

    # *************************************************************************
    #                        Dispatch Method
    # *************************************************************************
    def Dispatch(self, message):
        r"""
        Dispatch method

        Writes data to the communication buffers and read existing data

        arguments:
            message - data to be Writen

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
            logger.error("USB Dispatch (Write) data exception: %s", str(e))

        try:
            ret = self.ep_in.read(self.DEFAULT_READ_LENGTH, timeout)
            resp = ''.join([chr(x) for x in ret])

        except usb.core.USBError, e:
            logger.error("USB Dispatch (read) data exception: %s", str(e))

        return resp

    # *************************************************************************
    #                        SendCmd Method
    # *************************************************************************
    def SendCmd(self, cmd, wait=None, timeout=None):
        r"""
        SendCmd method

        sends command to the printer

        arguments:
            cmd - command to send
            wait - optional wait for reply
            timeout - optional communication timeout

        returns:
            resp - string with data read from the buffer
        """
        if '\n' not in cmd:
            cmd = cmd + "\n"

        if wait is None:
            resp = self.Dispatch(cmd)
        else:
            if wait.isdigit():
                resp = self._waitForStatus(cmd, wait, timeout)
            else:
                resp = self._waitFor(cmd, wait, timeout)

        return resp

    # *************************************************************************
    #                        waitFor Method
    # *************************************************************************
    def _waitFor(self, cmd, s, timeout=None):
        r"""
        waitFor method

        Writes command to the printer and waits for the response

        arguments:
            cmd - commmand to send
            s - string to be found in the response
            timeout - optional communication timeout (seconds)

        returns:
            resp - string with data read from the buffer
        """
        c_time = time.time()

        self.Write(cmd)

        resp = ""
        while s not in resp:
            resp += self.Read()

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

        Writes command to the printer and waits for status the response

        arguments:
            cmd - commmand to send
            s - string to be found in the response
            timeout - optional communication timeout (seconds)

        returns:
            resp - string with data read from the buffer
        """
        c_time = time.time()

        self.Write(cmd)

        str2find = "S:" + str(s)

        resp = ""
        while "ok" not in resp:

            resp += self.Read()

            # Checks timeout
            if timeout is not None:
                e_time = time.time()
                if e_time-c_time > timeout:
                    break

        while str2find not in resp:
            try:
                self.Write("M625\n")
                time.sleep(0.5)
                resp += self.Read()
            except Exception, ex:
                logger.error("Exception while waiting for %s response: %s", str2find, str(ex))

        return resp

    # *************************************************************************
    #                        Close Method
    # *************************************************************************
    def Close(self):
        r"""
        Close method

        closes active connection with printer
        """
        if self.ep_out is not None:
            try:
                # release the device
                usb.util.dispose_resources(self.dev)
                self.ep_out = None
                self.ep_in = None
                self.intf = None
                self.cfg = None
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
        if self.isConnected():
            self.command_intf = BeeCmd(self)

        return self.command_intf
    # *************************************************************************
    #                        Reconnect Method
    # *************************************************************************
    def Reconnect(self):
        r"""
        Reconnect method

        tries to reconnect to the printer

        returns:
            True if connected
            False if disconnected
        """
        
        SN = str(self.connectedPrinter['Serial Number'])
        self.Close()
        time.sleep(3)
        self.GetPrinterList()
        self.ConnectToPrinterWithSN(SN)
        
        return self.connected
