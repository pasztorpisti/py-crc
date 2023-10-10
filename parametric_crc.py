#!/usr/bin/env python3
# SPDX-License-Identifier: MIT-0
# SPDX-FileCopyrightText:  2023 Istvan Pasztor
"""
Arbitrary-precision CRC calculator in Python

Execute this script as a command to calculate CRCs or to run the tests.
Use this as a module to access predefined CRC algorithms (through the
CRC_CATALOGUE list, CRC_PARAMS dict and the create_crc_fn function).

The parametric_crc() function can calculate a wide range of CRCs including those
that aren't 8, 16, 32 or 64 bits wide, for example CRC-5/USB or CRC-82/DARC.
It was tested against the parameters of all the 100+ CRC algorithms that
are currently listed in the CRC catalogue of the CRC RevEng project:
https://reveng.sourceforge.io/crc-catalogue/all.htm
"""


def reverse_bits(value: int, width: int):
    assert 0 <= value < (1 << width)
    return int('{v:0{w}b}'.format(v=value, w=width)[::-1], 2)


reversed_int8_bits = tuple(reverse_bits(i, 8) for i in range(256))


def parametric_crc(data: bytes, ref_init: int, *, width: int, ref_poly: int,
        refin: bool, refout: bool, xorout: int, bit_len: int = None,
        interim: bool = False, residue: bool = False, table: [int] = None):
    """ Parametrized CRC function. Uses a reflected (LSB-first) CRC register
    because this has simpler implementation than the unreflected (MSB-first)
    variant. The ref_init and ref_poly parameters are the reflected values of
    the init and poly parameters listed in the RevEng CRC catalogue. """
    bit_len = len(data)*8 if bit_len is None else bit_len
    assert width > 0 and 0 <= xorout < (1 << width) and bit_len <= len(data)*8
    crc = ref_init
    if table:  # the table is used for processing units of 8 bits (whole bytes)
        num_bytes, bit_len = bit_len >> 3, bit_len & 7
        for i in range(num_bytes):
            b = data[i] if refin else reversed_int8_bits[data[i]]
            crc = table[(crc & 0xff) ^ b] ^ (crc >> 8)
        data = data[num_bytes:num_bytes+1] if bit_len else b''
    for b in data:  # even with a table we may have up to 7 bits remaining
        b = b if refin else reversed_int8_bits[b]
        if bit_len < 8:
            if bit_len <= 0:
                break
            b &= (1 << bit_len) - 1  # zeroing the unused bits
        crc ^= b
        for _ in range(min(bit_len, 8)):
            crc = (crc >> 1) ^ ref_poly if crc & 1 else crc >> 1
        bit_len -= 8
    if interim:
        return crc
    crc = crc if refout else reverse_bits(crc, width)
    return crc if residue else crc ^ xorout


def specialized_crc(width: int, poly: int, init: int, refin: bool,
                    refout: bool, xorout: int, tableless: bool = False):
    """ Creates a CRC function for a specific CRC algorithm.
    The parameters are expected in the format used in the RevEng CRC catalogue:
    https://reveng.sourceforge.io/crc-catalogue/all.htm """
    ref_init = reverse_bits(init, width)  # compatibility with the CRC catalogue
    ref_poly = reverse_bits(poly, width)  # compatibility with the CRC catalogue
    p = dict(width=width, ref_poly=ref_poly, xorout=xorout, refin=refin, refout=refout)
    t = None if tableless else [parametric_crc(b'\0', i, interim=True, **p)
                                for i in range(256)]
    def crc_fn(data: bytes, ref_init: int = ref_init, *, interim: bool = False,
               residue: bool = False, bit_len: int = None):
        return parametric_crc(data, ref_init, interim=interim, residue=residue,
                              bit_len=bit_len, table=t, **p)
    crc_fn.refreg = True  # reflected (LSB-first) CRC shift register
    return crc_fn


_REVENG_CRC_CATALOGUE_FILE = '''
# The lines in this file follow the format used in the online CRC catalogue of
# the CRC RevEng tool: https://reveng.sourceforge.io/crc-catalogue/all.htm
# The `reveng` commandline tool can also output similar lines with its -D
# parameter. I appended the optional "alias" parameters based on the information
# provided in the online catalogue.
#
# I believe that the names of the CRC algorithm parameters come from an old
# document that explains CRC algorithms in layman's terms and proposes a
# parametric CRC model:
#
# A PAINLESS GUIDE TO CRC ERROR DETECTION ALGORITHMS by Ross N. Williams
# http://www.ross.net/crc/download/crc_v3.txt (or just search for crc_v3.txt)
#
# Precise description of the CRC algorithm parameters:
# https://reveng.sourceforge.io/crc-catalogue/all.htm#crc.legend.params
#
# The init, poly, refin and refout parameters in the RevEng CRC catalogue assume
# that the implementation has an unreflected MSB-first CRC shift register.
# The implementation in this script uses a reflected LSB-first CRC shift register.

width=3 poly=0x3 init=0x0 refin=false refout=false xorout=0x7 check=0x4 residue=0x2 name="CRC-3/GSM"
width=3 poly=0x3 init=0x7 refin=true refout=true xorout=0x0 check=0x6 residue=0x0 name="CRC-3/ROHC"
width=4 poly=0x3 init=0x0 refin=true refout=true xorout=0x0 check=0x7 residue=0x0 name="CRC-4/G-704" alias="CRC-4/ITU"
width=4 poly=0x3 init=0xf refin=false refout=false xorout=0xf check=0xb residue=0x2 name="CRC-4/INTERLAKEN"
width=5 poly=0x09 init=0x09 refin=false refout=false xorout=0x00 check=0x00 residue=0x00 name="CRC-5/EPC-C1G2" alias="CRC-5/EPC"
width=5 poly=0x15 init=0x00 refin=true refout=true xorout=0x00 check=0x07 residue=0x00 name="CRC-5/G-704" alias="CRC-5/ITU"
width=5 poly=0x05 init=0x1f refin=true refout=true xorout=0x1f check=0x19 residue=0x06 name="CRC-5/USB"
width=6 poly=0x27 init=0x3f refin=false refout=false xorout=0x00 check=0x0d residue=0x00 name="CRC-6/CDMA2000-A"
width=6 poly=0x07 init=0x3f refin=false refout=false xorout=0x00 check=0x3b residue=0x00 name="CRC-6/CDMA2000-B"
width=6 poly=0x19 init=0x00 refin=true refout=true xorout=0x00 check=0x26 residue=0x00 name="CRC-6/DARC"
width=6 poly=0x03 init=0x00 refin=true refout=true xorout=0x00 check=0x06 residue=0x00 name="CRC-6/G-704" alias="CRC-6/ITU"
width=6 poly=0x2f init=0x00 refin=false refout=false xorout=0x3f check=0x13 residue=0x3a name="CRC-6/GSM"
width=7 poly=0x09 init=0x00 refin=false refout=false xorout=0x00 check=0x75 residue=0x00 name="CRC-7/MMC" alias="CRC-7"
width=7 poly=0x4f init=0x7f refin=true refout=true xorout=0x00 check=0x53 residue=0x00 name="CRC-7/ROHC"
width=7 poly=0x45 init=0x00 refin=false refout=false xorout=0x00 check=0x61 residue=0x00 name="CRC-7/UMTS"
width=8 poly=0x2f init=0xff refin=false refout=false xorout=0xff check=0xdf residue=0x42 name="CRC-8/AUTOSAR"
width=8 poly=0xa7 init=0x00 refin=true refout=true xorout=0x00 check=0x26 residue=0x00 name="CRC-8/BLUETOOTH"
width=8 poly=0x9b init=0xff refin=false refout=false xorout=0x00 check=0xda residue=0x00 name="CRC-8/CDMA2000"
width=8 poly=0x39 init=0x00 refin=true refout=true xorout=0x00 check=0x15 residue=0x00 name="CRC-8/DARC"
width=8 poly=0xd5 init=0x00 refin=false refout=false xorout=0x00 check=0xbc residue=0x00 name="CRC-8/DVB-S2"
width=8 poly=0x1d init=0x00 refin=false refout=false xorout=0x00 check=0x37 residue=0x00 name="CRC-8/GSM-A"
width=8 poly=0x49 init=0x00 refin=false refout=false xorout=0xff check=0x94 residue=0x53 name="CRC-8/GSM-B"
width=8 poly=0x1d init=0xff refin=false refout=false xorout=0x00 check=0xb4 residue=0x00 name="CRC-8/HITAG"
width=8 poly=0x07 init=0x00 refin=false refout=false xorout=0x55 check=0xa1 residue=0xac name="CRC-8/I-432-1"
width=8 poly=0x1d init=0xfd refin=false refout=false xorout=0x00 check=0x7e residue=0x00 name="CRC-8/I-CODE"
width=8 poly=0x9b init=0x00 refin=false refout=false xorout=0x00 check=0xea residue=0x00 name="CRC-8/LTE"
width=8 poly=0x31 init=0x00 refin=true refout=true xorout=0x00 check=0xa1 residue=0x00 name="CRC-8/MAXIM-DOW" alias="CRC-8/MAXIM,DOW-CRC"
width=8 poly=0x1d init=0xc7 refin=false refout=false xorout=0x00 check=0x99 residue=0x00 name="CRC-8/MIFARE-MAD"
width=8 poly=0x31 init=0xff refin=false refout=false xorout=0x00 check=0xf7 residue=0x00 name="CRC-8/NRSC-5"
width=8 poly=0x2f init=0x00 refin=false refout=false xorout=0x00 check=0x3e residue=0x00 name="CRC-8/OPENSAFETY"
width=8 poly=0x07 init=0xff refin=true refout=true xorout=0x00 check=0xd0 residue=0x00 name="CRC-8/ROHC"
width=8 poly=0x1d init=0xff refin=false refout=false xorout=0xff check=0x4b residue=0xc4 name="CRC-8/SAE-J1850"
width=8 poly=0x07 init=0x00 refin=false refout=false xorout=0x00 check=0xf4 residue=0x00 name="CRC-8/SMBUS"
width=8 poly=0x1d init=0xff refin=true refout=true xorout=0x00 check=0x97 residue=0x00 name="CRC-8/TECH-3250" alias="CRC-8/AES,CRC-8/EBU"
width=8 poly=0x9b init=0x00 refin=true refout=true xorout=0x00 check=0x25 residue=0x00 name="CRC-8/WCDMA"
width=10 poly=0x233 init=0x000 refin=false refout=false xorout=0x000 check=0x199 residue=0x000 name="CRC-10/ATM" alias="CRC-10,CRC-10/I-610"
width=10 poly=0x3d9 init=0x3ff refin=false refout=false xorout=0x000 check=0x233 residue=0x000 name="CRC-10/CDMA2000"
width=10 poly=0x175 init=0x000 refin=false refout=false xorout=0x3ff check=0x12a residue=0x0c6 name="CRC-10/GSM"
width=11 poly=0x385 init=0x01a refin=false refout=false xorout=0x000 check=0x5a3 residue=0x000 name="CRC-11/FLEXRAY"
width=11 poly=0x307 init=0x000 refin=false refout=false xorout=0x000 check=0x061 residue=0x000 name="CRC-11/UMTS"
width=12 poly=0xf13 init=0xfff refin=false refout=false xorout=0x000 check=0xd4d residue=0x000 name="CRC-12/CDMA2000"
width=12 poly=0x80f init=0x000 refin=false refout=false xorout=0x000 check=0xf5b residue=0x000 name="CRC-12/DECT" alias="X-CRC-12"
width=12 poly=0xd31 init=0x000 refin=false refout=false xorout=0xfff check=0xb34 residue=0x178 name="CRC-12/GSM"
width=12 poly=0x80f init=0x000 refin=false refout=true xorout=0x000 check=0xdaf residue=0x000 name="CRC-12/UMTS" alias="CRC-12/3GPP"
width=13 poly=0x1cf5 init=0x0000 refin=false refout=false xorout=0x0000 check=0x04fa residue=0x0000 name="CRC-13/BBC"
width=14 poly=0x0805 init=0x0000 refin=true refout=true xorout=0x0000 check=0x082d residue=0x0000 name="CRC-14/DARC"
width=14 poly=0x202d init=0x0000 refin=false refout=false xorout=0x3fff check=0x30ae residue=0x031e name="CRC-14/GSM"
width=15 poly=0x4599 init=0x0000 refin=false refout=false xorout=0x0000 check=0x059e residue=0x0000 name="CRC-15/CAN" alias="CRC-15"
width=15 poly=0x6815 init=0x0000 refin=false refout=false xorout=0x0001 check=0x2566 residue=0x6815 name="CRC-15/MPT1327"
width=16 poly=0x8005 init=0x0000 refin=true refout=true xorout=0x0000 check=0xbb3d residue=0x0000 name="CRC-16/ARC" alias="ARC,CRC-16,CRC-16/LHA,CRC-IBM"
width=16 poly=0xc867 init=0xffff refin=false refout=false xorout=0x0000 check=0x4c06 residue=0x0000 name="CRC-16/CDMA2000"
width=16 poly=0x8005 init=0xffff refin=false refout=false xorout=0x0000 check=0xaee7 residue=0x0000 name="CRC-16/CMS"
width=16 poly=0x8005 init=0x800d refin=false refout=false xorout=0x0000 check=0x9ecf residue=0x0000 name="CRC-16/DDS-110"
width=16 poly=0x0589 init=0x0000 refin=false refout=false xorout=0x0001 check=0x007e residue=0x0589 name="CRC-16/DECT-R" alias="R-CRC-16"
width=16 poly=0x0589 init=0x0000 refin=false refout=false xorout=0x0000 check=0x007f residue=0x0000 name="CRC-16/DECT-X" alias="X-CRC-16"
width=16 poly=0x3d65 init=0x0000 refin=true refout=true xorout=0xffff check=0xea82 residue=0x66c5 name="CRC-16/DNP"
width=16 poly=0x3d65 init=0x0000 refin=false refout=false xorout=0xffff check=0xc2b7 residue=0xa366 name="CRC-16/EN-13757"
width=16 poly=0x1021 init=0xffff refin=false refout=false xorout=0xffff check=0xd64e residue=0x1d0f name="CRC-16/GENIBUS" alias="CRC-16/DARC,CRC-16/EPC,CRC-16/EPC-C1G2,CRC-16/I-CODE"
width=16 poly=0x1021 init=0x0000 refin=false refout=false xorout=0xffff check=0xce3c residue=0x1d0f name="CRC-16/GSM"
width=16 poly=0x1021 init=0xffff refin=false refout=false xorout=0x0000 check=0x29b1 residue=0x0000 name="CRC-16/IBM-3740" alias="CRC-16/AUTOSAR,CRC-16/CCITT-FALSE"
width=16 poly=0x1021 init=0xffff refin=true refout=true xorout=0xffff check=0x906e residue=0xf0b8 name="CRC-16/IBM-SDLC" alias="CRC-16/ISO-HDLC,CRC-16/ISO-IEC-14443-3-B,CRC-16/X-25,CRC-B,X-25"
width=16 poly=0x1021 init=0xc6c6 refin=true refout=true xorout=0x0000 check=0xbf05 residue=0x0000 name="CRC-16/ISO-IEC-14443-3-A" alias="CRC-A"
width=16 poly=0x1021 init=0x0000 refin=true refout=true xorout=0x0000 check=0x2189 residue=0x0000 name="CRC-16/KERMIT" alias="CRC-16/BLUETOOTH,CRC-16/CCITT,CRC-16/CCITT-TRUE,CRC-16/V-41-LSB,CRC-CCITT,KERMIT"
width=16 poly=0x6f63 init=0x0000 refin=false refout=false xorout=0x0000 check=0xbdf4 residue=0x0000 name="CRC-16/LJ1200"
width=16 poly=0x5935 init=0xffff refin=false refout=false xorout=0x0000 check=0x772b residue=0x0000 name="CRC-16/M17"
width=16 poly=0x8005 init=0x0000 refin=true refout=true xorout=0xffff check=0x44c2 residue=0xb001 name="CRC-16/MAXIM-DOW" alias="CRC-16/MAXIM"
width=16 poly=0x1021 init=0xffff refin=true refout=true xorout=0x0000 check=0x6f91 residue=0x0000 name="CRC-16/MCRF4XX"
width=16 poly=0x8005 init=0xffff refin=true refout=true xorout=0x0000 check=0x4b37 residue=0x0000 name="CRC-16/MODBUS" alias="MODBUS"
width=16 poly=0x080b init=0xffff refin=true refout=true xorout=0x0000 check=0xa066 residue=0x0000 name="CRC-16/NRSC-5"
width=16 poly=0x5935 init=0x0000 refin=false refout=false xorout=0x0000 check=0x5d38 residue=0x0000 name="CRC-16/OPENSAFETY-A"
width=16 poly=0x755b init=0x0000 refin=false refout=false xorout=0x0000 check=0x20fe residue=0x0000 name="CRC-16/OPENSAFETY-B"
width=16 poly=0x1dcf init=0xffff refin=false refout=false xorout=0xffff check=0xa819 residue=0xe394 name="CRC-16/PROFIBUS" alias="CRC-16/IEC-61158-2"
width=16 poly=0x1021 init=0xb2aa refin=true refout=true xorout=0x0000 check=0x63d0 residue=0x0000 name="CRC-16/RIELLO"
width=16 poly=0x1021 init=0x1d0f refin=false refout=false xorout=0x0000 check=0xe5cc residue=0x0000 name="CRC-16/SPI-FUJITSU" alias="CRC-16/AUG-CCITT"
width=16 poly=0x8bb7 init=0x0000 refin=false refout=false xorout=0x0000 check=0xd0db residue=0x0000 name="CRC-16/T10-DIF"
width=16 poly=0xa097 init=0x0000 refin=false refout=false xorout=0x0000 check=0x0fb3 residue=0x0000 name="CRC-16/TELEDISK"
width=16 poly=0x1021 init=0x89ec refin=true refout=true xorout=0x0000 check=0x26b1 residue=0x0000 name="CRC-16/TMS37157"
width=16 poly=0x8005 init=0x0000 refin=false refout=false xorout=0x0000 check=0xfee8 residue=0x0000 name="CRC-16/UMTS" alias="CRC-16/BUYPASS,CRC-16/VERIFONE"
width=16 poly=0x8005 init=0xffff refin=true refout=true xorout=0xffff check=0xb4c8 residue=0xb001 name="CRC-16/USB"
width=16 poly=0x1021 init=0x0000 refin=false refout=false xorout=0x0000 check=0x31c3 residue=0x0000 name="CRC-16/XMODEM" alias="CRC-16/ACORN,CRC-16/LTE,CRC-16/V-41-MSB,XMODEM,ZMODEM"
width=17 poly=0x1685b init=0x00000 refin=false refout=false xorout=0x00000 check=0x04f03 residue=0x00000 name="CRC-17/CAN-FD"
width=21 poly=0x102899 init=0x000000 refin=false refout=false xorout=0x000000 check=0x0ed841 residue=0x000000 name="CRC-21/CAN-FD"
width=24 poly=0x00065b init=0x555555 refin=true refout=true xorout=0x000000 check=0xc25a56 residue=0x000000 name="CRC-24/BLE"
width=24 poly=0x5d6dcb init=0xfedcba refin=false refout=false xorout=0x000000 check=0x7979bd residue=0x000000 name="CRC-24/FLEXRAY-A"
width=24 poly=0x5d6dcb init=0xabcdef refin=false refout=false xorout=0x000000 check=0x1f23b8 residue=0x000000 name="CRC-24/FLEXRAY-B"
width=24 poly=0x328b63 init=0xffffff refin=false refout=false xorout=0xffffff check=0xb4f3e6 residue=0x144e63 name="CRC-24/INTERLAKEN"
width=24 poly=0x864cfb init=0x000000 refin=false refout=false xorout=0x000000 check=0xcde703 residue=0x000000 name="CRC-24/LTE-A"
width=24 poly=0x800063 init=0x000000 refin=false refout=false xorout=0x000000 check=0x23ef52 residue=0x000000 name="CRC-24/LTE-B"
width=24 poly=0x864cfb init=0xb704ce refin=false refout=false xorout=0x000000 check=0x21cf02 residue=0x000000 name="CRC-24/OPENPGP" alias="CRC-24"
width=24 poly=0x800063 init=0xffffff refin=false refout=false xorout=0xffffff check=0x200fa5 residue=0x800fe3 name="CRC-24/OS-9"
width=30 poly=0x2030b9c7 init=0x3fffffff refin=false refout=false xorout=0x3fffffff check=0x04c34abf residue=0x34efa55a name="CRC-30/CDMA"
width=31 poly=0x04c11db7 init=0x7fffffff refin=false refout=false xorout=0x7fffffff check=0x0ce9e46c residue=0x4eaf26f1 name="CRC-31/PHILIPS"
width=32 poly=0x814141ab init=0x00000000 refin=false refout=false xorout=0x00000000 check=0x3010bf7f residue=0x00000000 name="CRC-32/AIXM" alias="CRC-32Q"
width=32 poly=0xf4acfb13 init=0xffffffff refin=true refout=true xorout=0xffffffff check=0x1697d06a residue=0x904cddbf name="CRC-32/AUTOSAR"
width=32 poly=0xa833982b init=0xffffffff refin=true refout=true xorout=0xffffffff check=0x87315576 residue=0x45270551 name="CRC-32/BASE91-D" alias="CRC-32D"
width=32 poly=0x04c11db7 init=0xffffffff refin=false refout=false xorout=0xffffffff check=0xfc891918 residue=0xc704dd7b name="CRC-32/BZIP2" alias="CRC-32/AAL5,CRC-32/DECT-B,B-CRC-32"
width=32 poly=0x8001801b init=0x00000000 refin=true refout=true xorout=0x00000000 check=0x6ec2edc4 residue=0x00000000 name="CRC-32/CD-ROM-EDC"
width=32 poly=0x04c11db7 init=0x00000000 refin=false refout=false xorout=0xffffffff check=0x765e7680 residue=0xc704dd7b name="CRC-32/CKSUM" alias="CKSUM,CRC-32/POSIX"
width=32 poly=0x1edc6f41 init=0xffffffff refin=true refout=true xorout=0xffffffff check=0xe3069283 residue=0xb798b438 name="CRC-32/ISCSI" alias="CRC-32/BASE91-C,CRC-32/CASTAGNOLI,CRC-32/INTERLAKEN,CRC-32C"
width=32 poly=0x04c11db7 init=0xffffffff refin=true refout=true xorout=0xffffffff check=0xcbf43926 residue=0xdebb20e3 name="CRC-32/ISO-HDLC" alias="CRC-32,CRC-32/ADCCP,CRC-32/V-42,CRC-32/XZ,PKZIP"
width=32 poly=0x04c11db7 init=0xffffffff refin=true refout=true xorout=0x00000000 check=0x340bc6d9 residue=0x00000000 name="CRC-32/JAMCRC" alias="JAMCRC"
width=32 poly=0x741b8cd7 init=0xffffffff refin=true refout=true xorout=0x00000000 check=0xd2c22f51 residue=0x00000000 name="CRC-32/MEF"
width=32 poly=0x04c11db7 init=0xffffffff refin=false refout=false xorout=0x00000000 check=0x0376e6e7 residue=0x00000000 name="CRC-32/MPEG-2"
width=32 poly=0x000000af init=0x00000000 refin=false refout=false xorout=0x00000000 check=0xbd0be338 residue=0x00000000 name="CRC-32/XFER"
width=40 poly=0x0004820009 init=0x0000000000 refin=false refout=false xorout=0xffffffffff check=0xd4164fc646 residue=0xc4ff8071ff name="CRC-40/GSM"
width=64 poly=0x42f0e1eba9ea3693 init=0x0000000000000000 refin=false refout=false xorout=0x0000000000000000 check=0x6c40df5f0b497347 residue=0x0000000000000000 name="CRC-64/ECMA-182" alias="CRC-64"
width=64 poly=0x000000000000001b init=0xffffffffffffffff refin=true refout=true xorout=0xffffffffffffffff check=0xb90956c775a41001 residue=0x5300000000000000 name="CRC-64/GO-ISO"
width=64 poly=0x259c84cba6426349 init=0xffffffffffffffff refin=true refout=true xorout=0x0000000000000000 check=0x75d4b74f024eceea residue=0x0000000000000000 name="CRC-64/MS"
width=64 poly=0xad93d23594c935a9 init=0x0000000000000000 refin=true refout=true xorout=0x0000000000000000 check=0xe9c6d914c4b8d9ca residue=0x0000000000000000 name="CRC-64/REDIS"
width=64 poly=0x42f0e1eba9ea3693 init=0xffffffffffffffff refin=false refout=false xorout=0xffffffffffffffff check=0x62ec59e3f1a4f00a residue=0xfcacbebd5931a992 name="CRC-64/WE"
width=64 poly=0x42f0e1eba9ea3693 init=0xffffffffffffffff refin=true refout=true xorout=0xffffffffffffffff check=0x995dc9bbdf1939fa residue=0x49958c9abd7d353f name="CRC-64/XZ" alias="CRC-64/GO-ECMA"
width=82 poly=0x0308c0111011401440411 init=0x000000000000000000000 refin=true refout=true xorout=0x000000000000000000000 check=0x09ea83f625023801fd612 residue=0x000000000000000000000 name="CRC-82/DARC"

# I picked 0xa2eb from the CRC Polynomial Zoo:
# https://users.ece.cmu.edu/~koopman/crc/crc16.html
# The "check" value was calculated by the following command:
# echo -n '123456789' | python3 parametric_crc.py -c "custom: width=16 poly=0xa2eb init=0xffff xorout=0xffff refin=true refout=true"
# With the --residue-const parameter it outputs the residue constant.
# I used refin=true because I prefer LSB/little-endian in general.
# The init parameter should be tuned to the kind of data you work with. E.g.:
# If your data often has leading zeros then init=0 may not be the best choice
# because that way the CRC stays the same while the leading zeros are processed.
width=16 poly=0xa2eb init=0xffff refin=true refout=true xorout=0xffff check=0x4e4c residue=0x3fbb name="CRC-16/ZOO-A2EB-FF-LSB"
'''


def _parse_crc_params(line: str) -> dict[str, object]:
    m = {kv[0]: kv[1] for kv in (field.split('=') for field in line.split())}
    if 'width' not in m or 'poly' not in m:
        raise Exception('the required "width" or "poly" field is missing')
    invalid = set(m.keys()) - {'width', 'poly', 'init', 'refin', 'refout',
                               'xorout', 'check', 'residue', 'name', 'alias'}
    if invalid:
        raise Exception('invalid parameters: ' + ', '.join(sorted(invalid)))
    def unquote(s):
        return s[1:-1] if s.startswith('"') and s.endswith('"') else s
    def to_bool(s):
        if s.lower() not in ('true', 'false'):
            raise Exception('invalid bool value: %r' % s)
        return s.lower() == 'true'
    return {
        'width': int(m['width'], 0),
        'poly': int(m['poly'], 0),
        'init': int(m.get('init', '0'), 0),
        'refin': to_bool(m.get('refin', 'false')),
        'refout': to_bool(m.get('refout', 'false')),
        'xorout': int(m.get('xorout', '0'), 0),
        'check': int(m.get('check', '0'), 0),
        'residue': int(m.get('residue', '0'), 0),
        'name': unquote(m.get('name', 'CUSTOM')),
        'alias': [s for s in unquote(m.get('alias', '')).split(',') if s],
    }


def _parse_crc_catalogue(crc_catalouge_file_contents) -> [dict[str, object]]:
    lines = (x.strip() for x in crc_catalouge_file_contents.splitlines())
    return [_parse_crc_params(x) for x in lines if x and not x.startswith('#')]


CRC_CATALOGUE = _parse_crc_catalogue(_REVENG_CRC_CATALOGUE_FILE)
CRC_PARAMS = {m['name'].upper(): m for m in CRC_CATALOGUE}
for _m in CRC_CATALOGUE:
    for _alias in _m.get('alias', ()):
        CRC_PARAMS[_alias] = _m


# Creates and returns a CRC function with the following signature:
# def crc_fn(data: bytes, ref_init: int = ref_init, *, interim: bool = False,
#            residue: bool = False, bit_len: int = None):
def create_crc_fn(name: str, tableless=False):
    p = CRC_PARAMS.get(name.upper())
    if not p:
        return None
    return specialized_crc(p['width'], p['poly'], p['init'], p['refin'],
                           p['refout'], p['xorout'], tableless=tableless)


def residue_const(crc_fn, width: int, xorout: int, refin: bool, refout: bool):
    """ Using the residue constant is one way to check for errors.
    Software CRC implementations often perform CRC check without the residue:
    https://en.wikipedia.org/wiki/Cyclic_redundancy_check

    This simple implementation is based on the description provided by the
    RevEng project in its CRC catalogue:

        Residue:
        The contents of the register after initialising, reading an error-free
        codeword and optionally reflecting the register (if refout=true), but
        not applying the final XOR. This is mathematically equivalent to
        initialising the register with the xorout parameter, reflecting it as
        described (if refout=true), reading as many zero bits as there are cells
        in the register, and reflecting the result (if refin=true). The residue
        of a crossed-endian model is calculated assuming that the characters of
        the received CRC are specially reflected before submitting the codeword.

    It's important to note that the above description assumes an unreflected CRC
    shift register. Our implementation has a reflected CRC register (refreg==True)
    """
    data = b'\0' * ((width+7) // 8)
    xorout = xorout if refout==crc_fn.refreg else reverse_bits(xorout, width)
    residue = crc_fn(data, xorout, bit_len=width, interim=True)
    return residue if refin==crc_fn.refreg else reverse_bits(residue, width)


def residue_const_naive(crc_fn, width: int, refin: bool, refout: bool, dataword: bytes=b''):
    """ Using the residue constant is one way to check for errors.
    Software CRC implementations often perform CRC check without the residue:
    https://en.wikipedia.org/wiki/Cyclic_redundancy_check

    This is the naive method to calculate the residue constant. It forms a valid
    codeword by calculating the CRC of the dataword and appending the CRC to
    that dataword in the correct bit and byte order. The CRC of the codeword is
    calculated without the xorout step to get the residue constant. Unlike the
    other method this one doesn't have to know the reflectedness of the CRC
    register. The dataword can be anything including the empty string.

    I leave this naive implementation here because it explains how to form a
    valid codeword in a way that works with all CRCs in the catalogue. """
    # dataword can be anything, it won't affect the result
    crc = crc_fn(dataword)
    if refin != refout:
        crc = reverse_bits(crc, width)
    crc_byte_size = (width + 7) // 8
    if not refin and crc_byte_size*8 > width:
        crc <<= crc_byte_size*8 - width  # big endian, aligning to the MSB
    endianness = 'little' if refin else 'big'
    codeword = dataword + crc.to_bytes(crc_byte_size, endianness)
    bit_len = len(dataword)*8 + width
    # The codeword (data+crc) is what the sender transmits through a channel.
    # The residue constant should appear in the CRC register of the receiver
    # after receiving all bits of the codeword without transmission errors.
    return crc_fn(codeword, bit_len=bit_len, residue=True)


def _test_crc(name, width, poly, init, xorout, refin, refout, check, residue, alias=()):
    crc_fn = specialized_crc(width, poly, init, refin, refout, xorout)
    print('{:25s} crc_func = specialized_crc(width={!r}, poly=0x{:0{w}x}, '
          'init=0x{:0{w}x}, refin={!r}, refout={!r}, xorout=0x{:0{w}x})'.format
          (name, width, poly, init, refin, refout, xorout, w=(width+3)//4))

    crc_1 = crc_fn(b'123456789')

    # Calculating the same CRC by feeding in the data in smaller chunks
    # including zero-sized chunks.
    crc_2 = crc_fn(b'', interim=True)
    crc_2 = crc_fn(b'1', crc_2, interim=True)
    crc_2 = crc_fn(b'234', crc_2, interim=True)
    crc_2 = crc_fn(b'', crc_2, interim=True)
    crc_2 = crc_fn(b'56', crc_2, interim=True)
    crc_2 = crc_fn(b'789', crc_2, interim=True)
    crc_2 = crc_fn(b'', crc_2)

    residue_1 = residue_const(crc_fn, width, xorout, refin, refout)
    residue_2 = residue_const_naive(crc_fn, width, refin, refout, b'hope it works...')
    residue_3 = residue_const_naive(crc_fn, width, refin, refout, b'')

    print('{:25s} expected:    check={:0{w}x} residue={:0{w}x}\n'
          '{:25s} test_output: check={:0{w}x} residue={:0{w}x}'.format
          ('', check, residue, '', crc_1, residue_1, w=(width+3)//4))
    if alias:
        print('{:25s} aliases:     {}'.format('', ', '.join(alias)))

    if crc_1 != crc_2:
        print('Chunked CRC calculation failed.')
        return False
    if crc_1 != check:
        print('CRC doesn\'t match the reference "check" value.')
        return False

    if residue_1 != residue_2 or residue_1 != residue_3:
        print('The residue calculations returned conflicting results.')
        return False
    if residue_1 != residue:
        print('The residue value does not match the reference constant.')
        return False

    return True


def _test_and_list_catalogue_entries(crc_catalogue):
    passed, failed = [], []
    for entry in crc_catalogue:
        if _test_crc(**entry):
            passed.append(entry['name'])
        else:
            failed.append(entry['name'])
    if failed:
        print('Failed CRCs: ' + ', '.join(failed))
    print('Number of failed CRC algorithms: %s' % len(failed))
    print('Number of CRC algorithms that passed the test: %s' % len(passed))
    return not failed


def _test_input_iterators():
    """ My primitive "test environment" for the input iterators. :-D """

    class FakeFile:
        def __init__(self, chunks: [bytes]):
            self.chunks = chunks
            self.index = 0
        def read(self, max_size: int):
            if self.index >= len(self.chunks):
                return b''
            self.index += 1
            return self.chunks[self.index-1]

    # _input_iterator_01
    # ==================

    # msb stdin, msb crc input
    ff = FakeFile([b'10000000', b'0100', b'001', b'0101'])
    chunks = tuple(_input_iterator_01(ff, False, False, 1))
    assert chunks == ((b'\x80', 8), (b'\x40', 4), (b'\x20', 3), (b'\x50', 4))

    # msb stdin, lsb crc input
    ff = FakeFile([b'10000000', b'0100', b'001', b'1'])
    chunks = tuple(_input_iterator_01(ff, False, True, 1))
    assert chunks == ((b'\x80', 8), (b'\x43', 8))

    # msb stdin, lsb crc input, unconsumed bits
    ff = FakeFile([b'10000000', b'0100', b'001', b'0011'])
    try:
        chunks = tuple(_input_iterator_01(ff, False, True, 1))
    except Exception as ex:
        assert str(ex).find('unconsumed most significant bits at the end of input stream: 011') >= 0

    # lsb stdin, lsb crc input
    ff = FakeFile([b'10000000', b'0100', b'001', b'0101'])
    chunks = tuple(_input_iterator_01(ff, True, True, 1))
    assert chunks == ((b'\x01', 8), (b'\x02', 4), (b'\x04', 3), (b'\x0a', 4))

    # lsb stdin, msb crc input
    ff = FakeFile([b'10000000', b'0100', b'001', b'1'])
    chunks = tuple(_input_iterator_01(ff, True, False, 1))
    assert chunks == ((b'\x01', 8), (b'\xC2', 8))

    # lsb stdin, msb crc input, unconsumed bits
    ff = FakeFile([b'10000000', b'0100', b'001', b'0011'])
    try:
        chunks = tuple(_input_iterator_01(ff, True, False, 1))
    except Exception as ex:
        assert str(ex).find('unconsumed least significant bits at the end of input stream: 011') >= 0

    # _input_iterator_hex
    # ===================

    # msb stdin, msb crc input
    ff = FakeFile([b'AF', b'0', b'9', b'5'])
    chunks = tuple(_input_iterator_hex(ff, False, False, 1))
    assert chunks == ((b'\xaf', 8), (b'\x00', 4), (b'\x90', 4), (b'\x50', 4))

    # msb stdin, lsb crc input
    ff = FakeFile([b'af', b'0', b'9'])
    chunks = tuple(_input_iterator_hex(ff, False, True, 1))
    assert chunks == ((b'\xaf', 8), (b'\x09', 8))

    # msb stdin, lsb crc input, unconsumed upper nibble
    ff = FakeFile([b'af', b'0', b'9', b'5'])
    try:
        chunks = tuple(_input_iterator_hex(ff, False, True, 1))
    except Exception as ex:
        assert str(ex).find('unconsumed upper nibble at the end of input stream: 5') >= 0

    # lsb stdin, lsb crc input
    ff = FakeFile([b'AF', b'0', b'9', b'5'])
    chunks = tuple(_input_iterator_hex(ff, True, True, 1))
    assert chunks == ((b'\xfa', 8), (b'\x00', 4), (b'\x09', 4), (b'\x05', 4))

    # lsb stdin, msb crc input
    ff = FakeFile([b'af', b'0', b'9'])
    chunks = tuple(_input_iterator_hex(ff, True, False, 1))
    assert chunks == ((b'\xfa', 8), (b'\x90', 8))

    # lsb stdin, msb crc input, unconsumed lower nibble
    ff = FakeFile([b'af', b'0', b'9', b'5'])
    try:
        chunks = tuple(_input_iterator_hex(ff, True, False, 1))
    except Exception as ex:
        assert str(ex).find('unconsumed lower nibble at the end of input stream: 5') >= 0


def _input_iterator_hex(infile, lsb_input, refin, max_chunk_size=16*1024):
    import re
    p_space = re.compile(rb'\s+')
    p_hex = re.compile(rb'^[0-9a-fA-F]*$')

    # If the endianness of the input stream and the input of the CRC algorithm
    # don't match (if lsb_input!=refin) then we have to store partially received
    # bytes in leftover.
    leftover = b''
    while 1:
        chunk = infile.read(max_chunk_size)
        if chunk:
            chunk = p_space.sub(b'', chunk)
            if not p_hex.match(chunk):
                raise Exception('invalid input character - '
                                'allowed characters: hex digits, whitespace')
            chunk = leftover + chunk
            leftover = b''
            num_bits = len(chunk) * 4
            if len(chunk) & 1: # making sure it's an even number of nibbles
                if lsb_input != refin:
                    leftover = chunk[-1:]
                    chunk = chunk [:-1]
                    if not chunk:
                        continue
                    num_bits = len(chunk) * 4
                else:
                    chunk += b'0'  # padding
            if lsb_input: # reversing the nibbles in each byte
                chunk = b''.join(chunk[i:i+2][::-1]
                                 for i in range(0, len(chunk), 2))
            yield bytes.fromhex(chunk.decode('ascii')), num_bits

        else:
            if not leftover:
                break

            leftover = leftover.decode('ascii')
            if lsb_input:
                # The CRC algorithm has MSB input (refin==false) so it can
                # consume only completed bytes from the LSB input stream.
                raise Exception('unconsumed lower nibble at the end of input stream: ' + leftover)
            else:
                # The CRC algorithm has LSB input (refin==true) so it can
                # consume only completed bytes from the MSB input stream.
                raise Exception('unconsumed upper nibble at the end of input stream: ' + leftover)


def _input_iterator_01(infile, lsb_input, refin, max_chunk_size=16*1024):
    import re
    p_space = re.compile(rb'\s+')
    p_01 = re.compile(rb'^[01]*$')

    # If the endianness of the input stream and the input of the CRC algorithm
    # don't match (if lsb_input!=refin) then we have to store partially received
    # bytes in leftover.
    leftover = b''
    while 1:
        chunk = infile.read(max_chunk_size)
        if chunk:
            chunk = p_space.sub(b'', chunk)
            if not p_01.match(chunk):
                raise Exception("invalid input character - "
                                "allowed characters: '0', '1', whitespace")
            chunk = leftover + chunk
            leftover = b''
            num_bits = len(chunk)
            b = num_bits & 7
            if b: # the number of digits must be a multiple of 8
                if lsb_input != refin:
                    leftover = chunk[-b:]
                    chunk = chunk [:-b]
                    if not chunk:
                        continue
                    num_bits = len(chunk)
                else:
                    chunk += b'0' * (8-b)  # padding
            reverse_if_lsb = lambda x: x[::-1] if lsb_input else x
            data = bytes(int(reverse_if_lsb(chunk[i:i+8]).decode('ascii'), 2)
                         for i in range(0, len(chunk), 8))
            yield data, num_bits

        else:
            if not leftover:
                break

            leftover = leftover.decode('ascii')
            if lsb_input:
                # The CRC algorithm has MSB input (refin==false) so it can
                # consume only completed bytes from the LSB input stream.
                raise Exception('unconsumed least significant bits at the end of input stream: ' + leftover)
            else:
                # The CRC algorithm has LSB input (refin==true) so it can
                # consume only completed bytes from the MSB input stream.
                raise Exception('unconsumed most significant bits at the end of input stream: ' + leftover)


def _input_iterator(infile, input_format, refin):
    """ This generator yields tuples of the form (bytes, num_bits). """
    if input_format in ('hex', 'lsb_hex'):
        # lsb_hex: least significant nibble first
        yield from _input_iterator_hex(infile, input_format == 'lsb_hex', refin)
        return
    elif input_format in ('01', 'lsb_01'):
        yield from _input_iterator_01(infile, input_format == 'lsb_01', refin)
        return

    assert input_format == 'binary'
    MAX_CHUNK_SIZE = 128 * 1024
    while 1:
        chunk = infile.read(MAX_CHUNK_SIZE)
        if not chunk:
            break
        yield chunk, len(chunk)*8


def _calc_crc(args):
    name_or_params = args.crc.strip()
    custom_prefix = 'custom:'
    if name_or_params.lower().startswith(custom_prefix):
        try:
            p = _parse_crc_params(name_or_params[len(custom_prefix):].strip())
        except Exception as ex:
            raise Exception('invalid "CUSTOM:" CRC parameters') from ex
        name_or_params = 'CUSTOM'
    else:
        p = CRC_PARAMS.get(name_or_params.upper())
        if p is None:
            raise Exception('invalid CRC algorithm name')

    crc_fn = specialized_crc(p['width'], p['poly'], p['init'],
                             p['refin'], p['refout'], p['xorout'])

    if not args.quiet:
        print('{} specialized_crc(width={!r}, poly=0x{:0{w}x}, '
            'init=0x{:0{w}x}, refin={!r}, refout={!r}, xorout=0x{:0{w}x})'.format
            (name_or_params, p['width'], p['poly'], p['init'],
            p['refin'], p['refout'], p['xorout'], w=(p['width']+3)//4))

    if args.format == '0xhex':
        fmt_str = '0x{:0{w}x}'
    elif args.format == 'hex':
        fmt_str = '{:0{w}x}'
    else:
        fmt_str = '{!r}'

    if args.residue_const:
        v = residue_const(crc_fn, p['width'], p['xorout'], p['refin'], p['refout'])
        fmt_str = fmt_str if args.quiet else 'residue constant: ' + fmt_str
        print(fmt_str.format(v, w=(p['width']+3)//4))
        return

    input_iter = _input_iterator(args.infile, args.input_format, p['refin'])
    if args.continue_from is None:
        crc = crc_fn(b'', interim=True)
    else:
        crc = crc_fn(b'', args.continue_from, interim=True)
    bits_processed = 0
    if args.max_input_bits is None or args.max_input_bits > 0:
        max_input_bits = args.max_input_bits
        for chunk, num_bits in input_iter:
            if max_input_bits is not None:
                if max_input_bits <= 0:
                    break
                num_bits = min(num_bits, max_input_bits)
                max_input_bits -= num_bits
            crc = crc_fn(chunk, crc, interim=True, bit_len=num_bits)
            bits_processed += num_bits
    v = crc_fn(b'', crc, interim=args.interim_remainder, residue=args.residue)
    if not args.quiet:
        msg = 'number of bits processed: %s' % bits_processed
        msg += ' [%s bytes(s) +%s bit(s)]' % (bits_processed // 8, bits_processed & 7)
        print(msg)
        if args.interim_remainder:
            fmt_str = 'interim remainder: ' + fmt_str
        elif args.residue:
            fmt_str = 'residue: ' + fmt_str
        else:
            fmt_str = 'crc: ' + fmt_str
    print(fmt_str.format(v, w=(p['width']+3)//4))


def _main():
    import argparse
    import sys
    p = argparse.ArgumentParser(description='Parametric CRC calculator.')
    auto_int = lambda s: int(s, 0)
    p.add_argument('-l', '--list', action='store_true', help=
                   'list and test all builtin CRC algorithms')
    p.add_argument('--residue-const', action='store_true', help=
                   'calculate the residue constant for the specified CRC '
                   'algorithm (this requires no input data)')
    p.add_argument('--residue', action='store_true', help=
                   'ouput the residue instead of the final CRC '
                   '(skip the xorout step)')
    p.add_argument('-c', '--crc', help='the name of the CRC algorithm or'
                   ' "CUSTOM: width=X poly=Y ..."')
    p.add_argument('-r', '--interim-remainder', action='store_true', help=
                   'output an interim remainder instead of the final CRC')
    p.add_argument('-k', '--continue-from', type=auto_int, help='continue CRC '
                   'calculation from the specified interim remainder')
    p.add_argument('-i', '--input-format', choices=['binary', 'hex', '01',
                   'lsb_01'], default='binary', help='input data format')
    p.add_argument('-m', '--max-input-bits', type=auto_int, help=
                   'maximum number of bits to process from the input')
    p.add_argument('-f', '--format', choices=['0xhex', 'hex', 'decimal'],
                   default='0xhex', help='output format of the crc, residue, '
                   'residue constant or interim remainder')
    p.add_argument('-q', '--quiet', action='store_true', help=
                   'output only the result of the calculation')
    p.add_argument('infile', nargs='?', type=argparse.FileType('rb'), help=
                   'name of the input file, default: stdin', default=sys.stdin)
    args = p.parse_args()

    if sum((args.interim_remainder, args.residue_const, args.residue)) > 1:
        print('You can use at most one of the following parameters: '
              '--interim-remainder, --residue-const, --residue', file=sys.stderr)
        sys.exit(1)

    if args.infile == sys.stdin:
        args.infile = sys.stdin.buffer # we want to read binary data not strings

    if args.list:
        sys.exit(0 if _test_and_list_catalogue_entries(CRC_CATALOGUE) else 1)

    if args.crc:
        try:
            _calc_crc(args)
            sys.exit(0)
        finally:
            args.infile.close()

    p.print_help()
    sys.exit(2)


if __name__ == '__main__':
    #_test_input_iterators()
    _main()


"""
The example below shows how to use --residue-const and --residue parameters.
A codeword is a dataword (a piece of data) with its CRC appended in the correct
bit and byte order. Feeding the whole codeword (including the appended CRC value)
into the CRC calculator should leave the residue constant in the CRC register if
the codeword isn't corrupted.

The CRC catalogue of the RevEng project mentions codeword examples when the
documentation of a CRC algorithm provides some:
https://reveng.sourceforge.io/crc-catalogue/all.htm
We will test a codeword provided for the CRC-32/CASTAGNOLI algorithm:
000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F4E79DD46

# 1. Getting the residue constant of the CRC algorithm:

$ python3 parametric_crc.py -qc CRC-32/CASTAGNOLI --residue-const
0xb798b438

# 2. Feeding the codeword into parametric_crc.py and asking for the residue left
#    in the CRC register:

$ echo '000102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F4E79DD46' \
       | python3 parametric_crc.py -qc CRC-32/CASTAGNOLI -i hex --residue
0xb798b438

# 3. Performing the same check after corrupting the first byte of the codeword:

$ echo '600102030405060708090A0B0C0D0E0F101112131415161718191A1B1C1D1E1F4E79DD46' \
       | python3 parametric_crc.py -qc CRC-32/CASTAGNOLI -i hex --residue
0x199a76d2


The docstring of the parametric_crc function mentions that its implementation
uses a reflected (LSB-first) CRC register because it is simpler than the
alternative implementation with unreflected (MSB-first) CRC register. Below you
can see the alternative implementation. It uses more shift magic and two
different masks that make it a bit more complicated than LSB variant. Problems
like this aren't uncommon when you have to deal with variable integer width on
MSB-first/big-endian systems.


def parametric_crc(data: bytes, init: int, *, width: int, poly: int,
        refin: bool, refout: bool, xorout: int, bit_len: int = None,
        interim: bool = False, residue: bool = False, table: [int] = None):
    assert width > 0 and 0 <= poly < (1 << width)
    bit_len = len(data)*8 if bit_len is None else bit_len
    # The size of the CRC register is at least 8 bits to make it easy to process
    # the bytes of the input data. If the CRC width is below 8 then the CRC
    # sits in the most significant bits of the 8-bit register.
    CRC_REG_SIZE = max(width, 8)
    assert 0 <= init < (1 << CRC_REG_SIZE) and bit_len <= len(data)*8
    MASK = (1 << CRC_REG_SIZE) - 1
    MASK_MSB = 1 << (CRC_REG_SIZE - 1)
    SHIFT = CRC_REG_SIZE - width
    crc = init
    if SHIFT > 0:  # greater than zero if (width < 8)
        crc <<= SHIFT
        poly <<= SHIFT

    if table:  # the table is used for processing units of 8 bits (whole bytes)
        num_bytes, bit_len = bit_len >> 3, bit_len & 7
        for i in range(num_bytes):
            b = reversed_int8_bits[data[i]] if refin else data[i]
            crc = table[(crc >> (CRC_REG_SIZE-8)) ^ b] ^ ((crc << 8) & MASK)
        data = data[num_bytes:num_bytes+1] if bit_len else b''
    for b in data:  # even with a table we may have up to 7 bits remaining
        b = reversed_int8_bits[b] if refin else b
        if bit_len < 8:
            if bit_len <= 0:
                break
            b &= 0xff00 >> bit_len  # zeroing the unused bits
        crc ^= b << (CRC_REG_SIZE - 8)
        for _ in range(min(bit_len, 8)):
            crc = ((crc << 1) & MASK) ^ poly if crc & MASK_MSB else crc << 1
        bit_len -= 8

    if SHIFT > 0:
        crc >>= SHIFT
    if interim:
        return crc
    crc = reverse_bits(crc, width) if refout else crc
    return crc if residue else crc ^ xorout


def specialized_crc(width: int, poly: int, init: int, refin: bool,
                    refout: bool, xorout: int, tableless: bool = False):
    p = dict(width=width, poly=poly, xorout=xorout, refin=refin, refout=refout)
    SHIFT = 0 if width >= 8 else 8 - width
    t = None if tableless else [parametric_crc(bytes(
                                [reversed_int8_bits[i] if refin else i]), 0,
                                interim=True, **p) << SHIFT for i in range(256)]
    def crc_fn(data: bytes, init: int = init, *, interim: bool = False,
               residue: bool = False, bit_len: int = None):
        return parametric_crc(data, init, interim=interim, residue=residue,
                              bit_len=bit_len, table=t, **p)
    crc_fn.refreg = False  # unreflected (MSB-first) CRC shift register
    return crc_fn
"""
