import json, struct, re, sys, zipfile, os

def enc_u8len(n):
    if n > 0x7f: return bytes([0x80 | (n >> 8), n & 0xff])
    return bytes([n])
def enc_u16len(n):
    if n > 0x7fff: return struct.pack('<HH', 0x8000 | (n >> 16), n & 0xffff)
    return struct.pack('<H', n)

def parse_pool(buf, off):
    typ, hsize, size = struct.unpack_from('<HHI', buf, off)
    assert typ == 1, hex(typ)
    count, style_count, flags, strings_start, styles_start = struct.unpack_from('<IIIII', buf, off+8)
    offsets = list(struct.unpack_from('<%dI' % count, buf, off+hsize))
    style_offsets = list(struct.unpack_from('<%dI' % style_count, buf, off+hsize+4*count)) if style_count else []
    utf8 = bool(flags & 0x100)
    strings = []
    for o in offsets:
        p = off + strings_start + o
        if utf8:
            n = buf[p]; p += 1
            if n & 0x80: n = ((n & 0x7f) << 8) | buf[p]; p += 1
            m = buf[p]; p += 1
            if m & 0x80: m = ((m & 0x7f) << 8) | buf[p]; p += 1
            s = buf[p:p+m].decode('utf-8', 'replace')
        else:
            n = struct.unpack_from('<H', buf, p)[0]; p += 2
            if n & 0x8000:
                n2 = struct.unpack_from('<H', buf, p)[0]; p += 2
                n = ((n & 0x7fff) << 16) | n2
            s = buf[p:p+n*2].decode('utf-16-le', 'replace')
        strings.append(s)
    styles = buf[off+styles_start: off+size] if style_count else b''
    return dict(off=off, hsize=hsize, size=size, count=count, style_count=style_count,
                flags=flags, offsets=offsets, style_offsets=style_offsets,
                strings=strings, styles=styles, utf8=utf8)

def build_pool(p, newstrings):
    data = bytearray(); offs = []
    for s in newstrings:
        offs.append(len(data))
        if p['utf8']:
            b = s.encode('utf-8')
            data += enc_u8len(len(s.encode('utf-16-le')) // 2) + enc_u8len(len(b)) + b + b'\x00'
        else:
            b = s.encode('utf-16-le')
            data += enc_u16len(len(b)//2) + b + b'\x00\x00'
    hsize = 28
    strings_start = hsize + 4*p['count'] + 4*p['style_count']
    pad = (-len(data)) % 4
    strings_start_field = strings_start
    styles_start = strings_start + len(data) + pad
    total = styles_start + len(p['styles'])
    hdr = struct.pack('<HHIIIIII', 1, hsize, total, p['count'], p['style_count'], p['flags'],
                      strings_start_field, styles_start if p['style_count'] else 0)
    out = bytearray(hdr)
    out += struct.pack('<%dI' % len(offs), *offs)
    if p['style_count']:
        out += struct.pack('<%dI' % len(p['style_offsets']), *p['style_offsets'])
    out += data + b'\x00'*pad + p['styles']
    return bytes(out)

def patch_bytes(buf, mapping):
    total_off = 4
    hsize = struct.unpack_from('<H', buf, 2)[0]
    p = parse_pool(buf, hsize)
    new = [mapping.get(s, s) for s in p['strings']]
    changed = sum(1 for a, b in zip(p['strings'], new) if a != b)
    if changed == 0:
        return buf, 0
    nb = build_pool(p, new)
    delta = len(nb) - p['size']
    out = bytearray(buf[:p['off']] + nb + buf[p['off']+p['size']:])
    old_total = struct.unpack_from('<I', out, total_off)[0]
    struct.pack_into('<I', out, total_off, old_total + delta)
    return bytes(out), changed

def strip_locale_configs(buf):
    """Remove ResTable_type chunks that carry a locale (language/country) config."""
    hsize = struct.unpack_from('<H', buf, 2)[0]
    total = struct.unpack_from('<I', buf, 4)[0]
    out = bytearray(buf[:hsize])
    p = hsize; removed = 0
    while p < total:
        typ, hs, size = struct.unpack_from('<HHI', buf, p)
        chunk = buf[p:p+size]
        if typ == 0x0200:
            body = bytearray(chunk[:hs]); c = p + hs; end = p + size
            while c < end:
                t2, h2, s2 = struct.unpack_from('<HHI', buf, c)
                drop = False
                if t2 == 0x0201:
                    cfg = c + 20
                    lang = buf[cfg+8:cfg+10]; country = buf[cfg+10:cfg+12]
                    if lang != b'\x00\x00' or country != b'\x00\x00':
                        drop = True
                if drop: removed += 1
                else: body += buf[c:c+s2]
                c += s2
            struct.pack_into('<I', body, 4, len(body))
            chunk = bytes(body)
        out += chunk
        p += size
    struct.pack_into('<I', out, 4, len(out))
    return bytes(out), removed
