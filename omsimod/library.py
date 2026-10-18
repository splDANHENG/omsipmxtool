# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Character catalogue and reversible per-map activation (no engine patch)."""
import json
import shutil
import uuid
import hashlib
import subprocess
import tempfile
import threading
import os
import stat
import re
from functools import wraps
from pathlib import Path
from .locking import catalogue_lock
from .resources import mesh_textures, require_texture


def digest(data):
    return hashlib.sha256(data).hexdigest()


def fingerprint(data):
    return digest(data) if data is not None else None


def atomic_write(path, data):
    """Keep the previous file intact if writing or replacement fails."""
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix='.'+path.name,
                                     suffix='.tmp', delete=False) as stream:
        temp=Path(stream.name)
        try:
            stream.write(data)
        except BaseException:
            stream.close();temp.unlink(missing_ok=True)
            raise
    try:temp.replace(path)
    finally:temp.unlink(missing_ok=True)


def serialized(fn):
    @wraps(fn)
    def call(self,*args,**kwargs):
        with self.lock:
            if self._transaction_depth:
                return fn(self,*args,**kwargs)
            with catalogue_lock(self.directory/'library.lock'):
                if fn.__name__ != 'save':
                    self.reload()
                self._transaction_depth += 1
                try:
                    return fn(self,*args,**kwargs)
                finally:
                    self._transaction_depth -= 1
    return call


def write_state(path,state):
    atomic_write(path,json.dumps(state,indent=2).encode('utf-8'))


def check_state(state,current):
    accepted=[state['applied_hash']]
    if state.get('pending'):accepted.append(state['before_hash'])
    if state.get('restoring'):
        original=state['original_hex']
        accepted.append(fingerprint(bytes.fromhex(original) if original is not None else None))
    if fingerprint(current) not in accepted:
        raise ValueError('司机列表已被外部修改，操作已停止；原始内容仍保存在备份中。')


def read_text(path):
    data = path.read_bytes()
    if data.startswith((b'\xff\xfe',b'\xfe\xff')): return data.decode('utf-16')
    try: return data.decode('utf-8-sig')
    except UnicodeDecodeError: return data.decode('cp1252')


def prepend_driver(original, relative):
    """Keep existing paths byte-for-byte; do not guess GBK versus Western ANSI."""
    for bom, encoding in ((b'\xff\xfe','utf-16-le'), (b'\xfe\xff','utf-16-be'),
                          (b'\xef\xbb\xbf','utf-8')):
        if original.startswith(bom):
            return bom + (relative+'\r\n').encode(encoding) + original[len(bom):]
    try:
        prefix=(relative+'\r\n').encode('ascii')
    except UnicodeEncodeError:
        try: original.decode('utf-8')
        except UnicodeDecodeError as exc:
            raise ValueError('旧司机列表编码不明确，请将 HUM 文件名改为英文或拼音后再应用。') from exc
        prefix=(relative+'\r\n').encode('utf-8')
    return prefix + original


def local_file(base, value):
    root=base.resolve(); path=(base/value.replace('\\','/')).resolve()
    if not path.is_relative_to(root) or not path.is_file():
        raise ValueError('人物包缺少资源，或引用了人物目录以外的文件：'+value)
    return path


def check_package_entry(path, root):
    """Reject links/reparse points before traversing or copying an entry."""
    info = path.lstat()
    if stat.S_ISLNK(info.st_mode) or getattr(info, 'st_file_attributes', 0) & 0x400:
        raise ValueError('人物目录不支持符号链接、目录联接或其他重解析点：' + str(path))
    if not path.resolve().is_relative_to(root):
        raise ValueError('人物资源超出人物目录：' + str(path))
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise ValueError('人物目录包含不支持的特殊文件：' + str(path))
    return info


def validate_package_tree(directory):
    root = directory.resolve()
    pending = [directory]
    while pending:
        path = pending.pop()
        info = check_package_entry(path, root)
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(path) as entries:
                pending.extend(Path(entry.path) for entry in entries)


def copy_package(source, destination):
    root = source.resolve()
    def check_path(path):
        path = Path(path)
        check_package_entry(path, root)
        if path == root:
            return
        for parent in path.parents:
            if parent == root:
                check_package_entry(parent, root)
                break
            check_package_entry(parent, root)
    def inspect(directory, names):
        check_path(directory)
        for name in names:
            check_path(Path(directory)/name)
        return []
    def copy_file(src, dst):
        check_path(src)
        return shutil.copy2(src, dst, follow_symlinks=False)
    validate_package_tree(source)
    shutil.copytree(source, destination, symlinks=True, ignore=inspect, copy_function=copy_file)


def validate_hum(path):
    path=Path(path).absolute()
    validate_package_tree(path.parent)
    path=path.resolve()
    if path.suffix.lower()!='.hum': raise ValueError('请选择 .hum 文件')
    lines=read_text(path).splitlines()
    try: model=local_file(path.parent,lines[lines.index('[model]')+1])
    except (ValueError,IndexError) as exc: raise ValueError('人物缺少有效 [model] 配置：'+str(exc)) from exc
    lines=read_text(model).splitlines()
    meshes=[]
    for i,line in enumerate(lines):
        if line=='[mesh]':
            if i+1>=len(lines):raise ValueError('[mesh] 缺少文件名')
            meshes.append(local_file(model.parent,lines[i+1]))
    if not meshes:raise ValueError('模型配置没有 [mesh]')
    for mesh in meshes:
        for texture in mesh_textures(mesh):
            require_texture(path.parent,mesh.parent,texture)
    for i,line in enumerate(lines):
        if line.strip() in ('[matl]','[matl_change]','[matl_nightmap]',
                            '[matl_lightmap]','[matl_bumpmap]','[matl_transmap]','[matl_envmap]'):
            if i+1>=len(lines):raise ValueError('材质配置缺少贴图文件名')
            texture=lines[i+1].strip()
            if texture and not texture.startswith('\\S:'):
                require_texture(path.parent,model.parent,texture)
    return path


class Library:
    def __init__(self,directory):
        self.lock=threading.RLock()
        self._transaction_depth=0
        self.directory=Path(directory)
        self.directory.mkdir(parents=True,exist_ok=True)
        self.path=self.directory/'library.json'
        self.reload()

    def reload(self):
        self._loaded_bytes=self.path.read_bytes() if self.path.exists() else None
        self.data=json.loads(self._loaded_bytes.decode('utf-8')) if self._loaded_bytes is not None else {'characters':[],'settings':{}}

    @serialized
    def save(self):
        current=self.path.read_bytes() if self.path.exists() else None
        if current != self._loaded_bytes:
            raise ValueError('角色库已被其他程序更新，请刷新后重试，未覆盖新数据。')
        encoded=json.dumps(self.data,ensure_ascii=False,indent=2).encode('utf-8')
        atomic_write(self.path,encoded)
        self._loaded_bytes=encoded

    @serialized
    def settings(self,values):
        self.data['settings'].update(values);self.save()

    @serialized
    def add(self,hum):
        path=validate_hum(hum)
        for item in self.data['characters']:
            if item['hum']==str(path):return item
        item={'id':uuid.uuid4().hex,'name':path.parent.name,'hum':str(path)}
        self.data['characters'].append(item);self.save();return item

    @serialized
    def remove(self,key):
        self.data['characters']=[c for c in self.data['characters'] if c['id']!=key]
        self.save()

    def state_path(self,root,map_name):
        key=digest((str(Path(root).resolve())+'|'+map_name).encode())[:24]
        return self.directory/(key+'.activation.json')

    def all_maps(self,root):
        maps=Path(root).expanduser().resolve()/'maps'
        names=sorted(p.parent.name for p in maps.glob('*/global.cfg') if p.is_file())
        if not names:raise ValueError('内容目录中没有找到地图')
        return names

    @serialized
    def batch(self,root,item=None):
        """Apply to installed maps, or restore owned maps; report partial failures."""
        root=Path(root).expanduser().resolve()
        names=self.all_maps(root)
        done=[];failed=[];skipped=[]
        for name in names:
            if item is None and not self.state_path(root,name).exists():
                skipped.append(name);continue
            try:
                if item is None:self.restore(root,name)
                else:self.activate(item,root,name)
                done.append(name)
            except Exception as exc:
                failed.append(f'{name}：{exc}')
        action='恢复' if item is None else '应用'
        lines=[f'{action}成功 {len(done)} 张地图；失败 {len(failed)} 张；跳过 {len(skipped)} 张。']
        lines += [f'已{action}：{name}' for name in done]
        lines += ['失败：'+entry for entry in failed]
        if skipped:lines.append('没有本工具备份，未修改：'+ '、'.join(skipped))
        return '\n'.join(lines)

    @serialized
    def install(self,item,root):
        """Install the complete character without changing any driver list."""
        root=Path(root).expanduser().resolve()
        if not (root/'maps').is_dir():
            raise ValueError('请选择包含 maps 的 OMSI 内容目录')
        if not isinstance(item.get('id'), str) or not re.fullmatch(r'[A-Za-z0-9_-]+', item['id']):
            raise ValueError('非法角色标识')
        target=root/'Humans'/('OMSIMod_'+item['id'])
        for entry in (target.parent, target):
            if entry.exists() or entry.is_symlink():
                check_package_entry(entry, root)
        source=Path(item['hum']).resolve().parent
        resolved=target.resolve()
        if resolved.is_relative_to(source) or source.is_relative_to(resolved):
            raise ValueError('人物源目录与安装目录重叠，请先将完整人物包放到独立目录。')
        hum=Path(item['hum'])
        marker=target/'.omsimod-install.json'
        ownership={'id':item['id'],'hum':hum.name}
        if target.exists():
            # IDs are owned by this catalogue; never merge or overwrite an unknown directory.
            if str(target) not in self.data.get('installed',[]):
                if not marker.is_file() or json.loads(marker.read_text())!=ownership:
                    raise ValueError('角色安装目录已存在，请使用已有应用状态或换一个角色导入。')
            validate_hum(target/hum.name)
        else:
            hum=validate_hum(hum)
            target.parent.mkdir(parents=True,exist_ok=True)
            with tempfile.TemporaryDirectory(prefix='.omsimod-install-',dir=target.parent) as temp:
                staged=Path(temp)/'character'
                copy_package(hum.parent,staged)
                validate_hum(staged/hum.name)
                write_state(staged/marker.name,ownership)
                staged.rename(target)
        if str(target) not in self.data.get('installed',[]):
            self.data.setdefault('installed',[]).append(str(target))
        self.save()
        return target/hum.name

    @serialized
    def activate(self,item,root,map_name):
        root=Path(root).expanduser().resolve()
        maps=(root/'maps').resolve(); folder=(maps/map_name).resolve()
        if not folder.is_relative_to(maps) or not (folder/'global.cfg').is_file():raise ValueError('地图不存在')
        drivers=folder/'drivers.txt'
        statepath=self.state_path(root,map_name)
        old=drivers.read_bytes() if drivers.exists() else None
        if statepath.exists():
            state=json.loads(statepath.read_text())
            check_state(state,old)
        else:
            state={'original_hex':old.hex() if old is not None else None,'targets':[]}
        hum=self.install(item,root)
        target=hum.parent
        original=bytes.fromhex(state['original_hex']) if state['original_hex'] is not None else b''
        rel=f'Humans\\{target.name}\\{hum.name}'
        new=prepend_driver(original, rel)
        state['applied_hash']=digest(new)
        state['before_hash']=fingerprint(old)
        state['pending']=True
        state.pop('restoring',None)
        if str(target) not in state['targets']:state['targets'].append(str(target))
        # Persist the backup before altering the map. A crash still leaves the original bytes.
        write_state(statepath,state)
        atomic_write(drivers,new)
        state.pop('pending');state.pop('before_hash')
        write_state(statepath,state)
        return rel

    @serialized
    def restore(self,root,map_name):
        maps=(Path(root).resolve()/'maps').resolve()
        if not (maps/map_name).resolve().is_relative_to(maps):raise ValueError('非法地图路径')
        statepath=self.state_path(root,map_name)
        if not statepath.exists():raise ValueError('此地图没有本工具保存的备份')
        state=json.loads(statepath.read_text())
        drivers=Path(root)/'maps'/map_name/'drivers.txt'
        check_state(state,drivers.read_bytes() if drivers.exists() else None)
        original=state['original_hex']
        state['restoring']=True
        write_state(statepath,state)
        if original is None:drivers.unlink(missing_ok=True)
        else:
            atomic_write(drivers,bytes.fromhex(original))
        statepath.unlink()
        # Keep installed assets; restoring a map must not break another map using them.


def game_command(executable,root,map_name,bus):
    executable=Path(executable)
    if not executable.is_file():raise ValueError('游戏可执行文件不存在')
    root=Path(root).resolve()
    for value,base in [(f'maps/{map_name}/global.cfg',root),(bus,root)]:local_file(base,value)
    return [str(executable),'--root',str(root),'--map',f'maps/{map_name}/global.cfg',
            '--bus',bus,'--no-menu','--view','outside']
