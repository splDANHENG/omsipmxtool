# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
"""Show the bundled project notice before creating the main window."""
import hashlib
import os
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QMessageBox

from .model_notice import ModelNotice
from .paths import prepare_data_directory


def require_startup_notice():
    try:
        document = Path(__file__).with_name('MODEL-RIGHTS.txt').read_text(encoding='utf-8')
        if not document.strip():
            raise ValueError('版权说明文件为空')
        fingerprint = hashlib.sha256(document.encode('utf-8')).hexdigest()
        # Migrate legacy backups before the notice creates the destination folder.
        record = prepare_data_directory()/'model-rights-read.txt'
        try:
            if record.read_text(encoding='ascii').strip() == fingerprint:
                return True
        except (OSError, UnicodeError):
            pass
    except (OSError, ValueError) as exc:
        QMessageBox.critical(None, '无法加载版权说明', f'请重新完整解压软件包。\n{exc}')
        return False

    notice = ModelNotice(dict(name='', english_name='', comment='', english_comment=''),
                         document=document)
    if notice.exec() != ModelNotice.DialogCode.Accepted or not notice.read_complete:
        return False
    temporary = None
    try:
        record.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode='w', encoding='ascii', dir=record.parent,
                                         prefix='.notice-', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(fingerprint)
        os.replace(temporary, record)
    except OSError:
        QMessageBox.warning(None, '无法保存阅读记录', '本次可继续使用，下次启动时需要重新阅读说明。')
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True
