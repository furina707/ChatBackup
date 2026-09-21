import sys
import os

# 将当前 desktop 所在根目录加入 Python Path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from desktop.ui.app import main

if __name__ == "__main__":
    main()
