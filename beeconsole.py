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
import math
import re
from beedriver import connection
from utils import gcoder
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

        * "-flash LOCALFILE_PATH" Flash firmware.

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
                if self.beeConn.isConnected() is True:

                    self.beeCmd = self.beeConn.getCommandIntf()

                    resp = self.beeConn.sendCmd("M625\n")

                    if 'Bad M-code 625' in resp:   # printer in bootloader mode
                        logger.info("Printer running in Bootloader Mode")
                        self.mode = "bootloader"
                        self.connected = True
                    elif 'ok Q' in resp:
                        logger.info("Printer running in firmware mode")
                        self.mode = "firmware"
                        self.connected = True
                    else:
                        cmdStr = "M625\n;" + "a"*507
                        tries = 32
                        logger.info("Cleaning buffer")

                        resp = self.beeCmd.cleanBuffer()

                        if resp == 0:
                            logger.warning("Error connecting to printer... Restarting application")
                            self.beeConn.close()
                            self.beeConn = None
                            self.exit = True
                            self.exitState = "restart"
                            return

                        """
                        while(tries > 0):
                            try:
                                resp = self.beeConn.sendCmd(cmdStr,None,50)
                            except:
                                pass
                            tries -= 1
                        """
                        self.beeConn.close()
                        self.beeConn = None
                        # return None

                nextPullTime = time.time() + 1

        return

    # *************************************************************************
    #                            goToFirmware Method
    # *************************************************************************
    def goToFirmware(self):

        self.connected = False
        self.exit = False

        self.beeConn.close()
        self.beeConn = None

        self.beeCmd = None

        nextPullTime = time.time() + 0.1

        while (not self.connected) and (not self.exit):

            t = time.time()
            if t > nextPullTime:

                self.beeConn = connection.Conn()
                if self.beeConn.isConnected() is True:

                    self.beeCmd = self.beeConn.getCommandIntf()

                    resp = self.beeCmd.startPrinter()

                    if 'Firmware' in resp:
                        self.connected = self.beeConn.connected
                        self.mode = "firmware"
                        return

                    elif 'Bootloader' in resp:
                        self.beeConn = None

                nextPullTime = time.time() + 0.1
                logger.info("Waiting for connection...")

        return

    # *************************************************************************
    #                            close Method
    # *************************************************************************
    def close(self):

        self.beeConn.close()

        logger.info("Connection closed.")

        return

    # *************************************************************************
    #                            sendCmd Method
    # *************************************************************************
    def sendCmd(self, cmd, printReply=True):

        cmdStr = cmd + "\n"

        wait = None
        if "g" in cmd.lower():
            wait = "3"

        resp = self.beeConn.sendCmd(cmdStr, wait)

        if printReply is False:
            return resp

        splits = resp.rstrip().split("\n")

        for r in splits:
            print r

        return resp

    # *************************************************************************
    #                            load Method
    # *************************************************************************
    def load(self):

        self.beeCmd.Load()

        return

    # *************************************************************************
    #                            unload Method
    # *************************************************************************
    def unload(self):

        self.beeCmd.Unload()

        return

    # *************************************************************************
    #                            transferGCodeWithColor Method
    # *************************************************************************
    def transferGCodeWithColor(self, cmd):

        localFN = None
        sdFN = None
        color = None

        fields = cmd.split(" ")

        if len(fields) < 4:
            logger.info("transferGCodeWithColor: Insufficient fields")
            return
        elif len(fields) == 4:
            localFN = fields[2]
            sdFN = localFN
            color = fields[3]
        elif len(fields) == 5:
            localFN = fields[2]
            sdFN = fields[3]
            color = fields[4]

        if os.path.isfile(localFN) is False:
            logger.info("transferGCodeWithColor: G-code File does not exist")
            return

        colorCode = "W1"
        if "black" in color.lower():
            colorCode = "W1"

        header = "M300\nG28\nM206 X500\nM107\nM104 S220\nG92 E\nM642 "
        header += str(colorCode) + "\nM130 T6 U1.3 V80\nG1 X-98.0 Y-20.0 Z5.0 F3000\n"
        header += "G1 Y-68.0 Z0.3\nG1 X-98.0 Y0.0 F500 E20\nG92 E\n"

        footer = "M300\nM104 S0\nG28 X\nG28 Z\nG1 Y65\nG92 E\n"

        f = open(localFN, 'r')

        localFile = f.read()
        f.close()

        fw = open(localFN, 'w')

        fw.write(header)
        fw.write(localFile)
        fw.write(footer)

        fw.close()

        self.transferGFile(localFN, sdFN)

        return

    # *************************************************************************
    #                            transferGCode Method
    # *************************************************************************
    def transferGCode(self, cmd):

        localFN = None
        sdFN = None
        estimate = False

        fields = cmd.split(" ")

        if len(fields) < 2:
            logger.info("transferGCode: Insufficient fields")
            return
        elif len(fields) == 2:
            localFN = fields[1]
            sdFN = localFN
        elif len(fields) == 3:
            localFN = fields[1]
            if '-e' in cmd:
                estimate = True

        # check if file exists
        if os.path.isfile(localFN) is False:
            logger.info("transferGCode: File does not exist")
            return

        # REMOVE SPECIAL CHARS
        sdFN = re.sub('[\W_]+', '', sdFN)

        # CHECK FILENAME
        if len(sdFN) > 8:
            sdFN = sdFN[:7]

        firstChar = sdFN[0]

        if firstChar.isdigit():
            nameChars = list(sdFN)
            nameChars[0] = 'a'
            sdFN = "".join(nameChars)

        # ADD ESTIMATOR HEADER
        if sys.platform.system() != 'Windows' and estimate:
            gc = gcoder.GCode(open(localFN, 'rU'))

            est = gc.estimate_duration()
            eCmd = 'M300\n'                 # Beep
            eCmd += 'M31 A' + str(est['seconds']//60) + ' L' + str(est['lines']) + '\n' # Estimator command
            eCmd += 'M32 A0\n'      # Clear time counter

            newFile = open('gFile.gcode','w')
            newFile.write(eCmd)
            newFile.close()

            os.system("cat '" + localFN + "' >> " + "gFile.gcode")

            self.transferGFile('gFile.gcode', sdFN)
        else:
            self.transferGFile(localFN, sdFN)

        return

    # *************************************************************************
    #                            estimateTime Method
    # *************************************************************************
    @staticmethod
    def estimateTime(cmd):

        localFN = None

        fields = cmd.split(" ")

        if len(fields) < 2:
            logger.error("estimateTime: Insufficient fields")
            return
        elif len(fields) == 2:
            localFN = fields[1]
        elif len(fields) == 3:
            localFN = fields[1]

        estimator = gcoder.GCode(open(localFN, "rU"))
        est = estimator.estimate_duration()
        nLines = est['lines']
        minTime = est['seconds']//60

        logger.info('Number of GCode Lines: %d', nLines)
        logger.info("Estimated Time: %d min", minTime)

        return

    # *************************************************************************
    #                            transferGCode Method
    # *************************************************************************
    def transferGFile(self, localFN, sdFN):

        # Load File
        logger.info("transferGFile: Loading File...")
        f = open(localFN, 'rb')
        fSize = os.path.getsize(localFN)
        logger.info("File Size: %d bytes", fSize)

        blockBytes = self.beeCmd.MESSAGE_SIZE * self.beeCmd.BLOCK_SIZE
        nBlocks = math.ceil(fSize/blockBytes)
        logger.info("Number of Blocks: %d", nBlocks)

        # TODO RUN ESTIMATOR

        # CREATE SD FILE
        resp = self.beeCmd.CraeteFile(sdFN)
        if not resp:
            return

        # Start transfer
        blocksTransferred = 0
        totalBytes = 0

        startTime = time.time()

        # Load local file
        with open(localFN, 'rb') as f:

            self.beeCmd.transmissionErrors = 0

            while blocksTransferred < nBlocks:

                startPos = totalBytes
                endPos = totalBytes + blockBytes

                bytes2write = endPos - startPos

                if blocksTransferred == (nBlocks-1):
                    endPos = fSize

                blockTransferred = False
                while blockTransferred is False:
                    
                    blockTransferred = self.beeCmd.sendBlock(startPos, f)
                    if blockTransferred is None:
                        logger.info("transferGFile: Transfer aborted")
                        return False

                totalBytes += bytes2write
                blocksTransferred += 1
                logger.info("transferGFile: Transferred %s / %s blocks %d / %d bytes",
                            str(blocksTransferred), str(nBlocks), totalBytes, fSize)

        logger.info("transferGFile: Transfer completed", ". Errors Resolved: ", self.beeCmd.transmissionErrors)

        elapsedTime = time.time() - startTime
        avgSpeed = fSize//elapsedTime
        logger.info("transferGFile: Elapsed time: %d seconds", elapsedTime)
        logger.info("transferGFile: Average Transfer Speed: %.2f bytes/second", avgSpeed)

        return

    # *************************************************************************
    #                            flashFirmware Method
    # *************************************************************************
    def flashFirmware(self, cmd):

        split = cmd.split(' ')

        fileName = ''
        try:
            fileName = split[1]
        except Exception, ex:
            logger.error("flashFirmware: Flash firmware error - invalid filename in command %s", cmd)

        if "'" in fileName:
            fields = fileName.split("'")
            fileName = fields[1]

        self.beeCmd.flashFirmware(fileName)

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
            console.close()
            console = None
            finished = True

        elif "mode" in var.lower():
            logger.info(console.mode)

        elif "-gcode" in var.lower() and console.mode == "firmware":
            logger.info("Starting gcode transfer...")

            if "-gcode -c" in var.lower() and console.mode == "firmware":
                logger.info("Editing gCode...")
                console.transferGCodeWithColor(var)
            else:
                console.transferGCode(var)

        elif "-load" in var.lower():
            logger.info("Loading filament")
            console.load()

        elif "-unload" in var.lower():
            logger.info("Unloading filament")
            console.unload()

        elif "-estimate" in var.lower():
            logger.info("Estimating time")
            console.estimateTime(var)

        elif "-flash" in var.lower():
            logger.info("Flashing Firmware")
            console.FlashFirmware(var)

        elif "-verify" in var.lower():
            logger.info("Newest Printer Firmware Available: %s", newestFirmwareVersion)
            currentVersionResp = console.sendCmd('M115', printReply=False)       # Ask Printer Firmware Version

            if newestFirmwareVersion in currentVersionResp:
                logger.info("Printer is already running the latest firmware")
            else:
                printerModeResp = console.sendCmd('M116', printReply=False)      # Ask Printer Bootloader Version
                if 'Bad M-code' in printerModeResp:                             # Firmware Does not reply to M116 command, Bad M-Code Error
                    logger.info("Printer in Firmware, restarting your Printer to Bootloader")
                    console.sendCmd('M609', printReply=False)                    # Send Restart Command to Firmware
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

                console.beeCmd.FlashFirmware(fwFile)         # Flash New Firmware
                newFwCmd = 'M114 A' + newestFirmwareVersion  # prepare command string to set Firmware String
                console.sendCmd(newFwCmd, printReply=False)  # Record New FW String in Bootloader
            # console.FlashFirmware(var)
        else:
            if ("m630" in var.lower() and console.mode == "bootloader") \
                    or ("m609" in var.lower() and console.mode == "firmware"):

                logger.info("Changing to firmware/bootloader")
                # console.goToFirmware()
                console.sendCmd(var)
                try:
                    console.beeConn.close()
                except:
                    pass
                console = None
                time.sleep(1)
                restart_program()
            else:
                console.sendCmd(var)


if __name__ == "__main__":
    main()
