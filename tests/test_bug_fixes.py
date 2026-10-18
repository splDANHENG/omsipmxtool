# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from omsimod.pmx import load, ConversionError
from omsimod.export import convert
from omsimod.library import Library, validate_hum, prepend_driver
from omsimod.naming import pinyin_name
from test_converter import fixture, p, txt


class BugFixTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.base=Path(self.temp.name)
        self.source=self.base/'model.pmx';self.source.write_bytes(fixture())

    def tearDown(self):self.temp.cleanup()

    def package(self,name):
        convert(load(self.source),self.source,self.base/name,name,1.75,{})
        return self.base/name/'Humans'/name/'driver.hum'

    def test_large_material_index_count_and_invalid_count(self):
        data=fixture().replace(p('i3Bi',3,0,1,2,0),p('i',6000)+bytes([0,1,2])*2000+p('i',0),1)
        marker=p('bbBBB',-1,-1,0,1,0)+txt('')
        data=data.replace(marker+p('i',3),marker+p('i',6000),1)
        self.source.write_bytes(data)
        self.assertEqual(load(self.source).materials[0].count,6000)
        self.source.write_bytes(data.replace(marker+p('i',6000),marker+p('i',6003),1))
        with self.assertRaises(ConversionError):load(self.source)

    def test_driver_encodings_roundtrip(self):
        root=self.base/'game';folder=root/'maps/Map';folder.mkdir(parents=True)
        (folder/'global.cfg').write_text('map');drivers=folder/'drivers.txt'
        lib=Library(self.base/'catalog');item=lib.add(self.package('Driver'))
        for encoding in ('gbk','utf-8','utf-8-sig','utf-16','utf-16-be','cp1252'):
            text='Humans\\中国司机\\driver.hum\r\n' if encoding!='cp1252' else 'Humans\\Müller\\driver.hum\r\n'
            original=text.encode(encoding)
            if encoding=='utf-16-be':original=b'\xfe\xff'+original
            drivers.write_bytes(original);lib.activate(item,root,'Map')
            result=drivers.read_bytes()
            codec='utf-16' if encoding=='utf-16-be' else encoding
            self.assertIn(text,result.decode(codec))
            lib.restore(root,'Map');self.assertEqual(drivers.read_bytes(),original)
        with self.assertRaises(ValueError):prepend_driver('中国'.encode('gbk'),'Humans\\中文.hum')

    def test_two_instances_preserve_additions_and_stale_save_refused(self):
        first=Library(self.base/'data');second=Library(self.base/'data')
        first.add(self.package('First'));second.add(self.package('Second'))
        self.assertEqual(len(Library(first.directory).data['characters']),2)
        with self.assertRaises(ValueError):first.save()

    def test_two_processes_preserve_additions(self):
        paths=[self.package('First'),self.package('Second')]
        code="from omsimod.library import Library;import sys;l=Library(sys.argv[1]);print('ready',flush=True);input();l.add(sys.argv[2])"
        processes=[subprocess.Popen([sys.executable,'-c',code,str(self.base/'shared'),str(path)],
                    stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True) for path in paths]
        try:
            for process in processes:self.assertEqual(process.stdout.readline().strip(),'ready')
            for process in processes:process.stdin.write('\n');process.stdin.flush()
            for process in processes:
                _,err=process.communicate(timeout=15);self.assertEqual(process.returncode,0,err)
            self.assertEqual(len(Library(self.base/'shared').data['characters']),2)
        finally:
            for process in processes:
                if process.poll() is None:process.kill();process.wait()

    def test_missing_o3d_texture_even_without_cfg_material(self):
        hum=self.package('Missing');cfg=hum.parent/'model/model.cfg'
        cfg.write_text('[mesh]\nbody_0000.o3d\n')
        (hum.parent/'texture/mat_000.png').unlink()
        with self.assertRaisesRegex(ValueError,'贴图'):validate_hum(hum)
        lib=Library(self.base/'data')
        with self.assertRaises(ValueError):lib.add(hum)
        self.assertEqual(lib.data['characters'],[])

    def test_missing_cfg_extra_texture_and_truncated_mesh(self):
        hum=self.package('Extra');cfg=hum.parent/'model/model.cfg'
        with cfg.open('a') as f:f.write('\n[matl_nightmap]\nmissing.png\n')
        with self.assertRaisesRegex(ValueError,'贴图'):validate_hum(hum)
        cfg.write_text('[mesh]\nbody_0000.o3d\n')
        (hum.parent/'model/body_0000.o3d').write_bytes(b'\x84\x19\x01\x26\x01\x00')
        with self.assertRaises(ValueError):validate_hum(hum)

    def test_pinyin_is_portable_and_keeps_ascii(self):
        self.assertEqual(pinyin_name('饮月君 1708'),'yinyuejun_1708')
        self.assertEqual(pinyin_name('星穹铁道—海瑟音'),'xingqiongtiedao_haiseyin')
        self.assertEqual(pinyin_name('Test-01'),'Test-01')
        self.assertEqual(pinyin_name('CON'),'_CON')
        self.assertTrue(pinyin_name('中文 / A:*?').isascii())
