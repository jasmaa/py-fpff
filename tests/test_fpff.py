import unittest
import os
import tempfile
import shutil
from py_fpff import FPFF, SectionType


class FPFFTest(unittest.TestCase):
    """FPFF test cases.
    """

    def setUp(self):
        self.test_dir = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_empty(self):
        file_path = os.path.join(self.test_dir, 'out.fpff')

        fpff_1 = FPFF()
        with open(file_path, 'wb') as f:
            fpff_1.write(f)

        with open(file_path, 'rb') as f:
            fpff_2 = FPFF(f)
            assert fpff_2.version == 1
            assert fpff_2.author == ''
            assert fpff_2.nsects == 0

    def test_empty_2(self):
        file_path = os.path.join(self.test_dir, 'out.fpff')

        fpff_1 = FPFF(author='jasmaa')
        with open(file_path, 'wb') as f:
            fpff_1.write(f)

        with open(file_path, 'rb') as f:
            fpff_2 = FPFF(f)
            assert fpff_2.version == 1
            assert fpff_2.author == 'jasmaa'
            assert fpff_2.nsects == 0

    def test_nonmedia(self):
        file_path = os.path.join(self.test_dir, 'out.fpff')

        fpff_1 = FPFF(author='jasmaa')
        data = [
            (SectionType.ASCII, 'Hello, world!'),
            (SectionType.UTF8, 'おはよう世界'),
            (SectionType.WORDS, [b'\x00\x00\x00\x00', b'\xFF\xFF\xFF\xFF']),
            (SectionType.DWORDS, [
             b'\xFF\xFF\xFF\xFF\xFF\x9A\x00\xFF', b'\xFF\xFF\xFF\xFF\xFF\xFF\xFF\xFF'
             ]),
            (SectionType.REF, 1),
            (SectionType.DOUBLES, [-1, 0, 0.3, -0.53]),
            (SectionType.COORD, (90.23, -200.34)),
        ]
        with open(file_path, 'wb') as f:
            for t, v in data:
                fpff_1.append(t, v)
            fpff_1.write(f)

        with open(file_path, 'rb') as f:
            fpff_2 = FPFF(f)
            assert fpff_2.version == 1
            assert fpff_2.author == 'jasmaa'
            assert fpff_2.nsects == len(data)

            cmp = list(zip(data, zip(fpff_2.stypes, fpff_2.svalues)))

            for (t1, v1), (t2, v2) in cmp[:5]:
                assert t1 == t2
                assert v1 == v2
            for (t1, v1), (t2, v2) in cmp[5:]:
                assert t1 == t2
                for n1, n2 in zip(v1, v2):
                    assert abs(n1 - n2) < 0.001


if __name__ == '__main__':
    unittest.main()
