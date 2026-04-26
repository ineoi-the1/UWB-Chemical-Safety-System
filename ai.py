# ai.py
import requests

class LocalAIMonitor:
    def __init__(self):
        # 你的本地 Ollama API 地址
        self.api_url = "http://localhost:11434/api/generate"
        self.model_name = "qwen:4b"

    def analyze_still(self, role_name, idle_seconds):
        """
        分析人员静止状态，生成AI预警信息
        :param role_name: 人员角色（班长/外操员1/外操员2/内操员）
        :param idle_seconds: 静止时长（秒）
        :return: AI生成的预警文本
        """
        prompt = f"""你是化工实训安全监控AI助手。
监控对象：{role_name}
静止时长：{idle_seconds}秒
规则：静止超过3秒即为异常，需要发出预警。
请输出一句简洁、专业的预警信息。"""

        try:
            resp = requests.post(self.api_url, json={
                "model": self.model_name,
                "prompt": prompt,
                "stream": False
            }, timeout=10)
            return resp.json()["response"].strip()
        except Exception as e:
            print(f"⚠️ 大模型调用失败: {e}")
            return f"⚠️ {role_name}已静止超过{idle_seconds}秒，异常预警"