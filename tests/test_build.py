# SPDX-FileCopyrightText: 2026 roolrz
# SPDX-License-Identifier: Apache-2.0

import importlib.util
import json
import lzma
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
spec = importlib.util.spec_from_file_location("build", ROOT / "scripts/build.py")
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class BuildTests(unittest.TestCase):
    def test_invalid_io_package_stops_before_image_build(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            hyper = root / "system"
            hyper.mkdir()
            (hyper / "source-inventory.json").write_text(
                json.dumps({"components": {"io-vm": {"commit": "new"}}})
            )
            package = root / "package"
            (package / "materials").mkdir(parents=True)
            for profile in ("io-bringup", "sd"):
                with (
                    self.subTest(profile=profile),
                    patch.object(build, "ROOT", root),
                    patch.object(build, "build_image") as compile_image,
                    patch.object(
                        build,
                        "validate_io_materials",
                        side_effect=ValueError("package checksum mismatch"),
                    ),
                    patch.object(
                        sys,
                        "argv",
                        [
                            "build.py",
                            "--profile",
                            profile,
                            "--source",
                            str(hyper),
                            "--io-package",
                            str(package),
                        ],
                    ),
                ):
                    with self.assertRaisesRegex(
                        ValueError, "package checksum mismatch"
                    ):
                        build.main()
                    compile_image.assert_not_called()
                    self.assertFalse((root / "dist").exists())

    def test_default_io_uses_a_published_package_without_compilation(self):
        with (
            patch.object(
                build.subprocess, "check_output", return_value="/cache/digest\n"
            ) as fetch,
            patch.object(build, "validate_io_materials") as validate,
            patch.object(build, "run") as compile_source,
        ):
            result = build.prepare_io(Path("/workspace"), None)
        self.assertEqual(result, Path("/cache/digest"))
        self.assertIn("--materials", fetch.call_args.args[0])
        self.assertIn("/workspace/scripts/fetch-io-vm.py", fetch.call_args.args[0])
        compile_source.assert_not_called()
        validate.assert_called_once_with(Path("/workspace"), result)

    def test_native_checkout_needs_no_io_materials(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "source-inventory.json").write_text("{}")
            with (
                patch.object(build, "ROOT", root),
                patch.object(build, "checkout_hyper", return_value=root),
                patch.object(build, "build_image") as compile_image,
                patch.object(
                    sys, "argv", ["build.py", "--profile", "native", "--checkout-only"]
                ),
            ):
                build.main()
                compile_image.assert_not_called()
                self.assertFalse((root / "dist").exists())

    def test_compression_preserves_image(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            image = directory / "disk.img"
            image.write_bytes(b"partition table fixture" + bytes(65536))
            digest = build.compress_image(image, directory, "sd")
            with lzma.open(directory / "hyper-rpi5-sd.img.xz", "rb") as stream:
                self.assertEqual(stream.read(), image.read_bytes())
            self.assertEqual(digest, build.sha(image))

    def test_release_build_excludes_local_overrides(self):
        environment = {
            "PATH": "/usr/bin",
            "IO_VM_PACKAGE": "/local/io",
            "RPI5_BOOT_PACKAGE": "/local/boot",
            "BOARD_CONFIG": "/local/board",
            "NATIVE_IMAGE_PROFILE": "test",
            "MAKEFLAGS": "-e",
            "MAKEOVERRIDES": "ARCH=x86_64",
        }
        with (
            patch.dict(build.os.environ, environment, clear=True),
            patch.object(build, "run") as run,
        ):
            target = build.build_image(Path("/checkout"), "sd")
        self.assertEqual(target, "rpi5-sd")
        self.assertEqual(run.call_args.kwargs["env"], {"PATH": "/usr/bin"})
        self.assertEqual(run.call_args.kwargs["cwd"], Path("/checkout"))
        self.assertEqual(
            run.call_args.args,
            ("make", "rpi5-sd", "ARCH=aarch64", "BOARD_IMAGE_REPLACE=--replace"),
        )


if __name__ == "__main__":
    unittest.main()
