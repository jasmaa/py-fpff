"""Provides operations for working with FPFF.
"""

import os
import shutil
import time
import struct
from typing import Any, BinaryIO, Union
from enum import IntEnum


class SectionType(IntEnum):
    """Enum types for FPFF section types.

    Example:
        >>> t = SectionType.ASCII
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
    """FPFF file.

    Attributes:
        version (int): FPFF version number. Only accepts 1.
        timestamp (int): UNIX timestamp indicating time of creation.
        author (str): Author name.
        nsects (int): Number of sections in the FPFF.
        stypes (List[SectionType]): List of section types indexed by section.
        svalues (List[Any]): List of section values indexed by section.
    """

    def __init__(self, file: Union[BinaryIO, None] = None, author: str = ''):
        """Initializes new FPFF.

        Args:
            file (BinaryIO): Optional FPFF input byte stream. Provided if reading FPFF.
            author (str): Author name. Defaults to ''.

        Example:
            >>> with open('./input.fpff', 'rb') as f:
            >>>     fpff = FPFF(f)
        """

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
        """Reads in FPFF from byte stream.

        Args:
            file (BinaryIO): FPFF input byte stream.

        Raises:
            ValueError: Magic did not match FPFF magic.
            ValueError: Unsupported version. Only version 1 is supported.
            ValueError: Section length must be greater than 0.
            ValueError: Improper section length.
            ValueError: Reference value is out of bounds.
            ValueError: File contained an unsupported type.

        Example:
            >>> with open('./input.fpff', 'rb') as f:
            >>>     fpff = FPFF()
            >>>     fpff.read(f)
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
                self.stypes.append(SectionType.ASCII)
                self.svalues.append(svalue.decode('ascii'))
            elif stype == 0x2:
                # UTF-8
                self.stypes.append(SectionType.UTF8)
                self.svalues.append(svalue.decode('utf8'))
            elif stype == 0x3:
                # Words
                if slen % 4 != 0:
                    raise ValueError("Improper section length.")
                self.stypes.append(SectionType.WORDS)
                self.svalues.append(
                    [svalue[j:j+4] for j in range(0, slen, 4)]
                )
            elif stype == 0x4:
                # DWords
                if slen % 8 != 0:
                    raise ValueError("Improper section length.")
                self.stypes.append(SectionType.DWORDS)
                self.svalues.append(
                    [svalue[j:j+8] for j in range(0, slen, 8)]
                )
            elif stype == 0x5:
                # Doubles
                if slen % 8 != 0:
                    raise ValueError("Improper section length.")
                self.stypes.append(SectionType.DOUBLES)
                self.svalues.append(
                    [struct.unpack("<d", svalue[j:j+8])[0]
                     for j in range(0, slen, 8)]
                )
            elif stype == 0x6:
                # Coord
                if slen != 16:
                    raise ValueError("Improper section length.")
                self.stypes.append(SectionType.COORD)
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
                self.stypes.append(SectionType.REF)
                self.svalues.append(ref)
            elif stype == 0x8:
                # PNG
                self.stypes.append(SectionType.PNG)
                sig = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'
                out = sig + svalue[0:slen]
                self.svalues.append(out)
            elif stype == 0x9:
                # GIF87a
                self.stypes.append(SectionType.GIF87)
                sig = b'\x47\x49\x46\x38\x37\x61'
                out = sig + svalue[0:slen]
                self.svalues.append(out)
            elif stype == 0xA:
                # GIF89a
                self.stypes.append(SectionType.GIF89)
                sig = b'\x47\x49\x46\x38\x39\x61'
                out = sig + svalue[0:slen]
                self.svalues.append(out)
            else:
                raise ValueError("File contained an unsupported type.")

    def write(self, file: BinaryIO):
        """Writes FPFF to byte stream.

        Args:
            file (BinaryIO): FPFF output byte stream.

        Raises:
            ValueError: Word needs to be 4 bytes.
            ValueError: DWord needs to be 8 bytes.

        Example:
            >>> with open('./output.fpff', 'wb') as out_f:
            >>>     fpff = FPFF()
            >>>     fpff.append(SectionType.ASCII, 'Hello, world!')
            >>>     fpff.write(out_f)
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

            if self.stypes[i] == SectionType.ASCII:
                # ASCII
                section_bytes = self.svalues[i].encode('ascii')
            elif self.stypes[i] == SectionType.UTF8:
                # UTF-8
                section_bytes = self.svalues[i].encode('utf8')
            elif self.stypes[i] == SectionType.WORDS:
                # Words
                for w in self.svalues[i]:
                    if len(w) != 4:
                        raise ValueError("Word needs to be 4 bytes.")
                    section_bytes += w
            elif self.stypes[i] == SectionType.DWORDS:
                # DWords
                for w in self.svalues[i]:
                    if len(w) != 8:
                        raise ValueError("DWord needs to be 8 bytes.")
                    section_bytes += w
            elif self.stypes[i] == SectionType.DOUBLES:
                # Doubles
                section_bytes = b''.join(
                    [struct.pack("<d", w) for w in self.svalues[i]]
                )
            elif self.stypes[i] == SectionType.COORD:
                # Coords
                section_bytes = struct.pack("<d", self.svalues[i][0])
                section_bytes += struct.pack("<d", self.svalues[i][1])
            elif self.stypes[i] == SectionType.REF:
                # Reference
                section_bytes = self.svalues[i].to_bytes(4, 'little')
            elif self.stypes[i] == SectionType.PNG:
                # PNG
                section_bytes = self.svalues[i][8:]
            elif self.stypes[i] == SectionType.GIF87:
                # GIF87a
                section_bytes = self.svalues[i][6:]
            elif self.stypes[i] == SectionType.GIF89:
                # GIF89a
                section_bytes = self.svalues[i][6:]

            # Write to file
            file.write(self.stypes[i].to_bytes(4, 'little'))
            file.write(len(section_bytes).to_bytes(4, 'little'))
            file.write(section_bytes)

    def export(self, output_path: str):
        """Exports FPFF sections to directory.

        Args:
            output_path (str): Path to export directory.

        Example:
            >>> with open('./input.fpff') as f:
            >>>     fpff = FPFF(f)
            >>>     fpff.export('./exported')
        """

        # Ensure output path exists
        if os.path.exists(output_path):
            shutil.rmtree(output_path)
        os.mkdir(output_path)

        # Export files
        for i in range(self.nsects):
            if self.stypes[i] not in [SectionType.PNG, SectionType.GIF87, SectionType.GIF89]:
                # Non-media section
                file_name = f'section-{i}.txt'
                output = ''
                if self.stypes[i] == SectionType.ASCII:
                    output = self.svalues[i]
                elif self.stypes[i] == SectionType.UTF8:
                    output = self.svalues[i]
                elif self.stypes[i] == SectionType.WORDS:
                    output = ', '.join(
                        [val.hex() for val in self.svalues[i]]
                    )
                elif self.stypes[i] == SectionType.DWORDS:
                    output = ', '.join(
                        [val.hex() for val in self.svalues[i]]
                    )
                elif self.stypes[i] == SectionType.DOUBLES:
                    output = ', '.join(
                        [str(val) for val in self.svalues[i]]
                    )
                elif self.stypes[i] == SectionType.COORD:
                    output = f'LAT: {str(self.svalues[i][0])}\nLNG: {str(self.svalues[i][1])}'
                elif self.stypes[i] == SectionType.REF:
                    output = f'REF: {str(self.svalues[i])}'

                with open(os.path.join(output_path, file_name), 'w', encoding='utf8') as f:
                    f.write(output)

            else:
                # Media section
                if self.stypes[i] == SectionType.PNG:
                    file_name = f'section-{i}.png'
                    with open(os.path.join(output_path, file_name), 'wb') as f:
                        f.write(self.svalues[i])
                elif self.stypes[i] == SectionType.GIF87:
                    file_name = f'section-{i}.gif'
                    with open(os.path.join(output_path, file_name), 'wb') as f:
                        f.write(self.svalues[i])
                elif self.stypes[i] == SectionType.GIF89:
                    file_name = f'section-{i}.gif'
                    with open(os.path.join(output_path, file_name), 'wb') as f:
                        f.write(self.svalues[i])

    def insert(self, section_idx: int, obj_type: SectionType, obj_data: Any):
        """Inserts section before indicated index.

        Args:
            section_idx (int): Section index to insert in front of.
            obj_type (int): Section type of new section.
            obj_data (Any): Section value of new section.

        Raises:
            TypeError: Object data not valid for object type.

        Example:
            >>> fpff.insert(0, SectionType.ASCII, 'Hello, world!')
        """

        if obj_type == SectionType.ASCII and type(obj_data) == str:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == SectionType.UTF8 and type(obj_data) == str:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == SectionType.WORDS and type(obj_data) == list:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == SectionType.DWORDS and type(obj_data) == list:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == SectionType.DOUBLES and type(obj_data) == list:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == SectionType.COORD and type(obj_data) == tuple:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == SectionType.REF and type(obj_data) == int:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == SectionType.PNG and type(obj_data) in [bytes, bytearray]:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == SectionType.GIF87 and type(obj_data) in [bytes, bytearray]:
            self.svalues.insert(section_idx, obj_data)
        elif obj_type == SectionType.GIF89 and type(obj_data) in [bytes, bytearray]:
            self.svalues.insert(section_idx, obj_data)
        else:
            raise TypeError("Object data not valid for object type.")

        self.stypes.insert(section_idx, obj_type)
        self.nsects += 1

    def append(self, obj_type: SectionType, obj_data: Any):
        """Appends section.

        Args:
            obj_type (int): Section type of new section.
            obj_data (Any): Section value of new section.

        Example:
            >>> fpff.append(SectionType.ASCII, 'Hello, world!')
        """

        self.insert(self.nsects, obj_type, obj_data)

    def remove(self, section_idx: int):
        """Removes section at index.

        Args:
            section_idx (int): Index of section to remove.

        Example:
            >>> fpff.remove(0)
        """

        del self.svalues[section_idx]
        del self.stypes[section_idx]
        self.nsects -= 1

    def __repr__(self) -> str:
        """String representation of FPFF.

        Returns:
            string: String representation of FPFF.
        """

        return str(self.stypes)
