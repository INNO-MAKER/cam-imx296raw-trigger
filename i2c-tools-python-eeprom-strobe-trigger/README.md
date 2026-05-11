# i2c-tools — IMX296 GS Camera (trigger + strobe + on-board EEPROM)

A single Python script (`i2c.py`) that lets you drive three things on the
**CAM-IMX296RAW** module over I2C:

- **External trigger** — put the sensor in / out of trigger mode in one
  command (User Manual §4; replaces InnoMaker's standalone
  `imx296_trigger` binary)
- **Strobe** — turn the sensor's strobe output on/off in one command
  (User Manual §5)
- **On-board EEPROM** — read / write / back-up the FT24C08A 1 KB EEPROM
  (User Manual §6)

It also works as a drop-in replacement for the prebuilt `i2c_read` /
`i2c_write` C binaries — same arguments, no compilation needed.

No external dependencies — uses Python 3 stdlib only and talks to
`/dev/i2c-N` directly. Tested on Raspberry Pi OS Bookworm and Trixie,
both 32-bit and 64-bit.

## Which `--bus` number to use? (Raspberry Pi 5)

Every command below takes `--bus N` — that number tells the script which
I2C bus to talk on, which depends on **which CSI port on the Pi5 your
camera ribbon is plugged into**. The bus number has nothing to do with
the camera or the EEPROM — it is decided by the Pi5 hardware itself.

| CSI port on the Pi5 | use this `--bus` |
|---------------------|------------------|
| CAM1                | `--bus 4`        |
| CAM0                | `--bus 6`        |

Not sure? Run `ls /dev/i2c-*` to see which buses exist, then
`i2cdetect -y 4` (or `-y 6`) to confirm which one the camera is on —
you should see the sensor at `0x1a` and the EEPROM at `0x50..0x53`.

## Quick start

```bash
sudo chmod +x i2c.py

# Sanity check: should print "EEPROM chips found: 0x50 0x51 0x52 0x53"
sudo python3 i2c.py eeprom detect --bus 4
```

## External trigger (manual chapter 4)

> Run `trigger on/off` while the camera stream is **off** (no
> `rpicam-hello` / `libcamera-*` / `v4l2` running). The standby toggle in
> the middle of the sequence will not commit cleanly if the kernel driver
> is actively streaming.

```bash
# Enter external-trigger mode: sensor waits for a pulse on the XTR pin
# before exposing each frame.
sudo python3 i2c.py trigger on  --bus 4

# Back to free-running mode (sensor self-exposes at its native frame rate)
sudo python3 i2c.py trigger off --bus 4

# Read back the 4 trigger-related registers with hints
sudo python3 i2c.py trigger show --bus 4
```

This subcommand replaces InnoMaker's standalone `imx296_trigger` ELF
binary. It runs the same 6-write sequence the binary does:

```
0x300A = 0x01       # register-hold (atomic write begin)
0x3000 = 0x01       # standby on
0x3000 = 0x00       # standby off  (commits the new mode)
0x300B = 0x01/0x00  # enable bit   (ON / OFF)
0x30AE = 0x01/0x00  # trigger enable (ON / OFF)
0x300A = 0x00       # register-hold (atomic write end)
```

> Note: the manual references the `imx296_trigger` tool but does not
> document its individual registers. The sequence above was obtained by
> disassembling the prebuilt binary — Python output is byte-for-byte
> identical to the C tool, but the per-register semantic comments are
> best-effort guesses.

## Combining trigger + strobe (the common case)

Hardware-synchronised flash usually wants both: the sensor only fires when
an external pulse arrives, **and** when it does fire it outputs a strobe
pulse to drive a LED.

```bash
sudo python3 i2c.py trigger on --bus 4
sudo python3 i2c.py strobe  on --bus 4 --mode trigger
# now each pulse on XTR -> one frame + one strobe pulse on the STROBE pin
```

To revert:

```bash
sudo python3 i2c.py strobe  off --bus 4
sudo python3 i2c.py trigger off --bus 4
```

## Strobe (manual chapter 5)

> Strobe settings only stick while the camera stream is **off**. Stop any
> running `rpicam-hello` / `libcamera-*` / `v4l2` preview before calling
> `strobe on`.

```bash
# external-trigger mode + strobe out (use with the XTR pin)
sudo python3 i2c.py strobe on  --bus 4 --mode trigger

# continuous-streaming mode + strobe out
sudo python3 i2c.py strobe on  --bus 4 --mode normal

# turn it off again
sudo python3 i2c.py strobe off --bus 4

# read every strobe-related register back, with hints
sudo python3 i2c.py strobe show --bus 4
```

`strobe on` runs the full 16-write sequence from §5.3 of the manual:
common setup (`0x3026=0x0F, 0x3029=0x21`), the two enable registers
(`0x306D`, `0x3079`) for the chosen mode, and the start/end timing
registers (`0x3070..0x3082`).

## EEPROM (manual chapter 6)

The board has an FT24C08A — four "pages" of 256 bytes each at
addresses **0x50, 0x51, 0x52, 0x53** = 1 KB total.

```bash
# Confirm all 4 pages ACK
sudo python3 i2c.py eeprom detect --bus 4

# Back up everything to a file (do this BEFORE writing anything)
sudo python3 i2c.py eeprom dump --bus 4 --out cal_$(date +%Y%m%d).bin

# Read 16 bytes from page 0x51 starting at offset 0
sudo python3 i2c.py eeprom read --bus 4 --chip 0x51 --offset 0 --length 16

# Write a few bytes
sudo python3 i2c.py eeprom write --bus 4 --chip 0x51 --offset 0 --data 0xAA 0xBB 0xCC

# Write a binary blob from a file (handles 16-byte page splits and chip rollover)
sudo python3 i2c.py eeprom write --bus 4 --chip 0x50 --offset 0 --from-file payload.bin

# Restore a previous full dump (must be exactly 1024 bytes)
sudo python3 i2c.py eeprom restore --bus 4 --in cal_20260425.bin

# Erase everything (DESTRUCTIVE — note the required --yes flag)
sudo python3 i2c.py eeprom clear --bus 4 --yes
```

Tip: `eeprom write` automatically respects the chip's 16-byte hardware
page boundary and rolls over from 0x50 → 0x51 → 0x52 → 0x53 once you
fill 256 bytes, so you can pass arbitrary-length data without thinking
about pages.

## Low-level (drop-in for `i2c_read` / `i2c_write`)

```bash
# Same argument order as the original C tools:
sudo python3 i2c.py read  4 0x1a 0x306D 1
sudo python3 i2c.py write 4 0x1a 0x306D 0x02

# EEPROM uses 8-bit register addressing instead of the sensor's 16-bit:
sudo python3 i2c.py read  4 0x51 0x00 16 --reg-bits 8
sudo python3 i2c.py write 4 0x51 0x00 0xAA --reg-bits 8
```

Slave addresses accept either the 7-bit form the manual uses (`0x1a`,
`0x51`) or the 8-bit "write address" form (`0x34`, `0xA2`). The 8-bit
form is auto-detected and shifted, matching the original C tool.

## Troubleshooting

| Symptom                                       | Likely cause                                          |
|-----------------------------------------------|-------------------------------------------------------|
| `FATAL: /dev/i2c-4 not found`                 | I2C disabled in raspi-config, or wrong bus number     |
| `device did not ACK (errno=…)`                | Wrong slave addr, no camera on that port, or stream is running |
| Strobe writes succeed but no pulse on the pin | Camera was streaming when you wrote — stop it and re-run `strobe on` |
| `eeprom detect` only sees 0x50                | Likely a different EEPROM chip — confirm with `i2cdetect -y 4` |
| `trigger on` but sensor still free-runs        | Stream was running — stop `rpicam-hello` / `libcamera-*` and re-run |

## Files

- `i2c.py` — the tool (Python 3, stdlib only)
- `README.md` — this file
