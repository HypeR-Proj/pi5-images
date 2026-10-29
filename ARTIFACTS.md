<!-- SPDX-FileCopyrightText: 2026 roolrz -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Pi 5 image downloads

All `.img.xz` files contain a **whole-disk image**, including a partition table.
Decompress before flashing (or use a flasher that supports XZ). Write the image
to the whole SD card, **not an existing boot partition**. This replaces the card's
partition table and data. Verify SHA256SUMS and the destination device first.

| Filename | Uncompressed layout | Use |
| --- | --- | --- |
| **hyper-rpi5-sd.img.xz** | About 3 GiB: 1 GiB FAT boot/configuration partition + 2 GiB Alpine ext4 root disk, plus partition/alignment space | **Full system image. Choose this for the Pi SD backend and Alpine VM.** HypeR shell + resident I/O VM; Linux owns the SD controller, dm-linear exports volumes, HypeR mounts configuration at `/data`. Alpine is installed but not autostarted: `vmm start alpine`, then `vmm console alpine`. |
| hyper-rpi5-io-bringup.img.xz | About 69.2 MB (66 MiB): 64 MiB FAT boot partition plus partition/alignment space | Minimal Linux guest bring-up. HypeR shell + manual diskless I/O VM (`vmm list` to find its board-configured name; currently `vmm start io`, then `vmm console io`). No SD backend, `/data` mount or Alpine disk. |
| hyper-rpi5-native.img.xz | About 69.2 MB (66 MiB): 64 MiB FAT boot partition plus partition/alignment space | HypeR kernel/Native shell bring-up only. No Linux I/O VM or Alpine. |

Sizes follow the pinned board configuration. Exact uncompressed size and digest
are recorded in each profile's `inventory.json`. Zero-filled space compresses
well, so download size is not the disk's usable capacity. Use a card larger than
the uncompressed image (at least 4 GB for the current full SD layout). Spare card
capacity is not automatically added to the fixed guest partitions.

## Companion downloads

- `SHA256SUMS`: checksums of the published image and companion archives.
- `hyper-rpi5-<profile>-materials.tar.xz`: matching profile inventory, locks,
  notices, source archives and configuration. Includes Rust sources for every
  profile, libc materials for I/O profiles, and Alpine sources for SD. Not a
  bootable image; do not flash.
- `ARTIFACTS.md`: this image-selection guide.
- `DISTRIBUTION.md`: component licenses and supplied source/notice materials.

Actions artifacts (`pi5-native`, `pi5-io-bringup`, `pi5-sd`) contain the image and
unbundled companion files. A draft Release packages the companion files into
one materials archive per image to avoid ambiguous duplicate filenames. Images
are identical between Actions artifacts and the draft; no rebuild occurs during
Release assembly. Successful main builds automatically create a Draft Release
containing all three profiles. Public publication remains manual.

## Licenses and validation

Components retain their individual licenses; HypeR-authored code remains
Apache-2.0. The companion materials archive supplies the source archives and
notices listed in [DISTRIBUTION.md](https://github.com/HypeR-Proj/pi5-images/blob/main/DISTRIBUTION.md).

Native and diskless I/O profiles run QEMU boot/console smoke tests. The full SD
profile has no automated physical-board test; these builds do not record SD
write durability, DMA retirement or power-loss test results.
