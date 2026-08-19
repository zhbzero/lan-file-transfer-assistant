# Linux / Ubuntu 无界面部署版

与仓库根目录的 Windows 桌面版（Tkinter）分开，本目录是 **Flask + gunicorn + systemd** 服务，适合 Ubuntu 服务器。

网页功能与桌面版相同：浏览器上传/下载/删除文件、共享文字；文件和文字约 30 分钟后自动删除。

## 能不能在开发机上打成 Linux 可执行文件？

**不能可靠地交叉打包。** PyInstaller 必须在目标系统上执行。正确做法是把本目录同步到 Ubuntu，用 Python 虚拟环境运行（下面安装脚本会自动完成）。

## 服务器要求

- Ubuntu 22.04 / 24.04 / 26.04（x86_64）
- Python 3.10+
- root（安装 systemd 服务）
- 在云厂商 **安全组** / 防火墙放行监听端口（默认 `5000`）

## 安装

把本目录拷到服务器（例如 `/opt/lan-file-transfer`），然后：

```bash
sudo bash /opt/lan-file-transfer/install.sh
```

若本机已配置好 SSH，也可以从开发机同步并安装（把 `user@host` 换成你的服务器）：

```bash
bash deploy-remote.sh user@host
```

默认：

| 项 | 路径 / 值 |
|---|---|
| 程序 | `/opt/lan-file-transfer` |
| 共享目录 | `/var/lib/lan-file-transfer/share` |
| 端口 | `5000` |
| systemd | `lan-file-transfer.service` |
| 账号 | `admin` |
| 密码 | 安装时随机生成，写入服务器上的 `env` 文件（该文件不进 git） |

安装结束后，脚本会在终端打印本机探活地址、用户名和密码。请自行保存，不要写进公开文档。

## 常用命令

```bash
systemctl status lan-file-transfer
journalctl -u lan-file-transfer -f
# 改端口/密码后：
sudo nano /opt/lan-file-transfer/env
sudo systemctl restart lan-file-transfer
```

卸载（默认保留已上传文件）：

```bash
sudo bash /opt/lan-file-transfer/uninstall.sh
```

## 安全说明

公网部署时请务必设置访问密码（安装脚本默认启用 HTTP Basic Auth，并生成随机口令）。服务器上的 `env` 文件权限为 `640`，且已在 `.gitignore` 中忽略，不要把真实地址、账号或密码写进 README。
