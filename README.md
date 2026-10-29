<!-- SPDX-FileCopyrightText: 2026 roolrz -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# HypeR Pi 5 images

Downloadable Raspberry Pi 5 SD-card images for [HypeR](https://github.com/HypeR-Proj/HypeR).
For HypeR with the Linux I/O VM, SD storage and an Alpine guest, choose
**`hyper-rpi5-sd.img.xz`** from [Releases](https://github.com/HypeR-Proj/pi5-images/releases).
See [ARTIFACTS.md](ARTIFACTS.md) for the smaller bring-up images and flashing instructions.

## Downloads

- `hyper-rpi5-sd.img.xz`: full system image, approximately 3 GiB after decompression.
- `hyper-rpi5-io-bringup.img.xz`: diskless Linux I/O VM bring-up image.
- `hyper-rpi5-native.img.xz`: HypeR kernel and Native shell image.
- `hyper-rpi5-<profile>-materials.tar.xz`: source archives, input versions and notices.
- `SHA256SUMS`: download checksums.

Images contain a partition table and are written to the **whole SD card**.
Flashing replaces existing partitions and data. The board's EEPROM is not updated.

## Builds and versions

The manual image workflow resolves each HypeR component's `main` once and records the
result in `source-inventory.json`. There is no HypeR version pin to advance. Kernel,
firmware and Alpine upstream versions still follow their owning component's dependency policy.

For I/O profiles, the selected `io-vm` source is built and its exported package must match
the source inventory. Corresponding sources include the installed cross libc's exact source
packages and retained runtime notices. Historical records in `materials/legacy` are not inputs
to new builds. Use `python3 scripts/build.py --checkout-only` to resolve source inputs first.

PRs run recipe self tests. Image creation and system acceptance are manual. A successful image
workflow can create a draft prerelease; publication remains an explicit release action.
QEMU smoke tests cover Native and I/O payloads, not physical Pi 5 hardware qualification.

## Script checks

Use Python 3.11 or newer. Install `requirements-dev.txt`, then run:

```sh
python3 -m black --check scripts tests
python3 -m unittest discover -s tests
```

Run `python3 -m black scripts tests` to apply the shared format.

## HypeR workspace integration

This repository is part of the [HypeR workspace](https://github.com/HypeR-Proj/HypeR).
The image workflow is manual. It resolves current component `main` branches once per build;
`source-inventory.json` records the selected inputs. `materials/legacy` is historical only.
Appliance build records carry matching libc sources; there is no HypeR revision to advance manually.
