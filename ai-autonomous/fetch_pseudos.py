#!/usr/bin/env python3
"""Recover exact common PseudoDojo UPFs and reject any changed bytes.

Usage: python fetch_pseudos.py
Dependencies: Python standard library, HTTPS to raw.githubusercontent.com.
Only missing files are downloaded. Existing wrong bytes are an error; never overwrite.
The original upstream commit and blob identities were live-read via GitHub in R01.
"""
from pathlib import Path
import hashlib
import urllib.request

ROOT=Path(__file__).resolve().parent/'pseudos'
COMMIT='823b18f7701b6303e0e69114eaa645173f706600'
FILES={
 'Fe': '79848bdb660ac0fe3f93ac0967cba01fe200f5cc2cf37e7f01e6ac051f107105',
 'Se': '1f5d0f8b99028dee90766aab811ce5d8bb2c2b2ad38ec60436d1c2888ef5109c'}

def main():
    """Write only verified bytes; print the actual hash of each recovered file."""
    ROOT.mkdir(exist_ok=True)
    for element,expected in FILES.items():
        target=ROOT/f'{element}_std.upf'
        url=f'https://raw.githubusercontent.com/PseudoDojo/ONCVPSP-PBE-SR/{COMMIT}/{element}/{element}_std.upf'
        data=target.read_bytes() if target.exists() else urllib.request.urlopen(url,timeout=60).read()
        actual=hashlib.sha256(data).hexdigest()
        if actual!=expected:
            raise ValueError(f'Pseudo checksum mismatch: {target.name}, {actual}')
        if not target.exists():target.write_bytes(data)
        print(target.name,actual)

if __name__=='__main__':main()
