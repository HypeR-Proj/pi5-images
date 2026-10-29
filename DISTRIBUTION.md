<!-- SPDX-FileCopyrightText: 2026 roolrz -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Image components and source materials

The disk image combines independently licensed components. HypeR-authored
kernel, application and SDK code retains Apache-2.0; Linux, BusyBox, libraries,
firmware inputs and Alpine packages retain their own licenses. This repository's
Apache-2.0 license covers its build scripts, not every file in the disk image.

## Components

| Component | License information | Accompanying materials |
| --- | --- | --- |
| Image build scripts | Apache-2.0 | This repository's LICENSE and release commit |
| HypeR-authored kernel, applications and SDK | Apache-2.0 | HypeR-LICENSE, HypeR-NOTICE when present, HypeR-source.tar.gz |
| Rust standard library, runtime and linked crates | Respective upstream licenses | rust-materials.tar.gz: lockfile-selected registry source archives, original license files, assembled patched std source and COPYRIGHT-library.html |
| I/O VM Linux and bridge modules | Linux license terms and per-file exceptions; bridge modules GPL-2.0-only | io-vm-sources.tar.xz, io-vm-kernel.config, io-vm.lock.json and io-vm-manifest.json |
| I/O VM BusyBox and services | BusyBox GPL terms; project-authored services Apache-2.0; linked libraries retain their own licenses | Appliance sources and build configuration in io-vm-sources.tar.xz; the libc-materials directory in that archive supplies the identified glibc sources, Ubuntu patches/build recipes and GCC runtime license texts |
| Pi device trees and overlays | Upstream per-file licenses | pi-boot-sources.tar.gz, pi-boot.lock.json and boot-notices.txt |
| Alpine kernel and rootfs (SD profile) | Per-package licenses | alpine-materials.tar.gz: installed-package inventory, exact aports recipes, patches, configs and checksum-verified upstream sources, including the guest kernel |
| Board EEPROM and its bundled firmware | Vendor terms | Not included or updated by these images |

## Companion archive

Each `hyper-rpi5-<profile>-materials.tar.xz` accompanies one image and contains:

- `inventory.json`: HypeR revision, build profile, image size and SHA-256, and
  hashes of the recorded inputs.
- `source-inventory.json` and the exact assembled HypeR source archive.
- Official Pi boot-input sources, lock and notices.
- `rust-materials.tar.gz`: a superset of kernel/app registry dependencies and
  the assembled patched Rust standard-library sources with upstream notices.
- For I/O profiles, the matched appliance build manifest, source archive and kernel
  configuration. The source archive includes the collected libc materials.
- For the SD profile, `alpine-materials.tar.gz` with the guest kernel and
  installed package sources and build recipes.
- Component documentation and checksums.

The inventory records artifact identities. Hardware test results are documented
separately from the source and license materials.

## Source provenance

The build resolves component main branches once and records the resulting source inventory.
I/O runtime files and source materials are verified against their matching build records. Official Pi
boot inputs are validated by HypeR's download tooling. Source archives retain
the upstream license files they contain; they are not relicensed by this repository.

The image build and bundle scripts are available in `scripts/`. Release assets
are assembled from the same Actions outputs without rebuilding the images.

## Material identity checks

Registry archives are verified against Cargo.lock. Alpine packages select aports
commits from their installed APK database; external recipe inputs are verified
against APKBUILD SHA-512 hashes. Build recipes are archived, not executed by the
collector. The guest kernel source selection is bound to its Image hash and
module release. Static libc material selection is bound to the selected I/O source revision and its actual cross-libc package versions,
with checksummed source descriptors and archives retained.

Upstream source records under `materials/` identify corresponding sources; they do not select
alternative image dependencies. `materials/legacy` preserves historical release evidence only.
Service source and link commands accompany the I/O archive for rebuilding against a modified
compatible libc.
