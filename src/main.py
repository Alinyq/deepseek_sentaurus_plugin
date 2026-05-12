#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DeepSeek TCAD 插件 - 主程序入口 (PyQt6 版本)
Sentaurus Workbench 自定义工具

安装位置: <插件目录>/src/main.py
"""

import sys
import os
import threading
import configparser
import markdown
from datetime import datetime

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTextEdit, QTextBrowser,
    QTabWidget, QFileDialog, QSplitter, QStatusBar, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont

PLUGIN_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PLUGIN_DIR)

from core.deepseek_client import DeepSeekClient
from tcad.file_reader import TCADFileReader
from tcad.project_parser import TCADProjectParser

SYSTEM_CHINESE = "You are a TCAD expert. Always respond in Chinese (简体中文). 请用中文回复所有问题。"


class MarkdownThread(QThread):
    chunk_received = pyqtSignal(str)
    finished_signal = pyqtSignal(str)
    error_signal = pyqtSignal(str)

    def __init__(self, client, messages):
        super().__init__()
        self.client = client
        self.messages = messages
        self.full_text = ""
        self._stop_flag = False

    def stop(self):
        self._stop_flag = True

    def run(self):
        try:
            for chunk in self.client.stream_chat(self.messages):
                if self._stop_flag:
                    self.finished_signal.emit(self.full_text + "\n\n[用户已停止]")
                    return
                self.full_text += chunk
                self.chunk_received.emit(chunk)
            self.finished_signal.emit(self.full_text)
        except Exception as e:
            self.error_signal.emit(str(e))


class MarkdownRenderer:
    """Markdown 渲染器：使用 markdown 库转为 HTML 并设置 QTextBrowser"""

    def __init__(self, browser, base_font_size=11):
        self.browser = browser
        self.base_font_size = base_font_size

    def render(self, text):
        html = markdown.markdown(
            text,
            extensions=['tables', 'fenced_code', 'nl2br'],
            extension_configs={
                'fenced_code': {
                    'lang_prefix': 'language-',
                }
            }
        )
        css = f"""
        <style>
        body {{ font-family: 'WenQuanYi Micro Hei', 'Noto Sans CJK SC', sans-serif; font-size: {self.base_font_size}px; }}
        h1 {{ font-size: {self.base_font_size + 10}px; font-weight: bold; margin-top: 16px; margin-bottom: 8px; color: #1a1a2e; }}
        h2 {{ font-size: {self.base_font_size + 8}px; font-weight: bold; margin-top: 14px; margin-bottom: 6px; color: #16213e; }}
        h3 {{ font-size: {self.base_font_size + 6}px; font-weight: bold; margin-top: 12px; margin-bottom: 4px; color: #0f3460; }}
        h4 {{ font-size: {self.base_font_size + 4}px; font-weight: bold; margin-top: 10px; margin-bottom: 4px; }}
        h5 {{ font-size: {self.base_font_size + 2}px; font-weight: bold; }}
        h6 {{ font-size: {self.base_font_size + 1}px; font-weight: bold; }}
        p {{ margin: 4px 0; line-height: 1.6; }}
        code {{ font-family: 'Courier New', monospace; font-size: {self.base_font_size - 1}px; background-color: #f0f0f0; padding: 1px 4px; border-radius: 3px; }}
        pre {{ background-color: #f6f8fa; padding: 12px; border-radius: 6px; overflow-x: auto; margin: 8px 0; }}
        pre code {{ background-color: transparent; padding: 0; }}
        ul, ol {{ margin: 4px 0; padding-left: 24px; }}
        li {{ margin: 2px 0; line-height: 1.6; }}
        blockquote {{ border-left: 4px solid #ddd; margin: 8px 0; padding: 8px 16px; color: #6a737d; background-color: #f9f9f9; }}
        table {{ border-collapse: collapse; margin: 8px 0; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 6px 12px; text-align: left; }}
        th {{ background-color: #f2f2f2; font-weight: bold; }}
        hr {{ border: none; border-top: 1px solid #ddd; margin: 12px 0; }}
        a {{ color: #0366d6; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        </style>
        """
        full_html = f"<html><head>{css}</head><body>{html}</body></html>"
        self.browser.setHtml(full_html)


class DeepSeekTCADGUI(QMainWindow):
    """DeepSeek TCAD AI 助手 GUI 主类 (PyQt6)"""

    def __init__(self, project_path=None):
        super().__init__()
        self.project_path = project_path or os.getcwd()
        self.config = self.load_config()
        self.client = DeepSeekClient(
            api_key=self.config.get('deepseek', 'api_key', fallback=''),
            model=self.config.get('deepseek', 'model', fallback='deepseek-chat'),
            base_url=self.config.get('deepseek', 'base_url', fallback='https://api.deepseek.com')
        )
        self.file_reader = TCADFileReader()
        self.project_parser = TCADProjectParser(self.project_path)
        self.active_threads = []

        self.setWindowTitle("DeepSeek TCAD AI 助手")
        self.resize(1200, 800)
        self.setMinimumSize(800, 600)

        self.setup_ui()

    def load_config(self):
        config = configparser.ConfigParser()
        config_file = os.path.join(PLUGIN_DIR, 'config', 'settings.ini')
        if os.path.exists(config_file):
            config.read(config_file)
        return config

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(10, 10, 10, 10)

        # 项目路径栏
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("项目路径："))
        self.path_entry = QLineEdit(self.project_path)
        path_layout.addWidget(self.path_entry)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_project)
        path_layout.addWidget(browse_btn)
        main_layout.addLayout(path_layout)

        # 标签页
        self.tabs = QTabWidget()
        main_layout.addWidget(self.tabs)

        self.create_code_review_tab()
        self.create_result_analysis_tab()
        self.create_param_optimization_tab()
        self.create_report_generation_tab()

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    # ============================================================
    # 四个功能标签页
    # ============================================================

    def _create_output_browser(self):
        browser = QTextBrowser()
        browser.setOpenExternalLinks(True)
        browser.setReadOnly(True)
        browser.setStyleSheet("""
            QTextBrowser {
                font-family: 'WenQuanYi Micro Hei', 'Noto Sans CJK SC', sans-serif;
                font-size: 11px;
                padding: 8px;
                background-color: #f8f9fa;
                border: 2px solid #e9ecef;
                border-radius: 6px;
            }
        """)
        return browser

    def _create_input_widget(self):
        group = QWidget()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(0, 4, 0, 0)
        layout.setSpacing(2)

        top_row = QHBoxLayout()
        title_label = QLabel("补充说明：")
        title_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        top_row.addWidget(title_label)
        hint = QLabel("输入额外需求或提示，会一并发送给AI模型")
        hint.setStyleSheet("color: gray; font-size: 9px;")
        top_row.addWidget(hint)
        top_row.addStretch()
        layout.addLayout(top_row)

        extra = QTextEdit()
        extra.setFixedHeight(50)
        extra.setStyleSheet("""
            QTextEdit {
                font-family: 'WenQuanYi Micro Hei', 'Noto Sans CJK SC', sans-serif;
                font-size: 11px;
                padding: 4px;
                border: 1px solid #ced4da;
                border-radius: 3px;
            }
        """)
        layout.addWidget(extra)
        return group, extra

    def _create_separator(self):
        from PyQt6.QtWidgets import QFrame
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        return line

    def _run_query(self, messages, browser, action_btn, running_text="停止", idle_text="运行中..."):
        self.status_bar.showMessage("正在处理...")
        browser.setHtml("<body style='font-family: sans-serif; font-size: 14px;'>**[AI 分析结果]**\n\n</body>")

        renderer = MarkdownRenderer(browser)
        self._current_stream = ""

        self._is_streaming = True
        action_btn.setText(running_text)
        action_btn.setEnabled(True)

        def on_chunk(chunk):
            self._current_stream += chunk
            renderer.render("**[AI 分析结果]**\n\n" + self._current_stream)
            browser.verticalScrollBar().setValue(browser.verticalScrollBar().maximum())

        def on_finished(full_text):
            self._is_streaming = False
            renderer.render("**[AI 分析结果]**\n\n" + full_text)
            action_btn.setText(idle_text)
            self.status_bar.showMessage("完成")

        def on_error(err):
            self._is_streaming = False
            browser.insertPlainText(f"\n\n错误：{err}")
            action_btn.setText(idle_text)
            self.status_bar.showMessage("错误")

        thread = MarkdownThread(self.client, messages)
        thread.chunk_received.connect(on_chunk)
        thread.finished_signal.connect(on_finished)
        thread.error_signal.connect(on_error)
        thread.finished.connect(lambda: self.active_threads.remove(thread) if thread in self.active_threads else None)
        self.active_threads.append(thread)
        self._active_action_btn = action_btn
        self._idle_btn_text = idle_text
        thread.start()

    def _stop_query(self):
        for thread in self.active_threads:
            if isinstance(thread, MarkdownThread):
                thread.stop()

    # --- 1. Code Review ---
    def create_code_review_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        top_input = QVBoxLayout()

        file_layout = QHBoxLayout()
        file_layout.addWidget(QLabel("文件："))
        self.code_file_entry = QLineEdit()
        file_layout.addWidget(self.code_file_entry)
        browse_btn = QPushButton("浏览")
        browse_btn.clicked.connect(self.browse_code_file)
        file_layout.addWidget(browse_btn)
        top_input.addLayout(file_layout)

        top_input.addWidget(self._create_separator())
        self.code_extra_widget, self.code_extra = self._create_input_widget()
        top_input.addWidget(self.code_extra_widget)

        out_label = QLabel("分析结果：")
        out_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.code_review_browser = self._create_output_browser()

        bottom_input = QVBoxLayout()
        bottom_input.addWidget(out_label)
        bottom_input.addWidget(self.code_review_browser)

        top_widget = QWidget()
        top_widget.setLayout(top_input)
        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom_input)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([200, 600])
        main_layout.addWidget(splitter)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.review_btn = QPushButton("代码审查")
        self.review_btn.setMinimumWidth(130)
        self.review_btn.clicked.connect(self._on_review_btn)
        btn_layout.addWidget(self.review_btn)
        main_layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "代码审查")
        self._is_streaming = False

    def _on_review_btn(self):
        if self._is_streaming:
            self._stop_query()
        else:
            self.review_code()

    def review_code(self):
        code_file = self.code_file_entry.text()
        if not code_file or not os.path.exists(code_file):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", "请选择有效的代码文件")
            return
        try:
            with open(code_file, 'r', encoding='utf-8', errors='ignore') as f:
                code_content = f.read()
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", f"无法读取文件：{e}")
            return

        extra = self.code_extra.toPlainText().strip()
        extra_prompt = f"\n\nUser Additional Requirements:\n{extra}" if extra else ""

        messages = [
            {"role": "system", "content": SYSTEM_CHINESE},
            {"role": "user", "content": (
                f"Please review this Sentaurus TCAD code file ({os.path.basename(code_file)}):\n\n"
                f"```tcl\n{code_content}\n```\n\n"
                f"Check for:\n1. Syntax errors\n2. Physical model selection\n"
                f"3. Mesh settings\n4. Solver parameters\n5. Boundary conditions\n"
                f"6. Convergence issues{extra_prompt}"
            )}
        ]
        self._run_query(messages, self.code_review_browser, self.review_btn, running_text="停止", idle_text="代码审查")

    def browse_code_file(self):
        f, _ = QFileDialog.getOpenFileName(
            self, "选择 TCAD 命令文件", "", "TCAD Cmd 文件 (*.cmd);;所有文件 (*)"
        )
        if f:
            self.code_file_entry.setText(f)

    # --- 2. Result Analysis ---
    def create_result_analysis_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        top_input = QVBoxLayout()

        detect_btn = QPushButton("自动检测结果文件")
        detect_btn.clicked.connect(self.auto_detect_results)
        top_input.addWidget(detect_btn)

        top_input.addWidget(self._create_separator())
        self.result_extra_widget, self.result_extra = self._create_input_widget()
        top_input.addWidget(self.result_extra_widget)

        out_label = QLabel("分析结果：")
        out_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.result_browser = self._create_output_browser()

        bottom_input = QVBoxLayout()
        bottom_input.addWidget(out_label)
        bottom_input.addWidget(self.result_browser)

        top_widget = QWidget()
        top_widget.setLayout(top_input)
        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom_input)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([200, 600])

        main_layout.addWidget(splitter)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.analyze_btn = QPushButton("分析结果")
        self.analyze_btn.setMinimumWidth(130)
        self.analyze_btn.clicked.connect(self._on_analyze_btn)
        btn_layout.addWidget(self.analyze_btn)
        main_layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "结果分析")

    def _on_analyze_btn(self):
        if self._is_streaming:
            self._stop_query()
        else:
            self.analyze_results()

    def auto_detect_results(self):
        info = self.project_parser.parse_results()
        self.result_browser.setHtml(f"<h3>检测结果</h3><pre>{info}</pre>")
        self.status_bar.showMessage("检测完成")

    def analyze_results(self):
        results = self.result_browser.toPlainText()
        if not results:
            self.auto_detect_results()
            results = self.result_browser.toPlainText()

        extra = self.result_extra.toPlainText().strip()
        extra_prompt = f"\n\nUser Additional Requirements:\n{extra}" if extra else ""

        messages = [
            {"role": "system", "content": SYSTEM_CHINESE},
            {"role": "user", "content": (
                f"Please analyze these TCAD simulation results:\n\n{results}\n\n"
                f"Include:\n1. Key performance metrics\n2. Convergence analysis\n"
                f"3. Suggestions for improvement{extra_prompt}"
            )}
        ]
        self._run_query(messages, self.result_browser, self.analyze_btn, running_text="停止", idle_text="分析结果")

    # --- 3. 参数优化 ---
    def create_param_optimization_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        top_input = QVBoxLayout()

        input_layout = QHBoxLayout()
        left_input = QVBoxLayout()
        left_input.addWidget(QLabel("目标性能："))
        self.target_edit = QTextEdit()
        self.target_edit.setFixedHeight(50)
        left_input.addWidget(self.target_edit)
        input_layout.addLayout(left_input)

        right_input = QVBoxLayout()
        right_input.addWidget(QLabel("可调参数："))
        self.param_edit = QTextEdit()
        self.param_edit.setFixedHeight(50)
        right_input.addWidget(self.param_edit)
        input_layout.addLayout(right_input)
        top_input.addLayout(input_layout)

        out_label = QLabel("优化建议：")
        out_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.opt_browser = self._create_output_browser()

        bottom_input = QVBoxLayout()
        bottom_input.addWidget(out_label)
        bottom_input.addWidget(self.opt_browser)

        top_widget = QWidget()
        top_widget.setLayout(top_input)
        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom_input)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([200, 600])

        main_layout.addWidget(splitter)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.optimize_btn = QPushButton("开始优化")
        self.optimize_btn.setMinimumWidth(130)
        self.optimize_btn.clicked.connect(self._on_optimize_btn)
        btn_layout.addWidget(self.optimize_btn)
        main_layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "参数优化")

    def _on_optimize_btn(self):
        if self._is_streaming:
            self._stop_query()
        else:
            self.optimize()

    def optimize(self):
        target = self.target_edit.toPlainText().strip()
        params = self.param_edit.toPlainText().strip()

        project_info = self.project_parser.parse_all()

        messages = [
            {"role": "system", "content": SYSTEM_CHINESE},
            {"role": "user", "content": (
                f"Please suggest parameter optimization for TCAD simulation:\n\n"
                f"Project Info:\n{json.dumps(project_info, indent=2, ensure_ascii=False)}\n\n"
                f"Target Performance:\n{target}\n\n"
                f"Adjustable Parameters:\n{params}\n\n"
                f"Provide:\n1. Recommended parameter ranges\n2. Optimization strategy\n"
                f"3. Expected performance improvement"
            )}
        ]
        self._run_query(messages, self.opt_browser, self.optimize_btn, running_text="停止", idle_text="开始优化")

    # --- 4. 报告生成 ---
    def create_report_generation_tab(self):
        tab = QWidget()
        main_layout = QVBoxLayout(tab)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(6)

        top_input = QVBoxLayout()

        title_layout = QHBoxLayout()
        title_layout.addWidget(QLabel("报告标题："))
        self.title_entry = QLineEdit("TCAD 仿真报告")
        title_layout.addWidget(self.title_entry)
        top_input.addLayout(title_layout)

        top_input.addWidget(self._create_separator())
        self.report_extra_widget, self.report_extra = self._create_input_widget()
        top_input.addWidget(self.report_extra_widget)

        out_label = QLabel("报告预览：")
        out_label.setStyleSheet("font-weight: bold; font-size: 11px;")
        self.report_browser = self._create_output_browser()

        bottom_input = QVBoxLayout()
        bottom_input.addWidget(out_label)
        bottom_input.addWidget(self.report_browser)

        top_widget = QWidget()
        top_widget.setLayout(top_input)
        bottom_widget = QWidget()
        bottom_widget.setLayout(bottom_input)

        splitter = QSplitter()
        splitter.setOrientation(Qt.Orientation.Vertical)
        splitter.addWidget(top_widget)
        splitter.addWidget(bottom_widget)
        splitter.setSizes([200, 600])

        main_layout.addWidget(splitter)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        self.generate_btn = QPushButton("生成报告")
        self.generate_btn.setMinimumWidth(140)
        self.generate_btn.clicked.connect(self._on_generate_btn)
        btn_layout.addWidget(self.generate_btn)
        self.save_btn = QPushButton("保存报告")
        self.save_btn.setMinimumWidth(110)
        self.save_btn.clicked.connect(self.save_report)
        btn_layout.addWidget(self.save_btn)
        main_layout.addLayout(btn_layout)

        self.tabs.addTab(tab, "报告生成")

    def _on_generate_btn(self):
        if self._is_streaming:
            self._stop_query()
        else:
            self.generate_report()

    def generate_report(self):
        title = self.title_entry.text()
        summary = self.project_parser.parse_all()
        current_date = datetime.now().strftime("%Y年%m月%d日")
        extra = self.report_extra.toPlainText().strip()
        extra_prompt = f"\n\nUser Additional Requirements:\n{extra}" if extra else ""

        messages = [
            {"role": "system", "content": SYSTEM_CHINESE},
            {"role": "user", "content": (
                f"Generate a comprehensive TCAD simulation report titled '{title}'\n\n"
                f"Report Date: {current_date}\n\n"
                f"Project Summary:\n{summary}\n\n"
                f"Include:\n1. Project Overview\n2. Device Structure\n"
                f"3. Simulation Settings\n4. Results Analysis\n"
                f"5. Conclusions and Recommendations{extra_prompt}"
            )}
        ]
        self._run_query(messages, self.report_browser, self.generate_btn, running_text="停止", idle_text="生成报告")

    def save_report(self):
        content = self.report_browser.toPlainText()
        if not content.strip():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(self, "错误", "没有报告内容可保存")
            return

        f, _ = QFileDialog.getSaveFileName(
            self, "保存报告",
            f"tcad_report_{datetime.now().strftime('%Y%m%d')}.md",
            "Markdown (*.md);;文本文件 (*.txt)"
        )
        if f:
            with open(f, 'w', encoding='utf-8') as fout:
                fout.write(f"# {self.title_entry.text()}\n\n{content}")
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(self, "成功", f"报告已保存到：\n{f}")

    # --- 对话框 ---
    def browse_project(self):
        d = QFileDialog.getExistingDirectory(self, "选择项目目录")
        if d:
            self.path_entry.setText(d)
            self.project_path = d
            self.project_parser = TCADProjectParser(d)


def main():
    import argparse
    parser = argparse.ArgumentParser(description='DeepSeek TCAD AI Assistant')
    parser.add_argument('--project', type=str, default=None, help='Project directory path')
    args = parser.parse_args()

    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    # 设置全局中文字体
    font = QFont("WenQuanYi Micro Hei", 11)
    if not font.exactMatch():
        font = QFont("Noto Sans CJK SC", 11)
    if not font.exactMatch():
        font = QFont("sans-serif", 11)
    app.setFont(font)

    window = DeepSeekTCADGUI(project_path=args.project)
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
