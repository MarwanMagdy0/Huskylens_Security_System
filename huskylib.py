# HuskyLens Python Library
# Author: Robert Prast (robert@dfrobot.com)
# 08/03/2020
# Dependenices :
#   pyserial
#   smbus
#   pypng
#
# How to use :
# 1) First import the library into your project and connect your HuskyLens
# 2) Init huskylens
#   A) Serial
#          huskyLens = HuskyLensLibrary("SERIAL","COM_PORT", speed) *speed is integer
#   B) I2C
#           huskyLens = HuskyLensLibrary("I2C","", address=0xADDR) *address is hex integer
# 3) Call your desired functions on the huskyLens object!
###
# Example code
'''
huskyLens = HuskyLensLibrary("I2C","",address=0x32)
huskyLens.algorthim("ALGORITHM_FACE_RECOGNITION")
while(true):
    data=huskyLens.blocks()
    x=0
    for i in data:
        x=x+1
        print("Face {} data: {}".format(x,i)
'''


import time
import serial
import png
import json


commandHeaderAndAddress = "55AA11"
algorthimsByteID = {
    "ALGORITHM_OBJECT_TRACKING": "0100",
    "ALGORITHM_FACE_RECOGNITION": "0000",
    "ALGORITHM_OBJECT_RECOGNITION": "0200",
    "ALGORITHM_LINE_TRACKING": "0300",
    "ALGORITHM_COLOR_RECOGNITION": "0400",
    "ALGORITHM_TAG_RECOGNITION": "0500",
    "ALGORITHM_OBJECT_CLASSIFICATION": "0600",
    "ALGORITHM_QR_CODE_RECOGNTITION" : "0700",
    "ALGORITHM_BARCODE_RECOGNTITION":"0800",
}

class Arrow:
    def __init__(self, xTail, yTail , xHead , yHead, ID):
        self.xTail=xTail
        self.yTail=yTail
        self.xHead=xHead
        self.yHead=yHead
        self.ID=ID
        self.learned= True if ID > 0 else False
        self.type="ARROW"


class Block:
    def __init__(self, x, y , width , height, ID):
        self.x = x
        self.y=y
        self.width=width
        self.height=height
        self.ID=ID
        self.learned= True if ID > 0 else False
        self.type="BLOCK"



class HuskyLensLibrary:
    def __init__(self, proto, comPort="", speed=3000000, channel=1, address=0x32):
        self.proto = proto
        self.address = address
        self.checkOnceAgain=True
        import smbus2 as smbus
        self.huskylensSer = smbus.SMBus(channel)
        self.lastCmdSent = ""

    def writeToHuskyLens(self, cmd):
        self.huskylensSer.write_i2c_block_data(self.address, 12, list(cmd))

    def calculateChecksum(self, hexStr):
        total = 0
        for i in range(0, len(hexStr), 2):
            total += int(hexStr[i:i+2], 16)
        hexStr = hex(total)[-2:]
        return hexStr

    def cmdToBytes(self, cmd):
        return bytes.fromhex(cmd)

    def splitCommandToParts(self, str):
        #print(f"We got this str=> {str}")
        headers = str[0:4]
        address = str[4:6]
        data_length = int(str[6:8], 16)
        command = str[8:10]
        if(data_length > 0):
            data = str[10:10+data_length*2]
        else:
            data = []
        checkSum = str[2*(6+data_length-1):2*(6+data_length-1)+2]

        return [headers, address, data_length, command, data, checkSum]

    def getBlockOrArrowCommand(self):
        byteString = b''
        for i in range(5):
            byteString += bytes([(self.huskylensSer.read_byte(self.address))])
        for i in range(int(byteString[3])+1):
            byteString += bytes([(self.huskylensSer.read_byte(self.address))])

        commandSplit = self.splitCommandToParts(byteString.hex())
        isBlock = True if commandSplit[3] == "2a" else False
        return (commandSplit[4],isBlock)

    def processReturnData(self, numIdLearnFlag=False, frameFlag=False):
        byteString=""
        byteString = b''
        for i in range(5):
            byteString += bytes([(self.huskylensSer.read_byte(self.address))])
        for i in range(int(byteString[3])+1):
            byteString += bytes([(self.huskylensSer.read_byte(self.address))])
        commandSplit = self.splitCommandToParts(byteString.hex())
        #print(commandSplit)
        if(commandSplit[3] == "2e"):
            self.checkOnceAgain=True
            return "Knock Recieved"
        else:
            returnData = []
            numberOfBlocksOrArrow = int(
                commandSplit[4][2:4]+commandSplit[4][0:2], 16)
            for i in range(numberOfBlocksOrArrow):
                tmpObj=self.getBlockOrArrowCommand()
                isBlock=tmpObj[1]
                returnData.append(tmpObj[0])

            finalData = []
            tmp = []
            for i in returnData:
                tmp = []
                for q in range(0, len(i), 4):
                    low=int(i[q:q+2], 16)
                    high=int(i[q+2:q+4], 16)
                    if(high>0):
                        val=low+255+high
                    else:
                        val=low
                    tmp.append(val)
                finalData.append(tmp)
                tmp = []
            self.checkOnceAgain=True
            return finalData


    def knock(self):
        cmd = self.cmdToBytes(commandHeaderAndAddress+"002c3c")
        self.writeToHuskyLens(cmd)
        return self.processReturnData()

    def forget(self):
        cmd = self.cmdToBytes(commandHeaderAndAddress+"003747")
        self.writeToHuskyLens(cmd)
        return self.processReturnData()

    def setCustomName(self,name,idV):
        nameDataSize = "{:02x}".format(len(name)+1)
        name = name.encode("utf-8").hex()+"00"
        localId = "{:02x}".format(idV)
        data = localId+nameDataSize+name
        dataLen = "{:02x}".format(len(data)//2)
        cmd = commandHeaderAndAddress+dataLen+"2f"+data
        cmd += self.calculateChecksum(cmd)
        cmd = self.cmdToBytes(cmd)
        self.writeToHuskyLens(cmd)

    def blocks(self):
        try:
            cmd = self.cmdToBytes(commandHeaderAndAddress+"002131")
            self.writeToHuskyLens(cmd)
            return self.processReturnData()
        except:
            return []

    def algorthim(self, alg):
        if alg in algorthimsByteID:
            cmd = commandHeaderAndAddress+"022d"+algorthimsByteID[alg]
            cmd += self.calculateChecksum(cmd)
            cmd = self.cmdToBytes(cmd)
            self.writeToHuskyLens(cmd)
        else:
            print("INCORRECT ALGORITHIM NAME")