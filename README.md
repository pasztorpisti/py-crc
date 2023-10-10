Arbitrary-precision CRC calculator in Python
============================================

The `parametric_crc()` function below can calculate any of the 100+ CRCs listed in
[Greg Cook's CRC catalogue](https://reveng.sourceforge.io/crc-catalogue/all.htm).
Can calculate CRCs of any bit width (e.g.: CRC-5/USB, CRC-82/DARC).
Can process input of any bit length (see the `bit_len` parameter).
This simple pure python implementation isn't blazingly fast - it can't compete
with C/C++ implementations - but it packs a punch considering what it can do.

1. Copy-paste the below code-block into a python script or console. You can use
   [the web-based python console of the Pyodide project](https://pyodide.org/en/stable/console.html)
   for simple experiments.
2. Pick a CRC algorithm from the catalogue and pass its `width`, `poly`, `init`,
   `refin`, `refout` and `xorout` parameters to the `specialized_crc()` function
   to create an algorithm-specific CRC function (see the examples below)

```python
def reverse_bits(value: int, width: int):
    assert 0 <= value < (1 << width)
    return int('{v:0{w}b}'.format(v=value, w=width)[::-1], 2)


reversed_int8_bits = tuple(reverse_bits(i, 8) for i in range(256))


def parametric_crc(data: bytes, ref_init: int, *, width: int, ref_poly: int,
        refin: bool, refout: bool, xorout: int, bit_len: int = None,
        interim: bool = False, residue: bool = False, table: [int] = None):
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
    ref_init = reverse_bits(init, width)  # compatibility with the CRC catalogue
    ref_poly = reverse_bits(poly, width)  # compatibility with the CRC catalogue
    p = dict(width=width, ref_poly=ref_poly, xorout=xorout, refin=refin, refout=refout)
    t = None if tableless else [parametric_crc(b'\0', i, interim=True, **p)
                                for i in range(256)]
    def crc_fn(data: bytes, ref_init: int = ref_init, *, interim: bool = False,
               residue: bool = False, bit_len: int = None):
        return parametric_crc(data, ref_init, interim=interim, residue=residue,
                              bit_len=bit_len, table=t, **p)
    return crc_fn
```


Examples
========

```python
>>> # The catalogue lists the following parameters for CRC-16/KERMIT:
>>> # width=16 poly=0x1021 init=0x0000 refin=true refout=true xorout=0x0000 check=0x2189
>>> # The "check" value of the catalogue is always the CRC of b'123456789'
>>>
>>> # CRC-16/KERMIT (AKA. CRC-16/V-41-LSB, CRC-16/CCITT-TRUE, CRC-16/CCITT)
>>> crc16_kermit = specialized_crc(16, 0x1021, 0, True, True, 0)
>>> hex(crc16_kermit(b'123456789'))
'0x2189'
>>> # CRC-16/IBM-SDLC (AKA. CRC-B, X-25)
>>> crc16b = specialized_crc(16, 0x1021, 0xffff, True, True, 0xffff)
>>> hex(crc16b(b'123456789'))
'0x906e'
>>> # CRC-16/XMODEM (AKA. CRC-16/V-41-MSB, ZMODEM)
>>> crc16_xmodem = specialized_crc(16, 0x1021, 0, False, False, 0)
>>> hex(crc16_xmodem(b'123456789'))
'0x31c3'
>>> # CRC-16/IBM-3740 (AKA. CRC-16/CCITT-FALSE)
>>> crc16_ibm3740 = specialized_crc(16, 0x1021, 0xffff, False, False, 0)
>>> hex(crc16_ibm3740(b'123456789'))
'0x29b1'
>>> # CRC-32/ISO-HDLC (AKA. CRC-32, CRC-32/V-42, CRC-32/XZ, PKZIP)
>>> crc32 = specialized_crc(32, 0x04c11db7, 0xffffffff, True, True, 0xffffffff)
>>> hex(crc32(b'123456789'))
'0xcbf43926'
>>> # CRC-32/ISCSI (AKA. CRC-32/CASTAGNOLI, CRC-32C)
>>> crc32c = specialized_crc(32, 0x1edc6f41, 0xffffffff, True, True, 0xffffffff)
>>> hex(crc32c(b'123456789'))
'0xe3069283'
>>>
>>> # Calculating the CRC-32C again by feeding in the data in smaller chunks:
>>>
>>> # The first call to the CRC function has to happen by not passing anything
>>> # in its 'ref_init' parameter because its default value is specific to the
>>> # CRC algorithm. Trying to pass zero or something else is a bug and works
>>> # only if you are lucky (or unlucky if we consider that you missed a chance
>>> # to catch a bug). As you see only the second and subsequent calls set the
>>> # 'ref_init' parameter by passing the value of the 'crc' variable as the
>>> # second positional argument.
>>> crc = crc32c(b'1', interim=True)
>>> crc = crc32c(b'23', crc, interim=True)
>>> # Zero-sized/empty chunks are allowed.
>>> # The first and last chunks are also allowed to be empty.
>>> crc = crc32c(b'', crc, interim=True)
>>> crc = crc32c(b'4567', crc, interim=True)
>>> # interim=False so this is the last chunk and the final CRC value
>>> crc = crc32c(b'89', crc)
>>> hex(crc)
'0xe3069283'
>>>
>>> # Calculating the CRC of a file by reading it in small chunks:
>>> def calc_file_crc(crc_fn, file_obj, max_chunk_size=1024*1024):
...     crc = crc_fn(b'', interim=True)
...     while 1:
...         chunk = file_obj.read(max_chunk_size)
...         if not chunk:
...             break
...         crc = crc_fn(chunk, crc, interim=True)
...     return crc_fn(b'', crc)  # interim=False returns the final CRC value
...
>>> with open('<filename>', 'rb') as f:
...     print(hex(calc_file_crc(crc32c, f)))
```
