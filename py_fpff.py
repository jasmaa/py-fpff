import os
import shutil
import time
import struct
from typing import Any, BinaryIO
from enum import IntEnum


class FileType(IntEnum):
    """FPFF file types.
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


class FPFF:
    """Handles read, write, and export for FPFF.
    """

    def __init__(self, file: BinaryIO = None, author: str = ''):
        self.version = 1
        self.timestamp = int(time.time())
        self.author = author
        self.nsects = 0
        self.stypes = list()
        self.svalues = list()

        # Read FPFF file if supplied
        if file != None:
            self.read(file)

    def read(self, file: BinaryIO):
        """Reads in FPFF.
        """
        data = file.read(24)

        magic = data[0:4][::-1]
        self.version = int.from_bytes(data[4:8], 'little')
        self.timestamp = int.from_bytes(data[8:12], 'little')
        self.author = data[12:20][::-1].decode('ascii').strip('\0')
        self.nsects = int.from_bytes(data[20:24], 'little')
        self.stypes = []
        self.svalues = []

        # Metadata checks
        if magic != b'\xBE\xFE\xDA\xDE':
            raise ValueError("Magic did not match FPFF magic.")
        if self.version != 1:
            raise ValueError(
                "Unsupported version. Only version 1 is supported."
            )

        # Read each section
        for _ in range(self.nsects):
            # Read section header and data
            data = file.read(8)
            stype = int.from_bytes(data[0:4], 'little')
            slen = int.from_bytes(data[4:8], 'little')

            if slen <= 0:
                raise ValueError("Section length must be greater than 0.")

            svalue = file.read(slen)

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
                self.stypes.append(FileType.WORDS)
                self.svalues.append(
                    [svalue[j:j+4] for j in range(0, slen, 4)]
                )
            elif stype == 0x4:
                # DWords
                if slen % 8 != 0:
                    raise ValueError("Improper section length.")
                self.stypes.append(FileType.DWORDS)
                self.svalues.append(
                    [svalue[j:j+8] for j in range(0, slen, 8)]
                )
            elif stype == 0x5:
                # Doubles
                if slen % 8 != 0:
                    raise ValueError("Improper section length.")
                self.stypes.append(FileType.DOUBLES)
                self.svalues.append(
                    [struct.unpack("<d", svalue[j:j+8])[0]
                     for j in range(0, slen, 8)]
                )
            elif stype == 0x6:
                # Coord
                if slen != 16:
                    raise ValueError("Improper section length.")
                self.stypes.append(FileType.COORD)
                lat = struct.unpack("<d", svalue[0:8])[0]
                lng = struct.unpack("<d", svalue[8:16])[0]
                # TODO: validate lat and lng
                self.svalues.append((lat, lng))
            elif stype == 0x7:
                # Reference
                if slen != 4:
                    raise ValueError("Improper section length.")
                ref = int.from_bytes(svalue[0:4], 'little')
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

    def write(self, file: BinaryIO):
        """Write to FPFF file.
        """
        # Write FPFF header
        file.write(b'\xDE\xDA\xFE\xBE')
        file.write(self.version.to_bytes(4, 'little'))
        file.write(self.timestamp.to_bytes(4, 'little'))
        author_bytes = self.author.encode('ascii')[::-1]
        file.write(author_bytes)
        file.write(b'\x00'*(8-len(author_bytes)))
        file.write(self.nsects.to_bytes(4, 'little'))

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
                for w in self.svalues[i]:
                    if len(w) != 4:
                        raise ValueError("Word needs to be 4 bytes.")
                    section_bytes += w
            elif self.stypes[i] == FileType.DWORDS:
                # DWords
                for w in self.svalues[i]:
                    if len(w) != 8:
                        raise ValueError("DWord needs to be 8 bytes.")
                    section_bytes += w
            elif self.stypes[i] == FileType.DOUBLES:
                # Doubles
                section_bytes = b''.join(
                    [struct.pack("<d", w) for w in self.svalues[i]]
                )
            elif self.stypes[i] == FileType.COORD:
                # Coords
                section_bytes = struct.pack("<d", self.svalues[i][0])
                section_bytes += struct.pack("<d", self.svalues[i][1])
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
            file.write(self.stypes[i].to_bytes(4, 'little'))
            file.write(len(section_bytes).to_bytes(4, 'little'))
            file.write(section_bytes)

    def export(self, output_path: str):
        """Export FPFF to folder.
        """

        # Ensure output path exists
        if os.path.exists(output_path):
            shutil.rmtree(output_path)
        os.mkdir(output_path)

        # Export files
        for i in range(self.nsects):
            if self.stypes[i] not in [FileType.PNG, FileType.GIF87, FileType.GIF89]:
                # Non-media section
                file_name = f'section-{i}.txt'
                output = ''
                if self.stypes[i] == FileType.ASCII:
                    output = self.svalues[i]
                elif self.stypes[i] == FileType.UTF8:
                    output = self.svalues[i]
                elif self.stypes[i] == FileType.WORDS:
                    output = ', '.join(
                        [val.hex() for val in self.svalues[i]]
                    )
                elif self.stypes[i] == FileType.DWORDS:
                    output = ', '.join(
                        [val.hex() for val in self.svalues[i]]
                    )
                elif self.stypes[i] == FileType.DOUBLES:
                    output = ', '.join(
                        [str(val) for val in self.svalues[i]]
                    )
                elif self.stypes[i] == FileType.COORD:
                    output = f'LAT: {str(self.svalues[i][0])}\nLNG: {str(self.svalues[i][1])}'
                elif self.stypes[i] == FileType.REF:
                    output = f'REF: {str(self.svalues[i])}'

                with open(os.path.join(output_path, file_name), 'w', encoding='utf8') as f:
                    f.write(output)

            else:
                # Media section
                if self.stypes[i] == FileType.PNG:
                    file_name = f'section-{i}.png'
                    with open(file_name, 'wb') as f:
                        f.write(self.svalues[i])
                elif self.stypes[i] == FileType.GIF87:
                    file_name = f'section-{i}.gif'
                    with open(file_name, 'wb') as f:
                        f.write(self.svalues[i])
                elif self.stypes[i] == FileType.GIF89:
                    file_name = f'section-{i}.gif'
                    with open(file_name, 'wb') as f:
                        f.write(self.svalues[i])

    def insert(self, section_idx: int, obj_type: FileType, obj_data: Any):
        """Insert section.
        """
        if obj_type == FileType.ASCII and type(obj_data) == str:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == FileType.UTF8 and type(obj_data) == str:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == FileType.WORDS and type(obj_data) == list:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == FileType.DWORDS and type(obj_data) == list:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == FileType.DOUBLES and type(obj_data) == list:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == FileType.COORD and type(obj_data) == tuple:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == FileType.REF and type(obj_data) == int:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == FileType.PNG and type(obj_data) == bytearray:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == FileType.GIF87 and type(obj_data) == bytearray:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == FileType.GIF89 and type(obj_data) == bytearray:
            self.svalues.insert(section_idx, obj_data)
        else:
            raise TypeError("Object data not valid for object type.")

        self.stypes.insert(section_idx, obj_type)
        self.nsects += 1

    def append(self, obj_type: FileType, obj_data: Any):
        """Append section.
        """
        self.insert(self.nsects, obj_type, obj_data)

    def remove(self, i: int):
        """Remove section.
        """
        del self.svalues[i]
        del self.stypes[i]
        self.nsects -= 1

    def __repr__(self):
        return str(self.stypes)
