"""
TCAD 聊天对话框 - 标准AI对话布局
"""
import os
import json
import configparser
import markdown
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QTextBrowser, QFrame, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QTextOption

from core.chat.upsonic_client import UpsonicClient
from core.chat import tcad_tools as tcad_tools_module

_MARKDOWN_CSS = """
<style>
body { font-family: 'WenQuanYi Micro Hei', 'Noto Sans CJK SC', sans-serif; font-size: 13px; }
h1 { font-size: 19px; font-weight: bold; margin-top: 16px; margin-bottom: 8px; color: #1a1a2e; }
h2 { font-size: 17px; font-weight: bold; margin-top: 14px; margin-bottom: 6px; color: #16213e; }
h3 { font-size: 15px; font-weight: bold; margin-top: 12px; margin-bottom: 4px; color: #0f3460; }
h4 { font-size: 14px; font-weight: bold; margin-top: 10px; margin-bottom: 4px; }
h5 { font-size: 13px; font-weight: bold; }
h6 { font-size: 12px; font-weight: bold; }
p { margin: 4px 0; line-height: 1.6; }
code { font-family: 'Courier New', monospace; font-size: 12px; background-color: #f0f0f0; padding: 1px 4px; border-radius: 3px; }
pre { background-color: #f6f8fa; padding: 12px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }
pre code { background-color: transparent; padding: 0; }
ul, ol { margin: 4px 0; padding-left: 24px; }
li { margin: 2px 0; line-height: 1.6; }
blockquote { border-left: 4px solid #ddd; margin: 8px 0; padding: 8px 16px; color: #6a737d; background-color: #f9f9f9; }
table { border-collapse: collapse; margin: 8px 0; width: 100%%; }
th, td { border: 1px solid #ddd; padding: 6px 12px; text-align: left; }
th { background-color: #f2f2f2; font-weight: bold; }
hr { border: none; border-top: 1px solid #ddd; margin: 12px 0; }
a { color: #0366d6; text-decoration: none; }
a:hover { text-decoration: underline; }
</style>
"""


def _render_md(text: str, color: str = "#333333") -> str:
    html = markdown.markdown(
        text,
        extensions=['tables', 'fenced_code', 'nl2br'],
        extension_configs={
            'fenced_code': {'lang_prefix': 'language-'},
        }
    )
    return html


class ChatMessageBubble(QWidget):
    """单条消息气泡"""

    def __init__(self, text: str, is_user: bool = False, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._raw_text = text
        self._setup_ui()
        if text:
            self.set_text(text)

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 6, 12, 6)
        layout.setSpacing(0)

        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.label.setOpenExternalLinks(True)

        if self.is_user:
            self.setStyleSheet("""
                QWidget {
                    background-color: #dcf8c6;
                    border-radius: 8px;
                }
            """)
            layout.setContentsMargins(48, 10, 16, 10)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #ffffff;
                    border: 1px solid #e8e8e8;
                    border-radius: 8px;
                }
            """)
            layout.setContentsMargins(16, 10, 48, 10)

        layout.addWidget(self.label)

    def set_text(self, text: str):
        self._raw_text = text
        color = "#1a1a1a" if self.is_user else "#333333"
        self.label.setText(_render_md(text, color))

    def append_text(self, token: str):
        self._raw_text += token
        color = "#1a1a1a" if self.is_user else "#333333"
        self.label.setText(_render_md(self._raw_text, color))

    def finalize(self):
        color = "#1a1a1a" if self.is_user else "#333333"
        self.label.setText(_render_md(self._raw_text, color))


class ChatWidget(QWidget):
    """聊天主组件"""

    def __init__(self, project_path: str = None, parent=None):
        super().__init__(parent)
        self.project_path = project_path or os.getcwd()
        self.client = None
        self.current_bubble = None
        self.current_text = ""
        self._scroll_to_bottom_enabled = True
        self._setup_ui()
        self._init_client()

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # 顶部标题栏
        header = QFrame()
        header.setStyleSheet("background-color: #1976d2;")
        header.setMinimumHeight(40)
        header.setMaximumHeight(40)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 0, 12, 0)
        title = QLabel(" TCAD AI 智能对话")
        title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        clear_btn = QPushButton("清空")
        clear_btn.setStyleSheet("""
            QPushButton { background-color: #1565c0; color: white; border: none;
                         padding: 4px 12px; border-radius: 4px; font-size: 12px; }
            QPushButton:hover { background-color: #0d47a1; }
        """)
        clear_btn.clicked.connect(self.clear_chat)
        header_layout.addWidget(clear_btn)
        main_layout.addWidget(header)

        # 消息滚动区域
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("QScrollArea { border: none; background-color: #f5f5f5; }")

        # 消息容器 - 使用简单的 QWidget + QVBoxLayout
        self.msg_container = QWidget()
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setContentsMargins(8, 8, 8, 8)
        self.msg_layout.setSpacing(4)
        self.msg_layout.addStretch(1)

        self.scroll.setWidget(self.msg_container)
        main_layout.addWidget(self.scroll, 1)

        # 监听滚动条范围变化，自动吸底
        vbar = self.scroll.verticalScrollBar()
        vbar.rangeChanged.connect(self._on_scroll_range_changed)

        # 底部输入区
        input_frame = QFrame()
        input_frame.setStyleSheet("background-color: white; border-top: 1px solid #e0e0e0;")
        input_frame.setMinimumHeight(48)
        input_frame.setMaximumHeight(48)
        input_layout = QHBoxLayout(input_frame)
        input_layout.setContentsMargins(8, 6, 8, 6)
        input_layout.setSpacing(8)

        self.input = QLineEdit()
        self.input.setPlaceholderText("输入消息... (Enter发送)")
        self.input.setFixedHeight(36)
        self.input.setStyleSheet("""
            QLineEdit { border: 1px solid #d0d0d0; border-radius: 18px;
                       padding: 0 16px; font-size: 13px; background: #fafafa; }
            QLineEdit:focus { border-color: #1976d2; background: white; }
        """)
        self.input.returnPressed.connect(self.send)
        input_layout.addWidget(self.input, 1)

        self.send_btn = QPushButton("发送")
        self.send_btn.setFixedSize(80, 36)
        self.send_btn.setStyleSheet("""
            QPushButton { background-color: #1976d2; color: white; border: none;
                         border-radius: 18px; font-weight: bold; font-size: 13px; }
            QPushButton:hover { background-color: #1565c0; }
            QPushButton:disabled { background-color: #b0bec5; }
        """)
        self.send_btn.clicked.connect(self.send)
        input_layout.addWidget(self.send_btn)
        main_layout.addWidget(input_frame)

        # 状态栏
        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #fafafa; border-top: 1px solid #e0e0e0;")
        status_frame.setMinimumHeight(24)
        status_frame.setMaximumHeight(24)
        s_layout = QHBoxLayout(status_frame)
        s_layout.setContentsMargins(10, 0, 10, 0)
        self.status = QLabel("就绪")
        self.status.setStyleSheet("color: #888; font-size: 11px;")
        s_layout.addWidget(self.status)
        main_layout.addWidget(status_frame)

    def set_project_path(self, path: str):
        self.project_path = path
        if self.client:
            self.client.project_path = path

    def _load_project_info(self):
        project_path = self.project_path
        if not project_path:
            project_path = os.getcwd()

        try:
            os.environ["TCAD_PROJECT_PATH"] = project_path
            info = tcad_tools_module.get_project_info()
            data = json.loads(info)
            summary = (f"**项目名称**: {data.get('project_name', '未知')}\n\n"
                       f"**仿真工具**: {', '.join(data.get('tools', []))}\n\n"
                       f"**实验数量**: {data.get('experiment_count', 0)}\n\n"
                       f"**参数(自变量)**: {', '.join(data.get('param_names', []))}\n\n"
                       f"**变量(因变量)**: {', '.join(data.get('var_names', []))}")
            self._add_bubble(summary, is_user=False)
            self.status.setText(f"已加载: {data.get('project_name', '')}")
        except Exception as e:
            self._add_bubble(f"加载项目信息失败：\n{e}", is_user=False)

    def _init_client(self):
        try:
            cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.ini")
            config = configparser.ConfigParser()
            if os.path.exists(cfg_path):
                config.read(cfg_path)

            client_cfg = {
                'api_key': config.get('deepseek', 'api_key', fallback=''),
                'base_url': config.get('deepseek', 'base_url', fallback='https://api.deepseek.com'),
                'model': config.get('deepseek', 'model', fallback='deepseek-chat'),
                'project_path': self.project_path,
            }

            self.client = UpsonicClient(client_cfg)
            self.client.token_received.connect(self.on_token)
            self.client.response_complete.connect(self.on_complete)
            self.client.error_occurred.connect(self.on_error)

            tools = [
                tcad_tools_module.get_project_info,
                tcad_tools_module.get_experiment_list,
                tcad_tools_module.get_cmd_files,
                tcad_tools_module.get_param_names,
                tcad_tools_module.get_var_names,
                tcad_tools_module.get_param_value,
                tcad_tools_module.set_param_value,
                tcad_tools_module.get_experiment_status,
                tcad_tools_module.run_experiment,
                tcad_tools_module.run_all_experiments,
                tcad_tools_module.add_experiment,
                tcad_tools_module.delete_experiment,
                tcad_tools_module.check_errors,
                tcad_tools_module.get_node_list,
                tcad_tools_module.read_file,
                tcad_tools_module.write_file,
                tcad_tools_module.list_files,
            ]

            print(f"[DEBUG] Found {len(tools)} tools")
            self.client.add_tools(tools)
            self.status.setText("就绪")
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)

        except Exception as e:
            import traceback
            error_msg = f"聊天组件初始化失败：\n{e}\n\n{traceback.format_exc()}"
            self.status.setText(f"错误: {e}")
            QMessageBox.warning(self, "警告", error_msg)

    def send(self):
        msg = self.input.text().strip()
        if not msg:
            return

        self.input.clear()
        self.input.setEnabled(False)
        self.send_btn.setEnabled(False)

        self.project_path = self.project_path or os.getcwd()
        if self.client:
            self.client.project_path = self.project_path

        self._add_bubble(msg, is_user=True)
        self.current_text = ""
        self.current_bubble = None

        self.client.send_message(msg)

    def _add_bubble(self, text: str, is_user: bool = False) -> ChatMessageBubble:
        # 移除底部的 stretch，让新气泡直接添加在底部
        if self.msg_layout.count() > 0:
            last = self.msg_layout.itemAt(self.msg_layout.count() - 1)
            if last and last.spacerItem():
                self.msg_layout.removeItem(last)

        bubble = ChatMessageBubble(text, is_user)
        self.msg_layout.addWidget(bubble)

        # 重新添加 stretch 在底部
        self.msg_layout.addStretch(1)

        # 滚动到底部
        QTimer.singleShot(50, self._scroll_to_bottom)
        return bubble

    def _on_scroll_range_changed(self, min_val, max_val):
        """内容高度变化时自动吸底"""
        if self._scroll_to_bottom_enabled:
            self.scroll.verticalScrollBar().setValue(max_val)

    def _scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def on_token(self, token: str):
        self.current_text += token
        if self.current_bubble is None:
            self.current_bubble = self._add_bubble("", is_user=False)
        self.current_bubble.append_text(token)

    def on_complete(self, response: str):
        if self.current_bubble:
            self.current_bubble.finalize()
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.status.setText("就绪")
        self.current_bubble = None
        self._scroll_to_bottom()

    def on_error(self, error: str):
        self._add_bubble(f"错误：{error}", is_user=False)
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.status.setText("错误")
        self.current_bubble = None

    def clear_chat(self):
        if self.client:
            self.client.clear_history()
        while self.msg_layout.count() > 0:
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.status.setText("已清空")
