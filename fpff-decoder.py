import binascii
from enum import Enum
from PIL import Image
import io
import time
import struct

class FileType(Enum):
    ASCII = 1
    UTF8 = 2
    WORDS = 3
    DWORDS = 4
    DOUBLES = 5
    COORD = 6
    REF = 7
    PNG = 8
    GIF87 = 9
    GIF89 = 10

class FPFF():
    @staticmethod
    def reverse_bytearray(s):
        rev = bytearray()
        for i in range(len(s)-1, -1, -1):
            rev.append(s[i])
        return rev

    @staticmethod
    def remove_padding(data):
        while data[0] == 0:
            data.pop(0)
        return data
    @staticmethod
    def add_padding(data, l):

        if len(data) > l:
            raise ValueError("Data too large to be padded!")
        
        while len(data) < l:
            data.insert(0, 0)
        return data
    
    def __init__(self, file=None, author=None):
        self.version = 1
        self.timestamp = None
        self.author = None
        self.sections = 0
        self.stypes = list()
        self.svalues = list()

        if file != None:
            self.read(file)

    def read(self, file):
        with open(file, "rb") as f:
            data = bytearray(f.read())

        magic            = FPFF.reverse_bytearray(data[0:4])
        self.version     = int.from_bytes(data[4:8], "little")
        self.timestamp   = int.from_bytes(data[8:12], "little")
        self.author      = FPFF.remove_padding(FPFF.reverse_bytearray(data[12:20])).decode('ascii')
        self.sect_num    = int.from_bytes(data[20:24], "little")

        # checks
        if magic != b'\xbe\xfe\xda\xde':
            print("Wrong header")
            return
        if self.version != 1:
            print("Not version 1")
            return

        # read sections
        count = 24
        for i in range(self.sect_num):
            stype = int.from_bytes(data[count:count+4], "little")
            slen =  int.from_bytes(data[count+4:count+8], "little")
            count += 8
            svalue = data[count:count+slen]

            # ascii
            if stype == 1:
                self.stypes.append(FileType.ASCII)
                self.svalues.append(svalue.decode('ascii'))
            # utf-8
            elif stype == 2:
                self.stypes.append(FileType.UTF8)
                self.svalues.append(svalue.decode('utf8'))
            # words
            elif stype == 3:
                self.stypes.append(FileType.WORDS)
                self.svalues.append([bytes(svalue[j:j+4]) for j in range(0, slen, 4)])
            # dwords
            elif stype == 4:
                self.stypes.append(FileType.DWORDS)
                self.svalues.append([bytes(svalue[j:j+8]) for j in range(0, slen, 8)])
            # doubles
            elif stype == 5:
                self.stypes.append(FileType.DOUBLES)
                self.svalues.append([int.from_bytes(svalue[j:j+8], "big") for j in range(0, slen, 8)])
            # coord
            elif stype == 6:
                self.stypes.append(FileType.COORD)
                self.svalues.append( (int.from_bytes(svalue[0:8],"big"), int.from_bytes(svalue[8:16],"big")) )
            # ref
            elif stype == 7:
                self.stypes.append(FileType.REF)
                self.svalues.append(int.from_bytes(svalue[0:4], "big"))
            # png
            elif stype == 8:
                self.stypes.append(FileType.PNG)
                sig = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'
                out = sig + svalue[0:slen]
                self.svalues.append(out)
            #gif87a
            elif stype == 9:
                self.stypes.append(FileType.GIF87)                
                sig = b'\x47\x49\x46\x38\x37\x61'
                out = sig + svalue[0:slen]
                self.svalues.append(out)
            #gif89a
            elif stype == 10:
                self.stypes.append(FileType.GIF89)                
                sig = b'\x47\x49\x46\x38\x39\x61'
                out = sig + svalue[0:slen]
                self.svalues.append(out)
            
            count += slen
            
        print("done")

    # assume data stored big endian
    def write(self, file):
        # convert to bytes
        w_magic       = bytearray(b'\xDE\xDA\xFE\xBE')
        w_version     = FPFF.reverse_bytearray(FPFF.add_padding(struct.pack(">I", self.version), 4))
        w_timestamp   = FPFF.reverse_bytearray(FPFF.add_padding(struct.pack(">I", int(time.time())), 4))
        w_author      = FPFF.reverse_bytearray(FPFF.add_padding(bytearray(self.author, 'ascii'), 8))
        w_sect_num    = FPFF.reverse_bytearray(FPFF.add_padding(struct.pack(">I", self.sect_num), 4))
        w_sections  = list()
        for i in range(self.sect_num):
            
            w_svalue = None

            if self.stypes[i] == FileType.ASCII:
                w_svalue = bytearray(self.svalues[i], 'ascii')
            elif self.stypes[i] == FileType.UTF8:
                w_svalue = bytearray(self.svalues[i], 'utf8')
            elif self.stypes[i] == FileType.WORDS:
                w_svalue = b''.join(self.svalues[i])
            elif self.stypes[i] == FileType.DWORDS:
                w_svalue = b''.join(self.svalues[i])
            elif self.stypes[i] == FileType.DOUBLES:
                w_svalue = bytearray()
                for b in self.svalues[i]:
                    w_svalue.extend(FPFF.add_padding(bytearray.fromhex(hex(b)[2:]), 8))
            elif self.stypes[i] == FileType.COORD:
                w_svalue = bytearray()
                w_svalue.extend(FPFF.add_padding(bytearray.fromhex(hex(self.svalues[i][0])[2:]), 8))
                w_svalue.extend(FPFF.add_padding(bytearray.fromhex(hex(self.svalues[i][1])[2:]), 8))
            elif self.stypes[i] == FileType.REF:
                w_svalue = FPFF.add_padding(bytearray.fromhex(hex(self.svalues[i])[2:]), 4)
            elif self.stypes[i] == FileType.PNG:
                w_svalue = bytearray(self.svalues[i])
                del w_svalue[:8]
            elif self.stypes[i] == FileType.GIF87:
                w_svalue = bytearray(self.svalues[i])
                del w_svalue[:6]
            elif self.stypes[i] == FileType.GIF89:
                w_svalue = bytearray(self.svalues[i])
                del w_svalue[:6]

            w_slen = len(w_svalue)
            w_section = bytearray()
            w_section.extend(FPFF.reverse_bytearray(FPFF.add_padding(struct.pack(">I", int(self.stypes[i].value)), 4)))
            w_section.extend(FPFF.reverse_bytearray(FPFF.add_padding(struct.pack(">I", w_slen), 4)))
            w_section.extend(w_svalue)

            w_sections.extend(w_section)

        # construct and write
        out_data = bytearray()
        out_data.extend(w_magic)
        out_data.extend(w_version)
        out_data.extend(w_timestamp)
        out_data.extend(w_author)
        out_data.extend(w_sect_num)
        out_data.extend(w_sections)
        with open(file, 'wb') as f:
            f.write(bytes(out_data))
            f.close()

    def __repr__(self):
        return str(self.stypes)

s = FPFF("hi")
#s.write('hi')
"""
out_name = file.split(".")[0]+"-"+str(i+1)
"""
