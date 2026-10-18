# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
import tempfile
import unittest
from pathlib import Path
from omsimod.library import Library, game_command


class LibraryTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.lib=Library(self.base/'data');self.root=self.base/'game'
        self.map=self.root/'maps'/'Test';self.map.mkdir(parents=True)
        (self.map/'global.cfg').write_text('map')
        self.driver=self.map/'drivers.txt';self.driver.write_bytes(b'old\\driver.hum\r\n')
        self.hum=self.base/'pack'/'driver.hum';self.hum.parent.mkdir()
        self.hum.write_text('[model]\nmodel.cfg\n')
        (self.hum.parent/'model.cfg').write_text('[mesh]\nmesh.o3d\n')
        # Valid empty material table; these tests exercise catalogue transactions.
        (self.hum.parent/'mesh.o3d').write_bytes(b'\x84\x19\x01\x26\x00\x00')
        self.item=self.lib.add(self.hum)

    def tearDown(self):self.temp.cleanup()

    def test_apply_restore_preserves_original(self):
        before=self.driver.read_bytes()
        self.lib.activate(self.item,self.root,'Test')
        self.assertIn(b'OMSIMod_',self.driver.read_bytes())
        self.lib.activate(self.item,self.root,'Test')
        self.lib.restore(self.root,'Test')
        self.assertEqual(self.driver.read_bytes(),before)
        self.lib.activate(self.item,self.root,'Test') # reuse owned assets
        self.lib.restore(self.root,'Test')

    def test_refuse_external_edit(self):
        self.lib.activate(self.item,self.root,'Test');self.driver.write_text('external')
        with self.assertRaises(ValueError):self.lib.restore(self.root,'Test')
        self.assertEqual(self.driver.read_text(),'external')

    def test_remove_only_catalogue(self):
        self.lib.remove(self.item['id']);self.assertTrue(self.hum.exists())
        self.assertFalse(self.lib.data['characters'])

    def test_install_complete_package_without_applying_and_reuse_without_source(self):
        import shutil
        before=self.driver.read_bytes()
        (self.hum.parent/'texture.png').write_bytes(b'texture')
        installed=self.lib.install(self.item,self.root)
        self.assertEqual((installed.parent/'texture.png').read_bytes(),b'texture')
        self.assertEqual(self.driver.read_bytes(),before)
        self.assertFalse(self.lib.state_path(self.root,'Test').exists())
        shutil.rmtree(self.hum.parent)
        reopened=Library(self.lib.directory)
        result=reopened.batch(self.root,self.item)
        self.assertIn('成功 1',result)
        reopened.restore(self.root,'Test')
        self.assertEqual(self.driver.read_bytes(),before)

    def test_missing_mesh(self):
        (self.hum.parent/'mesh.o3d').unlink()
        with self.assertRaises(ValueError):self.lib.add(self.hum)

    def make_link(self, source, target):
        import os
        if os.name == 'nt':
            import _winapi
            _winapi.CreateJunction(str(target), str(source))
        else:
            source.symlink_to(target, target_is_directory=True)

    def test_reject_external_directory_link_before_import_or_install(self):
        from omsimod.library import validate_hum
        outside = self.base/'outside'; outside.mkdir()
        (outside/'private.txt').write_text('synthetic marker')
        link = self.hum.parent/'extra'
        self.make_link(link, outside)
        try:
            with self.assertRaises(ValueError): validate_hum(self.hum)
            # The catalogue predates the injected link; install must recheck.
            with self.assertRaises(ValueError): self.lib.install(self.item, self.root)
            self.assertFalse((self.root/'Humans'/('OMSIMod_'+self.item['id'])).exists())
            self.assertEqual((outside/'private.txt').read_text(), 'synthetic marker')
        finally:
            if link.is_symlink(): link.unlink()
            else: link.rmdir()

    def test_reject_install_destination_link(self):
        outside = self.base/'outside'; outside.mkdir()
        link = self.root/'Humans'
        self.make_link(link, outside)
        try:
            with self.assertRaises(ValueError): self.lib.install(self.item, self.root)
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            if link.is_symlink(): link.unlink()
            else: link.rmdir()

    def test_reject_invalid_catalogue_id(self):
        item = dict(self.item, id='../outside')
        with self.assertRaises(ValueError): self.lib.install(item, self.root)

    def test_refuse_map_escape(self):
        with self.assertRaises(ValueError):self.lib.activate(self.item,self.root,'../../elsewhere')

    def test_batch_survives_restart_and_restores_missing_list(self):
        second=self.root/'maps'/'第二张地图';second.mkdir()
        (second/'global.cfg').write_text('map')
        before=self.driver.read_bytes()
        result=self.lib.batch(self.root,self.item)
        self.assertIn('成功 2',result)
        self.assertIn(b'OMSIMod_', (second/'drivers.txt').read_bytes())
        reopened=Library(self.lib.directory)
        reopened.batch(self.root,self.item)
        self.assertEqual(self.driver.read_bytes().count(b'OMSIMod_'),1)
        reopened.batch(self.root)
        self.assertEqual(self.driver.read_bytes(),before)
        self.assertFalse((second/'drivers.txt').exists())

    def test_batch_conflict_does_not_block_other_maps(self):
        self.lib.activate(self.item,self.root,'Test')
        self.driver.write_bytes(b'external change')
        second=self.root/'maps'/'New';second.mkdir()
        (second/'global.cfg').write_text('map')
        result=self.lib.batch(self.root,self.item)
        self.assertIn('成功 1 张地图；失败 1',result)
        self.assertEqual(self.driver.read_bytes(),b'external change')
        self.assertIn(b'OMSIMod_', (second/'drivers.txt').read_bytes())
        result=self.lib.batch(self.root)
        self.assertIn('失败 1',result)
        self.assertFalse((second/'drivers.txt').exists())
        self.assertTrue(self.lib.state_path(self.root,'Test').exists())
