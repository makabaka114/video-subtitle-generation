from __future__ import annotations

import os
import queue
import subprocess
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from app.models import SubtitleJobConfig, SubtitleJobResult
from app.paths import APP_DATA_DIR
from app.services.events import ProgressEvent
from app.services.subtitle_pipeline import SubtitlePipeline


class MainWindow:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("本地离线字幕工具")
        self.root.geometry("760x420")
        self.root.minsize(680, 360)

        self.pipeline = SubtitlePipeline()
        self.event_queue: queue.Queue[tuple[str, object]] = queue.Queue()
        self.current_output_path: Path | None = None
        self.is_running = False

        self.video_path_var = tk.StringVar()
        self.status_var = tk.StringVar(value="请选择一个视频文件。")
        self.result_var = tk.StringVar(value="输出文件：未生成")
        self.warning_var = tk.StringVar(value="")
        self.progress_var = tk.IntVar(value=0)

        self._build_ui()
        self.root.after(150, self._poll_events)

    def _build_ui(self) -> None:
        container = ttk.Frame(self.root, padding=24)
        container.pack(fill=tk.BOTH, expand=True)
        container.columnconfigure(0, weight=1)

        title_label = ttk.Label(
            container,
            text="本地离线视频字幕工具",
            font=("Microsoft YaHei UI", 20, "bold"),
        )
        title_label.grid(row=0, column=0, sticky="w")

        desc_label = ttk.Label(
            container,
            text=f"选择一个视频文件，自动识别语音并生成字幕。模型与翻译包会保存在：{APP_DATA_DIR}",
            font=("Microsoft YaHei UI", 10),
            wraplength=680,
        )
        desc_label.grid(row=1, column=0, sticky="w", pady=(8, 20))

        picker_frame = ttk.LabelFrame(container, text="视频文件", padding=16)
        picker_frame.grid(row=2, column=0, sticky="nsew")
        picker_frame.columnconfigure(0, weight=1)

        entry = ttk.Entry(
            picker_frame,
            textvariable=self.video_path_var,
            font=("Microsoft YaHei UI", 10),
        )
        entry.grid(row=0, column=0, sticky="ew", padx=(0, 12))

        browse_button = ttk.Button(picker_frame, text="选择视频", command=self._choose_video)
        browse_button.grid(row=0, column=1)

        action_frame = ttk.Frame(container, padding=(0, 18, 0, 18))
        action_frame.grid(row=3, column=0, sticky="ew")

        self.start_button = ttk.Button(action_frame, text="开始生成字幕", command=self._start_job)
        self.start_button.pack(side=tk.LEFT)

        self.open_button = ttk.Button(
            action_frame,
            text="打开输出目录",
            command=self._open_output_directory,
            state=tk.DISABLED,
        )
        self.open_button.pack(side=tk.LEFT, padx=(12, 0))

        progress_frame = ttk.LabelFrame(container, text="处理进度", padding=16)
        progress_frame.grid(row=4, column=0, sticky="ew")
        progress_frame.columnconfigure(0, weight=1)

        self.progress_bar = ttk.Progressbar(
            progress_frame,
            orient=tk.HORIZONTAL,
            mode="determinate",
            maximum=100,
            variable=self.progress_var,
        )
        self.progress_bar.grid(row=0, column=0, sticky="ew")

        status_label = ttk.Label(progress_frame, textvariable=self.status_var, font=("Microsoft YaHei UI", 10))
        status_label.grid(row=1, column=0, sticky="w", pady=(12, 0))

        result_frame = ttk.LabelFrame(container, text="结果", padding=16)
        result_frame.grid(row=5, column=0, sticky="nsew", pady=(18, 0))
        result_frame.columnconfigure(0, weight=1)
        container.rowconfigure(5, weight=1)

        result_label = ttk.Label(
            result_frame,
            textvariable=self.result_var,
            wraplength=660,
            font=("Microsoft YaHei UI", 10),
        )
        result_label.grid(row=0, column=0, sticky="w")

        warning_label = ttk.Label(
            result_frame,
            textvariable=self.warning_var,
            wraplength=660,
            foreground="#a35a00",
            font=("Microsoft YaHei UI", 10),
        )
        warning_label.grid(row=1, column=0, sticky="w", pady=(12, 0))

    def _choose_video(self) -> None:
        file_path = filedialog.askopenfilename(
            title="选择视频文件",
            filetypes=[
                ("视频文件", "*.mp4 *.mkv *.avi *.mov *.m4v *.wmv *.flv"),
                ("所有文件", "*.*"),
            ],
        )
        if not file_path:
            return
        self.video_path_var.set(file_path)
        self.current_output_path = self.pipeline.default_output_path(Path(file_path))
        self.result_var.set(f"输出文件：{self.current_output_path}")
        self.warning_var.set("")

    def _start_job(self) -> None:
        if self.is_running:
            return
        video_value = self.video_path_var.get().strip()
        if not video_value:
            messagebox.showerror("未选择视频", "请先选择一个视频文件。")
            return

        input_path = Path(video_value)
        output_path = self.pipeline.default_output_path(input_path)
        self.current_output_path = output_path
        config = SubtitleJobConfig(input_path=input_path, output_path=output_path)

        self.is_running = True
        self.start_button.config(state=tk.DISABLED)
        self.open_button.config(state=tk.DISABLED)
        self.progress_var.set(0)
        self.status_var.set("任务已启动，正在准备...")
        self.warning_var.set("")
        self.result_var.set(f"输出文件：{output_path}")

        worker = threading.Thread(target=self._run_job, args=(config,), daemon=True)
        worker.start()

    def _run_job(self, config: SubtitleJobConfig) -> None:
        result = self.pipeline.run(config, self._push_progress)
        self.event_queue.put(("result", result))

    def _push_progress(self, event: ProgressEvent) -> None:
        self.event_queue.put(("progress", event))

    def _poll_events(self) -> None:
        while True:
            try:
                event_type, payload = self.event_queue.get_nowait()
            except queue.Empty:
                break

            if event_type == "progress":
                self._handle_progress(payload)
            elif event_type == "result":
                self._handle_result(payload)

        self.root.after(150, self._poll_events)

    def _handle_progress(self, event: ProgressEvent) -> None:
        self.progress_var.set(event.progress)
        self.status_var.set(event.message)

    def _handle_result(self, result: SubtitleJobResult) -> None:
        self.is_running = False
        self.start_button.config(state=tk.NORMAL)
        if result.status == "success":
            self.result_var.set(
                f"输出文件：{result.subtitle_path}\n检测语言：{result.detected_language or 'unknown'}\n耗时：{result.elapsed_seconds:.1f} 秒"
            )
            if result.subtitle_path is not None:
                self.open_button.config(state=tk.NORMAL)
            if result.warnings:
                self.warning_var.set("提示：" + "；".join(result.warnings))
            else:
                self.warning_var.set("")
        else:
            self.result_var.set("输出文件：未生成")
            self.warning_var.set(result.error_message or "处理失败。")
            messagebox.showerror("字幕生成失败", result.error_message or "处理失败。")

    def _open_output_directory(self) -> None:
        if self.current_output_path is None:
            return
        target_dir = self.current_output_path.parent
        if not target_dir.exists():
            return
        subprocess.Popen(["explorer", os.fspath(target_dir)])
