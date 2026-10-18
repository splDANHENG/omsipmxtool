# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Failure injection for installation and map transactions; no game files touched."""
import json
import threading
import shutil
from pathlib import Path
from unittest.mock import patch
import unittest
import test_library
from omsimod.library import Library


class RecoveryTests(unittest.TestCase):
    setUp = test_library.LibraryTests.setUp
    tearDown = test_library.LibraryTests.tearDown
    def test_overlapping_source_rejected_before_copy(self):
        for f in self.hum.parent.iterdir():
            (self.root/f.name).write_bytes(f.read_bytes())
        item=self.lib.add(self.root/'driver.hum')
        with patch('omsimod.library.shutil.copytree') as copy:
            with self.assertRaisesRegex(ValueError,'重叠'):
                self.lib.activate(item,self.root,'Test')
            copy.assert_not_called()

    def test_failed_copy_cleans_staging_and_can_retry(self):
        def fail(src,dst):
            Path(dst).mkdir();(Path(dst)/'partial').write_bytes(b'partial')
            raise OSError('copy failed')
        with patch('omsimod.library.shutil.copytree',fail):
            with self.assertRaises(OSError):self.lib.activate(self.item,self.root,'Test')
        self.assertEqual(list((self.root/'Humans').iterdir()),[])
        self.lib.activate(self.item,self.root,'Test')
        self.lib.restore(self.root,'Test')

    def test_failed_map_replace_can_retry_or_restore(self):
        before=self.driver.read_bytes();replace=Path.replace
        def fail(path,target):
            if Path(target).resolve()==self.driver.resolve():raise OSError('replace failed')
            return replace(path,target)
        for missing in (False,True):
            for retry in (False,True):
                if missing:self.driver.unlink(missing_ok=True)
                else:self.driver.write_bytes(before)
                with patch.object(Path,'replace',fail):
                    with self.assertRaises(OSError):self.lib.activate(self.item,self.root,'Test')
                reopened=Library(self.lib.directory)
                if retry:reopened.activate(self.item,self.root,'Test')
                reopened.restore(self.root,'Test')
                if missing:self.assertFalse(self.driver.exists())
                else:self.assertEqual(self.driver.read_bytes(),before)

    def test_failed_journal_completion_recovers_after_restart(self):
        from omsimod.library import write_state
        def fail(path,state):
            if path.suffix=='.json' and 'applied_hash' in state and not state.get('pending'):
                raise OSError('completion failed')
            write_state(path,state)
        with patch('omsimod.library.write_state',fail):
            with self.assertRaises(OSError):self.lib.activate(self.item,self.root,'Test')
        Library(self.lib.directory).restore(self.root,'Test')
        self.assertEqual(self.driver.read_bytes(),b'old\\driver.hum\r\n')

    def test_pending_transaction_still_rejects_external_edits(self):
        replace=Path.replace
        def fail(path,target):
            if Path(target).resolve()==self.driver.resolve():raise OSError('replace failed')
            return replace(path,target)
        with patch.object(Path,'replace',fail):
            with self.assertRaises(OSError):self.lib.activate(self.item,self.root,'Test')
        self.driver.write_bytes(b'external')
        with self.assertRaises(ValueError):self.lib.restore(self.root,'Test')
        self.assertEqual(self.driver.read_bytes(),b'external')

    def test_completed_restore_with_failed_journal_delete_can_retry(self):
        self.lib.activate(self.item,self.root,'Test')
        statepath=self.lib.state_path(self.root,'Test');unlink=Path.unlink
        def fail(path,*a,**kw):
            if path==statepath:raise OSError('delete failed')
            return unlink(path,*a,**kw)
        with patch.object(Path,'unlink',fail):
            with self.assertRaises(OSError):self.lib.restore(self.root,'Test')
        Library(self.lib.directory).restore(self.root,'Test')
        self.assertFalse(statepath.exists())

    def test_install_survives_catalogue_save_failure(self):
        with patch.object(self.lib,'save',side_effect=OSError('save failed')):
            with self.assertRaises(OSError):self.lib.activate(self.item,self.root,'Test')
        reopened=Library(self.lib.directory)
        reopened.activate(self.item,self.root,'Test')
        self.assertTrue(reopened.data['installed'])

    def test_saves_and_adds_are_serialized(self):
        second=self.base/'second-pack'
        shutil.copytree(self.hum.parent,second)
        barrier=threading.Barrier(3);errors=[]
        def run(fn):
            try:barrier.wait();fn()
            except Exception as exc:errors.append(exc)
        threads=[threading.Thread(target=run,args=(lambda:self.lib.add(second/'driver.hum'),)),
                 threading.Thread(target=run,args=(lambda:self.lib.settings({'root':'test'}),))]
        for thread in threads:thread.start()
        barrier.wait()
        for thread in threads:thread.join(5);self.assertFalse(thread.is_alive())
        self.assertEqual(errors,[])
        saved=json.loads(self.lib.path.read_text())
        self.assertEqual(len(saved['characters']),2)
        self.assertEqual(saved['settings']['root'],'test')
