# SPDX-FileCopyrightText: 2026 roolrz
# SPDX-License-Identifier: Apache-2.0

import importlib.util
from pathlib import Path
import tarfile
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("bundle", ROOT / "scripts/bundle.py")
bundle = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bundle)


class BundleTests(unittest.TestCase):
    def fixture(self, root):
        profile = root / "inputs/pi5-native"
        profile.mkdir(parents=True)
        (profile / "hyper-rpi5-native.img.xz").write_bytes(b"image fixture")
        (profile / "inventory.json").write_text("{}\n")
        (profile / "HypeR-source.tar.xz").write_bytes(b"source fixture")
        (profile / "SHA256SUMS").write_text(
            "".join(f"{bundle.sha(p)}  {p.name}\n" for p in sorted(profile.iterdir()))
        )
        return profile

    def test_image_and_materials_are_preserved(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self.fixture(root)
            bundle.bundle(root / "inputs", root / "output")
            self.assertEqual(
                (root / "output/hyper-rpi5-native.img.xz").read_bytes(),
                (profile / "hyper-rpi5-native.img.xz").read_bytes(),
            )
            with tarfile.open(
                root / "output/hyper-rpi5-native-materials.tar.xz"
            ) as archive:
                self.assertIn("HypeR-source.tar.xz", archive.getnames())
                self.assertIn("inventory.json", archive.getnames())
                self.assertNotIn("hyper-rpi5-native.img.xz", archive.getnames())
            for line in (root / "output/SHA256SUMS").read_text().splitlines():
                checksum, name = line.split("  ", 1)
                self.assertEqual(checksum, bundle.sha(root / "output" / name))

    def test_corruption_does_not_create_release_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            profile = self.fixture(root)
            (profile / "hyper-rpi5-native.img.xz").write_bytes(b"corrupted")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                bundle.bundle(root / "inputs", root / "output")
            self.assertFalse((root / "output").exists())


if __name__ == "__main__":
    unittest.main()
