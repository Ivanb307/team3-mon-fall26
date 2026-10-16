"""Guard against accidental data replacement or broader database exposure."""
import importlib.util
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


spec = importlib.util.spec_from_file_location(
    "local_database", Path(__file__).resolve().parents[1] / ".platform/scripts/local_database.py")
database = importlib.util.module_from_spec(spec)
spec.loader.exec_module(database)


class LocalDatabaseTests(unittest.TestCase):
    def valid_environment(self):
        return {"DJANGO_LOCAL_POSTGRES": "True", "DB_HOST": "127.0.0.1", "DB_PORT": "5432",
                "DB_NAME": "nyc_active", "DB_USER": "nyc_active", "DB_PASSWORD": "a" * 50,
                "DJANGO_DB_BACKUP_BUCKET": database.BUCKET}

    def test_server_setup_is_opt_in(self):
        with patch.object(database, "environment", return_value={}), patch.object(database, "run") as run:
            database.setup()
        run.assert_not_called()

    def test_local_mode_refuses_network_hosts_or_another_projects_backup_bucket(self):
        for key, value in [("DB_HOST", "0.0.0.0"), ("DB_NAME", "other_project"),
                           ("DJANGO_DB_BACKUP_BUCKET", "other-project"), ("DB_PASSWORD", "weak")]:
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                database.validate({**self.valid_environment(), key: value})

    def test_existing_initialized_database_is_not_restored_or_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            (data / ".nyc-active-initialized").touch()
            with patch.object(database, "DATA", data), patch.object(database, "sql") as sql, \
                    patch.object(database, "s3") as s3:
                database.restore_if_new()
            sql.assert_not_called()
            s3.assert_not_called()

    def test_unmarked_nonempty_database_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(database, "DATA", Path(directory)), \
                patch.object(database, "sql", return_value="12"), patch.object(database, "s3") as s3:
            with self.assertRaisesRegex(RuntimeError, "refusing to overwrite"):
                database.restore_if_new()
            s3.assert_not_called()

    def test_inaccessible_backups_do_not_initialize_a_blank_database(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            with patch.object(database, "DATA", data), patch.object(database, "sql", return_value="0"), \
                    patch.object(database, "s3", side_effect=RuntimeError("Access denied")):
                with self.assertRaises(RuntimeError):
                    database.restore_if_new()
            self.assertFalse((data / ".nyc-active-initialized").exists())

    def test_new_database_can_initialize_when_backup_bucket_is_confirmed_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            data = Path(directory)
            with patch.object(database, "DATA", data), patch.object(database, "sql", return_value="0"), \
                    patch.object(database, "s3", return_value=SimpleNamespace(stdout=json.dumps({"KeyCount": 0}))):
                database.restore_if_new()
            self.assertTrue((data / ".nyc-active-initialized").exists())


if __name__ == "__main__":
    unittest.main()
