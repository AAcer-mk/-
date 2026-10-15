"""Focused integrity tests: protect existing assets and archive extraction roots."""
import hashlib
from pathlib import Path
import tempfile
import unittest
from recover_git import safe_write


class RecoveryGuards(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)/'restore';self.root.mkdir()
        self.payload=b'original verified asset';self.sha=hashlib.sha256(self.payload).hexdigest()

    def test_verified_file_can_be_reused_without_write(self):
        safe_write(self.root,'asset.bin',self.payload,self.sha)
        before=(self.root/'asset.bin').stat().st_mtime_ns
        safe_write(self.root,'asset.bin',self.payload,self.sha)
        self.assertEqual(before,(self.root/'asset.bin').stat().st_mtime_ns)

    def test_existing_different_file_survives(self):
        dst=self.root/'asset.bin';dst.write_bytes(b'user work')
        with self.assertRaises(ValueError):safe_write(self.root,'asset.bin',self.payload,self.sha)
        self.assertEqual(dst.read_bytes(),b'user work')

    def test_archive_hash_mismatch_stops_before_write(self):
        with self.assertRaises(ValueError):safe_write(self.root,'asset.bin',b'truncated',self.sha)
        self.assertFalse((self.root/'asset.bin').exists())

    def test_parent_traversal_is_blocked(self):
        with self.assertRaises(ValueError):safe_write(self.root,'../escaped.bin',self.payload,self.sha)
        self.assertFalse((self.root.parent/'escaped.bin').exists())

    def test_absolute_path_is_blocked(self):
        with self.assertRaises(ValueError):safe_write(self.root,str(self.root.parent/'escaped.bin'),self.payload,self.sha)

    def test_existing_escape_symlink_is_blocked(self):
        outside=self.root.parent/'outside';outside.mkdir();(self.root/'linked').symlink_to(outside,target_is_directory=True)
        with self.assertRaises(ValueError):safe_write(self.root,'linked/asset.bin',self.payload,self.sha)
        self.assertFalse((outside/'asset.bin').exists())


if __name__=='__main__':unittest.main()
