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

import os
import sys
import time
from beedriver import connection
import logging
import re

# Logger configuration
logger = logging.getLogger('beeconsole')
logger.setLevel(logging.INFO)

# create console handler with a higher log level
ch = logging.StreamHandler()
ch.setLevel(logging.INFO)

# add the handlers to logger
logger.addHandler(ch)


class Console:

    r"""
    Bee Console - Terminal console for the BeeTheFirst 3D Printer

    Every new line inserted in the console is processed in 2 different categories:

    Printer commands:
        Single M & G code lines.

    Operation Commands:
        Commands to do specific operations, like load filament and transfer files.
        Operation commands always start with an "-"

        The following operation commands are implemented:

        * "-load" Load filament operation
        * "-unload" Unload filament operation
        * "-gcode LOCALFILE_PATH R2C2_FILENAME" Transfer gcode file to Printer.

                LOCALFILE_PATH -> filepath to file
                R2C2_FILENAME -> Name to be used when writing in printer memory (Optional)

        * "-flash LOCALFILE_PATH" Flash Firmware.

                LOCALFILE_PATH -> filepath to file

        * "-exit" Closes console


    """
    beeConn = None
    beeCmd = None

    connected = False
    exit = False

    exitState = None

    mode = "None"

    # *************************************************************************
    #                            Init Method
    # *************************************************************************
    def __init__(self, findAll = False):

        self.connected = False
        self.exit = False
        self.exitState = None

        nextPullTime = time.time() + 1

        logger.info("Waiting for printer connection...")

        while (not self.connected) and (not self.exit):

            t = time.time()

            if t > nextPullTime:

                self.beeConn = connection.Conn()
                # Connect to first Printers
                #findAll = True
                if(findAll):
                    printerlist = self.beeConn.getPrinterList();
                    if len(printerlist) > 1:
                        print "Choose printer from list:"
                        i = 0
                        for printer in printerlist:
                            print "{}: Printer Name:{}      with serial number:{}\n".format(i,printer['Product'],printer['Serial Number'])
                            i = i + 1

                        selesctedPrinterIdx = input(':')
                        if(type( selesctedPrinterIdx ) == int and selesctedPrinterIdx >= 0 and selesctedPrinterIdx < len(printerlist)):
                            self.beeConn.connectToPrinter(printerlist[int(selesctedPrinterIdx)])
                    else:
                        self.beeConn.connectToFirstPrinter()
                else:
                    self.beeConn.connectToFirstPrinter()
                
                if self.beeConn.isConnected() is True:

                    self.beeCmd = self.beeConn.getCommandIntf()
                    
                    self.mode = self.beeCmd.getPrinterMode()
                    
                    # USB Buffer need cleaning
                    if self.mode is None:
                        logger.info('Printer not responding... cleaning buffer\n')
                        self.beeCmd.cleanBuffer()

                        self.beeConn.close()
                        self.beeConn = None
                        # return None
                    
                    # Printer ready
                    else:
                        self.connected = True

                nextPullTime = time.time() + 1

        logger.info('Printer started in %s mode\n' %self.mode)
        
        status = self.beeCmd.getStatus()
        if status is not None:
            if 'Shutdown' in status:
                logger.info('Printer recovering from shutdown. Choose action:\n')
                logger.info('0: Resume print\n')
                logger.info('1: Cancel print\n')
                i = int(raw_input(">:"))
                if i == 0:
                    self.beeCmd.resumePrint()
                elif i == 1:
                    self.beeCmd.clearShutdownFlag()

        return
    
    # *************************************************************************
    #                            listPrinters Method
    # *************************************************************************
    @staticmethod
    def listPrinters(printers):

        for i in range(len(printers)):
            logger.info('%s: %s with serial number: %s',str(i),printers[i]['Product'],str(printers[i]['Serial Number']))

        return

    # *************************************************************************
    #                           END Console Interface
    # *************************************************************************


done = False

newestFirmwareVersion = 'MSFT-BEETHEFIRST-10.4.0'
fwFile = 'MSFT-BEETHEFIRST-Firmware-10.4.0.BIN'


def restart_program():
    python = sys.executable
    os.execl(python, python, * sys.argv)


def main(findAll = False):
    finished = False

    console = Console(findAll)

    if console.exit:
        if console.exitState == "restart":
            try:
                console.beeConn.close()
            except Exception as ex:
                logger.error("Error closing connection: %s", str(ex))

            console = None
            restart_program()

    while finished is False:
        var = raw_input(">:")
        # print(var)

        if not var:
            continue

        if "-exit" in var.lower():
            console.beeConn.close()
            console = None
            finished = True

        elif "mode" in var.lower():
            logger.info(console.mode)

        elif "-gcode" in var.lower():
            logger.info("Transfering GCode")
            args = var.split(" ")
            if len(args) > 2:
                console.beeCmd.transferSDFile(args[1],args[2])
            else:
                console.beeCmd.transferSDFile(args[1])
            #while console.beeCmd.getTransferCompletionState() is not None:
            #    time.sleep(0.5)

        elif "-load" in var.lower():
            logger.info("Loading filament")
            console.beeCmd.load()

        elif "-unload" in var.lower():
            logger.info("Unloading filament")
            console.beeCmd.unload()

        elif "-flash" in var.lower():
            logger.info("Flashing Firmware")
            args = var.split(" ")
            console.beeCmd.flashFirmware(args[1])
            while console.beeCmd.getTransferCompletionState() is not None:
                time.sleep(0.5)
        
        elif "-print" in var.lower():
            args = var.split(" ")
            console.beeCmd.printFile(args[1],200)
        elif "-temp" in var.lower():
            logger.info(console.beeCmd.getNozzleTemperature())
            
        elif "-cancel" in var.lower():
            console.beeCmd.cancelTransfer()
        elif "-status" in var.lower():
            logger.info(console.beeCmd.getTransferCompletionState())
        elif "-getcode" in var.lower():
            logger.info(console.beeCmd.getFilamentString())
        elif "-move" in var.lower():
            console.beeCmd.move(x=10,y=10,z=-10)
        #Log Temperatures -logT <filename> <frequency> <nSamples>
        elif "-logt" in var.lower():
            lineSplit = var.split(' ')
            logFileName = lineSplit[1]
            logFile = open(logFileName,'w')
            logFile.write("T;B\n")
            logFile.close()
            logFile = open(logFileName,"a")
            freq = int(lineSplit[2])
            samples = int(lineSplit[3])
            print "Starting loging temperatures {} samples to {} at {} records per second".format(samples,logFileName,freq)
            for i in range(0,samples):
                reply = console.beeCmd.sendCmd("M105\n")
                #reply = reply.replace('\n','')
                if('ok Q:' in reply):
                    #replyLines = reply.split('ok Q:')

                    re1='(T)'	# Any Single Word Character (Not Whitespace) 1
                    re2='.*?'	# Non-greedy match on filler
                    re3='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 1
                    re4='.*?'	# Non-greedy match on filler
                    re5='(B)'	# Any Single Word Character (Not Whitespace) 2
                    re6='.*?'	# Non-greedy match on filler
                    re7='([+-]?\\d*\\.\\d+)(?![-+0-9\\.])'	# Float 2

                    #rg = re.compile(re1+re2+re3+re4+re5+re6+re7+re8+re9,re.IGNORECASE|re.DOTALL)
                    rg = re.compile(re1+re2+re3+re4+re5+re6+re7,re.IGNORECASE|re.DOTALL)
                    #m = rg.search(replyLines[0])
                    m = rg.search(reply)
                    if m:
                        w1=m.group(1)
                        float1=m.group(2)
                        w2=m.group(3)
                        float2=m.group(4)
                        logLine = "{};{}\n".format(float1,float2)
                        logFile.write(logLine)
                        print "T:{}     B:{}\n".format(float1,float2)
                time.sleep(freq)
            logFile.close()
            console.beeCmd.sendCmd("M300\n")
            console.beeCmd.sendCmd("M300\n")


        elif "-verify" in var.lower():
            logger.info("Newest Printer Firmware Available: %s", newestFirmwareVersion)
            currentVersionResp = console.beeCmd.sendCmd('M115', printReply=False)       # Ask Printer Firmware Version

            if newestFirmwareVersion in currentVersionResp:
                logger.info("Printer is already running the latest Firmware")
            else:
                printerModeResp = console.sendCmd('M116', printReply=False)      # Ask Printer Bootloader Version
                if 'Bad M-code' in printerModeResp:                             # Firmware Does not reply to M116 command, Bad M-Code Error
                    logger.info("Printer in Firmware, restarting your Printer to Bootloader")
                    console.beeCmd.sendCmd('M609', printReply=False)                    # Send Restart Command to Firmware
                    time.sleep(2)                                               # Small delay to make sure the board resets and establishes connection
                    # After Reset we must close existing connections and reconnect to the new device
                    while True:
                        try:
                            console.beeConn.close()          # close old connection
                            console = None
                            console = Console()     # search for printer and connect to the first
                            if console.connected is True:   # if connection is established proceed
                                break
                        except:
                            pass

                else:
                    logger.info("Printer is in Bootloader mode")

                console.beeCmd.flashFirmware(fwFile)         # Flash New Firmware
                #newFwCmd = 'M114 A' + newestFirmwareVersion  # prepare command string to set Firmware String
                #console.beeCmd.sendCmd(newFwCmd, printReply=False)  # Record New FW String in Bootloader
            # console.FlashFirmware(var)
        else:
            if "m630" in var.lower():
                console.beeCmd.goToFirmware()
                if 'Shutdown' in console.beeCmd.getStatus():
                    logger.info('Printer recovering from shutdown. Choose action:\n')
                    logger.info('0: Resume print\n')
                    logger.info('1: Cancel print\n')
                    i = int(raw_input(">:"))
                    if i == 0:
                        console.beeCmd.resumePrint()
                    elif i == 1:
                        console.beeCmd.clearShutdownFlag()
            elif "m609" in var.lower():
                console.beeCmd.goToBootloader()
            else:
                logger.info(console.beeCmd.sendCmd(var))
                

if __name__ == "__main__":

    findAll = False;

    for arg in sys.argv:
        re1='(findall)'	# Word 1
        re2='.*?'	# Non-greedy match on filler
        re3='(true)'	# Variable Name 1
        rg = re.compile(re1+re2+re3,re.IGNORECASE|re.DOTALL)
        m = rg.search(arg.lower())
        if m:
            word1=m.group(1)
            var1=m.group(2)
            if word1 == "findall" and var1 == "true":
                findAll = True
                print "Search all printers enabled\n"

    main(findAll)
