<!-- SPDX-FileCopyrightText: 2026 roolrz -->
<!-- SPDX-License-Identifier: Apache-2.0 -->

# Pi 5 image distribution

The [image-distribution repository](https://github.com/HypeR-Proj/pi5-images) builds
compressed images and optional draft releases through manual workflow dispatch.
It resolves the current repo manifest and records exact source inputs. Public release
publication is manual. A developer workspace can also compose images through its Make
targets; ordinary builds resolve the latest qualified appliance channel automatically.

## Ownership

- HypeR owns its Apache-2.0 kernel, Native applications, board policy, guest
  device trees, external-input download locks and reusable image composition tools.
- `io-vm` owns Linux/BusyBox builds, Linux modules, appliance startup policy
  and publication with matching corresponding sources.
- The distribution repository resolves the component main branches, records their
  exact commits, includes official Pi DTBs/overlays and optional Alpine payloads,
  and releases the assembled image.
  It does not update the board's EEPROM.

The combined image contains independently licensed components; it is not
licensed wholesale under Apache-2.0. HypeR retains its own license. Preserve
component license texts, copyright notices and applicable NOTICE files, and
provide the corresponding source/build materials required by each component.
A “mixed licenses” label or repository separation alone does not discharge
these obligations.

## Release inputs and outputs

The distribution repository resolves component sources once per run and records the
board profile and build configuration. It downloads the latest qualified RPi5 I/O appliance package and preserves
its digest-bound source materials. Official Pi boot inputs and Alpine versions remain selected by the
shared build configuration. No contributor advances an internal source or appliance lock.

For coupled control-plane and Linux appliance changes, use topic PRs and manually test
the combined system candidate in `HypeR-Proj/ci` before merging. Appliance source
changes are qualified in `io-vm`; system tests consume the latest qualified package.
Image generation is independently triggered by hand and never gates system tests or merges. See
[appliance adoption](https://hyper-proj.github.io/io-vm/docs/hyper-integration.html#protocol-version-3-appliance-requirement).
An explicit `IO_VM_PACKAGE` selects a development appliance without publishing a release.

Generate a resolved release inventory containing the HypeR binary checksums,
I/O VM payload checksums (and OCI digest when imported) and matching source artifact, official Pi firmware revision
and DTB/overlay checksums, and Alpine checksums and required source materials.
Record qualification results. This inventory records what was assembled; it
is not a second set of dependency selections. Board EEPROM remains an external
prerequisite and its tested version must be recorded separately.

Adopt a HypeR revision after merge, successful CI and required integration
checks. Local working trees and development reassemblies remain development
inputs, not release identities.

Release assets contain compressed whole-disk images (`.img.xz`), checksums,
resolved input records, component inventories, notices and companion source archives.
The distribution pipeline collects Rust dependency/std sources for every
profile, matching libc materials for I/O profiles, and Alpine package/kernel
sources for the full SD profile. See the
[artifact guide](https://github.com/HypeR-Proj/pi5-images/blob/main/ARTIFACTS.md)
for image selection and the
[component and source inventory](https://github.com/HypeR-Proj/pi5-images/blob/main/DISTRIBUTION.md)
for the supplied materials.

A boot-file update bundle is also planned. It must preserve Linux Image runtime padding
and state its required disk layout; it is not yet a dedicated Make target.
Replacing individual boot files is appropriate only when the partition and
configuration contracts remain compatible.

Hardware results currently establish Native boot, Linux appliance userspace
and SD-backed configuration-directory reads on Pi 5 D0. A two-vCPU Alpine
guest has also passed three secondary-CPU off/on cycles, ordinary reboot with
a synced file preserved on its ext4 root, and ordinary poweroff while the I/O
VM remained available. Those lifecycle results precede the combined SDIO1/RP1
deployment. The combined deployment using the published Pi 5 I/O VM pin then
completed 1 GiB Native/guest writes with readback and bidirectional guest TCP
measurements on 2026-10-06; see the
[exploratory survey](https://github.com/HypeR-Proj/HypeR/blob/8d42d047058a2b58a291803700e86487fb723f7a/README.md#exploratory-pi-5-io-measurements).
Power-loss durability, device-reset recovery, physical DMA retirement and
extended/concurrent load remain [deferred qualification](https://hyper-proj.github.io/HypeR/docs/project/roadmap.html#deferred-hardware-qualification).
These historical results do not certify a newly built image on physical hardware.

The [manual hardware fixtures](https://github.com/HypeR-Proj/ci/blob/main/hardware/storage/README.md) create
separate development images under explicit output directories. They enlarge
the test configuration partition and optionally add guest iperf3; they are not
default build or distribution profiles. Their manifests record the actual
source state and artifact hashes. Publishing such a test image would also
require carrying its additional package inventory and license/source materials.
