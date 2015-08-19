import threading
import time
from beedriver import logger
import os
import usb
import sys
import math

class FileTransferThread(threading.Thread):
    
    transfering = False
    fileSize = 0
    bytesTransferred = 0
    filePath = None
    transferType = None
    optionalString = None
    
    cancelTransfer = False
    
    MESSAGE_SIZE = 512
    BLOCK_SIZE = 64
    
    beeCon = None
    
    # *************************************************************************
    #                        __init__ Method
    # *************************************************************************
    def __init__(self, connection, filePath, transferType, optionalString = None):
        
        super(FileTransferThread, self).__init__()
        
        self.beeCon = connection
        self.filePath = filePath
        self.transferType = transferType
        self.optionalString = optionalString
        self.cancelTransfer = False
        
        self.fileSize = os.path.getsize(filePath)                         # Get Firmware size in bytes
        
        return
    
    def run(self):
        
        super(FileTransferThread, self).run()
        
        if self.transferType.lower() == 'firmware':
            self.transfering = True
            logger.info('Starting Firmware Transfer')
            self.TransferFirmwareFile()
            #Update Firmware String
            self.beeCon.SendCmd('M114 A%s' %self.optionalString,'ok')
            self.transfering = False
        
        elif self.transferType.lower() == 'gcode':
            self.transfering = True
            logger.info('Starting GCode Transfer')
            self.MultiBlockFileTransfer()
            self.transfering = False
        else:
            logger.info('Unknown Transfer Type')
        
        
        
        logger.info('Exiting transfer thread')
        
        return
    # *************************************************************************
    #                        GetTransferCompletionState Method
    # *************************************************************************
    def GetTransferCompletionState(self):
        
        if self.fileSize > 0:
            percent = (100 * self.bytesTransferred / self.fileSize)
            return "%.2f" %percent
        else:
            return None

    
    # *************************************************************************
    #                        CancelFileTransfer Method
    # *************************************************************************
    def CancelFileTransfer(self):
        
        self.cancelTransfer = True
        
        return True
    
    # *************************************************************************
    #                        TransferFirmwareFile Method
    # *************************************************************************
    def TransferFirmwareFile(self):
        
        cTime = time.time()                                         # Get current time

        message = "M650 A" + str(self.fileSize) + "\n"                      # Prepare Start Transfer Command string
        self.beeCon.Write(message)                                         # Send Start Transfer Command

        # Before continue wait for the reply from the Start Command transfer
        resp = ''
        while 'ok' not in resp:                                    # Once the printer is ready it replies 'ok'
            resp += self.beeCon.Read()

        resp = ''
        with open(self.filePath, 'rb') as f:                             # Open file to start transfer

            while True:                                             # while loop
                buf = f.read(64)                                    # Read 64 bytes from file

                if not buf:
                    break                                   # if nothing left to read, transfer finished

                bytesWriten = self.beeCon.Write(buf)                              # Send 64 bytes to the printer

                time.sleep(0.0000001)                               # Small delay helps remove sporadic errors

                # The printer will forward the received data
                # we then collect the received data and compare it to identify transfer errors
                ret = []
                while len(ret) != len(buf):                        # wait for the 64 bytes to be received
                    try:
                        ret += self.beeCon.ep_in.read(len(buf), 1000)
                    except usb.core.USBError as e:
                        if "timed out" in str(e.args):
                            pass

                bRet = bytearray(ret)                                   # convert the received data to bytes
                if not bRet == buf:                                 # Compare the data received with data sent
                                                                    # If data received/sent are different cancel transfer and reset the printer manually
                    logger.error('Firmware Flash error, please reset the printer')
                    return

                #sys.stdout.write('.')                               # print dot to console
                #sys.stdout.flush()                                  # used only to provide a simple indication as the process in running
                self.bytesTransferred += len(buf)

        eTime = time.time()

        avgSpeed = self.fileSize//(eTime - cTime)

        logger.info("Flashing completed in %d seconds", eTime-cTime)
        logger.info("Average Transfer Speed %.2f bytes/second", avgSpeed)
        
        self.bytesTransferred = 0
        self.fileSize = 0
        
        return True
    
    # *************************************************************************
    #                        MultiBlockFileTransfer Method
    # *************************************************************************
    def MultiBlockFileTransfer(self):
        
        #Get commands interface
        beeCmd = self.beeCon.getCommandIntf()
        
        #Create File
        beeCmd.InitSD()
        sdFileName = "ABCDE"
        
        #If a different SD Filename is provided 
        if self.optionalString is not None:
            sdFileName = self.optionalString
            # REMOVE SPECIAL CHARS
            sdFileName = re.sub('[\W_]+', '', sdFileName)
    
            # CHECK FILENAME
            if len(sdFileName) > 8:
                sdFileName = sdFileName[:7]
    
            firstChar = sdFileName[0]
    
            if firstChar.isdigit():
                nameChars = list(sdFileName)
                nameChars[0] = 'a'
                sdFileName = "".join(nameChars)
                
        #Get Number of blocks to transfer
        blockBytes = beeCmd.MESSAGE_SIZE * beeCmd.BLOCK_SIZE
        nBlocks = int(math.ceil(self.fileSize/blockBytes))
        logger.info("Number of Blocks: %d", nBlocks)
        
        # CREATE SD FILE
        resp = beeCmd.CreateFile(sdFileName)
        if not resp:
            return

        # Start transfer
        blocksTransferred = 0
        self.bytesTransferred = 0

        startTime = time.time()

        # Load local file
        with open(self.filePath, 'rb') as f:

            beeCmd.transmissionErrors = 0

            while blocksTransferred < nBlocks and not self.cancelTransfer:
                
                startPos = self.bytesTransferred
                endPos = self.bytesTransferred + blockBytes

                bytes2write = endPos - startPos

                if blocksTransferred == (nBlocks-1):
                    endPos = self.fileSize

                blockTransferred = False
                while blockTransferred is False:
                    
                    blockTransferred = self.SendBlock(startPos, f)
                    if blockTransferred is None:
                        logger.info("transferGFile: Transfer aborted")
                        return False

                self.bytesTransferred += bytes2write
                blocksTransferred += 1
                #logger.info("transferGFile: Transferred %s / %s blocks %d / %d bytes",
                #            str(blocksTransferred), str(nBlocks), endPos, self.fileSize)
                
        if self.cancelTransfer:
            logger.info('MultiBlockFileTransfer: File Transfer canceled')
            logger.info('MultiBlockFileTransfer: %s / %s bytes transferred',str(self.bytesTransferred),str(self.fileSize))
            return        

        logger.info("MultiBlockFileTransfer: Transfer completed. Errors Resolved: %s", str(beeCmd.transmissionErrors))

        elapsedTime = time.time() - startTime
        avgSpeed = self.fileSize//elapsedTime
        logger.info("MultiBlockFileTransfer: Elapsed time: %d seconds", elapsedTime)
        logger.info("MultiBlockFileTransfer: Average Transfer Speed: %.2f bytes/second", avgSpeed)
        
        return
    
    # *************************************************************************
    #                        SendBlock Method
    # *************************************************************************
    def SendBlock(self, startPos, fileObj):
        r"""
        SendBlock method

        writes a block of messages

        arguments:
            startPos - starting position of block
            fileObj - file object with file to write

        returns:
            True if block transfered successfully
            False if an error occurred and communication was reestablished
            None if an error occurred and could not reestablish communication with printer
        """

        fileObj.seek(startPos)
        block2write = fileObj.read(self.MESSAGE_SIZE*self.BLOCK_SIZE)

        endPos = startPos + len(block2write)

        #self.StartTransfer(endPos,startPos)
        self.beeCon.Write("M28 D" + str(endPos - 1) + " A" + str(startPos) + "\n")

        nMsg = int(math.ceil(len(block2write)/self.MESSAGE_SIZE))
        msgBuf = []
        for i in range(nMsg):
            if i < nMsg:
                msgBuf.append(block2write[i*self.MESSAGE_SIZE:(i+1)*self.MESSAGE_SIZE])
            else:
                msgBuf.append(block2write[i*self.MESSAGE_SIZE:])

        resp = self.beeCon.Read()
        while "ok q:0" not in resp.lower():
            resp += self.beeCon.Read()
        #print(resp)
        #resp = self.beeCon.Read(10) #force clear buffer

        for m in msgBuf:
            mResp = self.sendBlockMsg(m)
            if mResp is not True:
                return mResp

        return True

    # *************************************************************************
    #                        sendBlockMsg Method
    # *************************************************************************
    def sendBlockMsg(self, msg):
        r"""
        sendBlockMsg method

        sends a block message to the printer.

        arguments:
            msg - message to be writen

        returns:
            True if message transferred successfully
            False if an error occurred and communication was reestablished
            None if an error occurred and could not reestablish communication with printer
        """

        #resp = self.beeCon.dispatch(msg)
        msgLen = len(msg)
        bWriten = self.beeCon.Write(msg)
        if msgLen != bWriten:
            logger.info("Bytes lost")
            return False

        time.sleep(0.001)

        tries = 10
        resp = ""
        while (tries > 0) and ("tog" not in resp):
            try:
                resp += self.beeCon.Read()
                tries -= 1
            except Exception, ex:
                logger.error(str(ex))
                tries = -1

        if tries > 0:
            return True
        else:
            cleaningTries = 5
            clean = False
            self.transmissionErrors += 1
            while cleaningTries > 0 and clean is False:
                clean = self.cleanBuffer()
                time.sleep(0.5)
                self.beeCon.reconnect()

                cleaningTries -= 1

            if cleaningTries <= 0:
                return None

            if clean is False:
                return None

            return False