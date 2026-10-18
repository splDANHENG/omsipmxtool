# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 omsipmxtool contributors
def smoke_test(report_path):
    import json
    import os
    import tempfile
    from pathlib import Path
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from omsimod.gui import Window, main
    from omsimod.naming import pinyin_name
    from omsimod.model_notice import ModelNotice

    with tempfile.TemporaryDirectory() as directory:
        os.environ['OMSIMOD_DATA_DIR'] = directory
        app = QApplication([])
        checked = {'notice_seen': False, 'scroll_required': False}
        def finish():
            notice = next((w for w in app.topLevelWidgets()
                           if isinstance(w, ModelNotice) and w.isVisible()), None)
            if notice is not None:
                checked['notice_seen'] = True
                checked['scroll_required'] = not notice.proceed.isEnabled()
                bar = notice.text.verticalScrollBar()
                bar.setValue(bar.maximum())
                notice.check_end()
                notice.proceed.click()
                QTimer.singleShot(500, finish)
                return
            window = next(w for w in app.topLevelWidgets() if isinstance(w, Window))
            Path(report_path).write_text(json.dumps({
                'platform': app.platformName(),
                'visible': window.isVisible(),
                'title': window.windowTitle(),
                'pinyin_check': pinyin_name('饮月君 1708'),
                **checked,
                'notice_saved': (Path(directory)/'model-rights-read.txt').is_file(),
            }), encoding='utf-8')
            window.close()
            app.quit()

        QTimer.singleShot(1000, finish)
        return main()


if __name__ == '__main__':
    try:
        import sys
        if len(sys.argv) == 3 and sys.argv[1] == '--smoke-test':
            raise SystemExit(smoke_test(sys.argv[2]))
        from omsimod.gui import main
        raise SystemExit(main())
    except Exception:
        import traceback
        from omsimod.paths import data_directory
        directory = data_directory()
        directory.mkdir(parents=True, exist_ok=True)
        (directory / 'startup-error.log').write_text(traceback.format_exc(), encoding='utf-8')
        raise
