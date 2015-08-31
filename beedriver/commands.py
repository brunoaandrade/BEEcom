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

    This class exports some methods with predefined commands to control BEEVERYCREATIVE 3D printers
    __init__(conn)                                            Inits current class
    GoToFirmware()                                            Resets Printer in firmware mode
    GoToBootloader()                                          Resets Printer in bootloader mode
    GetPrinterMode()                                          Return printer mode
    CleanBuffer()                                             Cleans communication buffer
    isConnected()                                             Returns the connection state
    GetStatus()                                               Return printer status
    Beep()                                                    2s Beep
    Home()                                                    Home all axis
    HomeXY()                                                  Home X and Y axis
    HomeZ()                                                   Home Z axis
    Move(x, y, z, e, f, wait)                                 Relative move
    StartCalibration()                                        Starts the calibration procedure
    CancelCalibration()                                       Cancels the calibration procedure.
    GoToNextCalibrationPoint()                                Moves to next calibration point.
    GetNozzleTemperature()                                    Returns current nozzle temperature
    SetNozzleTemperature(t)                                   Sets nozzle target temperature
    Load()                                                    Performs load filament operation
    Unload()                                                  Performs unload operation
    StartHeating(t,extruder)                                  Starts Heating procedure
    GetHeatingState()                                         Returns the heating state
    CancelHeating()                                           Cancels Heating
    GoToHeatPos()                                             Moves the printer to the heating coordinates
    GoToRestPos()                                             Moves the printer to the rest position
    GetBeeCode()                                              Returns current filament BeeCode
    SetBeeCode(code)                                          Sets filament beecode
    SetFilamentString(filStr)                                 Sets filament string
    GetFilamentString()                                       Returns filament string
    PrintFile(filePath, printTemperature, sdFileName)         Transfers a file to the printer and starts printing
    InitSD()                                                  Inits SD card
    GetFileList()                                             Returns list with GCode files stored in the printers memory
    CreateFile(fileName)                                      Creates a file in the SD card root directory
    OpenFile(fileName)                                        Opens file in the sd card root dir
    StartSDPrint(sdFileName)                                  Starts printing selected file
    CancelPrint()                                             Cancels current print and home the printer axis
    GetPrintVariables()                                       Returns List with Print Variables:
    SetBlowerSpeed(speed)                                     Sets Blower Speed
    SetFirmwareString(fwStr)                                  Sets new bootloader firmware String
    FlashFirmware(fileName, firmwareString)                   Flash New Firmware
    TransferGcodeFile(fileName, sdFileName)                   Transfers GCode file to printer internal memory
    GetTransferCompletionState()                              Returns current transfer completion percentage 
    CancelTransfer()                                          Cancels Current Transfer 
    GetFirmwareVersion()                                      Returns Firmware Version String
    PausePrint()                                              Initiates pause process
    ResumePrint()                                             Resume print from pause/shutdown
    EnterShutdown()                                           Pauses print and sets printer in shutdown
    ClearShutdownFlag()                                       Clears shutdown Flag
    SendCmd(cmd, wait, timeout)                               Sends command to printer
    """
    
    connected = None
    beeCon = None

    transmissionErrors = 0

    oldFw = ''
    newFw = ''
    
    transfThread = None
    
    MESSAGE_SIZE = 512
    BLOCK_SIZE = 64
    
    calibrationState = 0
    setPointTemperature = 0
    
    pausing = False
    paused = False
    shutdown = False

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
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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

        return the sate of the connection:
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
        
        if 'Firmware' not in self.GetPrinterMode():
            #logger.info('GetStatus: can only get status in firmware')
            return ''
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None

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
            elif 's:7' in resp.lower() or 'pause' in resp.lower():
                status = 'Pause'
                self.paused = True
                done = True
            elif 's:9' in resp.lower() or 'shutdown' in resp.lower():
                status = 'Shutdown'
                self.shutdown = True
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
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None

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
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None

        self.beeCon.SendCmd("G28 Z0\n", "3")

        return

    # *************************************************************************
    #                            Move Method
    # *************************************************************************
    def Move(self, x=None, y=None, z=None, e=None, f=None, wait=None):
        r"""
        Move method

        performs a relative move at a given feedrate current

        arguments:
        x - X axis displacement
        y - Y axis displacement
        z - Z axis displacement
        e - E extruder displacement

        f - feedrate

        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
    #                     StartCalibration Method
    # *************************************************************************
    def StartCalibration(self,startZ = 2.0,repeat = False):
        r"""
        StartCalibration method

        Starts the calibration procedure. If a calibration repeat is asked the startZ heigh is used.
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.calibrationState = 0
        
        cmdStr = ''
        if repeat:
            cmdStr = 'G131 S0 Z%.2f' % startZ
        else:
            cmdStr = 'G131 S0'
        
        self.beeCon.SendCmd(cmdStr)
                    
        return True
    
    # *************************************************************************
    #                     CancelCalibration Method
    # *************************************************************************
    def CancelCalibration(self):
        r"""
        CancelCalibration method

        Cancels the calibration procedure.
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.Home()
        
        return
    
    # *************************************************************************
    #                     GoToNextCalibrationPoint Method
    # *************************************************************************
    def GoToNextCalibrationPoint(self):
        r"""
        GoToNextCalibrationPoint method

        Moves to next calibration point.
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.beeCon.SendCmd('G131')
        
        return
    
    # *************************************************************************
    #                     GetNozzleTemperature Method
    # *************************************************************************
    def GetNozzleTemperature(self):
        r"""
        getNozzleTemperature method

        reads current nozzle temperature

        returns:
            nozzle temperature
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
    #                        SetNozzleTemperature Method
    # *************************************************************************
    def SetNozzleTemperature(self, t):
        r"""
        setNozzleTemperature method

        Sets nozzle target temperature

        Arguments:
            t - nozzle temperature
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.beeCon.SendCmd("M701\n")
        return

    # *************************************************************************
    #                            Unload Method
    # *************************************************************************
    def Unload(self):
        r"""
        Unload method

        performs unload operation
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.beeCon.SendCmd("M702\n")

        return
    
    # *************************************************************************
    #                            StartHeating Method
    # *************************************************************************
    def StartHeating(self,temperature,extruder = 0):
        r"""
        StartHeating method

        Starts Heating procedure
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.setPointTemperature = temperature
        
        self.beeCon._waitForStatus('M703 S%.2f\n' %temperature,'3')

        return
    
    # *************************************************************************
    #                            GetHeatingState Method
    # *************************************************************************
    def GetHeatingState(self):
        r"""
        GetHeatingState method

        Returns the heating state
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        currentT = self.GetNozzleTemperature()
        
        if self.setPointTemperature > 0:
            return 100 * currentT/self.setPointTemperature
        else:
            return 100
        
        return
    
    # *************************************************************************
    #                            CancelHeating Method
    # *************************************************************************
    def CancelHeating(self):
        r"""
        CancelHeating method

        Cancels Heating
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.SetNozzleTemperature(0)
        self.setPointTemperature = 0

        return True
    
    # *************************************************************************
    #                            GoToHeatPos Method
    # *************************************************************************
    def GoToHeatPos(self):
        r"""
        GoToHeatPos method

        moves the printer to the heating coordinates
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
    #                            GoToRestPos Method
    # *************************************************************************
    def GoToRestPos(self):
        r"""
        GoToRestPos method

        moves the printer to the rest position
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None

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
    #                            GetBeeCode Method
    # *************************************************************************
    def GetBeeCode(self):
        r"""
        GetBeeCode method

        reads current filament BeeCode

        returns:
            Filament BeeCode
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None

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
    #                            SetBeeCode Method
    # *************************************************************************
    def SetBeeCode(self, code):
        r"""
        SetBeeCode method

        Sets filament beecode

        arguments:
            code - filament code
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None

        commandStr = "M400 " + code + "\n"

        # Set BeeCode
        self.beeCon.SendCmd(commandStr)

        return
    
    # *************************************************************************
    #                            SetFilamentString Method
    # *************************************************************************
    def SetFilamentString(self,filStr):
        r"""
        SetFilamentString method

        Sets filament string

        arguments:
            filStr - filament string
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.beeCon.SendCmd('M1000 %s' %filStr)
        
        return
    
    # *************************************************************************
    #                            GetFilamentString Method
    # *************************************************************************
    def GetFilamentString(self):
        r"""
        GetFilamentString method

        Returns filament string
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        replyStr = self.beeCon.SendCmd('M1001')
        splits = replyStr.split("'")
        
        filStr = splits[1]
        
        if '_no_file' in filStr:
            return ''
        
        return filStr
    
    # *************************************************************************
    #                            PrintFile Method
    # *************************************************************************
    def PrintFile(self, filePath, printTemperature = None, sdFileName = None):
        r"""
        PrintFile method
        
        Transfers a file to the printer and starts printing
        
        returns True if print starts successfully
        
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        # check if file exists
        if os.path.isfile(filePath) is False:
            logger.info("transferGCode: File does not exist")
            return False
        
        if self.GetPrinterMode() == 'Bootloader':
            self.GoToFirmware()
        
        if printTemperature is not None:
            self.StartHeating(200)
        
        time.sleep(1)
        self.beeCon.Read()
        
        self.transfThread = transferThread.FileTransferThread(self.beeCon,filePath,'print',sdFileName)
        self.transfThread.start()
        
        #TODO. ADD HEATING TO THE THREAD AND WAIT FOR PRINT
                
        return True    

    # *************************************************************************
    #                            InitSD Method
    # *************************************************************************
    def InitSD(self):
        r"""
        InitSD method

        inits Sd card
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
        r"""
        GetFileList method

        Returns list with GCode files strored in the printers memory
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
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
    #                            StartSDPrint Method
    # *************************************************************************
    def StartSDPrint(self, sdFileName = ''):
        r"""
        StartSDPrint method

        starts printing selected file
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.beeCon.SendCmd('M33 %s' %sdFileName)

        return True

    # *************************************************************************
    #                            CancelPrint Method
    # *************************************************************************
    def CancelPrint(self):
        r"""
        cancelPrint method

        cancels current print and home the printer axis
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        logger.info('Cancelling print')
        self.beeCon.Write("M112\n")

        return True

    # *************************************************************************
    #                        GetPrintVariables Method
    # *************************************************************************
    def GetPrintVariables(self):
        r"""
        GetPrintVariables method
        
        Returns List with Print Variables:
        
            Estimated Time
            Elpased Time
            Number of Lines
            Executed Lines
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None

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
    #                        SetBlowerSpeed Method
    # *************************************************************************
    def SetBlowerSpeed(self, speed):
        r"""
        SetBlowerSpeed method
        
        Sets Blower Speed
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None

        cmd = 'M106 S' + str(speed) + '\n'
        self.beeCon.SendCmd(cmd)

        return
    
    # *************************************************************************
    #                        SetFirmwareString Method
    # *************************************************************************
    def SetFirmwareString(self, fwStr):
        r"""
        SetFirmwareString method
        
        Sets new bootloader firmware String
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None

        cmd = 'M104 A' + str(fwStr) + '\n'
        self.beeCon.SendCmd(cmd,'ok')

        return

    # *************************************************************************
    #                            FlashFirmware Method
    # *************************************************************************
    def FlashFirmware(self, fileName, firmwareString = '20.0.0'):
        r"""
        FlashFirmware method
        
        Flash new firmware
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None

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
    def TransferGcodeFile(self, fileName, sdFileName = None):
        r"""
        TransferGcodeFile method
        
        Transfers GCode file to printer internal memory
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None

        if os.path.isfile(fileName) is False:
            logger.warning("Gcode Transfer: File does not exist")
            return

        logger.info("Transfer GCode File: %s" % fileName)
        
        if sdFileName is not None:
            self.transfThread = transferThread.FileTransferThread(self.beeCon,fileName,'gcode',sdFileName)
        else:
            self.transfThread = transferThread.FileTransferThread(self.beeCon,fileName,'gcode')
        self.transfThread.start()

        return
    
    # *************************************************************************
    #                        GetTransferCompletionState Method
    # *************************************************************************
    def GetTransferCompletionState(self):
        r"""
        GetTransferCompletionState method
        
        Returns current transfer completion percentage 
        """
        
        if self.transfThread.isAlive():
            p = self.transfThread.GetTransferCompletionState()
            logger.info("Transfer State: %s" %str(p))
            return p
        
        return None
    
    # *************************************************************************
    #                        CancelTransfer Method
    # *************************************************************************
    def CancelTransfer(self):
        r"""
        CancelTransfer method
        
        Cancels Current Transfer 
        """
        if self.transfThread.isAlive():
            self.transfThread.CancelFileTransfer()
            return True
        
        return False
    # *************************************************************************
    #                            IsTranfering Method
    # *************************************************************************
    def IsTranfering(self):
        r"""
        IsTranfering method
        
        Returns True if a file is being transfer
        """
        if self.transfThread is not None:
            return self.transfThread.transfering
        
        return False
    
    # *************************************************************************
    #                            GetFirmwareVersion Method
    # *************************************************************************
    def GetFirmwareVersion(self):
        r"""
        GetFirmwareVersion method
        
        Returns Firmware Version String
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        resp = self.beeCon.SendCmd('M115\n', 'ok')
        resp = resp.replace(' ', '')

        split = resp.split('ok')
        fw = split[0]

        return fw
    
    # *************************************************************************
    #                            PausePrint Method
    # *************************************************************************
    def PausePrint(self):
        r"""
        PausePrint method
        
        Initiates pause process
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.beeCon.SendCmd('M640\n')
        self.pausing = True
        
        return
    
    # *************************************************************************
    #                            ResumePrint Method
    # *************************************************************************
    def ResumePrint(self):
        r"""
        ResumePrint method
        
        Resume print from pause/shutdown
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.beeCon.SendCmd('M643\n')
        self.pausing = False
        self.shutdown = False
        
        return
    
    # *************************************************************************
    #                            EnterShutdown Method
    # *************************************************************************
    def EnterShutdown(self):
        r"""
        EnterShutdown method
        
        Pauses print and sets printer in shutdown
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        if not self.pausing or not self.paused:
            self.beeCon.SendCmd('M640\n')
        
        nextPullTime = time.time() + 1
        while not self.paused:
            t = time.time()
            if t > nextPullTime:
                s = self.GetStatus()
        
        self.beeCon.SendCmd('M36\n')
        
        return
    
    # *************************************************************************
    #                            ClearShutdownFlag Method
    # *************************************************************************
    def ClearShutdownFlag(self):
        r"""
        ClearShutdownFlag method
        
        Clears shutdown Flag
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        self.beeCon.SendCmd('M505\n')
        
        return True
    
    # *************************************************************************
    #                            SendCmd Method
    # *************************************************************************
    def SendCmd(self, cmd, wait=None, timeout=None):
        r"""
        SendCmd method
        
        Sends command to printer
        """
        
        if self.IsTranfering():
            logger.info('File Transfer Thread active, please wait for transfer thread to end')
            return None
        
        return self.beeCon.SendCmd(cmd, wait, timeout)
