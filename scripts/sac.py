#!/usr/bin/env python3
"""Contract id of the Stellar Asset Contract (SAC) of a classic asset, computed offline.

sha256(XDR HashIDPreimage{ENVELOPE_TYPE_CONTRACT_ID, networkID, CONTRACT_ID_PREIMAGE_FROM_ASSET(asset)})
encoded as a C... strkey. Used to join Soroban token contracts with SDEX assets without scanning
stellar.contract_data (SAC instances written before 2024 never show up there).
"""
import base64
import hashlib
import struct

NETWORK_ID = hashlib.sha256(b'Public Global Stellar Network ; September 2015').digest()


def _crc16(data):
    crc = 0
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            crc = ((crc << 1) ^ 0x1021 if crc & 0x8000 else crc << 1) & 0xFFFF
    return crc


def decode(strkey):
    raw = base64.b32decode(strkey)
    return raw[1:-2]


def encode(version, payload):
    body = bytes([version]) + payload
    return base64.b32encode(body + struct.pack('<H', _crc16(body))).decode()


def sac_id(asset):
    """asset: 'native' or 'CODE:ISSUER'."""
    if asset == 'native':
        xdr_asset = struct.pack('>i', 0)
    else:
        code, issuer = asset.split(':')
        kind, width = (1, 4) if len(code) <= 4 else (2, 12)
        xdr_asset = struct.pack('>i', kind) + code.encode().ljust(width, b'\0') + struct.pack('>i', 0) + decode(issuer)
    preimage = struct.pack('>i', 8) + NETWORK_ID + struct.pack('>i', 1) + xdr_asset
    return encode(2 << 3, hashlib.sha256(preimage).digest())


if __name__ == '__main__':
    import sys
    for a in sys.argv[1:]:
        print(a, sac_id(a))
