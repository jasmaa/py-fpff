from enum import Enum
import time
import struct
import os
import shutil


class FileType(Enum):
    """FPFF file types
    """
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
    """Handles read, write, and export for FPFF.
    """

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
            raise OverflowError("Data too large to be padded!")

        while len(data) < l:
            data.insert(0, 0)
        return data

    def __init__(self, file=None, author=None):
        self.version = 1
        self.timestamp = None
        self.author = None
        self.sect_num = 0
        self.stypes = list()
        self.svalues = list()

        if file != None:
            self.read(file)

    def read(self, file):
        """Reads in FPFF.
        """
        with open(file, "rb") as f:
            data = bytearray(f.read())

        magic = FPFF.reverse_bytearray(data[0:4])
        self.version = int.from_bytes(data[4:8], "little")
        self.timestamp = int.from_bytes(data[8:12], "little")
        self.author = FPFF.remove_padding(
            FPFF.reverse_bytearray(data[12:20])).decode('ascii')
        self.sect_num = int.from_bytes(data[20:24], "little")
        self.stypes = list()
        self.svalues = list()

        # checks
        if magic != b'\xbe\xfe\xda\xde':
            raise ValueError("Not a valid FPFF stream.")
        if self.version != 1:
            raise ValueError(
                "Unsupported version. Only version 1 is supported.")
        if self.sect_num <= 0:
            raise ValueError("Section length must be greater than 0.")

        # read sections
        count = 24
        for i in range(self.sect_num):
            stype = int.from_bytes(data[count:count+4], "little")
            slen = int.from_bytes(data[count+4:count+8], "little")
            count += 8
            svalue = data[count:count+slen]

            if stype == 1:
                # ASCII
                self.stypes.append(FileType.ASCII)
                self.svalues.append(svalue.decode('ascii'))
            elif stype == 2:
                # UTF-8
                self.stypes.append(FileType.UTF8)
                self.svalues.append(svalue.decode('utf8'))
            elif stype == 3:
                # Words
                self.stypes.append(FileType.WORDS)
                self.svalues.append([bytes(svalue[j:j+4])
                                    for j in range(0, slen, 4)])
            elif stype == 4:
                # DWords
                self.stypes.append(FileType.DWORDS)
                self.svalues.append([bytes(svalue[j:j+8])
                                    for j in range(0, slen, 8)])
            elif stype == 5:
                # Doubles
                self.stypes.append(FileType.DOUBLES)
                self.svalues.append(
                    [int.from_bytes(svalue[j:j+8], "big") for j in range(0, slen, 8)])
            elif stype == 6:
                # Coord
                self.stypes.append(FileType.COORD)
                self.svalues.append(
                    (int.from_bytes(svalue[0:8], "big"), int.from_bytes(svalue[8:16], "big")))
            elif stype == 7:
                # Reference
                self.stypes.append(FileType.REF)
                self.svalues.append(int.from_bytes(svalue[0:4], "big"))
            elif stype == 8:
                # PNG
                self.stypes.append(FileType.PNG)
                sig = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'
                out = sig + svalue[0:slen]
                self.svalues.append(out)
            elif stype == 9:
                # GIF87a
                self.stypes.append(FileType.GIF87)
                sig = b'\x47\x49\x46\x38\x37\x61'
                out = sig + svalue[0:slen]
                self.svalues.append(out)
            elif stype == 10:
                # GIF89a
                self.stypes.append(FileType.GIF89)
                sig = b'\x47\x49\x46\x38\x39\x61'
                out = sig + svalue[0:slen]
                self.svalues.append(out)

            else:
                raise ValueError("Stream contained an unsupported type.")

            count += slen

        # validate
        self.validate_fpff()

    def validate_fpff(self):
        """Checks if imported FPFF is valid
        """
        for i in range(self.sect_num):
            if self.stypes[i] == FileType.WORDS:
                for w in self.svalues[i]:
                    if len(w) != 4:
                        raise ValueError(
                            "FPFF is not valid. Improper word length.")
            elif self.stypes[i] == FileType.DWORDS:
                for w in self.svalues[i]:
                    if len(w) != 8:
                        raise ValueError(
                            "FPFF is not valid. Improper dword length.")
            elif self.stypes[i] == FileType.REF:
                if self.svalues[i] > self.sect_num:
                    raise ValueError(
                        "FPFF is not valid. Reference out of bounds.")

    def write(self, file):
        """Write to FPFF file.
        """
        # convert to bytes
        w_magic = bytearray(b'\xDE\xDA\xFE\xBE')
        w_version = FPFF.reverse_bytearray(
            FPFF.add_padding(struct.pack(">I", self.version), 4))
        w_timestamp = FPFF.reverse_bytearray(
            FPFF.add_padding(struct.pack(">I", int(time.time())), 4))
        w_author = FPFF.reverse_bytearray(
            FPFF.add_padding(bytearray(self.author, 'ascii'), 8))
        w_sect_num = FPFF.reverse_bytearray(
            FPFF.add_padding(struct.pack(">I", self.sect_num), 4))
        w_sections = list()
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
                    w_svalue.extend(FPFF.add_padding(
                        bytearray.fromhex(hex(b)[2:]), 8))
            elif self.stypes[i] == FileType.COORD:
                w_svalue = bytearray()
                w_svalue.extend(FPFF.add_padding(
                    bytearray.fromhex(hex(self.svalues[i][0])[2:]), 8))
                w_svalue.extend(FPFF.add_padding(
                    bytearray.fromhex(hex(self.svalues[i][1])[2:]), 8))
            elif self.stypes[i] == FileType.REF:
                w_svalue = FPFF.add_padding(
                    bytearray.fromhex(hex(self.svalues[i])[2:]), 4)
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
            w_section.extend(FPFF.reverse_bytearray(FPFF.add_padding(
                struct.pack(">I", int(self.stypes[i].value)), 4)))
            w_section.extend(FPFF.reverse_bytearray(
                FPFF.add_padding(struct.pack(">I", w_slen), 4)))
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

    def export(self, path):
        """Export FPFF data to folder.
        """

        # create path
        dirpath = "/".join(path.split('/')[:-1])
        dirname = path.split('/')[-1]

        if dirpath != "":
            dirpath += "/"

        if os.path.exists(dirpath+dirname+"-data"):
            shutil.rmtree(dirpath+dirname+"-data")
        os.makedirs(dirpath+dirname+"-data")

        # export files
        for i in range(self.sect_num):
            out_name = dirpath+dirname+"-data/"+dirname+"-"+str(i+1)
            w_svalue = None

            if self.stypes[i] in [FileType.ASCII, FileType.UTF8, FileType.WORDS, FileType.DWORDS, FileType.DOUBLES, FileType.COORD, FileType.REF]:

                if self.stypes[i] == FileType.ASCII:
                    w_svalue = self.svalues[i]
                elif self.stypes[i] == FileType.UTF8:
                    w_svalue = self.svalues[i]
                elif self.stypes[i] == FileType.WORDS:
                    w_svalue = " ".join([val.hex() for val in self.svalues[i]])
                elif self.stypes[i] == FileType.DWORDS:
                    w_svalue = " ".join([val.hex() for val in self.svalues[i]])
                elif self.stypes[i] == FileType.DOUBLES:
                    w_svalue = " ".join([str(val) for val in self.svalues[i]])
                elif self.stypes[i] == FileType.COORD:
                    w_svalue = "LAT: " + \
                        str(self.svalues[i][0]) + \
                        "\nLON: " + str(self.svalues[i][1])
                elif self.stypes[i] == FileType.REF:
                    w_svalue = "REF: " + str(self.svalues[i])

                with open(out_name+".txt", 'w') as f:
                    f.write(w_svalue)
                    f.close()
            else:
                if self.stypes[i] == FileType.PNG:
                    with open(out_name+".png", 'wb') as f:
                        f.write(self.svalues[i])
                        f.close()
                elif self.stypes[i] == FileType.GIF87:
                    with open(out_name+".gif", 'wb') as f:
                        f.write(self.svalues[i])
                        f.close()
                elif self.stypes[i] == FileType.GIF89:
                    with open(out_name+".gif", 'wb') as f:
                        f.write(self.svalues[i])
                        f.close()

    def add(self, obj_data, obj_type, i=0):
        """Add data.
        """
        # rudimentry type check
        if obj_type == FileType.ASCII and type(obj_data) == str:
            self.svalues.insert(i, obj_data)
        elif obj_type == FileType.UTF8 and type(obj_data) == str:
            self.svalues.insert(i, obj_data)
        elif obj_type == FileType.WORDS and type(obj_data) == list:
            self.svalues.insert(i, obj_data)
        elif obj_type == FileType.DWORDS and type(obj_data) == list:
            self.svalues.insert(i, obj_data)
        elif obj_type == FileType.DOUBLES and type(obj_data) == list:
            self.svalues.insert(i, obj_data)
        elif obj_type == FileType.COORD and type(obj_data) == tuple:
            self.svalues.insert(i, obj_data)
        elif obj_type == FileType.REF and type(obj_data) == int:
            self.svalues.insert(i, obj_data)
        elif obj_type == FileType.PNG and type(obj_data) == bytearray:
            self.svalues.insert(i, obj_data)
        elif obj_type == FileType.GIF87 and type(obj_data) == bytearray:
            self.svalues.insert(i, obj_data)
        elif obj_type == FileType.GIF89 and type(obj_data) == bytearray:
            self.svalues.insert(i, obj_data)

        else:
            raise TypeError("Object data not valid for object type.")

        self.stypes.insert(i, obj_type)
        self.sect_num += 1

    def remove(self, i):
        """Remove data.
        """
        del self.svalues[i]
        del self.stypes[i]
        self.sect_num -= 1

    def __repr__(self):
        return str(self.stypes)
