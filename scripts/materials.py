#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 roolrz
# SPDX-License-Identifier: Apache-2.0

"""Collect version-matched third-party sources without executing build recipes."""

import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import shutil
import subprocess
import tarfile
import tempfile
import tomllib
import urllib.parse
import urllib.request


def digest(path, algorithm="sha256"):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, algorithm).hexdigest()


def fetch(url, destination, checksum, algorithm="sha256"):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() and digest(destination, algorithm) == checksum:
        return destination
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as stream:
        temporary = Path(stream.name)
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": "HypeR-source-collector"}
            )
            with urllib.request.urlopen(request, timeout=120) as response:
                shutil.copyfileobj(response, stream)
            stream.close()
            if digest(temporary, algorithm) != checksum:
                raise ValueError(f"source checksum mismatch: {url}")
            temporary.replace(destination)
        finally:
            temporary.unlink(missing_ok=True)
    return destination


def add_json(archive, name, data):
    payload = (json.dumps(data, indent=2) + "\n").encode()
    info = tarfile.TarInfo(name)
    info.size = len(payload)
    info.mode = 0o644
    archive.addfile(info, io.BytesIO(payload))


def collect_rust(hyper, output, cache, sdk=None):
    packages = {}
    locks = [hyper / "kernel/Cargo.lock", hyper / "app/Cargo.lock"]
    for lock in locks:
        for package in tomllib.loads(lock.read_text())["package"]:
            source = package.get("source", "")
            if not source:
                continue  # In-tree dependencies are in HypeR-source.tar.xz.
            if source != "registry+https://github.com/rust-lang/crates.io-index":
                raise ValueError(f"unsupported dependency source: {source}")
            key = (package["name"], package["version"])
            if key in packages and packages[key]["checksum"] != package["checksum"]:
                raise ValueError(f"conflicting dependency checksum: {key}")
            packages[key] = package
    rust_source = (sdk or hyper / "target/sdk/aarch64") / "share/hyper/rust-src"
    if not (rust_source / "COPYRIGHT-library.html").is_file():
        raise ValueError("assembled Rust source and copyright inventory are required")
    inventory = []
    with tarfile.open(output, "w:gz") as archive:
        for (name, version), package in sorted(packages.items()):
            filename = f"{name}-{version}.crate"
            url = f"https://static.crates.io/crates/{name}/{filename}"
            path = fetch(url, cache / filename, package["checksum"])
            archive.add(path, arcname=f"crates/{filename}")
            inventory.append(
                {
                    "name": name,
                    "version": version,
                    "url": url,
                    "sha256": package["checksum"],
                }
            )
        archive.add(rust_source, arcname="patched-rust-src")
        for lock in locks:
            archive.add(lock, arcname=str(lock.relative_to(hyper)))
        archive.add(hyper / "rust-toolchain.toml", arcname="rust-toolchain.toml")
        add_json(
            archive,
            "inventory.json",
            {
                "scope": "Superset of kernel/app lockfile registry dependencies and assembled patched std sources, including upstream license files.",
                "crates": inventory,
            },
        )
    return len(inventory)


def apk_packages(text):
    packages = []
    for block in text.strip().split("\n\n"):
        fields = {}
        for line in block.splitlines():
            if len(line) > 2 and line[1] == ":" and line[0] in "PVLoc":
                fields[line[0]] = line[2:]
        if "P" in fields:
            if not all(key in fields for key in ("V", "L", "o", "c")):
                raise ValueError(f"incomplete package source identity: {fields['P']}")
            if not re.fullmatch(r"[0-9a-f]{40}", fields["c"]):
                raise ValueError("invalid Alpine recipe commit")
            if not re.fullmatch(r"[a-zA-Z0-9+_.-]+", fields["o"]):
                raise ValueError("invalid Alpine source origin")
            packages.append(fields)
    if not packages:
        raise ValueError("empty Alpine package database")
    return packages


def recipe_checksums(text):
    match = re.search(r'^sha512sums=["\'](.*?)["\']', text, re.M | re.S)
    if not match:
        if not re.search(r"^source[+=]", text, re.M):
            return (
                {}
            )  # Source-free recipes such as alpine-release generate their files.
        raise ValueError(
            "APKBUILD has no literal sha512sums; explicit support required"
        )
    checksums = {}
    for line in match[1].splitlines():
        if not line.strip():
            continue
        checksum, name = line.split(None, 1)
        if (
            not re.fullmatch(r"[0-9a-f]{128}", checksum)
            or Path(name).name != name
            or name in (".", "..")
        ):
            raise ValueError("invalid APKBUILD source checksum")
        if name in checksums:
            raise ValueError("duplicate APKBUILD source filename")
        checksums[name] = checksum
    return checksums


def recipe_archive(repository, commit, origin, output):
    if not (repository / ".git").exists():
        subprocess.run(
            ["git", "init", str(repository)], check=True, stdout=subprocess.DEVNULL
        )
        subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "remote",
                "add",
                "origin",
                "https://github.com/alpinelinux/aports.git",
            ],
            check=True,
        )
    subprocess.run(
        [
            "git",
            "-C",
            str(repository),
            "fetch",
            "--filter=blob:none",
            "--depth=1",
            "origin",
            commit,
        ],
        check=True,
        stdout=subprocess.DEVNULL,
    )
    for category in ("main", "community", "testing"):
        path = f"{category}/{origin}"
        found = subprocess.run(
            [
                "git",
                "-C",
                str(repository),
                "cat-file",
                "-e",
                f"{commit}:{path}/APKBUILD",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if found.returncode == 0:
            subprocess.run(
                [
                    "git",
                    "-C",
                    str(repository),
                    "archive",
                    "--format=tar",
                    "-o",
                    str(output),
                    commit,
                    path,
                ],
                check=True,
            )
            return path
    raise ValueError(f"no recipe found: {origin}@{commit}")


def collect_alpine(hyper, output, cache, kernel):
    rootfs = hyper / "kernel/target/guest/aarch64/rootfs.tar"
    with tarfile.open(rootfs) as archive:
        member = next(
            (m for m in archive if m.name.removeprefix("./") == "lib/apk/db/installed"),
            None,
        )
        if member is None:
            raise ValueError("rootfs has no installed APK database")
        database = archive.extractfile(member).read().decode()
        releases = {
            m.name.removeprefix("./").split("/")[2]
            for m in archive.getmembers()
            if m.name.removeprefix("./").startswith("lib/modules/")
            and len(m.name.removeprefix("./").split("/")) > 3
        }
    if releases != {kernel["release"]}:
        raise ValueError(f"Alpine kernel pin does not match rootfs modules: {releases}")
    image = hyper / "kernel/target/guest/aarch64/Image"
    if digest(image) != kernel["image_sha256"]:
        raise ValueError("Alpine kernel source pin does not match built Image")
    packages = apk_packages(database)
    recipes = {(p["o"], p["c"]) for p in packages}
    recipes.add((kernel["origin"], kernel["commit"]))
    inventory = []
    cache.mkdir(parents=True, exist_ok=True)
    with tarfile.open(output, "w:gz") as archive:
        add_json(archive, "packages.json", packages)
        add_json(archive, "kernel.json", kernel)
        for origin, commit in sorted(recipes):
            prefix = f"{origin}-{commit}"
            recipe = cache / f"{prefix}.tar"
            path = recipe_archive(cache / "aports", commit, origin, recipe)
            archive.add(recipe, arcname=f"recipes/{prefix}.tar")
            with tarfile.open(recipe) as inputs:
                text = inputs.extractfile(f"{path}/APKBUILD").read().decode()
                checksums = recipe_checksums(text)
                for name, checksum in checksums.items():
                    try:
                        local = inputs.getmember(f"{path}/{name}")
                    except KeyError:
                        local = None
                    if local is not None:
                        data = inputs.extractfile(local).read()
                        if hashlib.sha512(data).hexdigest() != checksum:
                            raise ValueError(f"recipe file checksum mismatch: {name}")
                        continue
                    url = f"https://distfiles.alpinelinux.org/distfiles/v3.23/{urllib.parse.quote(name)}"
                    source = fetch(
                        url, cache / "sources" / checksum / name, checksum, "sha512"
                    )
                    archive.add(source, arcname=f"sources/{prefix}/{name}")
            inventory.append(
                {
                    "origin": origin,
                    "commit": commit,
                    "path": path,
                    "sha512sums": checksums,
                }
            )
        add_json(archive, "recipes.json", inventory)
    return len(packages), len(recipes)


def validate_libc_pin(hyper, pin):
    selected = json.loads((hyper / "scripts/io-vm.lock.json").read_text())["platforms"][
        "rpi5"
    ]
    if (
        selected["reference"].split("@sha256:")[-1] != pin["io_manifest_sha256"]
        or selected["source_revision"] != pin["source_revision"]
    ):
        raise ValueError(
            "I/O VM changed; collect its actual libc build identity before publishing"
        )


def collect_libc(hyper, output, cache, pin):
    validate_libc_pin(hyper, pin)
    with tarfile.open(output, "w:gz") as archive:
        for item in pin["files"]:
            if Path(item["name"]).name != item["name"]:
                raise ValueError("invalid material filename")
            path = fetch(item["url"], cache / item["name"], item["sha256"])
            archive.add(path, arcname=item["name"])
        add_json(archive, "provenance.json", pin)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("kind", choices=["rust", "alpine", "libc"])
    parser.add_argument("--hyper", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    parser.add_argument("--kernel-pin", type=Path)
    parser.add_argument("--libc-pin", type=Path)
    args = parser.parse_args()
    if args.kind == "alpine" and args.kernel_pin is None:
        parser.error("--kernel-pin is required for Alpine materials")
    if args.kind == "libc" and args.libc_pin is None:
        parser.error("--libc-pin is required for libc materials")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    if args.kind == "rust":
        print(collect_rust(args.hyper.resolve(), args.output, args.cache.resolve()))
    elif args.kind == "libc":
        collect_libc(
            args.hyper.resolve(),
            args.output,
            args.cache.resolve(),
            json.loads(args.libc_pin.read_text()),
        )
    else:
        kernel = json.loads(args.kernel_pin.read_text())
        print(
            collect_alpine(
                args.hyper.resolve(), args.output, args.cache.resolve(), kernel
            )
        )


if __name__ == "__main__":
    main()
