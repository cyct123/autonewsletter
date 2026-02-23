# WSL2 + Zsh 开发环境配置指南

## 📋 目录

- [为什么选择 WSL2？](#为什么选择-wsl2)
- [系统要求](#系统要求)
- [第一步：安装 WSL2](#第一步安装-wsl2)
- [第二步：安装 Ubuntu](#第二步安装-ubuntu)
- [第三步：安装 Zsh 和 Oh My Zsh](#第三步安装-zsh-和-oh-my-zsh)
- [第四步：配置 Conda 环境](#第四步配置-conda-环境)
- [第五步：设置 AutoNewsletter 项目](#第五步设置-autonewsletter-项目)
- [第六步：配置 Windows Terminal](#第六步配置-windows-terminal)
- [开发工作流最佳实践](#开发工作流最佳实践)
- [常见问题排查](#常见问题排查)
- [参考资源](#参考资源)

---

## 🎯 为什么选择 WSL2？

### 相比 Git Bash

虽然 Git Bash 可以运行项目脚本，但 WSL2 提供了更完整的开发体验：

| 特性 | Git Bash | WSL2 |
|------|----------|------|
| **Linux 环境** | ❌ 模拟环境 | ✅ 完整 Linux 内核 |
| **Zsh 支持** | ⚠️ 需要复杂配置 | ✅ 原生支持 |
| **性能** | ⚠️ 较慢 | ✅ 接近原生 Linux |
| **工具兼容性** | ⚠️ 部分工具不可用 | ✅ 完整 Linux 工具链 |
| **开发体验** | ⚠️ 基础 | ✅ 与 VS Code 完美集成 |
| **维护** | ⚠️ 社区维护 | ✅ 微软官方支持 |

### 相比虚拟机

- **启动速度**: 秒级启动，无需等待系统引导
- **资源占用**: 动态内存分配，比虚拟机轻量 50%+
- **文件共享**: 通过 `/mnt/` 无缝访问 Windows 文件
- **网络集成**: 自动共享 Windows 网络配置

### 相比双系统

- **无需重启**: Windows 和 Linux 同时运行
- **集成度高**: 可以从 Windows 调用 WSL2 命令，反之亦然
- **磁盘空间**: 无需单独分区，动态占用空间

---

## ✅ 系统要求

### Windows 版本要求

- **Windows 11**: 所有版本 ✅
- **Windows 10**: 版本 2004 或更高（内部版本 19041 或更高）✅

### 检查 Windows 版本

按 `Win + R`，输入 `winver`，查看版本号：

```
版本 2004（OS 内部版本 19041）或更高
```

### 硬件要求

- **处理器**: 支持虚拟化的 64 位处理器
- **内存**: 至少 4GB RAM（推荐 8GB+）
- **磁盘空间**: 至少 10GB 可用空间

### 启用虚拟化

1. 重启电脑，进入 BIOS/UEFI 设置（通常按 F2/F10/Del）
2. 找到虚拟化选项（Intel VT-x 或 AMD-V）
3. 启用虚拟化技术
4. 保存并退出

---

## 📦 第一步：安装 WSL2

### 1.1 启用 WSL 功能

以**管理员身份**打开 PowerShell（右键开始菜单 → Windows PowerShell（管理员））：

```powershell
# 启用 WSL 和虚拟机平台功能
dism.exe /online /enable-feature /featurename:Microsoft-Windows-Subsystem-Linux /all /norestart
dism.exe /online /enable-feature /featurename:VirtualMachinePlatform /all /norestart
```

### 1.2 重启计算机

```powershell
Restart-Computer
```

### 1.3 下载并安装 WSL2 Linux 内核更新包

重启后，下载并安装内核更新包：

🔗 [WSL2 Linux 内核更新包（x64）](https://wslstorestorage.blob.core.windows.net/wslblob/wsl_update_x64.msi)

双击运行安装程序，按提示完成安装。

### 1.4 设置 WSL2 为默认版本

再次以管理员身份打开 PowerShell：

```powershell
wsl --set-default-version 2
```

### 1.5 验证 WSL 安装

```powershell
wsl --status
```

应该看到类似输出：

```
默认版本: 2
```

---

## 🐧 第二步：安装 Ubuntu

### 2.1 安装 Ubuntu 22.04 LTS

在 PowerShell 中运行：

```powershell
wsl --install -d Ubuntu-22.04
```

或者从 Microsoft Store 安装：

1. 打开 Microsoft Store
2. 搜索 "Ubuntu 22.04 LTS"
3. 点击"获取"并安装

### 2.2 首次启动配置

安装完成后，启动 Ubuntu（从开始菜单或运行 `wsl`）。

首次启动会要求创建用户：

```
Enter new UNIX username: your_username
New password: ********
Retype new password: ********
```

⚠️ **注意**: 输入密码时不会显示任何字符，这是正常的。

### 2.3 更新系统包

```bash
sudo apt update && sudo apt upgrade -y
```

### 2.4 安装基础开发工具

```bash
sudo apt install -y \
    build-essential \
    curl \
    wget \
    git \
    vim \
    ca-certificates \
    gnupg \
    lsb-release
```

### 2.5 配置 apt 镜像源（可选，提升国内下载速度）

```bash
# 备份原始源
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup

# 使用清华镜像源
sudo sed -i 's|http://archive.ubuntu.com|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list
sudo sed -i 's|http://security.ubuntu.com|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list

# 更新包列表
sudo apt update
```

---

## 🎨 第三步：安装 Zsh 和 Oh My Zsh

### 3.1 安装 Zsh

```bash
sudo apt install -y zsh
```

### 3.2 验证安装

```bash
zsh --version
```

应该显示类似：`zsh 5.8.1 (x86_64-ubuntu-linux-gnu)`

### 3.3 设置 Zsh 为默认 Shell

```bash
chsh -s $(which zsh)
```

⚠️ **注意**: 需要重新启动 WSL 才能生效。关闭终端窗口，重新打开。

### 3.4 安装 Oh My Zsh

```bash
sh -c "$(curl -fsSL https://raw.githubusercontent.com/ohmyzsh/ohmyzsh/master/tools/install.sh)"
```

如果网络问题导致下载失败，可以使用国内镜像：

```bash
sh -c "$(curl -fsSL https://gitee.com/mirrors/oh-my-zsh/raw/master/tools/install.sh)"
```

安装完成后会自动切换到 Zsh。

### 3.5 安装推荐插件

#### zsh-autosuggestions（自动建议）

```bash
git clone https://github.com/zsh-users/zsh-autosuggestions ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-autosuggestions
```

#### zsh-syntax-highlighting（语法高亮）

```bash
git clone https://github.com/zsh-users/zsh-syntax-highlighting ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/zsh-syntax-highlighting
```

#### conda-zsh-completion（Conda 补全）

```bash
git clone https://github.com/esc/conda-zsh-completion ${ZSH_CUSTOM:-~/.oh-my-zsh/custom}/plugins/conda-zsh-completion
```

### 3.6 配置插件

编辑 `~/.zshrc` 文件：

```bash
vim ~/.zshrc
```

找到 `plugins=` 行，修改为：

```bash
plugins=(
    git
    zsh-autosuggestions
    zsh-syntax-highlighting
    conda-zsh-completion
)
```

保存并退出（按 `Esc`，输入 `:wq`，按 `Enter`）。

### 3.7 应用配置

```bash
source ~/.zshrc
```

### 3.8 安装 Powerlevel10k 主题（可选）

Powerlevel10k 是一个美观且高性能的 Zsh 主题。

```bash
git clone --depth=1 https://github.com/romkatv/powerlevel10k.git ${ZSH_CUSTOM:-$HOME/.oh-my-zsh/custom}/themes/powerlevel10k
```

编辑 `~/.zshrc`，修改主题：

```bash
ZSH_THEME="powerlevel10k/powerlevel10k"
```

重新加载配置：

```bash
source ~/.zshrc
```

首次使用会启动配置向导，按提示选择你喜欢的样式。

---

## 🐍 第四步：配置 Conda 环境

### 4.1 下载 Miniconda

```bash
cd ~
wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh
```

如果下载速度慢，可以使用清华镜像：

```bash
wget https://mirrors.tuna.tsinghua.edu.cn/anaconda/miniconda/Miniconda3-latest-Linux-x86_64.sh
```

### 4.2 安装 Miniconda

```bash
bash Miniconda3-latest-Linux-x86_64.sh
```

安装过程中：
1. 按 `Enter` 查看许可协议
2. 输入 `yes` 接受协议
3. 按 `Enter` 确认安装位置（默认 `~/miniconda3`）
4. 输入 `yes` 初始化 Conda

### 4.3 初始化 Zsh

```bash
~/miniconda3/bin/conda init zsh
```

### 4.4 重新加载配置

```bash
source ~/.zshrc
```

现在你的提示符前应该显示 `(base)`，表示 Conda 已激活。

### 4.5 配置 Conda 镜像源（可选）

```bash
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/free/
conda config --add channels https://mirrors.tuna.tsinghua.edu.cn/anaconda/pkgs/main/
conda config --set show_channel_urls yes
```

### 4.6 验证安装

```bash
conda --version
python --version
```

---

## 🚀 第五步：设置 AutoNewsletter 项目

### 5.1 访问 Windows 文件系统

WSL2 可以通过 `/mnt/` 访问 Windows 驱动器：

```bash
# 访问 D 盘项目目录
cd /mnt/d/zc752/Documents/Github/autonewsletter

# 查看文件
ls -la
```

### 5.2 运行 Conda 设置脚本

```bash
./conda-setup.sh
```

脚本会自动：
- 创建 `autonewsletter` conda 环境
- 安装 Python 3.11 和所有依赖
- 配置环境变量

### 5.3 激活环境

```bash
conda activate autonewsletter
```

提示符应该变为 `(autonewsletter)`。

### 5.4 配置环境变量

```bash
# 复制环境变量模板
cp .env.example .env

# 编辑环境变量
vim .env
```

填入必要的配置：
- `DATABASE_URL`: PostgreSQL 连接字符串
- `DEEPSEEK_API_KEY` 或 `OPENAI_API_KEY`: AI 服务密钥

### 5.5 启动数据库服务

```bash
# 启动 PostgreSQL 和 Redis
docker-compose up -d db redis

# 检查服务状态
docker-compose ps
```

### 5.6 运行数据库迁移

```bash
alembic upgrade head
```

### 5.7 启动应用

```bash
# 开发模式（热重载）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5.8 验证运行

打开新的终端窗口（或按 `Ctrl+Shift+T`），运行：

```bash
curl http://localhost:8000/health
```

应该返回：

```json
{"status":"healthy"}
```

---

## 💻 第六步：配置 Windows Terminal

Windows Terminal 是微软推出的现代化终端应用，提供更好的 WSL2 使用体验。

### 6.1 安装 Windows Terminal

从 Microsoft Store 搜索并安装 "Windows Terminal"。

或使用 winget（Windows 11）：

```powershell
winget install Microsoft.WindowsTerminal
```

### 6.2 设置 WSL2 为默认配置文件

1. 打开 Windows Terminal
2. 点击下拉菜单 → 设置（或按 `Ctrl+,`）
3. 在"启动"部分，将"默认配置文件"设置为 "Ubuntu-22.04"

### 6.3 自定义外观

#### 安装 Nerd Font（支持图标）

1. 下载 [MesloLGS NF](https://github.com/romkatv/powerlevel10k#manual-font-installation) 字体
2. 解压并安装所有 `.ttf` 文件
3. 在 Windows Terminal 设置中：
   - 选择 Ubuntu 配置文件
   - 外观 → 字体 → 选择 "MesloLGS NF"

#### 配置配色方案

在设置中选择你喜欢的配色方案，推荐：
- **One Half Dark**（默认）
- **Solarized Dark**
- **Dracula**

### 6.4 快捷键设置

推荐快捷键：
- `Ctrl+Shift+T`: 新建标签页
- `Ctrl+Shift+W`: 关闭标签页
- `Ctrl+Tab`: 切换标签页
- `Alt+Shift+D`: 垂直分屏
- `Alt+Shift+-`: 水平分屏

---

## 🔧 开发工作流最佳实践

### 文件系统性能

#### ✅ 推荐：项目放在 WSL2 文件系统

```bash
# 在 WSL2 home 目录创建项目
cd ~
mkdir -p projects
cd projects
git clone https://github.com/yourusername/autonewsletter.git
```

**优势**:
- 文件 I/O 性能接近原生 Linux
- Git 操作速度快 5-10 倍
- 避免跨文件系统的性能损失

#### ⚠️ 可选：通过 /mnt/ 访问 Windows 文件

```bash
cd /mnt/d/zc752/Documents/Github/autonewsletter
```

**优势**:
- 方便与 Windows 应用共享文件
- 无需迁移现有项目

**劣势**:
- 文件 I/O 性能较慢（约 50% 性能损失）
- Git 操作较慢

### VS Code 集成

#### 安装 Remote - WSL 扩展

1. 在 VS Code 中安装 "Remote - WSL" 扩展
2. 在 WSL2 终端中，进入项目目录：

```bash
cd /mnt/d/zc752/Documents/Github/autonewsletter
code .
```

VS Code 会自动在 WSL2 模式下打开项目。

#### 验证 WSL2 模式

左下角应该显示 "WSL: Ubuntu-22.04"。

### Git 配置

在 WSL2 中配置 Git：

```bash
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"

# 配置默认编辑器
git config --global core.editor "vim"

# 配置行尾符（避免 Windows/Linux 差异）
git config --global core.autocrlf input
```

### 日常开发流程

```bash
# 1. 启动 WSL2（打开 Windows Terminal）
# 2. 进入项目目录
cd /mnt/d/zc752/Documents/Github/autonewsletter

# 3. 激活 conda 环境
conda activate autonewsletter

# 4. 启动数据库服务
docker-compose up -d db redis

# 5. 运行应用
uvicorn app.main:app --reload

# 6. 在另一个终端标签页中进行开发
# 按 Ctrl+Shift+T 新建标签页
```

---

## ❓ 常见问题排查

### 1. Alembic 报错 "No module named 'psycopg2'"

**问题描述:**

运行 `alembic upgrade head` 时出现:

```
ModuleNotFoundError: No module named 'psycopg2'
```

**原因:**

- 应用运行时使用 `asyncpg`(异步驱动)
- Alembic 迁移需要同步驱动 `psycopg2`
- 两个驱动需要同时安装

**解决方案:**

更新 conda 环境以安装 psycopg2:

```bash
conda env update -f environment.yml --prune
```

验证安装:

```bash
python -c "import psycopg2; print(psycopg2.__version__)"
# 应输出: 2.9.9 (dt dec pq3 ext lo64)
```

然后重新运行迁移:

```bash
alembic upgrade head
```

### 2. WSL2 无法启动

**症状**: 运行 `wsl` 命令报错

**解决方案**:

```powershell
# 检查 WSL 状态
wsl --status

# 重启 WSL
wsl --shutdown
wsl

# 检查虚拟化是否启用
systeminfo | findstr /i "Hyper-V"
```

### 网络连接问题

**症状**: WSL2 中无法访问网络

**解决方案**:

```bash
# 检查 DNS 配置
cat /etc/resolv.conf

# 如果 DNS 不正确，手动配置
sudo vim /etc/resolv.conf
# 添加：nameserver 8.8.8.8

# 防止自动覆盖
sudo vim /etc/wsl.conf
# 添加：
# [network]
# generateResolvConf = false
```

### 文件权限问题

**症状**: 脚本无法执行，提示权限不足

**解决方案**:

```bash
# 添加执行权限
chmod +x script.sh

# 如果是从 Windows 复制的文件，可能需要转换行尾符
dos2unix script.sh
```

### Docker 无法连接

**症状**: `docker-compose` 命令报错

**解决方案**:

```bash
# 安装 Docker Desktop for Windows
# 在 Docker Desktop 设置中启用 "Use the WSL 2 based engine"
# 在 "Resources" → "WSL Integration" 中启用 Ubuntu-22.04

# 验证 Docker
docker --version
docker-compose --version
```

### Conda 环境激活失败

**症状**: `conda activate` 不工作

**解决方案**:

```bash
# 重新初始化 conda
~/miniconda3/bin/conda init zsh

# 重新加载配置
source ~/.zshrc

# 如果还是不行，检查 .zshrc 中是否有 conda 初始化代码
cat ~/.zshrc | grep conda
```

### 性能优化

**症状**: WSL2 运行缓慢或占用内存过多

**解决方案**:

在 Windows 用户目录下创建 `.wslconfig` 文件（`C:\Users\YourUsername\.wslconfig`）：

```ini
[wsl2]
memory=4GB
processors=2
swap=2GB
```

重启 WSL2：

```powershell
wsl --shutdown
wsl
```

---

## 📚 参考资源

### 官方文档

- [WSL 官方文档](https://docs.microsoft.com/zh-cn/windows/wsl/)
- [Oh My Zsh 官方网站](https://ohmyz.sh/)
- [Powerlevel10k GitHub](https://github.com/romkatv/powerlevel10k)
- [Windows Terminal 文档](https://docs.microsoft.com/zh-cn/windows/terminal/)

### 社区资源

- [WSL GitHub Issues](https://github.com/microsoft/WSL/issues)
- [Oh My Zsh Plugins](https://github.com/ohmyzsh/ohmyzsh/wiki/Plugins)
- [Awesome WSL](https://github.com/sirredbeard/Awesome-WSL)

### 相关工具

- [VS Code Remote - WSL](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-wsl)
- [Docker Desktop for Windows](https://www.docker.com/products/docker-desktop)
- [Windows Terminal Themes](https://windowsterminalthemes.dev/)

---

## 🎉 完成！

现在你已经拥有了一个完整的 WSL2 + Zsh 开发环境，可以享受接近原生 Linux 的开发体验。

### 下一步

1. **熟悉 Zsh**: 探索自动补全、历史搜索等功能
2. **配置 VS Code**: 安装 Python、Docker 等扩展
3. **开始开发**: 运行 AutoNewsletter 项目
4. **自定义环境**: 根据个人喜好调整主题和插件

如有问题，请参考[常见问题排查](#常见问题排查)部分或查阅官方文档。

Happy coding! 🚀
