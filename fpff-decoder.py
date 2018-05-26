import binascii

def reverse_bytearray(s):
    rev = bytearray()
    for i in range(len(s)-1, -1, -1):
        rev.append(s[i])
    return rev



def read_fpff(file):
    with open(file, "rb") as f:
        data = bytearray(f.read())

    magic       = reverse_bytearray(data[0:4])
    version     = int.from_bytes(data[4:8], "little")
    timestamp   = reverse_bytearray(data[8:12])
    author      = reverse_bytearray(data[12:20])
    sections    = int.from_bytes(data[20:24], "little")

    # checks
    if magic != b'\xbe\xfe\xda\xde':
        print("Wrong header")
        return
    if version != 1:
        print("Not version 1")
        return

    # read sections
    count = 24
    for i in range(sections):
        stype = int.from_bytes(data[count:count+4], "little")
        slen =  int.from_bytes(data[count+4:count+8], "little")
        count += 8
        svalue = data[count:count+slen]

        out_name = file.split(".")[0]+"-"+str(i+1)

        # export for now
        # ascii
        if stype == 1:
            with open(out_name+".txt", "w") as f:
                f.write(svalue.decode('ascii'))
                f.close()
        # utf-8
        elif stype == 2:
            with open(out_name+".txt", "w") as f:
                f.write(svalue.decode('utf-8'))
                f.close()
        # word
        elif stype == 3:
            with open(out_name+".txt", "w") as f:
                f.write(" ".join([svalue[j:j+4].hex() for j in range(0, slen, 4)]))
                f.close()
        # dword
        elif stype == 4:
            with open(out_name+".txt", "w") as f:
                f.write(" ".join([svalue[j:j+8].hex() for j in range(0, slen, 8)]))
                f.close()
        # double
        elif stype == 5:
            with open(out_name+".txt", "w") as f:
                f.write(" ".join([str(int.from_bytes(svalue[j:j+8], "big")) for j in range(0, slen, 8)]))
                f.close()
        # coord
        elif stype == 6:
            with open(out_name+".txt", "w") as f:
                f.write("Lat: " + str(int.from_bytes(svalue[0:8], "big")))
                f.write("\n")
                f.write("Lon: " + str(int.from_bytes(svalue[8:16], "big")))
                f.close()
        # ref
        elif stype == 7:
            with open(out_name+".txt", "w") as f:
                f.write("Sect: " + str(int.from_bytes(svalue[0:4], "big")))
                f.close()
        # png
        elif stype == 8:
            with open(out_name+".png", "wb") as f:
                sig = b'\x89\x50\x4E\x47\x0D\x0A\x1A\x0A'
                out = sig + svalue[0:slen]
                f.write(out)
                f.close()
        #gif87a
        elif stype == 9:
            with open(out_name+".gif", "wb") as f:
                sig = b'\x47\x49\x46\x38\x37\x61'
                out = sig + svalue[0:slen]
                f.write(out)
                f.close()
        #gif89a
        elif stype == 10:
            with open(out_name+".gif", "wb") as f:
                sig = b'\x47\x49\x46\x38\x39\x61'
                out = sig + svalue[0:slen]
                f.write(out)
                f.close()
        
        count += slen
        
    print("done")
