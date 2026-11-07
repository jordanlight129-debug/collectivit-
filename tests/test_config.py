import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app.config as config


class EnsureDirectoriesTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.root = Path(self.temp_dir.name)
        self.exe_dir = self.root / "install"
        self.exe_dir.mkdir()
        self.data_root = self.root / "localappdata" / "SolidariteEtoile"

    def _frozen_config(self):
        return patch.multiple(
            config,
            BASE_DIR=self.exe_dir,
            DATA_DIR=self.data_root / "data",
            BACKUP_DIR=self.data_root / "backups",
            EXPORT_DIR=self.data_root / "exports",
            DB_PATH=self.data_root / "data" / "association.db",
        )

    def test_copies_legacy_database_without_removing_it(self):
        legacy_db = self.exe_dir / "data" / "association.db"
        legacy_db.parent.mkdir()
        legacy_db.write_bytes(b"legacy database")
        new_db = self.data_root / "data" / "association.db"

        with patch.object(config, "_is_frozen", return_value=True), self._frozen_config():
            config.ensure_directories()

        self.assertEqual(new_db.read_bytes(), b"legacy database")
        self.assertEqual(legacy_db.read_bytes(), b"legacy database")

    def test_does_not_overwrite_existing_database(self):
        legacy_db = self.exe_dir / "data" / "association.db"
        legacy_db.parent.mkdir()
        legacy_db.write_bytes(b"legacy database")
        new_db = self.data_root / "data" / "association.db"
        new_db.parent.mkdir(parents=True)
        new_db.write_bytes(b"new database")

        with patch.object(config, "_is_frozen", return_value=True), self._frozen_config():
            config.ensure_directories()

        self.assertEqual(new_db.read_bytes(), b"new database")
        self.assertEqual(legacy_db.read_bytes(), b"legacy database")
