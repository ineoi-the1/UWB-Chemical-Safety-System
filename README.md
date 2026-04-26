# 化工实训UWB定位数字孪生与大模型预警系统 V1.0

> 基于Python开发的化工实训场景人员实时定位、数字孪生可视化与本地大模型智能安全预警系统

---

## 📌 项目简介
本系统针对化工实训场景人员安全监控需求，实现了以下核心功能：
- UWB串口数据实时采集与三边定位解算
- 人员位置轨迹绘制与数字孪生设备场景可视化
- 多角色人员（班长/外操员/内操员）状态监控
- 本地大模型（Ollama）异常行为智能分析与预警
- 实时数据日志与异常信息滚动展示

---

## 🛠️ 技术栈
- 语言：Python 3.10+
- 界面：Tkinter
- 串口通信：PySerial
- 大模型：Ollama（本地部署）
- 依赖：见 `requirements.txt`

---

## 📁 项目结构
UWB-Chemical-Safety-System/
├── README.md 项目说明文档
├── main.py 系统入口文件
├── uwb_gui.py 数字孪生定位界面
├── ai.py 大模型 AI 预警模块
├── requirements.txt 依赖清单

🚀 快速运行
安装依赖：
bash
运行
pip install -r requirements.txt
确保本地 Ollama 已启动
运行主程序：
bash
运行
python main.py

📄 版权信息
本项目为原创独立开发，已申请计算机软件著作权，版本 V1.0，仅用于学术与实训场景使用。
---

