def smoke_test(report_path):
    import json
    import os
    import tempfile
    from pathlib import Path
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QApplication
    from omsimod.gui import Window, main

    with tempfile.TemporaryDirectory() as directory:
        os.environ['OMSIMOD_DATA_DIR'] = directory
        app = QApplication([])
        def finish():
            window = next(w for w in app.topLevelWidgets() if isinstance(w, Window))
            Path(report_path).write_text(json.dumps({
                'platform': app.platformName(),
                'visible': window.isVisible(),
                'title': window.windowTitle(),
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
