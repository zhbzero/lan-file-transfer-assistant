# 内网文件传输助手

局域网内通过浏览器上传、下载共享文件夹中的文件，并支持一段「共享文字」在多设备间同步。适合公司内网、无法使用外网传输工具的场景。

**打包成品**：使用下文脚本打包后，可直接运行 **`dist` 目录下的「文件传输助手.exe」**；该 exe 可单独复制使用，无需保留 PyInstaller 生成的 `build` 等临时目录（可随时删除）。

## 功能概览

- **桌面端（Tkinter）**：选择共享目录、端口（默认 `5000`）、展示访问链接与二维码、「在浏览器中打开」。
- **网页端（Flask）**：目录浏览、多文件上传、文件下载、删除（删除文件夹将递归删除其内容）；文字区块保存后其他设备可加载同步。
- **路径安全**：禁止通过 `..` 等方式访问共享根目录之外的文件。
- **可选打包**：支持打包为 Windows 单文件可执行程序（见下文）。

## 环境要求

- Windows（当前开发与打包环境；理论上也可在 macOS/Linux 运行 Python 源码）。
- Python **3.10+**（已在 3.13 下验证）。

## 快速开始

### 1. 克隆或解压代码后进入项目目录

```powershell
cd "路径\内网传输工具"
```

### 2. 创建虚拟环境并安装依赖

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 3. 启动程序

```powershell
python main.py
```

在同一局域网的其它电脑或手机浏览器中访问窗口里显示的地址（例如 `http://192.168.1.100:5000`）。

### 4. 防火墙

首次运行时 Windows 防火墙可能询问是否允许 Python/该程序访问网络，需在 **专用网络** 下允许，否则局域网无法访问。

## 配置说明

- 默认共享目录：`文档\内网传输共享`（若不存在会尝试创建）。
- 配置持久化路径：`%APPDATA%\LANTransferAssistant\config.json`（Windows）。
- 单次上传总体积上限：约 **512MB**（可在 `lan_transfer/server.py` 中调整 `MAX_CONTENT_LENGTH`）。

## 打包为 exe（Windows）

1. 安装打包依赖：

   ```powershell
   pip install -r requirements-build.txt
   ```

2. （可选）将应用图标命名为 **`图标.png`**，放在**项目根目录**或 **`assets/图标.png`**。打包脚本会自动生成 `dist_assets/app.ico`；若未提供 PNG，会使用内置占位图。

3. 执行一键脚本：

   ```powershell
   .\scripts\build_windows.ps1
   ```

   生成的可执行文件：`dist\文件传输助手.exe`（仅此目录下的 exe 为成品，其余打包中间文件无日常用途。）

## 安全提示

- 默认 **无账号密码**，同一局域网内知情者均可访问；仅建议在可信内网使用。
- 若需鉴权或 HTTPS，需在现有 Flask 应用外再扩展。

## 项目结构（简要）

```
main.py                 # 入口
lan_transfer/
  gui.py                # 桌面界面
  server.py             # Flask 服务与路由
  state.py              # 共享状态
  network.py            # 局域网 IPv4 探测
  paths.py              # 路径安全
  templates/            # 网页模板
  static/               # 静态资源
scripts/
  build_windows.ps1     # Windows 打包脚本
  png_to_ico.py         # 图标 PNG → ICO
build_windows.spec      # PyInstaller 配置
requirements.txt        # 运行时依赖
requirements-build.txt  # 打包依赖
```

## 开源协议

MIT License，见仓库根目录 [`LICENSE`](LICENSE)。

## 致谢

使用 [Flask](https://flask.palletsprojects.com/)、[qrcode](https://github.com/lincolnloop/python-qrcode)、[Pillow](https://python-pillow.org/) 等开源库。
