from enum import IntEnum
import time
import struct
import os
import shutil


class FileType(IntEnum):
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

    def __init__(self, file_path: str = None, author: str = None):
        self.version = 1
        self.timestamp = None
        self.author = None
        self.nsects = 0
        self.stypes = list()
        self.svalues = list()

        # Read FPFF file if supplied
        if file_path != None:
            self.read(file_path)

    def read(self, file_path: str):
        """Reads in FPFF.
        """
        self.__file = open(file_path, 'rb')
        data = self.__file.read(24)

        magic = data[0:4][::-1]
        self.version = int.from_bytes(data[4:8], 'little')
        self.timestamp = int.from_bytes(data[8:12], 'little')
        self.author = data[12:20][::-1].decode('ascii')
        self.nsects = int.from_bytes(data[20:24], 'little')
        self.stypes = []
        self.svalues = []

        # Read checks
        if magic != b'\xBE\xFE\xDA\xDE':
            raise ValueError("Magic did not match FPFF magic.")
        if self.version != 1:
            raise ValueError(
                "Unsupported version. Only version 1 is supported."
            )
        if self.nsects <= 0:
            raise ValueError("Section length must be greater than 0.")

        # Read each section
        for _ in range(self.nsects):
            # Read section header and data
            data = self.__file.read(8)
            stype = int.from_bytes(data[0:4], 'little')
            slen = int.from_bytes(data[4:8], 'little')
            svalue = self.__file.read(slen)

            # Decode section data
            if stype == 0x1:
                # ASCII
                self.stypes.append(FileType.ASCII)
                self.svalues.append(svalue.decode('ascii'))
            elif stype == 0x2:
                # UTF-8
                self.stypes.append(FileType.UTF8)
                self.svalues.append(svalue.decode('utf8'))
            elif stype == 0x3:
                # Words
                if slen % 4 != 0:
                    raise ValueError("Improper section length.")
                self.stypes.append(FileType.DOUBLES)
                self.stypes.append(FileType.WORDS)
                self.svalues.append(
                    [bytes(svalue[j:j+4])
                     for j in range(0, slen, 4)]
                )
            elif stype == 0x4:
                # DWords
                if slen % 8 != 0:
                    raise ValueError("Improper section length.")
                self.stypes.append(FileType.DOUBLES)
                self.stypes.append(FileType.DWORDS)
                self.svalues.append(
                    [bytes(svalue[j:j+8])
                     for j in range(0, slen, 8)]
                )
            elif stype == 0x5:
                # Doubles
                if slen % 8 != 0:
                    raise ValueError("Improper section length.")
                self.stypes.append(FileType.DOUBLES)
                self.svalues.append(
                    [float.from_bytes(svalue[j:j+8], 'big')
                     for j in range(0, slen, 8)]
                )
            elif stype == 0x6:
                # Coord
                if slen != 16:
                    raise ValueError("Improper section length.")
                self.stypes.append(FileType.COORD)
                lat = float.from_bytes(svalue[0:8], 'big')
                lng = float.from_bytes(svalue[8:16], 'big')
                # TODO: validate lat and lng
                self.svalues.append((lat, lng))
            elif stype == 0x7:
                # Reference
                if slen != 4:
                    raise ValueError("Improper section length.")
                ref = int.from_bytes(svalue[0:4], 'big')
                if ref < 0 or ref >= self.nsects:
                    raise ValueError("Reference value is out of bounds.")
                self.stypes.append(FileType.REF)
                self.svalues.append(ref)
            elif stype == 0x8:
                # PNG
                self.stypes.append(FileType.PNG)
                sig = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'
                out = sig + svalue[0:slen]
                self.svalues.append(out)
            elif stype == 0x9:
                # GIF87a
                self.stypes.append(FileType.GIF87)
                sig = b'\x47\x49\x46\x38\x37\x61'
                out = sig + svalue[0:slen]
                self.svalues.append(out)
            elif stype == 0xA:
                # GIF89a
                self.stypes.append(FileType.GIF89)
                sig = b'\x47\x49\x46\x38\x39\x61'
                out = sig + svalue[0:slen]
                self.svalues.append(out)
            else:
                raise ValueError("File contained an unsupported type.")

    def write(self, file_path: str):
        """Write to FPFF file.
        """
        self.__file = open(file_path, 'wb')

        # Write FPFF header
        self.__file.write(b'\xDE\xDA\xFE\xBE')
        self.__file.write(self.version.to_bytes(4, 'little'))
        self.__file.write(self.timestamp.to_bytes(4, 'little'))
        author_bytes = self.author.encode('ascii')[::-1]
        self.__file.write(author_bytes)
        self.__file.write(b'\x00'*(8-len(author_bytes)))
        self.__file.write(self.nsects.to_bytes(4, 'little'))

        # Write each section
        for i in range(self.nsects):
            section_bytes = b''

            if self.stypes[i] == FileType.ASCII:
                # ASCII
                section_bytes = self.svalues[i].encode('ascii')
            elif self.stypes[i] == FileType.UTF8:
                # UTF-8
                section_bytes = self.svalues[i].encode('utf8')
            elif self.stypes[i] == FileType.WORDS:
                # Words
                section_bytes = b''.join(
                    [w.to_bytes(4, 'little') for w in self.svalues[i]]
                )
            elif self.stypes[i] == FileType.DWORDS:
                # DWords
                section_bytes = b''.join(
                    [w.to_bytes(8, 'little') for w in self.svalues[i]]
                )
            elif self.stypes[i] == FileType.DOUBLES:
                # Doubles
                section_bytes = b''.join(
                    [w.to_bytes(8, 'little') for w in self.svalues[i]]
                )
            elif self.stypes[i] == FileType.COORD:
                # Coords
                section_bytes = self.svalues[i][0].to_bytes(8, 'little')
                section_bytes += self.svalues[i][1].to_bytes(8, 'little')
            elif self.stypes[i] == FileType.REF:
                # Reference
                section_bytes = self.svalues[i].to_bytes(4, 'little')
            elif self.stypes[i] == FileType.PNG:
                # PNG
                section_bytes = self.svalues[i][8:]
            elif self.stypes[i] == FileType.GIF87:
                # GIF87a
                section_bytes = self.svalues[i][6:]
            elif self.stypes[i] == FileType.GIF89:
                # GIF89a
                section_bytes = self.svalues[i][6:]

            # Write to file
            self.__file.write(self.stypes[i].to_bytes(4, 'little'))
            self.__file.write(len(section_bytes).to_bytes(4, 'little'))
            self.__file.write(section_bytes)

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
        for i in range(self.nsects):
            out_name = dirpath+dirname+"-data/"+dirname+"-"+str(i+1)
            w_svalue = None

            if self.stypes[i] in [FileType.ASCII, FileType.UTF8, FileType.WORDS, FileType.DWORDS, FileType.DOUBLES, FileType.COORD, FileType.REF]:

                if self.stypes[i] == FileType.ASCII:
                    w_svalue = self.svalues[i]
                elif self.stypes[i] == FileType.UTF8:
                    w_svalue = self.svalues[i]
                elif self.stypes[i] == FileType.WORDS:
                    w_svalue = " ".join([val.hex()
                                        for val in self.svalues[i]])
                elif self.stypes[i] == FileType.DWORDS:
                    w_svalue = " ".join([val.hex()
                                        for val in self.svalues[i]])
                elif self.stypes[i] == FileType.DOUBLES:
                    w_svalue = " ".join([str(val)
                                        for val in self.svalues[i]])
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
        self.nsects += 1

    def remove(self, i):
        """Remove data.
        """
        del self.svalues[i]
        del self.stypes[i]
        self.nsects -= 1

    def __repr__(self):
        return str(self.stypes)
