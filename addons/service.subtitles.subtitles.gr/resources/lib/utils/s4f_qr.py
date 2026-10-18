# -*- coding: utf-8 -*-

'''
    Subtitles.gr Addon
    Author Twilight0

    A minimal QR Code (model 2) encoder and a PNG writer.

    Kodi has no QR control and bundles no QR module, but the download hand-off
    has to put a LAN address on the television so a phone can scan it instead
    of typing it. This is byte mode at error-correction level L, versions 1 to
    6, which covers anything a URL like http://192.168.1.101:46805/ can be,
    with the standard mask selection so any reader accepts the result.

    No dependency and no image library: the PNG is written here with zlib and
    a CRC, and Kodi draws it like any other texture.

    SPDX-License-Identifier: GPL-3.0-only
    See LICENCES/GPL-3.0-only for more information.
'''

import binascii
import struct
import sys
import zlib

# version: (total codewords, data codewords, ec codewords per block, block sizes)
VERSIONS = {
    1: (26, 19, 7, [19]),
    2: (44, 34, 10, [34]),
    3: (70, 55, 15, [55]),
    4: (100, 80, 20, [80]),
    5: (134, 108, 26, [108]),
    6: (172, 136, 18, [68, 68]),
}

# Alignment pattern centres. Version 1 has none.
ALIGNMENT = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
    5: [6, 30],
    6: [6, 34],
}

# Bits that pad the end of the last codeword before the data is placed.
REMAINDER = {1: 0, 2: 7, 3: 7, 4: 7, 5: 7, 6: 7}

PAD = (0xEC, 0x11)

# --- GF(256), as QR defines it -------------------------------------------

EXP = [0] * 512
LOG = [0] * 256

_value = 1

for _index in range(255):
    EXP[_index] = _value
    LOG[_value] = _index
    _value <<= 1

    if _value & 0x100:
        _value ^= 0x11D

for _index in range(255, 512):
    EXP[_index] = EXP[_index - 255]


def _multiply(a, b):

    if a == 0 or b == 0:
        return 0

    return EXP[LOG[a] + LOG[b]]


def _poly_multiply(a, b):

    out = [0] * (len(a) + len(b) - 1)

    for i, left in enumerate(a):

        if not left:
            continue

        for j, right in enumerate(b):
            out[i + j] ^= _multiply(left, right)

    return out


def _poly_mod(dividend, divisor):

    out = list(dividend)

    for i in range(len(out) - len(divisor) + 1):

        factor = out[i]

        if not factor:
            continue

        for j, value in enumerate(divisor):
            out[i + j] ^= _multiply(value, factor)

    return out[-(len(divisor) - 1):]


def _generator(degree):

    poly = [1]

    for i in range(degree):
        poly = _poly_multiply(poly, [1, EXP[i]])

    return poly


# --- bit stream ----------------------------------------------------------

def _bit_stream(text, version):

    data = text.encode('utf-8')
    capacity = VERSIONS[version][1]

    if len(data) > 255 or len(data) + 2 > capacity:
        return None

    bits = [0, 1, 0, 0]                                  # byte mode
    bits += [(len(data) >> shift) & 1 for shift in range(7, -1, -1)]

    for byte in bytearray(data):
        bits += [(byte >> shift) & 1 for shift in range(7, -1, -1)]

    bits += [0] * min(4, capacity * 8 - len(bits))

    while len(bits) % 8:
        bits.append(0)

    pad = 0

    while len(bits) < capacity * 8:
        bits += [(PAD[pad % 2] >> shift) & 1 for shift in range(7, -1, -1)]
        pad += 1

    return bytes(bytearray(
        sum(bits[offset + i] << (7 - i) for i in range(8))
        for offset in range(0, len(bits), 8)
    ))


def _codewords(text, version):

    total, data_length, ec_length, blocks = VERSIONS[version]

    data = _bit_stream(text, version)

    if data is None:
        return None

    generator = _generator(ec_length)
    groups = []
    offset = 0

    for size in blocks:
        blocks_data = list(bytearray(data[offset:offset + size]))
        groups.append((blocks_data, _poly_mod(blocks_data + [0] * ec_length, generator)))
        offset += size

    # Data codewords are interleaved column by column across the blocks, then
    # the error codewords the same way.
    out = []

    for i in range(max(len(block) for block, _ in groups)):

        for block, _ in groups:

            if i < len(block):
                out.append(block[i])

    for i in range(ec_length):

        for _, ec in groups:
            out.append(ec[i])

    if len(out) != total:
        return None

    return out


# --- matrix --------------------------------------------------------------

def _blank_matrix(version):

    size = 17 + 4 * version

    return [[0] * size for _ in range(size)], [[False] * size for _ in range(size)]


def _finder(matrix, reserved, row, col):

    size = len(matrix)

    for dr in range(-1, 8):

        for dc in range(-1, 8):

            r, c = row + dr, col + dc

            if not (0 <= r < size and 0 <= c < size):
                continue

            if 0 <= dr <= 6 and 0 <= dc <= 6:
                edge = dr in (0, 6) or dc in (0, 6)
                core = 2 <= dr <= 4 and 2 <= dc <= 4
                matrix[r][c] = 1 if (edge or core) else 0
            else:
                matrix[r][c] = 0

            reserved[r][c] = True


def _function_patterns(version):

    matrix, reserved = _blank_matrix(version)
    size = len(matrix)

    _finder(matrix, reserved, 0, 0)
    _finder(matrix, reserved, 0, size - 7)
    _finder(matrix, reserved, size - 7, 0)

    for i in range(8, size - 8):

        matrix[6][i] = 1 if i % 2 == 0 else 0
        reserved[6][i] = True

        matrix[i][6] = 1 if i % 2 == 0 else 0
        reserved[i][6] = True

    corners = ALIGNMENT[version]
    last = corners[-1] if corners else 0

    for row in corners:

        for col in corners:

            # The three centres that would sit on a finder pattern are skipped.
            if (row, col) in ((6, 6), (6, last), (last, 6)):
                continue

            for dr in range(-2, 3):

                for dc in range(-2, 3):

                    matrix[row + dr][col + dc] = 0 if max(abs(dr), abs(dc)) == 1 else 1
                    reserved[row + dr][col + dc] = True

    # The module that is always dark, and the areas the format bits live in.
    matrix[4 * version + 9][8] = 1
    reserved[4 * version + 9][8] = True

    for i in range(9):

        if not reserved[8][i]:
            matrix[8][i] = 0
            reserved[8][i] = True

        if not reserved[i][8]:
            matrix[i][8] = 0
            reserved[i][8] = True

    for i in range(8):

        if not reserved[8][size - 1 - i]:
            matrix[8][size - 1 - i] = 0
            reserved[8][size - 1 - i] = True

        if not reserved[size - 1 - i][8]:
            matrix[size - 1 - i][8] = 0
            reserved[size - 1 - i][8] = True

    return matrix, reserved


def _place_data(matrix, reserved, codewords, remainder, version):

    size = len(matrix)
    total = VERSIONS[version][0]

    bits = []

    for byte in codewords:
        bits += [(byte >> shift) & 1 for shift in range(7, -1, -1)]

    bits += [0] * remainder

    if len(bits) != total * 8 + remainder:
        return False

    index = 0
    upward = True
    col = size - 1

    while col > 0:

        if col == 6:
            col -= 1

        for step in range(size):

            row = (size - 1 - step) if upward else step

            for c in (col, col - 1):

                if reserved[row][c]:
                    continue

                matrix[row][c] = bits[index] if index < len(bits) else 0
                index += 1

        upward = not upward
        col -= 2

    return index == len(bits)


def _mask_condition(mask, row, col):

    if mask == 0:
        return (row + col) % 2 == 0

    if mask == 1:
        return row % 2 == 0

    if mask == 2:
        return col % 3 == 0

    if mask == 3:
        return (row + col) % 3 == 0

    if mask == 4:
        return (row // 2 + col // 3) % 2 == 0

    if mask == 5:
        return (row * col) % 2 + (row * col) % 3 == 0

    if mask == 6:
        return ((row * col) % 2 + (row * col) % 3) % 2 == 0

    return ((row + col) % 2 + (row * col) % 3) % 2 == 0


def _penalty(matrix):

    size = len(matrix)
    score = 0

    # Rule 1: runs of five or more of the same colour, in either direction.
    for lines in (matrix, list(zip(*matrix))):

        for line in lines:

            run = 1

            for i in range(1, size):

                if line[i] == line[i - 1]:
                    run += 1
                else:
                    if run >= 5:
                        score += 3 + (run - 5)
                    run = 1

            if run >= 5:
                score += 3 + (run - 5)

    # Rule 2: every two by two block of one colour.
    for row in range(size - 1):

        for col in range(size - 1):

            if matrix[row][col] == matrix[row][col + 1] == matrix[row + 1][col] == matrix[row + 1][col + 1]:
                score += 3

    # Rule 3: the finder-like sequence, in either direction.
    finder = [1, 0, 1, 1, 1, 0, 1, 0, 0, 0, 0]
    reverse = list(reversed(finder))

    for line in list(matrix) + [list(row) for row in zip(*matrix)]:

        for i in range(size - 10):

            if line[i:i + 11] == finder or line[i:i + 11] == reverse:
                score += 40

    # Rule 4: how far the dark proportion is from half, per whole five percent.
    total = size * size
    dark = sum(sum(row) for row in matrix)
    score += int(abs(dark * 100.0 / total - 50) / 5) * 10

    return score


def _format_bits(data):

    value = data << 10
    remainder = value

    for i in range(14, 9, -1):

        if remainder >> i & 1:
            remainder ^= 0x537 << (i - 10)

    return ((data << 10) | (remainder & 0x3FF)) ^ 0x5412


def _draw_format(matrix, mask):

    size = len(matrix)
    bits = _format_bits((0b01 << 3) | mask)      # level L, then the mask
    bit = lambda i: (bits >> i) & 1

    # Both copies carry the fifteen bits most significant first, running along
    # the strip. Reading the value back the other way is invisible to the eye
    # but tells a reader the wrong mask, so the code still decodes - into
    # garbage.
    for i in range(6):
        matrix[8][i] = bit(14 - i)

    matrix[8][7] = bit(8)
    matrix[8][8] = bit(7)
    matrix[7][8] = bit(6)

    for i in range(6):
        matrix[5 - i][8] = bit(5 - i)

    # The duplicate runs up the left of the dark module in the opposite
    # direction to the first copy (bit 8 at the top, bit 14 at the bottom),
    # then across the top right the same way round as the first.
    for i in range(7):
        matrix[size - 7 + i][8] = bit(8 + i)

    for i in range(8):
        matrix[8][size - 8 + i] = bit(7 - i)


def matrix(text, mask=None):

    '''
    The finished module grid, or None when the text does not fit.

    With mask left out this mirrors the reference encoders: build the version,
    place the data, then try all eight masks and keep the one with the lowest
    penalty score. Naming a mask pins it instead, which is only useful for
    checking this file against another encoder.
    '''

    codewords = None
    version = 1

    while version <= max(VERSIONS):

        codewords = _codewords(text, version)

        if codewords is not None:
            break

        version += 1

    if codewords is None:
        return None

    base, reserved = _function_patterns(version)

    if not _place_data(base, reserved, codewords, REMAINDER[version], version):
        return None

    chosen = None
    chosen_score = None

    for candidate in range(8):

        if mask is not None and candidate != mask:
            continue

        grid = [row[:] for row in base]

        for row in range(len(grid)):

            for col in range(len(grid)):

                if not reserved[row][col] and _mask_condition(candidate, row, col):
                    grid[row][col] ^= 1

        _draw_format(grid, candidate)

        score = _penalty(grid)

        if chosen_score is None or score < chosen_score:
            chosen, chosen_score = grid, score

    return chosen


# --- PNG -----------------------------------------------------------------

def _chunk(tag, payload):

    return (
        struct.pack('>I', len(payload)) + tag + payload
        + struct.pack('>I', binascii.crc32(tag + payload) & 0xFFFFFFFF)
    )


def png(path, text, scale=8, border=4):

    '''
    Writes the code as an 8-bit greyscale PNG. Returns the path, or '' when the
    text does not fit - the caller then shows the address as text only.

    Written by hand because Kodi cannot be asked for a QR image and PIL is a
    module that may not be installed, while zlib and a CRC always are.
    '''

    grid = matrix(text)

    if grid is None:
        return ''

    size = len(grid)
    side = (size + border * 2) * scale
    margin = b'\xff' * (border * scale)
    quiet = b'\x00' + b'\xff' * side
    rows = [quiet] * (border * scale)

    for line in grid:

        pixels = bytearray()

        for module in line:
            pixels += (b'\x00' if module else b'\xff') * scale

        rows += [b'\x00' + margin + bytes(pixels) + margin] * scale

    rows += [quiet] * (border * scale)

    header = b'\x89PNG\r\n\x1a\n'
    header += _chunk(b'IHDR', struct.pack('>IIBBBBB', side, side, 8, 0, 0, 0, 0))
    header += _chunk(b'IDAT', zlib.compress(b''.join(rows), 9))
    header += _chunk(b'IEND', b'')

    try:

        with open(path, 'wb') as handle:
            handle.write(header)

    except OSError:
        return ''

    return path


if __name__ == '__main__':

    # Handy when checking the encoder by eye: python s4f_qr.py <text> <out.png>
    if len(sys.argv) == 3:
        print(png(sys.argv[2], sys.argv[1]))
