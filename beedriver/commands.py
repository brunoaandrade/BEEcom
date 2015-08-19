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

import sys
import os
import time
import math
import thread

import usb.core
import usb.util
from beedriver import logger
from beedriver import transferThread

class BeeCmd:
    r"""
    BeeCmd Class

    This class exports some methods with predefined commands to control the BTF

    __init__()        Initializes current class
    isConnected()    returns the connection state
    startPrinter()    Initializes the printer in firmware mode
    getStatus()        returns the status of the printer
    beep()            beep during 2s
    home()            Homes axis XYZ
    homeXY()          Homes axis XY
    homeZ()            Homes Z axis
    move(x,y,z,e)        Relatie move of axis XYZE at given feedrate
    GoToFirstCalibrationPoint()    Moves the BTF to the first calibration point
    GoToSecondCalibrationPoint()    Saves calibration offset and moves to second calibration point
    GoToThirdCalibrationPoint()    Moves the BTF to the third calibration point
    GetNozzleTemperature(T)        Defines nozzle target setpoint temperature
    SetNozzleTemperature()        Returns current nozzle temperature
    Load()                        Performs load filament operation
    Unload()                        Performs unload filament operation
    GoToHeatPos()                Moves the BTF to its heat coordinates during filament change
    GoToRestPos()                Moves the BTF to its Rest coordinates
    GetBeeCode()                Get current filament beecode
    SetBeeCode(A)                Set current filament beecode
    InitSD()                    Initializes SD card
    CreateFile(f)                Creates SD file
    OpenFile(f)                    Opens file in the SD card
    StartTransfer(f,a)            prepares the printer to receive a block of messages
    StartSDPrint()                Starts printing selected sd file
    cancleSDPrint()                Cancels SD print
    sendBlock()                    Sends a block of messages
    sendBlockMsg()                Sends a message from the block
    CleanBuffer()                Clears communication buffer
    getPrintStatus()                Gets print status
    """
    connected = None
    beeCon = None

    transmissionErrors = 0

    oldFw = ''
    newFw = ''
    
    transfThread = None
    
    MESSAGE_SIZE = 512
    BLOCK_SIZE = 64

    # *************************************************************************
    #                            Init Method
    # *************************************************************************
    def __init__(self, conn):
        r"""
        Init Method

        arguments:
            conn - Connection object

        Initializes this class

        """

        self.beeCon = conn
        self.connected = self.beeCon.isConnected()

        return
    
    # *************************************************************************
    #                            GoToFirmware Method
    # *************************************************************************
    def GoToFirmware(self):
        r"""
        GoToFirmware method

        Resets the printer to firmware
        """
        
        if self.beeCon.transfering:
            logger.info('File transfer in progress... Can not change to Firmware\n')
            return None
        
        logger.info('Changing to Firmware...\n')
        
        mode = self.GetPrinterMode()
        
        if mode == 'Firmware':
            logger.info('Printer Already in Firmware\n')
            return False
        
        self.beeCon.Write('M630\n')
        self.beeCon.Reconnect()
        
        mode = self.GetPrinterMode()
        
        return mode
    
    # *************************************************************************
    #                            GoToBootloader Method
    # *************************************************************************
    def GoToBootloader(self):
        r"""
        GoToBootloader method

        Resets the printer to Bootloader
        """
        if self.beeCon.transfering:
            logger.info('File transfer in progress... Can not change to Bootloader\n')
            return None
        
        logger.info('Changing to Bootloader...\n')
        
        mode = self.GetPrinterMode()
        
        if mode == 'Bootloader':
            logger.info('Printer Already in Bootloader\n')
            return False
        
        self.beeCon.Write('M609\n')
        self.beeCon.Reconnect()
        
        mode = self.GetPrinterMode()
        
        return mode
    
    # *************************************************************************
    #                            GetPrinterMode Method
    # *************************************************************************
    def GetPrinterMode(self):
        r"""
        GetPrinterMode method

        Returns a string with the current printer mode (Bootloader/Firmware).
        """
        if self.beeCon.transfering:
            logger.info('File transfer in progress... Can not get printer mode\n')
            return None
        
        resp = self.beeCon.SendCmd("M625\n")

        if 'Bad M-code 625' in resp:   # printer in bootloader mode
            return "Bootloader"
        elif 'ok Q' in resp:
            return "Firmware"
        else:
            return None
        
        return
        
    # *************************************************************************
    #                            CleanBuffer Method
    # *************************************************************************
    def CleanBuffer(self):
        r"""
        CleanBuffer method

        Cleans communication buffer and establishes communications
        """
        logger.debug("Cleaning")
        cleanStr = 'M625;' + 'a'*(self.MESSAGE_SIZE-6) + '\n'

        self.beeCon.Write(cleanStr, 50)

        tries = self.BLOCK_SIZE + 1

        resp = self.beeCon.Read()
        acc_resp = ""

        while "ok" not in acc_resp.lower() and tries > 0:
            try:
                self.beeCon.Write(cleanStr)
                
                resp = self.beeCon.Read()
                
                acc_resp += resp
                #print(resp)
                tries -= 1
            except Exception, ex:
                logger.error("Read timeout %s", str(ex))
                tries = 0

        #print(resp)

        return tries

    # *************************************************************************
    #                            connected Method
    # *************************************************************************
    def isConnected(self):
        r"""
        isConnected method

        return the sate of the BTF connection:
            connected = True
            disconnected = False
        """
        return self.connected

    # *************************************************************************
    #                            GetStatus Method
    # *************************************************************************
    def GetStatus(self):
        r"""
        GetStatus method

        returns the current status of the printer
        """

        resp = ''
        status = ''
        done = False

        while not done:

            while 's:' not in resp.lower():
                resp += self.beeCon.SendCmd("M625\n")
                time.sleep(1)

            if 's:3' in resp.lower():
                status = 'Ready'
                done = True
            elif 's:4' in resp.lower():
                status = 'Moving'
                done = True
            elif 's:5' in resp.lower():
                status = 'SD_Print'
                done = True
            elif 's:6' in resp.lower():
                status = 'Transfer'
                done = True
            elif 's:7' in resp.lower():
                status = 'Pause'
                done = True
            elif 's:9' in resp.lower():
                status = 'SDown_Wait'
                done = True

        return status

    # *************************************************************************
    #                            Beep Method
    # *************************************************************************
    def Beep(self):
        r"""
        Beep method

        performs a beep with 2 seconds duration
        """

        self.beeCon.SendCmd("M300 P2000\n")

        return

    # *************************************************************************
    #                            Home Method
    # *************************************************************************
    def Home(self):
        r"""
        Home method

        homes all axis
        """

        self.beeCon.SendCmd("G28\n", "3")

        return

    # *************************************************************************
    #                            HomeXY Method
    # *************************************************************************
    def HomeXY(self):
        r"""
        HomeXY method

        home axis X and Y
        """

        self.beeCon.SendCmd("G28 X0 Y0\n", "3")

        return

    # *************************************************************************
    #                            HomeZ Method
    # *************************************************************************
    def HomeZ(self):
        r"""
        HomeZ method

        homes Z axis
        """

        self.beeCon.SendCmd("G28 Z0\n", "3")

        return

    # *************************************************************************
    #                            move Method
    # *************************************************************************
    def move(self, x=None, y=None, z=None, e=None, f=None, wait=None):
        r"""
        move method

        performs a relative move at a given feedrate current

        arguments:
        x - X axis displacement
        y - Y axis displacement
        z - Z axis displacement
        e - E extruder displacement

        f - feedrate

        """
        resp = self.beeCon.SendCmd("M121\n")

        splits = resp.split(" ")
        xSplit = splits[2].split(":")
        ySplit = splits[3].split(":")
        zSplit = splits[4].split(":")
        eSplit = splits[5].split(":")

        currentX = float(xSplit[1])
        currentY = float(ySplit[1])
        currentZ = float(zSplit[1])
        currentE = float(eSplit[1])

        newX = currentX
        newY = currentY
        newZ = currentZ
        newE = currentE

        if x is not None:
            newX = newX + x
        if y is not None:
            newY = newY + y
        if z is not None:
            newZ = newZ + z
        if e is not None:
            newE = newE + e

        if f is not None:
            newF = float(f)
            commandStr = "G1 X" + str(newX) + " Y" + str(newY) + " Z" + str(newZ) + " E" + str(newE) + "F" + str(newF) + "\n"
        else:
            commandStr = "G1 X" + str(newX) + " Y" + str(newY) + " Z" + str(newZ) + " E" + str(newE) + "\n"

        if wait is not None:
            self.beeCon.SendCmd(commandStr)
        else:
            self.beeCon.SendCmd(commandStr, "3")

        return

    # *************************************************************************
    #                     goToFirstCalibrationPoint Method
    # *************************************************************************
    def goToFirstCalibrationPoint(self):
        r"""
        goToFirstCalibrationPoint method

        moves the printer to the first calibration point
        """

        # go to home
        self.beeCon.SendCmd("G28\n","3")

        # set feedrate
        self.beeCon.SendCmd("G1 F15000\n")

        # set acceleration
        self.beeCon.SendCmd("M206 X400\n")

        # go to first point
        self.beeCon.SendCmd("G1 X0 Y67 Z2\n")

        # set acceleration
        self.beeCon.SendCmd("M206 X1000\n")

        return

    # *************************************************************************
    #                     goToSecondCalibrationPoint Method
    # *************************************************************************
    def goToSecondCalibrationPoint(self):
        r"""
        goToSecondCalibrationPoint method

        Saves calibration offset and moves to second calibration point
        """

        # record calibration position
        self.beeCon.SendCmd("M603\n")
        self.beeCon.SendCmd("M601\n")

        # set feedrate
        self.beeCon.SendCmd("G1 F5000\n")
        # set acceleration
        self.beeCon.SendCmd("M206 X400\n")

        # go to SECOND point
        self.move(0, 0, 10, 0)
        # self.beeCon.SendCmd("G1 X-31 Y-65\n","3")
        self.beeCon.SendCmd("G1 X-31 Y-65\n")
        self.move(0, 0, -10, 0)

        return

    # *************************************************************************
    #                     goToThirdCalibrationPoint Method
    # *************************************************************************
    def GoToThirdCalibrationPoint(self):
        r"""
        goToThirdCalibrationPoint method

        moves the printer to the third calibration point
        """

        # set feedrate
        self.beeCon.SendCmd("G1 F5000\n")
        # set acceleration
        self.beeCon.SendCmd("M206 X400\n")

        self.move(0, 0, 10, 0)
        # go to SECOND point
        # self.beeCon.SendCmd("G1 X35 Y-65\n","3")
        self.beeCon.SendCmd("G1 X35 Y-65\n")

        self.move(0, 0, -10, 0)

        return

    # *************************************************************************
    #                     getNozzleTemperature Method
    # *************************************************************************
    def getNozzleTemperature(self):
        r"""
        getNozzleTemperature method

        reads current nozzle temperature

        returns:
            nozzle temperature
        """

        # get Temperature
        resp = self.beeCon.SendCmd("M105\n")

        try:
            splits = resp.split(" ")
            tPos = splits[0].find("T:")
            t = float(splits[0][tPos+2:])
            return t
        except Exception, ex:
            logger.error("Error getting nozzle temperature: %s", str(ex))

        return 0

    # *************************************************************************
    #                        setNozzleTemperature Method
    # *************************************************************************
    def setNozzleTemperature(self, t):
        r"""
        setNozzleTemperature method

        Sets nozzle target temperature

        Arguments:
            t - nozzle temperature
        """

        commandStr = "M104 S" + str(t) + "\n"

        # set Temperature
        self.beeCon.SendCmd(commandStr)

        return

    # *************************************************************************
    #                            Load Method
    # *************************************************************************
    def Load(self):
        r"""
        Load method

        performs load filament operation
        """

        self.beeCon.SendCmd("G92 E\n")
        self.beeCon.SendCmd("M300 P500\n")
        self.beeCon.SendCmd("M300 S0 P500\n")
        self.beeCon.SendCmd("M300 P500\n")
        self.beeCon.SendCmd("M300 S0 P500\n")
        self.beeCon.SendCmd("M300 P500\n")
        self.beeCon.SendCmd("M300 S0 P500\n")
        self.beeCon.SendCmd("G1 F300 E100\n","3")
        self.beeCon.SendCmd("G92 E\n")
        return

    # *************************************************************************
    #                            Unload Method
    # *************************************************************************
    def Unload(self):
        r"""
        Unload method

        performs unload operation
        """

        self.beeCon.SendCmd("G92 E\n")
        self.beeCon.SendCmd("M300 P500\n")
        self.beeCon.SendCmd("M300 S0 P500\n")
        self.beeCon.SendCmd("M300 P500\n")
        self.beeCon.SendCmd("M300 S0 P500\n")
        self.beeCon.SendCmd("M300 P500\n")
        self.beeCon.SendCmd("M300 S0 P500\n")
        self.beeCon.SendCmd("G1 F300 E50\n")
        self.beeCon.SendCmd("G92 E\n")
        self.beeCon.SendCmd("G1 F1000 E-23\n")
        self.beeCon.SendCmd("G1 F800 E2\n")
        self.beeCon.SendCmd("G1 F2000 E-23\n")
        self.beeCon.SendCmd("G1 F200 E-50\n","3")
        self.beeCon.SendCmd("G92 E\n")

        return

    # *************************************************************************
    #                            goToHeatPos Method
    # *************************************************************************
    def goToHeatPos(self):
        r"""
        goToHeatPos method

        moves the printer to the heating coordinates
        """

        # set feedrate
        self.beeCon.SendCmd("G1 F15000\n")

        # set acceleration
        self.beeCon.SendCmd("M206 X400\n")

        # go to first point
        self.beeCon.SendCmd("G1 X30 Y0 Z10\n")

        # set acceleration
        self.beeCon.SendCmd("M206 X1000\n","3")

        return

    # *************************************************************************
    #                            goToRestPos Method
    # *************************************************************************
    def goToRestPos(self):
        r"""
        goToRestPos method

        moves the printer to the rest position
        """

        # set feedrate
        self.beeCon.SendCmd("G1 F15000\n")

        # set acceleration
        self.beeCon.SendCmd("M206 X400\n")

        # go to first point
        self.beeCon.SendCmd("G1 X-50 Y0 Z110\n")

        # set acceleration
        self.beeCon.SendCmd("M206 X1000\n","3")

        return

    # *************************************************************************
    #                            getBeeCode Method
    # *************************************************************************
    def getBeeCode(self):
        r"""
        getBeeCode method

        reads current filament BeeCode

        returns:
            Filament BeeCode
        """

        # Get BeeCode
        resp = self.beeCon.SendCmd("M400\n")

        splits = resp.split(" ")

        code = ""

        for s in splits:
            cPos = s.find("bcode")
            if cPos >= 0:
                code = s[cPos+6:]

        return code

    # *************************************************************************
    #                            setBeeCode Method
    # *************************************************************************
    def setBeeCode(self, code):
        r"""
        setBeeCode method

        Sets filament beecode

        arguments:
            code - filament code
        """

        commandStr = "M400 " + code + "\n"

        # Set BeeCode
        self.beeCon.SendCmd(commandStr)

        return
    
    # *************************************************************************
    #                            PrintFile Method
    # *************************************************************************
    def PrintFile(self, filePath, printTemperature = None, sdFileName = None):
        r"""
        PrintFile method
        
        Transfers a file to the printer and starts printing
        
        returns True if print starts successfully
        
        """
        
        # check if file exists
        if os.path.isfile(filePath) is False:
            logger.info("transferGCode: File does not exist")
            return False
        
                
        return True    

    # *************************************************************************
    #                            InitSD Method
    # *************************************************************************
    def InitSD(self):
        r"""
        InitSD method

        inits Sd card
        """
        # Init SD
        self.beeCon.Write("M21\n")

        tries = 10
        resp = ""
        while (tries > 0) and ("ok" not in resp.lower()):
            try:
                resp += self.beeCon.Read()
                tries -= 1
            except Exception, ex:
                logger.error("Error initializing SD Card: %s", str(ex))

        return tries

    # *************************************************************************
    #                            GetFileList Method
    # *************************************************************************
    def GetFileList(self):

        fList = {}
        fList['FileNames'] = []
        fList['FilePaths'] = []

        self.InitSD()

        resp = ""
        self.beeCon.Write("M20\n")

        while "end file list" not in resp.lower():
            resp += self.beeCon.Read()

        lines = resp.split('\n')

        for l in lines:

            if "/" in l:
                if "firmware.bck" in l.lower():
                    pass
                elif "firmware.bin" in l.lower():
                    pass
                elif "config.txt" in l.lower():
                    pass
                elif "config.bck" in l.lower():
                    pass
                elif l == "":
                    pass
                else:
                    fName = l[1:len(l)-1]
                    fList['FileNames'].append(fName)
                    fList['FilePaths'].append('')

            elif "end file list" in l.lower():
                return fList

        return fList

    # *************************************************************************
    #                            CreateFile Method
    # *************************************************************************
    def CreateFile(self, fileName):
        r"""
        CreateFile method

        Creates a file in the SD card root directory

        arguments:
            fileName - file name
        """
        # Init SD
        self.InitSD()

        fn = fileName
        if len(fileName) > 8:
            fn = fileName[:8]

        cmdStr = "M30 " + fn + "\n"

        resp = self.beeCon.SendCmd(cmdStr)

        tries = 10
        while tries > 0:

            if "file created" in resp.lower():
                logger.info("SD file created")
                break
            elif "error" in resp.lower():
                logger.error("Error creating file")
                return False
            else:
                resp = self.beeCon.SendCmd("\n")
                logger.debug("Create file in SD: " + resp)

            tries -= 1
        if tries <= 0:
            return False

        return True

    # *************************************************************************
    #                            OpenFile Method
    # *************************************************************************
    def OpenFile(self, fileName):
        r"""
        OpenFile method

        opens file in the sd card root dir

        arguments:
            fileName - file name
        """

        # Init SD
        self.InitSD()

        cmdStr = "M23 " + fileName + "\n"

        # Open File
        resp = self.beeCon.SendCmd(cmdStr)

        tries = 10
        while tries > 0:
            if "file opened" in resp.lower():
                logger.info("SD file opened")
                break
            else:
                resp = self.beeCon.SendCmd("\n")
            tries -= 1

        if tries <= 0:
            return False

        return True

    # *************************************************************************
    #                            startTransfer Method
    # *************************************************************************
    def startTransfer(self, fSize, a):
        r"""
        startTransfer method

        prepares the printer to receive a block of messages

        arguments:
            fSize - bytes to be writen
            a - initial write position
        """

        cmdStr = "M28 D" + str(fSize - 1) + " A" + str(a) + "\n"
        # waitStr = "will write " + str(fSize) + " bytes ok"

        resp = self.beeCon.SendCmd(cmdStr)

        tries = 10
        while (tries > 0) and ("ok" not in resp.lower()):
            resp += self.beeCon.SendCmd("dummy")
            tries -= 1

        if tries <= 0:
            return False

        return True

    # *************************************************************************
    #                            StartSDPrint Method
    # *************************************************************************
    def StartSDPrint(self, sdFileName = ''):
        r"""
        StartSDPrint method

        starts printing selected file
        """
        self.beeCon.SendCmd('M33 %s' %sdFileName)

        return True

    # *************************************************************************
    #                            cancelSDPrint Method
    # *************************************************************************
    def cancelSDPrint(self):
        r"""
        cancelSDPrint method

        cancels current print and home the printer axis
        """

        logger.info('Cancelling print')
        self.beeCon.Write("M112\n", 100)
        logger.info(self.beeCon.Read(100))

        self.beeCon.Write("G28 Z \n", 100)
        self.beeCon.Read(100)

        self.beeCon.Write("G28\n", 100)
        logger.info(self.beeCon.Read(100))

        logger.info(self.beeCon.Read())

        #self.beeCon.Read()
        #self.homeZ()
        #self.homeXY()

        return True

    # *************************************************************************
    #                        getPrintStatus Method
    # *************************************************************************
    def getPrintStatus(self):

        printStatus = {}

        self.beeCon.Write('M32\n')

        resp = ""

        while 'ok' not in resp:
            resp += self.beeCon.Read()

        split = resp.split(' ')

        for s in split:
            if 'A' in s:
                printStatus['Estimated Time'] = int(s[1:])
            elif 'B' in s:
                printStatus['Elapsed Time'] = int(s[1:])//(60*1000)
            elif 'C' in s:
                printStatus['Lines'] = int(s[1:])
            elif 'D' in s:
                printStatus['Executed Lines'] = int(s[1:])

        return printStatus

    # *************************************************************************
    #                        setBlowerSpeed Method
    # *************************************************************************
    def setBlowerSpeed(self, speed):

        cmd = 'M106 S' + str(speed) + '\n'
        self.beeCon.SendCmd(cmd)

        return
    
    # *************************************************************************
    #                        SetFirmwareString Method
    # *************************************************************************
    def SetFirmwareString(self, fwStr):

        cmd = 'M104 A' + str(fwStr) + '\n'
        self.beeCon.SendCmd(cmd,'ok')

        return

    # *************************************************************************
    #                            FlashFirmware Method
    # *************************************************************************
    def FlashFirmware(self, fileName, firmwareString = '20.0.0'):

        if os.path.isfile(fileName) is False:
            logger.warning("Flash firmware: File does not exist")
            return

        logger.info("Flashing new firmware File: %s", fileName)
        self.SetFirmwareString('0.0.0')                  # Clear FW Version

        self.transfThread = transferThread.FileTransferThread(self.beeCon,fileName,'Firmware',firmwareString)
        self.transfThread.start()

        return
    
    # *************************************************************************
    #                            TransferGcodeFile Method
    # *************************************************************************
    def TransferGcodeFile(self, fileName):

        if os.path.isfile(fileName) is False:
            logger.warning("Gcode Transfer: File does not exist")
            return

        logger.info("Transfer GCode File: %s", fileName)

        self.transfThread = transferThread.FileTransferThread(self.beeCon,fileName,'gcode')
        self.transfThread.start()

        return
    
    # *************************************************************************
    #                        GetTransferCompletionState Method
    # *************************************************************************
    def GetTransferCompletionState(self):
        
        if self.transfThread.isAlive():
            p = self.transfThread.GetTransferCompletionState()
            logger.info("Transfer State: %s" %str(p))
            return p
        
        return None
    
    # *************************************************************************
    #                        CancelTransfer Method
    # *************************************************************************
    def CancelTransfer(self):
        
        if self.transfThread.isAlive():
            self.transfThread.CancelFileTransfer()
            return True
        
        return False
    

    # *************************************************************************
    #                            GetFirmwareVersion Method
    # *************************************************************************
    def GetFirmwareVersion(self):

        resp = self.beeCon.SendCmd('M115\n', 'ok')
        resp = resp.replace(' ', '')

        split = resp.split('ok')
        fw = split[0]

        return fw
    
    # *************************************************************************
    #                            HeatExtruder Method
    # *************************************************************************
    def HeatExtruder(self, temperature,extruder = 0):

        self.beeCon.SendCmd('M703 S%.2f' %temperature)

        return True
