"""
TCAD Chat Widget - Multi-turn conversation with Upsonic streaming + project path
"""
import os
import json
import configparser
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLineEdit,
    QPushButton, QLabel, QFrame, QScrollArea, QMessageBox, QFileDialog
)
from PyQt6.QtCore import Qt, QThread
from PyQt6.QtGui import QFont

from core.chat.upsonic_client import UpsonicClient
from core.chat.tcad_tools import create_tcad_tools
from upsonic.tools import tool


class ChatMessageBubble(QFrame):
    """Message bubble widget"""

    def __init__(self, is_user: bool = False, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 5, 10, 5)
        bg = "#e3f2fd" if self.is_user else "#f5f5f5"
        self.setStyleSheet(f"QFrame {{ background-color: {bg}; border-radius: 8px; }}")
        self.label = QLabel()
        self.label.setWordWrap(True)
        self.label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(self.label)

    def set_text(self, text: str):
        self.label.setText(text)

    def append_text(self, text: str):
        self.label.setText(self.label.text() + text)


class ChatWorker(QThread):
    """Worker for sending messages"""

    def __init__(self, client: UpsonicClient, message: str):
        super().__init__()
        self.client = client
        self.message = message

    def run(self):
        self.client.send_message(self.message)


class ChatWidget(QWidget):
    """Main chat widget with project path input and streaming"""

    def __init__(self, project_path: str = None, parent=None):
        super().__init__(parent)
        self.project_path = project_path or os.getcwd()
        self.client = None
        self.worker = None
        self.current_bubble = None
        self.current_text = ""
        self._setup_ui()
        self._init_client()

    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setStyleSheet("background-color: #1976d2; padding: 8px;")
        header_layout = QHBoxLayout(header)
        title = QLabel(" TCAD AI Chat (Multi-turn + Project Control)")
        title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        header_layout.addWidget(title)
        header_layout.addStretch()

        clear_btn = QPushButton("Clear")
        clear_btn.setStyleSheet("""
            QPushButton { background-color: #1565c0; color: white; border: none;
                         padding: 5px 15px; border-radius: 4px; }
            QPushButton:hover { background-color: #0d47a1; }
        """)
        clear_btn.clicked.connect(self.clear_chat)
        header_layout.addWidget(clear_btn)
        layout.addWidget(header)

        path_frame = QFrame()
        path_frame.setStyleSheet("QFrame { background-color: #e8f5e9; border-bottom: 1px solid #c8e6c9; padding: 6px; }")
        path_layout = QHBoxLayout(path_frame)
        path_layout.addWidget(QLabel("Project:"))
        self.path_input = QLineEdit(self.project_path)
        self.path_input.setStyleSheet("""
            QLineEdit { border: 1px solid #a5d6a7; border-radius: 4px; padding: 4px 8px; }
            QLineEdit:focus { border-color: #4caf50; }
        """)
        path_layout.addWidget(self.path_input)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self._browse_project)
        path_layout.addWidget(browse_btn)

        detect_btn = QPushButton("Detect Project")
        detect_btn.clicked.connect(self._detect_project)
        path_layout.addWidget(detect_btn)

        load_btn = QPushButton("Load Info")
        load_btn.clicked.connect(self._load_project_info)
        path_layout.addWidget(load_btn)
        layout.addWidget(path_frame)

        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("border: none; background-color: #fafafa;")

        self.msg_container = QWidget()
        self.msg_layout = QVBoxLayout(self.msg_container)
        self.msg_layout.setContentsMargins(10, 10, 10, 10)
        self.msg_layout.setSpacing(8)
        self.msg_layout.addStretch()

        self.scroll.setWidget(self.msg_container)
        layout.addWidget(self.scroll)

        input_frame = QFrame()
        input_frame.setStyleSheet("QFrame { background-color: white; border-top: 1px solid #e0e0e0; padding: 10px; }")
        input_layout = QHBoxLayout(input_frame)

        self.input = QLineEdit()
        self.input.setPlaceholderText("Ask me about your TCAD project... (Enter to send)")
        self.input.setMinimumHeight(40)
        self.input.setStyleSheet("""
            QLineEdit { border: 1px solid #bdbdbd; border-radius: 20px;
                       padding: 0 15px; font-size: 13px; }
            QLineEdit:focus { border-color: #1976d2; }
        """)
        self.input.returnPressed.connect(self.send)
        input_layout.addWidget(self.input)

        self.send_btn = QPushButton("Send")
        self.send_btn.setMinimumSize(80, 40)
        self.send_btn.setStyleSheet("""
            QPushButton { background-color: #1976d2; color: white; border: none;
                         border-radius: 20px; font-weight: bold; }
            QPushButton:hover { background-color: #1565c0; }
            QPushButton:disabled { background-color: #90caf9; }
        """)
        self.send_btn.clicked.connect(self.send)
        input_layout.addWidget(self.send_btn)
        layout.addWidget(input_frame)

        status_frame = QFrame()
        status_frame.setStyleSheet("background-color: #f5f5f5; padding: 5px 10px;")
        s_layout = QHBoxLayout(status_frame)
        s_layout.setContentsMargins(5, 2, 5, 2)
        self.status = QLabel("Initializing...")
        self.status.setStyleSheet("color: #666; font-size: 11px;")
        s_layout.addWidget(self.status)
        layout.addWidget(status_frame)

    def _browse_project(self):
        d = QFileDialog.getExistingDirectory(self, "Select SWB Project")
        if d:
            self.path_input.setText(d)
            self.project_path = d
            if self.client:
                self.client.project_path = d
                self.status.setText(f" Project: {d}")

    def _detect_project(self):
        current = self.path_input.text() or os.getcwd()
        if os.path.isfile(os.path.join(current, "gtree.dat")):
            self.project_path = os.path.abspath(current)
            self.status.setText(f" Detected: {self.project_path}")
            self._add_bubble(f"Detected SWB project:\n{self.project_path}", is_user=False)
        else:
            parent = os.path.dirname(current)
            for root, dirs, files in os.walk(parent):
                if "gtree.dat" in files:
                    self.project_path = os.path.abspath(root)
                    self.path_input.setText(self.project_path)
                    self.status.setText(f" Detected: {self.project_path}")
                    self._add_bubble(f"Detected SWB project:\n{self.project_path}", is_user=False)
                    return
            self.status.setText(" No SWB project found")
            self._add_bubble("No SWB project (gtree.dat) found in current directory or parents.", is_user=False)

    def _load_project_info(self):
        project_path = self.path_input.text()
        if not project_path:
            project_path = os.getcwd()
        self.project_path = project_path
        if self.client:
            self.client.project_path = project_path

        tools_dict = create_tcad_tools(project_path)
        info = tools_dict['get_project_info']()
        try:
            data = json.loads(info)
            summary = (f"Project: {data.get('project_name', 'Unknown')}\n"
                       f"Tools: {', '.join(data.get('tools', []))}\n"
                       f"Experiments: {data.get('experiment_count', 0)}\n"
                       f"Params: {', '.join(data.get('param_names', []))}\n"
                       f"Variables: {', '.join(data.get('var_names', []))}")
            self._add_bubble(summary, is_user=False)
            self.status.setText(f" Loaded: {data.get('project_name', '')}")
        except:
            self._add_bubble(f"Failed to load project info:\n{info}", is_user=False)

    def _init_client(self):
        try:
            cfg_path = os.path.join(os.path.dirname(__file__), "..", "..", "config", "settings.ini")
            config = configparser.ConfigParser()
            if os.path.exists(cfg_path):
                config.read(cfg_path)

            client_cfg = {
                'api_key': config.get('deepseek', 'api_key', fallback=''),
                'base_url': config.get('deepseek', 'base_url', fallback='https://api.deepseek.com') + '/v1',
                'model': config.get('deepseek', 'model', fallback='deepseek-chat'),
                'project_path': self.project_path,
            }

            skill_base = os.path.join(os.path.dirname(__file__), "..", "..", "..", ".trae", "skills", "sentaurus-tcad")
            if os.path.exists(skill_base):
                client_cfg['skill_path'] = skill_base

            self.client = UpsonicClient(client_cfg)
            self.client.token_received.connect(self.on_token)
            self.client.response_complete.connect(self.on_complete)
            self.client.error_occurred.connect(self.on_error)

            tools_dict = create_tcad_tools(self.project_path)
            tools_list = [tool(func) for func in tools_dict.values()]
            self.client.add_tools(tools_list)
            self.status.setText(" Ready")
            self.input.setEnabled(True)
            self.send_btn.setEnabled(True)

        except Exception as e:
            self.status.setText(f" Error: {e}")
            QMessageBox.warning(self, "Warning", f"Chat init error:\n{e}\n\nInstall upsonic: pip install upsonic")

    def send(self):
        msg = self.input.text().strip()
        if not msg:
            return

        self.input.clear()
        self.input.setEnabled(False)
        self.send_btn.setEnabled(False)

        self.project_path = self.path_input.text() or os.getcwd()
        if self.client:
            self.client.project_path = self.project_path
            new_tools = create_tcad_tools(self.project_path)
            self.client.add_tools([tool(func) for func in new_tools.values()])

        self._add_bubble(msg, is_user=True)
        self.current_text = ""
        self.current_bubble = None

        self.worker = ChatWorker(self.client, msg)
        self.worker.start()

    def _add_bubble(self, text: str, is_user: bool = False) -> ChatMessageBubble:
        self.msg_layout.removeItem(self.msg_layout.takeAt(self.msg_layout.count() - 1))
        bubble = ChatMessageBubble(is_user=is_user)
        bubble.set_text(text)
        self.msg_layout.addWidget(bubble)
        self.msg_layout.addStretch()
        self._scroll_to_bottom()
        return bubble

    def _scroll_to_bottom(self):
        self.scroll.verticalScrollBar().setValue(self.scroll.verticalScrollBar().maximum())

    def on_token(self, token: str):
        self.current_text += token
        if self.current_bubble is None:
            self.current_bubble = self._add_bubble("", is_user=False)
        self.current_bubble.append_text(token)
        self._scroll_to_bottom()

    def on_complete(self, response: str):
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.status.setText(" Ready")
        self.current_bubble = None

    def on_error(self, error: str):
        self._add_bubble(f"Error: {error}", is_user=False)
        self.input.setEnabled(True)
        self.send_btn.setEnabled(True)
        self.status.setText(" Error")
        self.current_bubble = None

    def clear_chat(self):
        if self.client:
            self.client.clear_history()
        while self.msg_layout.count() > 1:
            item = self.msg_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.status.setText(" Cleared")
