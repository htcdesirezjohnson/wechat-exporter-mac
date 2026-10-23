"""Regression coverage using synthetic accounts and encrypted databases only."""
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from core import account_state, constants, db_decryptor
from core.key_extractor import KeyExtractionError
from core.models import Layout


class RepairTests(unittest.TestCase):
    def test_prepared_copy_cannot_disable_installed_executable(self):
        from vendor.wechat41.bootstrap_keys import validate_prepared_copy
        with tempfile.TemporaryDirectory(prefix='wechat-debug-copy-') as tmp:
            original = Path(tmp)/'Official.app'
            original_exe = original/'Contents/MacOS/WeChat'
            original_exe.parent.mkdir(parents=True)
            original_exe.write_bytes(b'original fixture')
            shadow = Path(tmp)/'WeChat-trial.app'
            executable = shadow/'Contents/MacOS/WeChat'
            executable.parent.mkdir(parents=True)
            executable.write_bytes(b'copy fixture')
            self.assertEqual(validate_prepared_copy(shadow, original), shadow.resolve())
            with self.assertRaises(RuntimeError):
                validate_prepared_copy(original, original)
            executable.unlink()
            executable.symlink_to(original_exe)
            with self.assertRaises(RuntimeError):
                validate_prepared_copy(shadow, original)
            executable.unlink()
            os.link(original_exe, executable)
            with self.assertRaises(RuntimeError):
                validate_prepared_copy(shadow, original)
            self.assertEqual(original_exe.read_bytes(), b'original fixture')

    def test_account_isolation_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(constants, 'APP_DIR', tmp):
            a = Layout(version='v4', account_id='same', account_dir=tmp+'/a', message_dbs=[])
            b = Layout(version='v4', account_id='same', account_dir=tmp+'/b', message_dbs=[])
            ka, kb = {'1'*32: 'a'*64}, {'2'*32: 'b'*64}
            account_state.save_keys(a, ka)
            with self.assertRaises(KeyExtractionError):
                account_state.load_keys(b)
            account_state.save_keys(b, kb)
            self.assertEqual(account_state.load_keys(a), ka)
            self.assertEqual(account_state.load_keys(b), kb)
            self.assertEqual((account_state.state_dir(a)/'keys.json').stat().st_mode & 0o777, 0o600)

    def test_export_includes_committed_wal_without_changing_source(self):
        import sqlcipher3.dbapi2 as sq
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/'messages.db'
            target = Path(tmp)/'plain.db'
            key = 'a'*64
            writer = sq.connect(str(source))
            writer.execute('PRAGMA key = "x\'' + key + '\'"')
            db_decryptor._apply_pragmas(writer.cursor(), 'v4')
            writer.execute('CREATE TABLE messages(content TEXT)')
            writer.commit()
            writer.execute('PRAGMA journal_mode=WAL')
            writer.execute('PRAGMA wal_autocheckpoint=0')
            writer.execute("INSERT INTO messages VALUES('committed in WAL')")
            writer.commit()
            before = source.read_bytes(), Path(str(source)+'-wal').read_bytes()
            try:
                db_decryptor.decrypt_database(str(source), key, 'v4', str(target))
                with sqlite3.connect(str(target)) as reader:
                    self.assertEqual(reader.execute('SELECT content FROM messages').fetchall(), [('committed in WAL',)])
                self.assertEqual(before, (source.read_bytes(), Path(str(source)+'-wal').read_bytes()))
            finally:
                writer.close()

    def test_missing_database_key_is_not_a_silent_partial_export(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(constants, 'DECRYPTED_DIR', tmp+'/out'):
            paths = [str(Path(tmp)/name) for name in ('message_0.db','message_1.db')]
            for i, path in enumerate(paths):
                Path(path).write_bytes(bytes([i+1])*4096)
            layout = Layout(version='v4', account_id='a', account_dir=tmp, message_dbs=paths)
            with patch.object(db_decryptor, 'decrypt_database', return_value='ok'):
                with self.assertRaises(db_decryptor.DecryptError):
                    db_decryptor.decrypt_layout(layout, {'01'*16: 'a'*64})

    def test_unconfigured_gui_never_scans_processes(self):
        import app
        with tempfile.TemporaryDirectory() as tmp, patch.object(constants, 'APP_DIR', tmp):
            layout = Layout(version='v4', account_id='test', account_dir=tmp+'/test', message_dbs=[])
            with patch.object(app.locator, 'select_account', return_value=layout), patch.object(app.key_extractor, 'get_keys', side_effect=AssertionError('must not scan')):
                result = app.app.test_client().get('/api/contacts?account_id=test')
                self.assertIn('配置账号.command', result.get_json()['error'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
