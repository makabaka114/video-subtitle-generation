# Windows 本地离线视频字幕工具

一个面向 Windows 的本地离线桌面小工具。选择视频后，工具会尝试自动识别语音并生成 `.srt` 字幕文件，默认输出到视频同目录。

模型、翻译包和下载缓存默认都放在软件目录下的 `app_data\` 中，不写入用户主目录。

## 当前能力

- 单个视频生成一个 `.srt` 字幕文件
- 中文视频输出单语中文字幕
- 英文、日文、韩文视频输出双语字幕
- 首次启动时自动下载识别模型和离线翻译包
- 识别优先尝试 GPU，失败后自动回退到 CPU
- 模型和翻译包保存在软件目录下的 `app_data\`

## 运行

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python -m pip install --upgrade pip
.\.venv\Scripts\python -m pip install -e .
.\.venv\Scripts\python launcher.py
```

## 打包

```powershell
.\build\build.ps1
```

打包结果输出在 `dist\offline_subtitle_tool\`。

## 输出规则

- 默认文件名：`原视频文件名.zh-bilingual.srt`
- 中文视频：每条字幕一行
- 英文、日文、韩文视频：每条字幕两行，第一行原文，第二行简体中文
- 其他语言：仅输出原文字幕，并在界面显示提示

## 说明

- 首次下载模型或翻译包需要联网。
- 当前实现不包含批量处理、实时字幕和字幕样式编辑。
- 如果机器上没有可用的 GPU 运行环境，工具会自动回退到 CPU 模式。
