import sys
import os

# 兼容源码启动与 PyInstaller 打包环境
if getattr(sys, "frozen", False):
    base_dir = getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__)))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)
else:
    base_dir = os.path.abspath(os.path.dirname(__file__))
    if base_dir not in sys.path:
        sys.path.insert(0, base_dir)

from desktop.ui.app import main

if __name__ == "__main__":
    main()
