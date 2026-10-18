import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from omsimod.paths import data_directory,migrate_legacy


class PathsTests(unittest.TestCase):
    def test_override(self):
        with patch.dict('os.environ',{'OMSIMOD_DATA_DIR':'/tmp/omsimod-test-state'}):
            self.assertEqual(data_directory(),Path('/tmp/omsimod-test-state'))

    def test_preserve_backups_and_never_overwrite(self):
        with tempfile.TemporaryDirectory() as temp:
            source=Path(temp)/'legacy';source.mkdir()
            (source/'map.activation.json').write_text('original-backup')
            target=Path(temp)/'state'
            self.assertTrue(migrate_legacy(source,target))
            self.assertEqual((target/'map.activation.json').read_text(),'original-backup')
            (source/'map.activation.json').write_text('changed')
            self.assertFalse(migrate_legacy(source,target))
            self.assertEqual((target/'map.activation.json').read_text(),'original-backup')
