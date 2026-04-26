# uwb_gui.py（布局修复版）
import serial
import math
import time
import random
from datetime import datetime
try:
    import tkinter as tk
except ImportError:
    import Tkinter as tk

# ===================== 核心配置常量 =====================
COM_PORT = 'COM5'              # 串口端口
BAUD_RATE = 115200             # 波特率
MAX_TRAIL_LENGTH = 300         # 最大轨迹点数量
MAX_LANES = 26                 # 日志最大行数
ANIMATION_FPS = 60             # 动画帧率
BLINK_INTERVAL = 500           # 塔灯闪烁间隔(ms)
AI_INSIGHT_INTERVAL = 1000     # AI分析间隔(ms)
SERIAL_UPDATE_INTERVAL = 20    # 串口更新间隔(ms)

# ===================== 颜色配置 =====================
COLORS = {
    "bg_main": "#0B0F19",        # 主背景色
    "bg_panel": "#111827",       # 面板背景色
    "border": "#1E293B",         # 边框色
    "equip_fill": "#1F2937",     # 设备填充色
    "equip_line": "#374151",     # 设备线条色
    "equip_text": "#9CA3AF",     # 设备文字色
    "zone_line": "#4B5563",      # 区域线条色
    "matrix_green": "#10B981",   # 矩阵绿色
    "gold": "#F59E0B",           # 金色
    "alert_red": "#EF4444",      # 警告红
    "cyan": "#0EA5E9",           # 青色
    "ai_blue": "#8B5CF6",        # AI蓝色
    "tower": "#64748B",          # 塔架色
    "white": "#F8FAFC",          # 白色
    "text_dim": "#475569"        # 暗淡文字色
}

# ===================== 角色与颜色映射 =====================
ROLE_MAP = {5: "班长", 6: "外操员1", 7: "外操员2", 8: "内操员"}
TAG_COLORS = {5: "#FF003C", 6: "#00F0FF", 7: "#FFD700", 8: "#B026FF"}

class UWBRadar_GUI:
    def __init__(self, master, ai_monitor=None):
        self.master = master
        self.ai_monitor = ai_monitor
        self._init_ui()          # 初始化UI
        self._init_data()        # 初始化数据
        self._init_serial()      # 初始化串口
        self._start_animations() # 启动动画循环

    def _init_ui(self):
        """初始化界面布局"""
        # 主窗口配置
        self.master.title("化工实训数字孪生监控系统")
        self.master.geometry("1600x1000")  # 加宽窗口，适配双区域
        self.master.configure(bg=COLORS["bg_main"])

        # 底部控制台（滑块区域）
        self._create_control_frame()

        # 状态栏
        self._create_status_frame()

        # 主容器（画布+日志区）
        self._create_main_container()

    def _create_control_frame(self):
        """创建底部控制滑块区域"""
        self.control_frame = tk.Frame(
            self.master, 
            bg=COLORS["bg_panel"], 
            highlightthickness=1, 
            highlightbackground=COLORS["border"]
        )
        self.control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=(0, 15))
        self.control_frame.pack_propagate(False)

        # 左右间距填充
        tk.Frame(self.control_frame, bg=COLORS["bg_panel"]).pack(side=tk.LEFT, expand=True)

        # 滑块变量
        self.h_var = tk.DoubleVar(value=4.80)  # A1(Y轴)间距
        self.w_var = tk.DoubleVar(value=3.20)  # A2(X轴)间距
        self.calib_var = tk.DoubleVar(value=0.00)  # 硬件误差补偿

        # 创建滑块
        self._create_slider(self.control_frame, self.h_var, "A1 (Y轴) 间距(m)", 1.0, 8.0)
        self._create_slider(self.control_frame, self.w_var, "A2 (X轴) 间距(m)", 1.0, 8.0)
        self._create_slider(self.control_frame, self.calib_var, "硬件误差补偿(m)", -1.0, 1.0)

        tk.Frame(self.control_frame, bg=COLORS["bg_panel"]).pack(side=tk.LEFT, expand=True)

    def _create_slider(self, parent, variable, label_text, from_val, to_val):
        """创建单个滑块组件"""
        container = tk.Frame(parent, bg=COLORS["bg_panel"])
        container.pack(side=tk.LEFT, padx=30, pady=10)
        
        # 滑块标签
        tk.Label(
            container, 
            text=label_text, 
            font=("Microsoft YaHei", 10, "bold"), 
            fg=COLORS["cyan"], 
            bg=COLORS["bg_panel"]
        ).pack(side=tk.TOP, pady=(0, 2))
        
        # 滑块
        tk.Scale(
            container, 
            variable=variable, 
            from_=from_val, 
            to=to_val, 
            resolution=0.01, 
            orient=tk.HORIZONTAL,
            bg=COLORS["bg_panel"], 
            fg=COLORS["white"], 
            troughcolor=COLORS["border"],
            highlightthickness=0, 
            length=180, 
            showvalue=True
        ).pack(side=tk.TOP)
        
        # 绑定滑块值变化事件（实时重绘）
        variable.trace_add('write', self.redraw_all)

    def _create_status_frame(self):
        """创建顶部状态栏"""
        self.status_frame = tk.Frame(self.master, bg=COLORS["bg_main"])
        self.status_frame.pack(fill=tk.X, pady=(15, 5))
        
        self.label = tk.Label(
            self.status_frame, 
            text="DIGITAL TWIN ENGINE 60FPS | AI MONITOR ONLINE",
            font=("Consolas", 12, "bold"), 
            fg=COLORS["cyan"], 
            bg=COLORS["bg_main"]
        )
        self.label.pack()

    def _create_main_container(self):
        """创建主容器（绘图画布+日志画布）"""
        self.main_container = tk.Frame(self.master, bg=COLORS["bg_main"])
        self.main_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)

        # 主绘图画布（固定宽度，防止被挤压）
        self.canvas_width = 1200
        self.canvas_height = 800
        self.canvas = tk.Canvas(
            self.main_container, 
            width=self.canvas_width, 
            height=self.canvas_height,
            bg=COLORS["bg_main"], 
            highlightthickness=0
        )
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # HUD标题
        self.hud_text_id = self.canvas.create_text(
            self.canvas_width/2, 20, text="",  # 居中显示HUD
            font=("Microsoft YaHei", 11, "bold"), 
            fill=COLORS["cyan"],
            anchor=tk.N, 
            justify=tk.CENTER
        )

        # 右侧日志画布（固定宽度）
        self.log_canvas = tk.Canvas(
            self.main_container, 
            width=380, 
            bg=COLORS["bg_panel"], 
            highlightthickness=1, 
            highlightbackground=COLORS["border"]
        )
        self.log_canvas.pack(side=tk.RIGHT, fill=tk.Y, padx=(15, 0))
        
        # 日志标题
        self.log_canvas.create_text(
            190, 15, 
            text="MATRIX DECODER", 
            font=("Consolas", 12, "bold"), 
            fill=COLORS["matrix_green"], 
            anchor=tk.N
        )
        self.log_canvas.create_line(15, 35, 365, 35, fill=COLORS["border"])

    def _init_data(self):
        """初始化数据存储"""
        self.logs = []                  # 日志列表
        self.log_queue = []             # 日志队列
        self.lane_tails = [None] * MAX_LANES  # 日志行尾标记
        self.frame_counter = 0          # 帧计数器
        
        # 标签状态存储
        self.tags_state = {}
        self.tower_lights = []          # 塔灯ID列表
        self.light_state = True         # 塔灯闪烁状态
        self.tower_centers = []         # 塔架中心坐标
        self.tower_waves = []           # 塔架波纹动画
        
        # 坐标缩放系数
        self.scale = 130
        self.offset_x = 0
        self.offset_y = 0
        
        # 串口缓冲区
        self.buffer = bytearray()

        # 初始重绘所有元素
        self.redraw_all()

    def _init_serial(self):
        """初始化串口通信"""
        try:
            self.ser = serial.Serial(COM_PORT, BAUD_RATE, timeout=0.05)
            self.update_serial_data()
            self._sys_log("✅ 物理链路层握手成功", COLORS["matrix_green"])
            self._sys_log("⚡ 防重叠红绿灯调度引擎已挂载...", COLORS["gold"])
        except Exception as e:
            self._sys_log(f"❌ 串口通信异常: {e}", COLORS["alert_red"])

    def _start_animations(self):
        """启动所有动画循环"""
        self.animate_60fps()       # 主动画循环(60FPS)
        self.blink_towers()        # 塔灯闪烁
        self.ai_insight_loop()     # AI分析循环

    # ===================== 核心绘图方法 =====================
    def redraw_all(self, *args):
        """重绘所有界面元素"""
        # 清除原有元素
        self.canvas.delete("anchor", "equip")
        self.tower_lights.clear()
        self.tower_centers.clear()
        
        # 获取当前配置值
        w = self.w_var.get()
        h = self.h_var.get()
        
        # 计算坐标偏移（以画布中心为基准，保证设备区居中）
        min_x, max_x = -4.0, max(w, 1.0) + 1.0
        min_y, max_y = -0.5, max(h, 5.3) + 0.5
        self.offset_x = self.canvas_width / 2 - ((max_x + min_x) / 2) * self.scale
        self.offset_y = self.canvas_height / 2 + ((max_y + min_y) / 2) * self.scale
        
        # 绘制设备布局、塔架
        self.draw_equipment_layout(h)
        self.draw_tower(0, 0, "A0 (原点)")
        self.draw_tower(0, h, f"A1 (Y轴 {h:.1f}m)")
        self.draw_tower(w, 0, f"A2 (X轴 {w:.1f}m)")
        
        # 提升HUD层级
        self.canvas.tag_raise(self.hud_text_id)
        
        # 重置标签初始化状态
        for tag_id in self.tags_state:
            self.tags_state[tag_id]['is_init'] = False
            self.init_tag_ui(tag_id)

    def draw_equipment_layout(self, h):
        """绘制化工设备布局"""
        # 设备区外框
        box_left = -3.8
        box_right = -1.2
        xc = -2.8
        text_center = -2.5
        
        # 绘制设备区边框
        cx1 = self.offset_x + box_left * self.scale
        cy1 = self.offset_y - 0.0 * self.scale
        cx2 = self.offset_x + box_right * self.scale
        cy2 = self.offset_y - 5.3 * self.scale
        self.canvas.create_rectangle(
            cx1, cy1, cx2, cy2, 
            fill=COLORS["bg_panel"], 
            outline=COLORS["zone_line"], 
            width=2, 
            dash=(8, 4), 
            tags="equip"
        )
        self._draw_text(text_center, 5.1, "化工实训核心设备区", font_size=15, color=COLORS["text_dim"])
        
        # 绘制具体设备
        self._draw_circle(xc, 0.5, 0.35, COLORS["equip_fill"])
        self._draw_circle(xc, 0.5, 0.15, COLORS["bg_main"])
        self._draw_text(xc, 0.5, "原料罐")
        
        self._draw_circle(xc, 1.4, 0.25, COLORS["equip_fill"])
        self._draw_circle(xc, 1.4, 0.05, COLORS["bg_main"])
        self._draw_text(xc, 1.4, "预热器")
        
        self._draw_rect(xc - 0.6, 2.1, xc + 0.6, 2.5, COLORS["equip_fill"])
        self._draw_rect(xc - 0.7, 2.15, xc - 0.6, 2.45, COLORS["bg_panel"])
        self._draw_rect(xc + 0.6, 2.15, xc + 0.7, 2.45, COLORS["bg_panel"])
        self._draw_text(xc, 2.3, "再沸器")
        
        self._draw_circle(xc - 0.2, 3.4, 0.25, COLORS["equip_fill"])
        self._draw_text(xc - 0.2, 3.4, "精馏塔")
        
        self._draw_rect(xc + 0.2, 3.2, xc + 0.6, 3.6, COLORS["equip_fill"])
        self._draw_text(xc + 0.4, 3.4, "换热器", font_size=9)
        
        self._draw_rect(xc - 0.5, 4.2, xc + 0.5, 4.6, COLORS["equip_fill"])
        self._draw_rect(xc - 0.6, 4.25, xc - 0.5, 4.55, COLORS["bg_panel"])
        self._draw_rect(xc + 0.5, 4.25, xc + 0.6, 4.55, COLORS["bg_panel"])
        self._draw_text(xc, 4.4, "残液罐")

    def _draw_circle(self, x, y, r, color):
        """绘制圆形元素"""
        cx = self.offset_x + x * self.scale
        cy = self.offset_y - y * self.scale
        r_px = r * self.scale
        self.canvas.create_oval(
            cx-r_px, cy-r_px, cx+r_px, cy+r_px,
            fill=color, 
            outline=COLORS["equip_line"], 
            width=2, 
            tags="equip"
        )

    def _draw_rect(self, x1, y1, x2, y2, color):
        """绘制矩形元素"""
        cx1 = self.offset_x + x1 * self.scale
        cy1 = self.offset_y - y1 * self.scale
        cx2 = self.offset_x + x2 * self.scale
        cy2 = self.offset_y - y2 * self.scale
        self.canvas.create_rectangle(
            cx1, cy1, cx2, cy2,
            fill=color, 
            outline=COLORS["equip_line"], 
            width=2, 
            tags="equip"
        )

    def _draw_text(self, x, y, text_str, font_size=10, color=COLORS["equip_text"]):
        """绘制文字元素"""
        cx = self.offset_x + x * self.scale
        cy = self.offset_y - y * self.scale
        self.canvas.create_text(
            cx, cy, 
            text=text_str, 
            font=("Microsoft YaHei", font_size, "bold"), 
            fill=color, 
            tags="equip"
        )

    def draw_tower(self, x, y, name):
        """绘制塔架元素"""
        cx = self.offset_x + x * self.scale
        cy = self.offset_y - y * self.scale
        
        # 塔架主体
        self.canvas.create_polygon(
            cx-12, cy+15, cx+12, cy+15, cx+4, cy-15, cx-4, cy-15,
            fill=COLORS["bg_panel"], 
            outline=COLORS["tower"], 
            width=2, 
            tags="equip"
        )
        self.canvas.create_line(
            cx, cy-15, cx, cy-25, 
            fill=COLORS["tower"], 
            width=2, 
            tags="equip"
        )
        
        # 塔灯
        light_id = self.canvas.create_oval(
            cx-3, cy-28, cx+3, cy-22, 
            fill=COLORS["cyan"], 
            outline=""
        )
        self.tower_lights.append(light_id)
        
        # 塔架中心（用于波纹动画）
        self.tower_centers.append((cx, cy-25))
        
        # 塔架标签
        self.canvas.create_text(
            cx, cy+38, 
            text=name, 
            font=("Segoe UI", 9, "bold"), 
            fill=COLORS["text_dim"], 
            tags="equip"
        )

    # ===================== 动画与交互 =====================
    def blink_towers(self):
        """塔灯闪烁动画"""
        self.light_state = not self.light_state
        color = COLORS["cyan"] if self.light_state else COLORS["bg_main"]
        for light in self.tower_lights:
            self.canvas.itemconfig(light, fill=color)
        self.master.after(BLINK_INTERVAL, self.blink_towers)

    def animate_60fps(self):
        """60FPS主动画循环"""
        self.frame_counter += 1
        current_time = time.time()
        
        # 更新HUD标题
        self._update_hud()
        
        # 塔架波纹动画
        self._update_tower_waves()
        
        # 处理日志队列和动画
        self._update_logs()
        
        # 更新标签位置和轨迹
        self._update_tags(current_time)
        
        # 循环调用
        self.master.after(int(1000/ANIMATION_FPS), self.animate_60fps)

    def _update_hud(self):
        """更新HUD显示信息"""
        w = self.w_var.get()
        radar_center_x = self.offset_x + (w / 2.0) * self.scale
        self.canvas.coords(self.hud_text_id, radar_center_x, 20)

        # 构建HUD信息
        hud_info = "⚡ TACTICAL HUD ⚡\n"
        has_tags = False
        count = 0
        
        for tag_id, tag in self.tags_state.items():
            if not tag['is_init']:
                continue
            has_tags = True
            idle_sec = int(time.time() - tag['last_move_time'])
            status = f"🏃移动" if tag['is_moving'] else f"🛑静止({idle_sec}s)"
            hud_info += f"[{tag['role']}]{status}   "
            count += 1
            # 每2个标签换行，防止文字溢出
            if count == 2:
                hud_info += "\n"
                
        if not has_tags:
            hud_info += "WAITING FOR UWB SIGNAL..."
            
        self.canvas.itemconfig(self.hud_text_id, text=hud_info.strip())

    def _update_tower_waves(self):
        """更新塔架波纹动画"""
        # 每60帧创建新波纹
        if self.frame_counter % 60 == 0:
            for tx, ty in self.tower_centers:
                wave_id = self.canvas.create_oval(
                    tx-1, ty-1, tx+1, ty+1,
                    outline=COLORS["cyan"], 
                    width=1.5, 
                    tags="wave"
                )
                self.canvas.tag_lower(wave_id, "equip")
                self.tower_waves.append({'id': wave_id, 'x': tx, 'y': ty, 'r': 1.0})

        # 更新波纹大小和透明度
        max_radius = 70.0
        for wave in self.tower_waves[:]:
            wave['r'] += 1.2
            r = wave['r']
            self.canvas.coords(wave['id'], wave['x']-r, wave['y']-r, wave['x']+r, wave['y']+r)
            
            # 渐变颜色
            progress = min(1.0, r / max_radius)
            self.canvas.itemconfig(wave['id'], outline=self._get_fade_color(progress))
            
            # 超出最大半径则删除
            if r > max_radius:
                self.canvas.delete(wave['id'])
                self.tower_waves.remove(wave)

    def _get_fade_color(self, progress):
        """获取波纹渐变颜色"""
        r = int(14 + (11 - 14) * progress)
        g = int(165 + (15 - 165) * progress)
        b = int(233 + (25 - 233) * progress)
        return f"#{r:02x}{g:02x}{b:02x}"

    def _update_logs(self):
        """更新日志动画"""
        # 处理日志队列
        if self.log_queue:
            if self._render_queued_log(self.log_queue[0]):
                self.log_queue.pop(0)

        # 更新日志位置和动画
        for log in self.logs[:]:
            # 随机数动画
            if log['scramble_id'] is not None:
                hex_str = f" [0x{random.randint(0x1000, 0xFFFF):04X}]"
                self.log_canvas.itemconfig(log['scramble_id'], text=hex_str)
                
            # 闪烁效果
            if log['blink_info'] is not None:
                current_color = log['blink_info']['color'] if (self.frame_counter % 8) < 4 else COLORS["white"]
                self.log_canvas.itemconfig(log['blink_info']['id'], fill=current_color)

            # 日志左移
            log['x'] -= log['speed_x']
            
            # 判断是否超出可视区域
            is_dead = False
            bbox_last = self.log_canvas.bbox(log['ids'][-1])
            if (bbox_last and bbox_last[2] < -50) or log['x'] < -600:
                is_dead = True

            # 删除或更新日志位置
            if is_dead:
                for tid in log['ids']:
                    self.log_canvas.delete(tid)
                self.logs.remove(log)
            else:
                current_x = log['x']
                for tid in log['ids']:
                    self.log_canvas.coords(tid, current_x, log['y'])
                    bbox = self.log_canvas.bbox(tid)
                    if bbox:
                        current_x = bbox[2] + 2

    def _update_tags(self, current_time):
        """更新标签位置和轨迹"""
        for tag_id, tag in self.tags_state.items():
            if not tag['is_init']:
                continue
            
            # 平滑移动到目标位置
            dx = tag['target_x'] - tag['last_drawn_x']
            dy = tag['target_y'] - tag['last_drawn_y']
            dist = math.hypot(dx, dy)
            
            if dist > 0.001:
                max_step = 1.5 / ANIMATION_FPS
                step = dist * 0.15
                
                if step > max_step:
                    step = max_step
                
                ratio = step / dist
                tag['last_drawn_x'] += dx * ratio
                tag['last_drawn_y'] += dy * ratio
            
            # 计算像素坐标
            cx = self.offset_x + tag['last_drawn_x'] * self.scale
            cy = self.offset_y - tag['last_drawn_y'] * self.scale
            
            # 更新标签UI位置
            error_px = 0.35 * self.scale
            self.canvas.coords(tag['ui_circle'], cx - error_px, cy - error_px, cx + error_px, cy + error_px)
            self.canvas.coords(tag['ui_dot'], cx - 8, cy - 8, cx + 8, cy + 8)
            self.canvas.coords(tag['ui_mono'], cx, cy)
            
            # 更新文字背景和位置
            self.canvas.coords(tag['ui_text'], cx + 18, cy)
            bbox = self.canvas.bbox(tag['ui_text'])
            if bbox:
                self.canvas.coords(tag['ui_text_bg'], bbox[0]-4, bbox[1]-2, bbox[2]+4, bbox[3]+2)
            
            # 更新轨迹
            dist_to_target = math.hypot(tag['last_drawn_x'] - tag['target_x'], tag['last_drawn_y'] - tag['target_y'])
            if tag['is_moving'] or dist_to_target > 0.02:
                tag['idle_frames'] = 0
                # 添加轨迹点
                trail_dot = self.canvas.create_oval(
                    cx-1.5, cy-1.5, cx+1.5, cy+1.5,
                    fill=tag['color'], 
                    outline="", 
                    tags=f"trail_{tag_id}"
                )
                tag['trails'].append(trail_dot)
                self.canvas.tag_lower(trail_dot, "equip")
                
                # 限制轨迹长度
                if len(tag['trails']) > MAX_TRAIL_LENGTH:
                    self.canvas.delete(tag['trails'].pop(0))
            else:
                tag['idle_frames'] += 1
                # 静止时逐渐删除轨迹
                if tag['idle_frames'] > 75 and tag['trails']:
                    self.canvas.delete(tag['trails'].pop(0))
                    
            # 提升标签层级
            self.canvas.tag_raise(f"tag_{tag_id}")

    # ===================== 日志处理 =====================
    def _sys_log(self, text, color):
        """系统日志封装"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        segments = [
            (f"[{timestamp}] ", COLORS["text_dim"], ("Consolas", 9)),
            (text, color, ("Microsoft YaHei", 9, "bold"))
        ]
        self.queue_segments(segments, 2.5, False)

    def queue_segments(self, segments, base_speed, has_scramble=False, blink_idx=None):
        """加入日志队列"""
        self.log_queue.append({
            'segments': segments,
            'base_speed': base_speed,
            'has_scramble': has_scramble,
            'blink_idx': blink_idx
        })
        # 限制队列长度
        if len(self.log_queue) > 60:
            self.log_queue = self.log_queue[-60:]

    def _render_queued_log(self, log_data):
        """渲染日志到画布"""
        # 寻找空闲行
        free_lane = -1
        for i in range(MAX_LANES):
            last_log = self.lane_tails[i]
            is_free = False
            
            if last_log is None or last_log not in self.logs:
                is_free = True
            else:
                bbox = self.log_canvas.bbox(last_log['ids'][-1])
                if not bbox or bbox[2] < 320:
                    is_free = True
                    
            if is_free:
                free_lane = i
                break
                
        if free_lane == -1:
            return False
            
        # 计算日志位置
        lane_y = 50.0 + free_lane * 28.0
        start_x = 380.0
        current_x = start_x
        
        segment_ids = []
        scramble_id = None
        blink_id = None
        
        # 绘制日志分段
        for idx, (text, color, font_tuple) in enumerate(log_data['segments']):
            txt_id = self.log_canvas.create_text(
                current_x, lane_y, 
                text=text, 
                font=font_tuple, 
                fill=color, 
                anchor=tk.NW
            )
            segment_ids.append(txt_id)
            
            if log_data['has_scramble'] and idx == 1:
                scramble_id = txt_id
            if log_data['blink_idx'] == idx:
                blink_id = {'id': txt_id, 'color': color}
                
            # 更新X坐标
            bbox = self.log_canvas.bbox(txt_id)
            if bbox:
                current_x = bbox[2] + 2

        # 随机速度
        final_speed = log_data['base_speed'] + random.uniform(-0.4, 0.4)
        
        # 创建日志对象
        new_log = {
            'ids': segment_ids,
            'scramble_id': scramble_id,
            'blink_info': blink_id,
            'x': start_x,
            'y': lane_y,
            'speed_x': final_speed
        }
        
        # 添加到日志列表
        self.logs.append(new_log)
        self.lane_tails[free_lane] = new_log
        
        return True

    # ===================== 标签管理 =====================
    def init_tag_ui(self, tag_id):
        """初始化标签UI"""
        color = TAG_COLORS.get(tag_id, COLORS["cyan"])
        role_name = ROLE_MAP.get(tag_id, "未知节点")
        tag_tag = f"tag_{tag_id}"
        
        # 创建标签元素
        error_circle = self.canvas.create_oval(
            -10, -10, -10, -10,
            outline=color, 
            dash=(2, 4), 
            width=1.5, 
            tags=tag_tag
        )
        dot = self.canvas.create_oval(
            -10, -10, -10, -10,
            fill=color, 
            outline=COLORS["white"], 
            width=2, 
            tags=tag_tag
        )
        monogram_text = self.canvas.create_text(
            -10, -10, 
            text=f"T{tag_id-4}", 
            font=("Arial", 6, "bold"), 
            fill=COLORS["bg_main"], 
            tags=tag_tag
        )
        text_bg = self.canvas.create_rectangle(
            -10, -10, -10, -10,
            fill=COLORS["bg_panel"], 
            outline=color, 
            width=1, 
            tags=tag_tag
        )
        text_label = self.canvas.create_text(
            -10, -10, 
            text=role_name, 
            font=("Microsoft YaHei", 9, "bold"), 
            fill=COLORS["white"], 
            anchor=tk.W, 
            tags=tag_tag
        )
        
        # 初始化标签状态
        if tag_id not in self.tags_state:
            self.tags_state[tag_id] = {
                'r0_hist': [], 'r1_hist': [], 'r2_hist': [],
                'x_hist': [], 'y_hist': [],
                'target_x': 0.0, 'target_y': 0.0,
                'last_drawn_x': 0.0, 'last_drawn_y': 0.0,
                'last_med_x': 0.0, 'last_med_y': 0.0,
                'last_update_time': time.time(),
                'reject_count': 0,
                'is_moving': False,
                'stop_frames': 0,
                'break_frames': 0,
                'idle_frames': 0,
                'last_move_time': time.time(),
                'last_track_log_time': 0.0,
                'trails': [],
                'color': color,
                'role': role_name
            }
            
        # 更新标签UI引用
        self.tags_state[tag_id].update({
            'ui_circle': error_circle,
            'ui_dot': dot,
            'ui_mono': monogram_text,
            'ui_text_bg': text_bg,
            'ui_text': text_label,
            'is_init': False
        })
        
        # 初始隐藏
        for k in ['ui_circle', 'ui_dot', 'ui_mono', 'ui_text_bg', 'ui_text']:
            self.canvas.itemconfig(self.tags_state[tag_id][k], state='hidden')

    # ===================== 串口数据处理 =====================
    def update_serial_data(self):
        """更新串口数据"""
        try:
            # 读取串口数据
            count = self.ser.inWaiting()
            if count > 0:
                data = self.ser.read(count)
                self.buffer.extend(bytearray(data) if type(data) is str else data)

            # 解析数据包（分隔符：0x0d 0x6d 0x72）
            while True:
                idx = self.buffer.find(b'\x0d\x6d\x72')
                if idx == -1:
                    # 保留最后2个字节防止分隔符被截断
                    if len(self.buffer) > 2:
                        self.buffer = self.buffer[-2:]
                    break
                    
                # 验证数据包长度
                if len(self.buffer) >= 16 and len(self.buffer) >= idx + 16:
                    payload = self.buffer[idx : idx+16]
                    tag_id = payload[4]
                    # 过滤无效标签ID
                    if tag_id not in [5, 6, 7, 8]:
                        self.buffer = self.buffer[idx+16:]
                        continue

                    # 初始化标签UI
                    if tag_id not in self.tags_state or 'ui_dot' not in self.tags_state[tag_id]:
                        self.init_tag_ui(tag_id)

                    # 解析距离数据
                    a0_cm = payload[7] | (payload[8] << 8)
                    a1_cm = payload[9] | (payload[10] << 8)
                    a2_cm = payload[11] | (payload[12] << 8)
                    
                    # 处理定位算法
                    self.process_math(tag_id, a0_cm, a1_cm, a2_cm)
                    self.buffer = self.buffer[idx+16:]
                else:
                    self.buffer = self.buffer[idx:]
                    break
        except Exception:
            pass
        
        # 循环调用
        self.master.after(SERIAL_UPDATE_INTERVAL, self.update_serial_data)

    def process_math(self, tag_id, a0_cm, a1_cm, a2_cm):
        """定位算法处理"""
        calib = self.calib_var.get()
        tag = self.tags_state[tag_id]
        role = tag['role']
        tag_color = tag['color']
        
        # 转换为米并补偿
        if a0_cm > 0:
            tag['r0_hist'].append(max(0.01, (a0_cm / 100.0) - calib))
        if a1_cm > 0:
            tag['r1_hist'].append(max(0.01, (a1_cm / 100.0) - calib))
        if a2_cm > 0:
            tag['r2_hist'].append(max(0.01, (a2_cm / 100.0) - calib))
        
        # 限制历史数据长度
        tag['r0_hist'] = tag['r0_hist'][-9:]
        tag['r1_hist'] = tag['r1_hist'][-9:]
        tag['r2_hist'] = tag['r2_hist'][-9:]

        # 数据不足则返回
        if len(tag['r0_hist']) < 9:
            return

        # 中位数滤波
        r0 = sorted(tag['r0_hist'])[len(tag['r0_hist'])//2]
        r1 = sorted(tag['r1_hist'])[len(tag['r1_hist'])//2]
        r2 = sorted(tag['r2_hist'])[len(tag['r2_hist'])//2]

        # 三边定位算法
        h, w = self.h_var.get(), self.w_var.get()
        if w > 0 and h > 0 and r0 > 0 and r1 > 0 and r2 > 0:
            raw_x = (r0**2 - r2**2 + w**2) / (2.0 * w)
            raw_y = (r0**2 - r1**2 + h**2) / (2.0 * h)
            
            # 边界限制
            raw_x = max(-3.5, min(w + 3.0, raw_x))
            raw_y = max(-1.5, min(h + 3.0, raw_y))
            
            # 存储原始坐标
            tag['x_hist'].append(raw_x)
            tag['y_hist'].append(raw_y)
            tag['x_hist'] = tag['x_hist'][-11:]
            tag['y_hist'] = tag['y_hist'][-11:]
                
            # 坐标中位数滤波
            med_x = sorted(tag['x_hist'])[len(tag['x_hist'])//2]
            med_y = sorted(tag['y_hist'])[len(tag['y_hist'])//2]

            # 时间差计算
            curr_time = time.time()
            dt = curr_time - tag.get('last_update_time', curr_time)
            if dt <= 0:
                dt = 0.01
            tag['last_update_time'] = curr_time

            # 初始化标签位置
            if not tag['is_init']:
                tag['target_x'], tag['target_y'] = med_x, med_y
                tag['last_drawn_x'], tag['last_drawn_y'] = med_x, med_y
                tag['last_med_x'], tag['last_med_y'] = med_x, med_y
                tag['last_move_time'] = curr_time
                tag['is_init'] = True
                # 显示标签UI
                for k in ['ui_dot', 'ui_mono', 'ui_circle', 'ui_text_bg', 'ui_text']:
                    self.canvas.itemconfig(tag[k], state='normal')
            else:
                # 异常跳变检测
                jump = math.hypot(med_x - tag['last_med_x'], med_y - tag['last_med_y'])
                max_allowed = 1.5 * dt  # 最大允许移动距离
                
                if jump > max_allowed and tag['reject_count'] < 15:
                    tag['reject_count'] += 1
                    # 每4次拦截记录一次日志
                    if tag['reject_count'] % 4 == 1:
                        ts = datetime.now().strftime("%H:%M:%S")
                        segs = [
                            (f"[{ts}]", COLORS["text_dim"], ("Consolas", 9)),
                            (" [0xDEAD]", COLORS["alert_red"], ("Consolas", 9, "bold")),
                            (f" [{role}]", tag_color, ("Microsoft YaHei", 9, "bold")),
                            (" 异常跳变拦截 ", COLORS["alert_red"], ("Microsoft YaHei", 9, "bold")),
                            (f"d={jump:.2f}m", COLORS["cyan"], ("Consolas", 9))
                        ]
                        self.queue_segments(segs, 4.5, True, blink_idx=1)
                    return 
                else:
                    tag['reject_count'] = 0
                    tag['last_med_x'], tag['last_med_y'] = med_x, med_y
                
                    # 移动状态检测
                    drift = math.hypot(med_x - tag['target_x'], med_y - tag['target_y'])
                    
                    if tag['is_moving']:
                        tag['last_move_time'] = curr_time
                        if drift > 0.10:
                            tag['target_x'], tag['target_y'] = med_x, med_y
                            tag['stop_frames'] = 0
                        else:
                            tag['stop_frames'] += 1
                            if tag['stop_frames'] > 15:
                                tag['is_moving'] = False
                                tag['break_frames'] = 0
                    else:
                        if drift > 0.45:
                            tag['break_frames'] += 1
                            if tag['break_frames'] > 5:
                                tag['is_moving'] = True
                                tag['stop_frames'] = 0
                                tag['target_x'], tag['target_y'] = med_x, med_y
                                tag['last_move_time'] = curr_time
                        else:
                            tag['break_frames'] = 0 

            # 定期记录追踪日志
            if curr_time - tag['last_track_log_time'] > 0.5:
                tag['last_track_log_time'] = curr_time
                state_str = "追踪" if tag['is_moving'] else "静止"
                state_color = COLORS["gold"] if tag['is_moving'] else COLORS["matrix_green"]
                ts = datetime.now().strftime("%H:%M:%S")
                
                segs = [
                    (f"[{ts}]", COLORS["text_dim"], ("Consolas", 9)),
                    (" [0x0000]", COLORS["matrix_green"], ("Consolas", 9, "bold")),
                    (f" [{role}] ", tag_color, ("Microsoft YaHei", 9, "bold")),
                    (f"[{state_str}] ", state_color, ("Microsoft YaHei", 9, "bold")),
                    (f"r0:{r0:.2f} r1:{r1:.2f}", COLORS["cyan"], ("Consolas", 9))
                ]
                self.queue_segments(segs, 3.2 if tag['is_moving'] else 2.2, True, blink_idx=None)

    # ===================== AI分析 =====================
    def ai_insight_loop(self):
        """AI分析循环"""
        curr_time = time.time()
        for tag_id, tag in self.tags_state.items():
            if not tag['is_init']:
                continue
            # 计算静止时间
            idle_sec = int(curr_time - tag['last_move_time'])
            # 静止超过5秒，调用大模型分析
            if not tag['is_moving'] and idle_sec == 5:
                if self.ai_monitor:
                    ai_result = self.ai_monitor.analyze_still(tag['role'], idle_sec)
                else:
                    ai_result = f"{tag['role']} 静止超时，请注意！"
                ts = datetime.now().strftime("%H:%M:%S")
                segs = [
                    (f"[{ts}]", COLORS["text_dim"], ("Consolas", 9)),
                    (" [AI_ALERT]", COLORS["alert_red"], ("Consolas", 9, "bold")),
                    (f" {ai_result} ", COLORS["white"], ("Microsoft YaHei", 9, "bold"))
                ]
                self.queue_segments(segs, 3.5, False, blink_idx=1)
                
        # 循环调用
        self.master.after(AI_INSIGHT_INTERVAL, self.ai_insight_loop)