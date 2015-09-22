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
    def __init__(self):

        self.connected = False
        self.exit = False
        self.exitState = None

        nextPullTime = time.time() + 1

        logger.info("Waiting for printer connection...")

        while (not self.connected) and (not self.exit):

            t = time.time()

            if t > nextPullTime:

                self.beeConn = connection.Conn()
                # Connect to first Printer
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

newestFirmwareVersion = 'MSFT-BEETHEFIRST-10.1.0'
fwFile = 'MSFT-BEETHEFIRST-Firmware-10.1.0.BIN'


def restart_program():
    python = sys.executable
    os.execl(python, python, * sys.argv)


def main():
    finished = False

    console = Console()

    if console.exit:
        if console.exitState == "restart":
            try:
                console.beeConn.close()
            except Exception, ex:
                logger.error("Error closing connection: %s", str(ex))

            console = None
            restart_program()

    while finished is False:
        var = raw_input(">:")
        # print(var)

        if not var:
            continue

        if "-exit" in var.lower():
            console.beeCmd.beeCon.close()
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
            while console.beeCmd.getTransferCompletionState() is not None:
                time.sleep(0.5)

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
            
        elif "-cancel" in var.lower():
            console.beeCmd.cancelTransfer()
        elif "-status" in var.lower():
            logger.info(console.beeCmd.getTransferCompletionState())
        elif "-getcode" in var.lower():
            logger.info(console.beeCmd.getFilamentString())
        elif "-move" in var.lower():
            console.beeCmd.move(x=10,y=10,z=-10)

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
    main()
