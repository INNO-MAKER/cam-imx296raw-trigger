#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
i2c.py - For CAM-IMX296 GS Camera Module (InnoMaker)
====================================================

Pure-Python I2C tool for the IMX296 camera board.  Replaces the prebuilt
aarch64 ``i2c_read`` / ``i2c_write`` C binaries and bundles two high-level
helpers customers actually use:

  * Chapter 5  - Strobe registers on the IMX296 sensor (slave 0x1a, 16-bit
                 reg addr).  Single-command on/off, no need to memorise any
                 register addresses.
  * Chapter 6  - On-board EEPROM FT24C08A (slaves 0x50/0x51/0x52/0x53,
                 256 bytes each = 1 KB total, 8-bit sub-addr).

Talks to ``/dev/i2c-N`` directly via ``ioctl(I2C_RDWR)``, no smbus2 / i2c-tools
dependency.  Works on stock Raspberry Pi OS (Bookworm/Trixie, 32-bit & 64-bit).

------------------------------------------------------------------------
COMMAND CHEATSHEET
------------------------------------------------------------------------

Strobe (Pi5: bus 4 = CAM1, bus 6 = CAM0):

    sudo python3 i2c.py strobe on  --bus 4 --mode trigger
    sudo python3 i2c.py strobe on  --bus 4 --mode normal
    sudo python3 i2c.py strobe off --bus 4
    sudo python3 i2c.py strobe show --bus 4

EEPROM:

    sudo python3 i2c.py eeprom detect  --bus 4
    sudo python3 i2c.py eeprom dump    --bus 4 --out cal.bin
    sudo python3 i2c.py eeprom read    --bus 4 --chip 0x51 --offset 0 --length 16
    sudo python3 i2c.py eeprom write   --bus 4 --chip 0x51 --offset 0 --data 0xAA
    sudo python3 i2c.py eeprom restore --bus 4 --in cal.bin
    sudo python3 i2c.py eeprom clear   --bus 4 --yes

Low-level (drop-in replacement for i2c_read / i2c_write C tools):

    sudo python3 i2c.py read  4 0x1a 0x306D 1
    sudo python3 i2c.py write 4 0x1a 0x306D 0x02
    sudo python3 i2c.py read  4 0x51 0x00  16  --reg-bits 8     # EEPROM raw

All integer args accept ``0x..``, ``0b..``, ``0o..`` or decimal.
Slave addresses accept either 7-bit (``0x1a``) or 8-bit "write address"
form (``0x34``) - 8-bit form is auto-detected (>0x7F) and shifted.
"""

from __future__ import annotations

import argparse
import ctypes
import errno
import fcntl
import os
import sys
import time
from typing import Iterable, List, Sequence


# -------------------------------------------------------------------- #
#  Linux I2C ioctl bindings (from <linux/i2c-dev.h> / <linux/i2c.h>)
# -------------------------------------------------------------------- #

I2C_SLAVE        = 0x0703
I2C_SLAVE_FORCE  = 0x0706
I2C_RDWR         = 0x0707
I2C_M_RD         = 0x0001


class _I2cMsg(ctypes.Structure):
    _fields_ = [
        ("addr",  ctypes.c_uint16),
        ("flags", ctypes.c_uint16),
        ("len",   ctypes.c_uint16),
        ("buf",   ctypes.c_void_p),
    ]


class _I2cRdwrIoctlData(ctypes.Structure):
    _fields_ = [
        ("msgs",  ctypes.POINTER(_I2cMsg)),
        ("nmsgs", ctypes.c_uint32),
    ]


# -------------------------------------------------------------------- #
#  Thin I2C bus wrapper
# -------------------------------------------------------------------- #

class I2CBus:
    """RAII wrapper around ``/dev/i2c-N``."""

    def __init__(self, bus: int):
        path = f"/dev/i2c-{bus}"
        try:
            self._fd = os.open(path, os.O_RDWR)
        except FileNotFoundError as e:
            raise SystemExit(
                f"FATAL: {path} not found.\n"
                "  - Is I2C enabled?  Run `sudo raspi-config` -> Interfaces -> I2C.\n"
                "  - On Pi5, CAM1 = bus 4, CAM0 = bus 6.  Check `ls /dev/i2c-*`."
            ) from e
        except PermissionError as e:
            raise SystemExit(
                f"FATAL: cannot open {path}: {e}\n"
                "  Re-run with sudo, or add your user to the 'i2c' group."
            ) from e
        self._bus = bus

    def __enter__(self) -> "I2CBus":
        return self

    def __exit__(self, *exc):
        self.close()

    def close(self):
        if self._fd is not None:
            try:
                os.close(self._fd)
            finally:
                self._fd = None

    def transfer(self, msgs: Sequence[_I2cMsg]) -> None:
        arr_t = _I2cMsg * len(msgs)
        arr = arr_t(*msgs)
        ioctl_data = _I2cRdwrIoctlData(
            msgs=ctypes.cast(arr, ctypes.POINTER(_I2cMsg)),
            nmsgs=len(msgs),
        )
        fcntl.ioctl(self._fd, I2C_RDWR, ioctl_data)

    def write_then_read(self, addr7: int, write_buf: bytes, read_len: int) -> bytes:
        wbuf = (ctypes.c_uint8 * len(write_buf))(*write_buf)
        rbuf = (ctypes.c_uint8 * read_len)()
        msgs = [
            _I2cMsg(addr=addr7, flags=0,        len=len(write_buf),
                    buf=ctypes.cast(wbuf, ctypes.c_void_p)),
            _I2cMsg(addr=addr7, flags=I2C_M_RD, len=read_len,
                    buf=ctypes.cast(rbuf, ctypes.c_void_p)),
        ]
        self.transfer(msgs)
        return bytes(rbuf)

    def write(self, addr7: int, write_buf: bytes) -> None:
        wbuf = (ctypes.c_uint8 * len(write_buf))(*write_buf)
        msg = _I2cMsg(addr=addr7, flags=0, len=len(write_buf),
                      buf=ctypes.cast(wbuf, ctypes.c_void_p))
        self.transfer([msg])

    def probe(self, addr7: int) -> bool:
        """Return True if the slave ACKs a 0-length write or 1-byte read."""
        try:
            msg = _I2cMsg(addr=addr7, flags=0, len=0, buf=0)
            self.transfer([msg])
            return True
        except OSError as e:
            if e.errno in (errno.ENXIO, errno.EREMOTEIO, errno.ETIMEDOUT):
                return False
            try:
                rbuf = (ctypes.c_uint8 * 1)()
                msg = _I2cMsg(addr=addr7, flags=I2C_M_RD, len=1,
                              buf=ctypes.cast(rbuf, ctypes.c_void_p))
                self.transfer([msg])
                return True
            except OSError:
                return False


# -------------------------------------------------------------------- #
#  Generic register helpers (8-bit OR 16-bit register addressing)
# -------------------------------------------------------------------- #

def _normalize_addr(addr: int) -> int:
    if addr < 0:
        raise ValueError(f"slave address must be non-negative, got {addr}")
    if addr > 0x7F:
        return (addr & 0xFE) >> 1
    return addr


def _reg_to_bytes(reg: int, reg_bits: int) -> bytes:
    if reg_bits == 8:
        if not 0 <= reg <= 0xFF:
            raise ValueError(f"reg 0x{reg:X} doesn't fit in 8 bits")
        return bytes([reg & 0xFF])
    if reg_bits == 16:
        if not 0 <= reg <= 0xFFFF:
            raise ValueError(f"reg 0x{reg:X} doesn't fit in 16 bits")
        return bytes([(reg >> 8) & 0xFF, reg & 0xFF])
    raise ValueError(f"unsupported reg_bits={reg_bits}")


def reg_read(bus: I2CBus, addr: int, reg: int,
             length: int = 1, reg_bits: int = 16) -> bytes:
    addr7 = _normalize_addr(addr)
    if not 1 <= length <= 100:
        raise ValueError("length must be 1..100")
    return bus.write_then_read(addr7, _reg_to_bytes(reg, reg_bits), length)


def reg_write(bus: I2CBus, addr: int, reg: int,
              data, reg_bits: int = 16) -> None:
    addr7 = _normalize_addr(addr)
    payload = bytes([data & 0xFF]) if isinstance(data, int) else bytes(data)
    bus.write(addr7, _reg_to_bytes(reg, reg_bits) + payload)


# -------------------------------------------------------------------- #
#  IMX296 strobe register helpers (manual section 5.3)
# -------------------------------------------------------------------- #

IMX296_ADDR = 0x1A   # 7-bit slave address of the IMX296 sensor

_STROBE_COMMON = [
    (0x3026, 0x0F),
    (0x3029, 0x21),
]

_STROBE_TIMING = [
    (0x3070, 0x00), (0x3071, 0x00), (0x3072, 0x00),  # group 1 start
    (0x3074, 0x2C), (0x3075, 0x01), (0x3076, 0x00),  # group 1 end
    (0x307C, 0x00), (0x307D, 0x00), (0x307E, 0x00),  # group 2 start
    (0x3080, 0x2C), (0x3081, 0x01), (0x3082, 0x00),  # group 2 end
]

_STROBE_MODE_REGS = {
    "trigger": [(0x306D, 0x02), (0x3079, 0x0A)],
    "normal":  [(0x306D, 0x01), (0x3079, 0x09)],
}

# All registers the strobe sequence touches - used by `strobe show`.
_STROBE_ALL_REGS = (
    [r for r, _ in _STROBE_COMMON]
    + [0x306D, 0x3079]
    + [r for r, _ in _STROBE_TIMING]
)


def strobe_on(bus: I2CBus, mode: str, addr: int = IMX296_ADDR) -> None:
    """Apply the full strobe-enable sequence (manual 5.3.1 + 5.3.2 + timing)."""
    if mode not in _STROBE_MODE_REGS:
        raise ValueError(f"strobe mode must be one of {list(_STROBE_MODE_REGS)}")
    for reg, val in _STROBE_COMMON:
        reg_write(bus, addr, reg, val, reg_bits=16)
    for reg, val in _STROBE_MODE_REGS[mode]:
        reg_write(bus, addr, reg, val, reg_bits=16)
    for reg, val in _STROBE_TIMING:
        reg_write(bus, addr, reg, val, reg_bits=16)


def strobe_off(bus: I2CBus, addr: int = IMX296_ADDR) -> None:
    """Clear the two strobe-enable registers (0x306D, 0x3079) to 0x00.

    This is the best-effort 'off' - timing registers are left as-is
    since they have no effect when the enable bits are cleared.
    Power-cycle the camera if you want a true factory state.
    """
    reg_write(bus, addr, 0x306D, 0x00, reg_bits=16)
    reg_write(bus, addr, 0x3079, 0x00, reg_bits=16)


def strobe_show(bus: I2CBus, addr: int = IMX296_ADDR) -> List[tuple]:
    rows = []
    for r in _STROBE_ALL_REGS:
        v = reg_read(bus, addr, r, length=1, reg_bits=16)[0]
        rows.append((r, v))
    return rows


# -------------------------------------------------------------------- #
#  FT24C08A on-board EEPROM helpers (manual chapter 6)
# -------------------------------------------------------------------- #

EEPROM_CHIPS = (0x50, 0x51, 0x52, 0x53)
EEPROM_PAGE_SIZE = 256             # bytes per chip
EEPROM_HW_PAGE = 16                # hardware page-write size for FT24C08A
EEPROM_TOTAL = EEPROM_PAGE_SIZE * len(EEPROM_CHIPS)   # 1024
EEPROM_TWR_S = 0.006               # tWR + slack (datasheet says 5ms)


def eeprom_detect(bus: I2CBus) -> List[int]:
    return [a for a in EEPROM_CHIPS if bus.probe(a)]


def eeprom_read(bus: I2CBus, chip: int, offset: int, length: int) -> bytes:
    chip = _normalize_addr(chip)
    if chip not in EEPROM_CHIPS:
        raise ValueError(f"chip 0x{chip:02X} is not an EEPROM page (use 0x50..0x53)")
    if not 0 <= offset <= 0xFF:
        raise ValueError("offset must be 0..255")
    if length < 1 or offset + length > EEPROM_PAGE_SIZE:
        raise ValueError(
            "read crosses the 256-byte chip boundary - use the next chip "
            "(0x50 -> 0x51 -> 0x52 -> 0x53) for the next page"
        )
    return bus.write_then_read(chip, bytes([offset]), length)


def eeprom_write_block(bus: I2CBus, chip: int, offset: int, data: bytes) -> None:
    """Write any length of bytes starting at (chip, offset).

    Splits on the FT24C08A's 16-byte hardware page boundary and rolls
    over from chip 0x50 -> 0x51 -> 0x52 -> 0x53 at 256-byte boundaries.
    """
    chip = _normalize_addr(chip)
    if chip not in EEPROM_CHIPS:
        raise ValueError(f"chip 0x{chip:02X} is not an EEPROM page (use 0x50..0x53)")
    if not 0 <= offset <= 0xFF:
        raise ValueError("offset must be 0..255")
    if not data:
        return

    pos = 0
    cur_chip = chip
    cur_off = offset
    while pos < len(data):
        room_in_hw_page = EEPROM_HW_PAGE - (cur_off % EEPROM_HW_PAGE)
        room_in_chip = EEPROM_PAGE_SIZE - cur_off
        chunk = min(room_in_hw_page, room_in_chip, len(data) - pos)
        bus.write(cur_chip, bytes([cur_off & 0xFF]) + data[pos:pos + chunk])
        time.sleep(EEPROM_TWR_S)
        pos += chunk
        cur_off += chunk
        # Only roll over to the next chip if we still have data to write -
        # writing exactly to offset 0xFF must not error out at the boundary.
        if cur_off >= EEPROM_PAGE_SIZE and pos < len(data):
            idx = EEPROM_CHIPS.index(cur_chip)
            if idx + 1 >= len(EEPROM_CHIPS):
                raise ValueError("write ran off the end of the last EEPROM chip (0x53)")
            cur_chip = EEPROM_CHIPS[idx + 1]
            cur_off = 0


def eeprom_dump_all(bus: I2CBus) -> bytes:
    out = bytearray()
    for chip in EEPROM_CHIPS:
        out += eeprom_read(bus, chip, 0, EEPROM_PAGE_SIZE)
    return bytes(out)


def eeprom_restore_all(bus: I2CBus, blob: bytes) -> None:
    """Write a 1024-byte dump back to the four EEPROM chips."""
    if len(blob) != EEPROM_TOTAL:
        raise ValueError(
            f"restore expects exactly {EEPROM_TOTAL} bytes (got {len(blob)})"
        )
    eeprom_write_block(bus, EEPROM_CHIPS[0], 0, blob)


def eeprom_clear_all(bus: I2CBus, fill: int = 0xFF) -> None:
    eeprom_write_block(bus, EEPROM_CHIPS[0], 0, bytes([fill & 0xFF]) * EEPROM_TOTAL)


# -------------------------------------------------------------------- #
#  Pretty printing
# -------------------------------------------------------------------- #

def _hexdump(data: bytes, base: int = 0) -> str:
    lines = []
    for i in range(0, len(data), 16):
        chunk = data[i:i + 16]
        hex_part = " ".join(f"{b:02X}" for b in chunk)
        ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)
        lines.append(f"{base + i:04X}  {hex_part:<47}  {ascii_part}")
    return "\n".join(lines)


# -------------------------------------------------------------------- #
#  CLI
# -------------------------------------------------------------------- #

def _autoint(s: str) -> int:
    return int(s, 0)


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="i2c.py",
        description="IMX296 strobe + on-board FT24C08A EEPROM tool. "
                    "Also a drop-in i2c_read / i2c_write replacement.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="See the top of this script for the full command cheatsheet.",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    # --- low-level read / write ----------------------------------------
    sp = sub.add_parser("read", help="generic register read (replaces ./i2c_read)")
    sp.add_argument("bus", type=_autoint)
    sp.add_argument("addr", type=_autoint, help="slave addr (7-bit 0x1a or 8-bit 0xA0)")
    sp.add_argument("reg",  type=_autoint)
    sp.add_argument("length", type=_autoint, nargs="?", default=1)
    sp.add_argument("--reg-bits", type=int, default=16, choices=(8, 16),
                    help="register-address width (16 for IMX296 sensor, 8 for EEPROM)")

    sp = sub.add_parser("write", help="generic register write (replaces ./i2c_write)")
    sp.add_argument("bus", type=_autoint)
    sp.add_argument("addr", type=_autoint)
    sp.add_argument("reg",  type=_autoint)
    sp.add_argument("value", type=_autoint, nargs="+")
    sp.add_argument("--reg-bits", type=int, default=16, choices=(8, 16))

    # --- strobe ---------------------------------------------------------
    sp = sub.add_parser("strobe", help="IMX296 strobe helpers (manual chapter 5)")
    ss = sp.add_subparsers(dest="strobe_cmd", required=True)

    on = ss.add_parser("on", aliases=["enable"], help="turn strobe on")
    on.add_argument("--bus", type=_autoint, required=True,
                    help="i2c bus number (Pi5: 4 = CAM1, 6 = CAM0)")
    on.add_argument("--mode", choices=("trigger", "normal"), required=True,
                    help="trigger = external XTR pulse, normal = continuous stream")
    on.add_argument("--addr", type=_autoint, default=IMX296_ADDR,
                    help=f"sensor slave addr (default 0x{IMX296_ADDR:02X})")

    off = ss.add_parser("off", aliases=["disable"], help="turn strobe off")
    off.add_argument("--bus",  type=_autoint, required=True)
    off.add_argument("--addr", type=_autoint, default=IMX296_ADDR)

    sh = ss.add_parser("show", help="read back every strobe-related register")
    sh.add_argument("--bus",  type=_autoint, required=True)
    sh.add_argument("--addr", type=_autoint, default=IMX296_ADDR)

    # --- eeprom ---------------------------------------------------------
    sp = sub.add_parser("eeprom", help="on-board FT24C08A EEPROM (manual chapter 6)")
    es = sp.add_subparsers(dest="eeprom_cmd", required=True)

    det = es.add_parser("detect", help="probe 0x50..0x53 and report ACKs")
    det.add_argument("--bus", type=_autoint, required=True)

    rd = es.add_parser("read", help="read N bytes starting at offset")
    rd.add_argument("--bus",    type=_autoint, required=True)
    rd.add_argument("--chip",   type=_autoint, required=True, help="0x50, 0x51, 0x52 or 0x53")
    rd.add_argument("--offset", type=_autoint, default=0)
    rd.add_argument("--length", type=_autoint, default=16)

    wr = es.add_parser("write", help="write 1+ bytes starting at offset")
    wr.add_argument("--bus",    type=_autoint, required=True)
    wr.add_argument("--chip",   type=_autoint, required=True)
    wr.add_argument("--offset", type=_autoint, required=True)
    g = wr.add_mutually_exclusive_group(required=True)
    g.add_argument("--data",      type=_autoint, nargs="+",
                   help="byte values, e.g. --data 0xAA 0xBB 0xCC")
    g.add_argument("--from-file", help="path to a binary file to write")

    dp = es.add_parser("dump", help="read all 4 chips (1024 bytes total)")
    dp.add_argument("--bus", type=_autoint, required=True)
    dp.add_argument("--out", help="save the full 1024-byte blob to this file")

    rs = es.add_parser("restore", help="write a 1024-byte dump back to all 4 chips")
    rs.add_argument("--bus", type=_autoint, required=True)
    rs.add_argument("--in",  dest="infile", required=True,
                    help="path to a 1024-byte file (typically from `eeprom dump --out`)")

    cl = es.add_parser("clear", help="erase all 1024 bytes (fills with 0xFF)")
    cl.add_argument("--bus",  type=_autoint, required=True)
    cl.add_argument("--fill", type=_autoint, default=0xFF, help="byte to fill with (default 0xFF)")
    cl.add_argument("--yes",  action="store_true", required=True,
                    help="confirm: this is destructive")

    return p


# -------------------------------------------------------------------- #
#  CLI dispatch
# -------------------------------------------------------------------- #

def _cmd_read(args) -> int:
    with I2CBus(args.bus) as bus:
        data = reg_read(bus, args.addr, args.reg,
                        length=args.length, reg_bits=args.reg_bits)
    width = args.reg_bits // 4
    print(f"==== I2C read: bus=0x{args.bus:X} addr=0x{_normalize_addr(args.addr):02X} "
          f"reg=0x{args.reg:0{width}X} ({args.length} byte{'s' if args.length>1 else ''}) ====")
    for i, b in enumerate(data):
        print(f"  reg 0x{args.reg + i:0{width}X} : 0x{b:02X}")
    return 0


def _cmd_write(args) -> int:
    payload = bytes(v & 0xFF for v in args.value)
    with I2CBus(args.bus) as bus:
        reg_write(bus, args.addr, args.reg, payload, reg_bits=args.reg_bits)
    width = args.reg_bits // 4
    print(f"==== I2C write: bus=0x{args.bus:X} addr=0x{_normalize_addr(args.addr):02X} "
          f"reg=0x{args.reg:0{width}X} <- {' '.join(f'0x{b:02X}' for b in payload)} ====")
    return 0


def _cmd_strobe_on(args) -> int:
    with I2CBus(args.bus) as bus:
        strobe_on(bus, args.mode, addr=args.addr)
    print(f"strobe ON  : bus={args.bus}  addr=0x{_normalize_addr(args.addr):02X}  mode={args.mode}")
    print("  ! strobe settings only stick while the camera stream is OFF.")
    print("    If libcamera/rpicam/v4l2 is streaming, stop it first then re-run.")
    return 0


def _cmd_strobe_off(args) -> int:
    with I2CBus(args.bus) as bus:
        strobe_off(bus, addr=args.addr)
    print(f"strobe OFF : bus={args.bus}  addr=0x{_normalize_addr(args.addr):02X}")
    print("  (cleared 0x306D and 0x3079 to 0x00; power-cycle for a full reset)")
    return 0


def _cmd_strobe_show(args) -> int:
    with I2CBus(args.bus) as bus:
        rows = strobe_show(bus, addr=args.addr)
    print(f"strobe registers on bus={args.bus} addr=0x{_normalize_addr(args.addr):02X}:")
    for reg, val in rows:
        note = ""
        if reg == 0x306D:
            note = "  <- 0x02 trigger / 0x01 normal / 0x00 off"
        elif reg == 0x3079:
            note = "  <- 0x0A trigger / 0x09 normal / 0x00 off"
        print(f"  0x{reg:04X} = 0x{val:02X}{note}")
    return 0


def _cmd_eeprom_detect(args) -> int:
    with I2CBus(args.bus) as bus:
        found = eeprom_detect(bus)
    if not found:
        print("No EEPROM chips at 0x50..0x53 responded.")
        print("  - Check that the camera is connected to the right CSI port.")
        print(f"  - Try `i2cdetect -y {args.bus}` to see what is actually on the bus.")
        return 1
    print("EEPROM chips found:", " ".join(f"0x{a:02X}" for a in found))
    if len(found) != len(EEPROM_CHIPS):
        print(f"  WARNING: expected all {len(EEPROM_CHIPS)} chips (0x50..0x53),"
              f" only saw {len(found)}.")
        return 1
    return 0


def _cmd_eeprom_read(args) -> int:
    with I2CBus(args.bus) as bus:
        data = eeprom_read(bus, args.chip, args.offset, args.length)
    print(f"EEPROM 0x{_normalize_addr(args.chip):02X}  offset=0x{args.offset:02X}  "
          f"length={args.length}")
    print(_hexdump(data, base=args.offset))
    return 0


def _cmd_eeprom_write(args) -> int:
    if args.from_file:
        with open(args.from_file, "rb") as f:
            payload = f.read()
    else:
        payload = bytes(v & 0xFF for v in args.data)
    with I2CBus(args.bus) as bus:
        eeprom_write_block(bus, args.chip, args.offset, payload)
    print(f"wrote {len(payload)} byte(s) to EEPROM 0x{_normalize_addr(args.chip):02X} "
          f"@ offset 0x{args.offset:02X}")
    return 0


def _cmd_eeprom_dump(args) -> int:
    with I2CBus(args.bus) as bus:
        blob = eeprom_dump_all(bus)
    if args.out:
        with open(args.out, "wb") as f:
            f.write(blob)
        print(f"saved {len(blob)} bytes to {args.out}")
    else:
        for i, chip in enumerate(EEPROM_CHIPS):
            print(f"--- chip 0x{chip:02X} ---")
            print(_hexdump(blob[i*256:(i+1)*256], base=0))
    return 0


def _cmd_eeprom_restore(args) -> int:
    with open(args.infile, "rb") as f:
        blob = f.read()
    if len(blob) != EEPROM_TOTAL:
        print(f"ERROR: {args.infile} is {len(blob)} bytes, expected {EEPROM_TOTAL}",
              file=sys.stderr)
        return 1
    with I2CBus(args.bus) as bus:
        eeprom_restore_all(bus, blob)
    print(f"restored {EEPROM_TOTAL} bytes from {args.infile}")
    return 0


def _cmd_eeprom_clear(args) -> int:
    with I2CBus(args.bus) as bus:
        eeprom_clear_all(bus, fill=args.fill)
    print(f"cleared all {EEPROM_TOTAL} bytes (filled with 0x{args.fill & 0xFF:02X})")
    return 0


_DISPATCH = {
    ("read",   None):              _cmd_read,
    ("write",  None):              _cmd_write,
    ("strobe", "on"):              _cmd_strobe_on,
    ("strobe", "enable"):          _cmd_strobe_on,
    ("strobe", "off"):             _cmd_strobe_off,
    ("strobe", "disable"):         _cmd_strobe_off,
    ("strobe", "show"):            _cmd_strobe_show,
    ("eeprom", "detect"):          _cmd_eeprom_detect,
    ("eeprom", "read"):            _cmd_eeprom_read,
    ("eeprom", "write"):           _cmd_eeprom_write,
    ("eeprom", "dump"):            _cmd_eeprom_dump,
    ("eeprom", "restore"):         _cmd_eeprom_restore,
    ("eeprom", "clear"):           _cmd_eeprom_clear,
}


def main(argv=None) -> int:
    args = _build_parser().parse_args(argv)
    sub = getattr(args, "strobe_cmd", None) or getattr(args, "eeprom_cmd", None)
    fn = _DISPATCH.get((args.cmd, sub))
    if fn is None:
        print(f"unknown subcommand: {args.cmd} {sub}", file=sys.stderr)
        return 2
    try:
        return fn(args)
    except OSError as e:
        if e.errno in (errno.ENXIO, errno.EREMOTEIO):
            print(f"I2C transaction failed: device did not ACK (errno={e.errno}).\n"
                  "  - Check the slave address (sensor 0x1a, EEPROM 0x50..0x53).\n"
                  "  - Make sure no streaming app is hogging the camera.\n"
                  "  - On Pi5 use --bus 4 for CAM1 or --bus 6 for CAM0.",
                  file=sys.stderr)
        else:
            print(f"I2C transaction failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
                  file=sys.stderr)
        else:
            print(f"I2C transaction failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
