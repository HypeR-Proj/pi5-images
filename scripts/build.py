#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 roolrz
# SPDX-License-Identifier: Apache-2.0
"""Compose release assets from an automatically resolved HypeR workspace."""

import argparse
import hashlib
import importlib.util
import json
import lzma
import os
import re
import shutil
import subprocess
import sys
import tarfile
from pathlib import Path

import materials

ROOT = Path(__file__).resolve().parents[1]


def run(*args, **kwargs):
    return subprocess.run(args, check=True, **kwargs)


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checkout_hyper():
    """Reuse this build's snapshot; a fresh work directory resolves latest main."""
    hyper = ROOT / "work/HypeR"
    if (hyper / "source-inventory.json").exists():
        return hyper
    control = ROOT / "work/control"
    control.mkdir(parents=True, exist_ok=True)
    for name in ("ci", "manifest"):
        run(
            "git",
            "clone",
            "--depth=1",
            f"https://github.com/HypeR-Proj/{name}.git",
            str(control / name),
        )
    snapshot = ROOT / "work/source-snapshot.json"
    run(
        sys.executable,
        str(control / "ci/tools/workspace.py"),
        "resolve",
        "--manifest",
        str(control / "manifest/default.xml"),
        "--output",
        str(snapshot),
    )
    sources = hyper
    run(
        sys.executable,
        str(control / "ci/tools/workspace.py"),
        "checkout",
        "--snapshot",
        str(snapshot),
        "--directory",
        str(sources),
    )
    run(
        sys.executable,
        str(sources / "project.py"),
        "--workspace",
        str(sources),
        "prepare",
    )
    return hyper


def build_image(hyper, profile, io_package=None):
    target = {
        "native": "rpi5-bringup",
        "io-bringup": "rpi5-io-bringup",
        "sd": "rpi5-sd",
    }[profile]
    # Do not inherit local dependency/board overrides into a release build.
    env = {
        name: value
        for name, value in os.environ.items()
        if not name.startswith(("IO_VM_", "RPI5_", "BOARD_", "NATIVE_"))
        and name not in ("MAKEFLAGS", "MAKEOVERRIDES")
    }
    if io_package is not None:
        env["IO_VM_PACKAGE"] = str(io_package)
    run(
        "make",
        target,
        "ARCH=aarch64",
        "BOARD_IMAGE_REPLACE=--replace",
        cwd=hyper,
        env=env,
    )
    return target


def compress_image(image, dist, profile):
    compressed = dist / f"hyper-rpi5-{profile}.img.xz"
    with image.open("rb") as source, lzma.open(compressed, "wb", preset=6) as output:
        shutil.copyfileobj(source, output)
    # Exercise the stream and check it reconstructs exactly the generated disk.
    with lzma.open(compressed, "rb") as stream:
        digest = hashlib.file_digest(stream, "sha256").hexdigest()
    if digest != sha(image):
        raise ValueError("compressed image round-trip mismatch")
    return digest


def collect_hyper_materials(hyper, dist, revision):
    for name in ("LICENSE", "NOTICE"):
        if (hyper / name).exists():
            shutil.copy2(hyper / name, dist / f"HypeR-{name}")
    run(
        sys.executable,
        str(hyper / "project.py"),
        "archive",
        str(dist / "HypeR-source.tar.xz"),
    )
    shutil.copy2(hyper / "source-inventory.json", dist / "source-inventory.json")


def collect_boot_materials(hyper, dist):
    boot = Path(
        subprocess.check_output(
            [sys.executable, "-B", str(hyper / "scripts/fetch-rpi5-boot.py")], text=True
        ).strip()
    )
    for source, name in [
        ("sources.tar.gz", "pi-boot-sources.tar.gz"),
        ("rpi5-boot.lock.json", "pi-boot.lock.json"),
        ("boot-notices.txt", "boot-notices.txt"),
    ]:
        shutil.copy2(boot / source, dist / name)


def validate_io_materials(hyper, package):
    specification = importlib.util.spec_from_file_location(
        "io_importer", hyper / "scripts/fetch-io-vm.py"
    )
    importer = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(importer)
    layers = importer.validate_manifest(
        package / "oci-manifest.json", "sha256:" + package.name, "rpi5"
    )
    importer.validate_runtime(package, layers)
    for name in ("kernel.config", "sources.tar.xz"):
        importer.checked_file(package / "materials" / name, layers[name])
    metadata = json.loads((package / "oci-manifest.json").read_text())
    revision = metadata["annotations"].get("org.opencontainers.image.revision", "")
    if not re.fullmatch(r"[0-9a-f]{40}", revision):
        raise ValueError("published package does not identify its source revision")
    with tarfile.open(package / "materials/sources.tar.xz") as archive:
        member = archive.getmember("libc-materials/manifest.json")
        if not member.isfile() or member.size > 1024 * 1024:
            raise ValueError("invalid libc build materials")
        manifest = json.load(archive.extractfile(member))
        for record in manifest["files"]:
            name = record["name"]
            if Path(name).name != name:
                raise ValueError("invalid libc material name")
            item = archive.getmember("libc-materials/" + name)
            if not item.isfile() or item.size != record["bytes"]:
                raise ValueError("libc source size differs from build record")
            with archive.extractfile(item) as data:
                if hashlib.file_digest(data, "sha256").hexdigest() != record["sha256"]:
                    raise ValueError("libc source checksum differs from build record")
    return metadata


def prepare_io(hyper, package):
    if package is None:
        package = Path(
            subprocess.check_output(
                [
                    sys.executable,
                    str(hyper / "scripts/fetch-io-vm.py"),
                    "--platform",
                    "rpi5",
                    "--materials",
                ],
                text=True,
            ).strip()
        )
    validate_io_materials(hyper, package)
    return package


def collect_io_materials(package, dist):
    shutil.copy2(package / "oci-manifest.json", dist / "io-vm-oci-manifest.json")
    for source, target in (
        ("sources.tar.xz", "io-vm-sources.tar.xz"),
        ("kernel.config", "io-vm-kernel.config"),
    ):
        shutil.copy2(package / "materials" / source, dist / target)


def write_inventory(dist, lock, profile, target, image, digest):
    inventory = {
        "hyper": lock,
        "profile": profile,
        "target": target,
        "image_sha256": digest,
        "image_bytes": image.stat().st_size,
        "files": {
            p.name: {"sha256": sha(p), "bytes": p.stat().st_size}
            for p in sorted(dist.iterdir())
        },
    }
    (dist / "inventory.json").write_text(json.dumps(inventory, indent=2) + "\n")
    shutil.copy2(ROOT / "DISTRIBUTION.md", dist / "DISTRIBUTION.md")
    shutil.copy2(ROOT / "ARTIFACTS.md", dist / "ARTIFACTS.md")
    (dist / "SHA256SUMS").write_text(
        "".join(
            f"{sha(p)}  {p.name}\n"
            for p in sorted(dist.iterdir())
            if p.name != "SHA256SUMS"
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--profile", choices=["native", "io-bringup", "sd"], default="io-bringup"
    )
    parser.add_argument(
        "--checkout-only",
        action="store_true",
        help="resolve and check out sources without building",
    )
    parser.add_argument("--source", type=Path, help="already resolved repo workspace")
    parser.add_argument(
        "--io-package",
        type=Path,
        help="verified RPi5 boot package with build materials",
    )
    args = parser.parse_args()
    hyper = args.source.resolve() if args.source else checkout_hyper()
    lock = json.loads((hyper / "source-inventory.json").read_text())
    if args.checkout_only:
        return

    io_package = (
        prepare_io(hyper, args.io_package.resolve() if args.io_package else None)
        if args.profile != "native"
        else None
    )

    dist = ROOT / "dist" / args.profile
    if dist.exists():
        raise ValueError(f"refusing to overwrite {dist}; use a fresh output directory")
    dist.mkdir(parents=True)

    target = build_image(hyper, args.profile, io_package)
    image = hyper / "target/board/rpi5-native/disk.img"
    digest = compress_image(image, dist, args.profile)
    collect_hyper_materials(hyper, dist, "HEAD")
    collect_boot_materials(hyper, dist)
    cache = ROOT / "work/materials-cache"
    materials.collect_rust(hyper, dist / "rust-materials.tar.gz", cache / "crates")
    if args.profile != "native":
        collect_io_materials(io_package, dist)
    if args.profile == "sd":
        kernel_pin = json.loads((ROOT / "materials/alpine-kernel.json").read_text())
        materials.collect_alpine(
            hyper, dist / "alpine-materials.tar.gz", cache / "alpine", kernel_pin
        )
    write_inventory(dist, lock, args.profile, target, image, digest)
    print(dist)


if __name__ == "__main__":
    main()
