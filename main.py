# main.py
import tkinter as tk
from uwb_gui import UWBRadar_GUI
from ai import LocalAIMonitor

if __name__ == "__main__":
    # 初始化大模型模块
    ai_monitor = LocalAIMonitor()
    # 启动主界面，传入AI模块
    root = tk.Tk()
    app = UWBRadar_GUI(root, ai_monitor=ai_monitor)
    root.mainloop()