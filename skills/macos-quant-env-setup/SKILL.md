---
name: macos_quant_env_setup
display_name: macOS量化环境搭建
description: 国内macOS量化开发环境一键搭建指南，涵盖Homebrew中科大镜像、Python 3.12、pip阿里云加速、venv虚拟环境、Git GitHub代理、SUDO_ASKPASS技巧及国内网络常见坑规避。
category: general
aliases: [配置环境, 搭建环境, 安装Homebrew, 量化环境, pip镜像, Git代理, 初始化机器]
default_active: false
user_invocable: true
default_priority: 95
---

> 国内 macOS 量化开发环境一键搭建 — Homebrew 镜像、Python 3.12、pip 加速、venv、Git 代理、常见坑规避

## 触发条件

当用户提到以下关键词时激活本 skill：
- "配置环境"、"搭建环境"、"初始化机器"
- "安装 Homebrew"、"brew 镜像"
- "搭建量化环境"、"安装 akshare"
- "pip 镜像"、"Python 虚拟环境"
- "Git 代理"、"GitHub 加速"
- 新机器初始化、macOS 开发环境

---

## 一、Homebrew 安装（中科大镜像）

### 1.1 一键安装脚本

```bash
# 使用中科大镜像安装 Homebrew（避免 GitHub 直连超时）
export HOMEBREW_INSTALL_FROM_API=1
export HOMEBREW_API_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles/api"
export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles"
export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.ustc.edu.cn/brew.git"
export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.ustc.edu.cn/homebrew-core.git"

/bin/bash -c "$(curl -fsSL https://mirrors.ustc.edu.cn/misc/brew-install.sh)"
```

### 1.2 安装后持久化镜像配置

```bash
# 写入 ~/.zshrc（macOS 默认 zsh）
cat >> ~/.zshrc << 'BREW'

# === Homebrew 中科大镜像 ===
export HOMEBREW_API_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles/api"
export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles"
export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.ustc.edu.cn/brew.git"
export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.ustc.edu.cn/homebrew-core.git"
export HOMEBREW_PIP_INDEX_URL="https://mirrors.aliyun.com/pypi/simple/"
BREW

source ~/.zshrc
```

### 1.3 验证

```bash
brew --version        # 应输出 Homebrew 4.x
brew doctor           # 检查环境问题
```

---

## 二、Python 3.12 + Git 安装

### 2.1 通过 Homebrew 安装

```bash
brew install python@3.12 git
```

### 2.2 验证版本

```bash
python3.12 --version   # Python 3.12.x
git --version          # git version 2.x
which python3.12       # /opt/homebrew/bin/python3.12 (Apple Silicon)
                       # /usr/local/bin/python3.12 (Intel)
```

### 2.3 设置 python3 默认指向（可选）

```bash
# 如果系统自带 python3 版本过旧，创建软链
ln -sf $(brew --prefix python@3.12)/bin/python3.12 /opt/homebrew/bin/python3
ln -sf $(brew --prefix python@3.12)/bin/pip3.12 /opt/homebrew/bin/pip3
```

---

## 三、pip 阿里云镜像

### 3.1 全局配置

```bash
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'PIP'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
timeout = 120

[install]
use-mirror = true
PIP
```

### 3.2 备选镜像（阿里云不稳定时切换）

| 镜像 | 地址 |
|------|------|
| 阿里云 | `https://mirrors.aliyun.com/pypi/simple/` |
| 清华 | `https://pypi.tuna.tsinghua.edu.cn/simple/` |
| 中科大 | `https://pypi.mirrors.ustc.edu.cn/simple/` |
| 腾讯云 | `https://mirrors.cloud.tencent.com/pypi/simple/` |

### 3.3 临时使用（不修改全局配置）

```bash
pip install akshare -i https://mirrors.aliyun.com/pypi/simple/
```

---

## 四、venv 创建与包安装

### 4.1 创建虚拟环境

```bash
# 在项目目录下创建
cd ~/Projects
python3.12 -m venv stock_env

# 激活
source stock_env/bin/activate

# 验证（提示符前出现 (stock_env)）
which python    # ~/Projects/stock_env/bin/python
python --version
```

### 4.2 升级基础工具

```bash
pip install --upgrade pip setuptools wheel
```

### 4.3 安装量化核心包

```bash
pip install \
  akshare \
  tushare \
  yfinance \
  pandas \
  numpy \
  matplotlib \
  scipy \
  requests \
  loguru
```

### 4.4 可选扩展包

```bash
pip install \
  baostock \
  efinance \
  mplfinance \
  ta-lib \
  stockstats \
  python-dotenv \
  litellm
```

> ⚠️ `ta-lib` 需要先安装 C 库：`brew install ta-lib`，否则 pip install 会编译失败。

### 4.5 导出依赖

```bash
pip freeze > requirements.txt
```

### 4.6 退出虚拟环境

```bash
deactivate
```

---

## 五、PATH 配置

### 5.1 Apple Silicon (M1/M2/M3/M4)

```bash
# ~/.zshrc 中确保以下路径存在
export PATH="/opt/homebrew/bin:$PATH"
export PATH="/opt/homebrew/sbin:$PATH"
```

### 5.2 Intel Mac

```bash
export PATH="/usr/local/bin:$PATH"
export PATH="/usr/local/sbin:$PATH"
```

### 5.3 Homebrew 环境初始化（Apple Silicon 必须）

```bash
# 在 ~/.zshrc 中添加
eval "$(/opt/homebrew/bin/brew shellenv)"
```

### 5.4 验证 PATH 生效

```bash
source ~/.zshrc
echo $PATH | tr ':' '\n' | head -5
which brew      # /opt/homebrew/bin/brew
which python3   # 应指向 homebrew 或 venv 中的版本
```

---

## 六、Git GitHub 代理（gh-proxy）

### 6.1 配置 insteadOf 加速

```bash
# 使用 gh-proxy 代理 GitHub（国内直连 GitHub 经常超时）
git config --global url."https://ghfast.top/https://github.com/".insteadOf "https://github.com/"
```

### 6.2 验证配置

```bash
git config --global --list | grep insteadOf
# url.https://ghfast.top/https://github.com/.insteadof=https://github.com/
```

### 6.3 测试克隆

```bash
# 以下命令实际会走 ghfast.top 代理
git clone https://github.com/ZhuLinsen/daily_stock_analysis.git
```

### 6.4 备选代理（ghfast 不可用时）

```bash
# 切换代理
git config --global url."https://gh-proxy.com/https://github.com/".insteadOf "https://github.com/"
# 或
git config --global url."https://mirror.ghproxy.com/https://github.com/".insteadOf "https://github.com/"
```

### 6.5 移除代理（恢复直连）

```bash
git config --global --unset url."https://ghfast.top/https://github.com/".insteadOf
```

### 6.6 Git 用户配置

```bash
git config --global user.name "your_name"
git config --global user.email "your_email@example.com"
git config --global init.defaultBranch main
```

---

## 七、SUDO_ASKPASS 非交互 sudo

### 7.1 场景

在自动化脚本或 AI Agent 执行环境中，`sudo` 需要密码但无法交互输入。

### 7.2 配置方法

```bash
# 创建 askpass 脚本
cat > ~/.sudo_askpass.sh << 'ASKPASS'
#!/bin/bash
echo "your_password_here"
ASKPASS

chmod +x ~/.sudo_askpass.sh
```

### 7.3 使用方式

```bash
# 单次使用
SUDO_ASKPASS=~/.sudo_askpass.sh sudo -A apt-get install xxx

# 或在脚本中
export SUDO_ASKPASS=~/.sudo_askpass.sh
sudo -A some_command
```

### 7.4 安全注意事项

- ⚠️ 密码明文存储在脚本中，仅用于个人开发机
- ⚠️ 确保文件权限 `chmod 700 ~/.sudo_askpass.sh`
- 🚫 不要在共享服务器或 CI 环境使用此方法
- 替代方案：配置 `/etc/sudoers` 的 NOPASSWD（更安全但需 root）

### 7.5 NOPASSWD 替代方案（推荐）

```bash
# 编辑 sudoers（需要已有 sudo 权限）
sudo visudo -f /etc/sudoers.d/username

# 添加一行（允许特定命令免密）
username ALL=(ALL) NOPASSWD: /usr/sbin/softwareupdate, /usr/bin/xcodebuild
```

---

## 八、Pitfalls（国内网络常见坑）

### 8.1 直连超时

| 问题 | 原因 | 解决 |
|------|------|------|
| `brew install` 卡住 | 直连 GitHub/Homebrew API 超时 | 使用中科大镜像（见第一节） |
| `pip install` 超时 | PyPI 官方源被墙/慢 | 配置阿里云镜像（见第三节） |
| `git clone` 失败 | GitHub 直连不稳定 | 配置 gh-proxy insteadOf（见第六节） |
| `curl` GitHub raw 403 | CDN 污染 | 使用 `https://ghfast.top/` 前缀 |

### 8.2 sudo 缓存失效

| 问题 | 原因 | 解决 |
|------|------|------|
| 脚本中途要求输入密码 | sudo 默认 5 分钟超时 | 脚本开头 `sudo -v` 预热，或用 SUDO_ASKPASS |
| `sudo: a terminal is required` | 在非 TTY 环境执行 sudo | 使用 `sudo -A` + SUDO_ASKPASS |
| macOS 升级后 sudo 失效 | SIP 重置了部分权限 | 重启后重新验证 |

### 8.3 venv 未激活

| 问题 | 原因 | 解决 |
|------|------|------|
| `ModuleNotFoundError` | 忘记 `source venv/bin/activate` | 检查提示符前是否有 `(venv_name)` |
| 包装到了系统 Python | pip 指向系统路径 | `which pip` 确认路径在 venv 内 |
| IDE 找不到包 | IDE 未配置 venv 解释器 | 设置 Project Interpreter 为 venv/bin/python |
| `python` 和 `python3` 不一致 | 系统 alias 干扰 | venv 激活后两者应指向同一位置 |

### 8.4 Homebrew 相关

| 问题 | 原因 | 解决 |
|------|------|------|
| `brew update` 极慢 | 拉取 homebrew-core 全量 | 设置 HOMEBREW_API_DOMAIN 走镜像 |
| `Error: SHA256 mismatch` | 镜像同步延迟 | `brew cleanup && brew update` 重试 |
| Apple Silicon 找不到 brew | PATH 缺少 /opt/homebrew/bin | 添加 `eval "$(/opt/homebrew/bin/brew shellenv)"` |
| `xcrun: error` | Xcode CLT 未安装 | `xcode-select --install` |

### 8.5 Python 包安装

| 问题 | 原因 | 解决 |
|------|------|------|
| `ta-lib` 编译失败 | 缺少 C 库 | 先 `brew install ta-lib` |
| `numpy` 版本冲突 | akshare 依赖特定版本 | `pip install numpy==1.26.4` 固定 |
| `matplotlib` 无中文 | 缺少中文字体 | 下载 SimHei.ttf 放入 mpl fonts 目录 |
| SSL 证书错误 | 镜像站证书链不完整 | pip.conf 添加 `trusted-host` |

---

## 九、一键初始化脚本（完整）

```bash
#!/bin/bash
set -e

echo "=== [1/7] 安装 Homebrew（中科大镜像）==="
export HOMEBREW_INSTALL_FROM_API=1
export HOMEBREW_API_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles/api"
export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles"
export HOMEBREW_BREW_GIT_REMOTE="https://mirrors.ustc.edu.cn/brew.git"
export HOMEBREW_CORE_GIT_REMOTE="https://mirrors.ustc.edu.cn/homebrew-core.git"
if ! command -v brew &>/dev/null; then
  /bin/bash -c "$(curl -fsSL https://mirrors.ustc.edu.cn/misc/brew-install.sh)"
fi
eval "$(/opt/homebrew/bin/brew shellenv)"

echo "=== [2/7] 安装 Python 3.12 + Git ==="
brew install python@3.12 git

echo "=== [3/7] 配置 pip 阿里云镜像 ==="
mkdir -p ~/.pip
cat > ~/.pip/pip.conf << 'PIP'
[global]
index-url = https://mirrors.aliyun.com/pypi/simple/
trusted-host = mirrors.aliyun.com
timeout = 120
PIP

echo "=== [4/7] 创建虚拟环境 ==="
VENV_DIR="$HOME/stock_env"
python3.12 -m venv "$VENV_DIR"
source "$VENV_DIR/bin/activate"
pip install --upgrade pip setuptools wheel

echo "=== [5/7] 安装量化核心包 ==="
pip install akshare tushare yfinance pandas numpy matplotlib scipy requests loguru

echo "=== [6/7] 配置 Git 代理 ==="
git config --global url."https://ghfast.top/https://github.com/".insteadOf "https://github.com/"

echo "=== [7/7] 写入 PATH 到 ~/.zshrc ==="
cat >> ~/.zshrc << 'ZSHRC'

# === Homebrew ===
eval "$(/opt/homebrew/bin/brew shellenv)"

# === Homebrew 中科大镜像 ===
export HOMEBREW_API_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles/api"
export HOMEBREW_BOTTLE_DOMAIN="https://mirrors.ustc.edu.cn/homebrew-bottles"

# === 量化环境 ===
alias stock='source ~/stock_env/bin/activate'
ZSHRC

echo ""
echo "✅ 环境搭建完成！"
echo "   Python: $(python --version)"
echo "   venv:   $VENV_DIR"
echo "   激活:   source ~/stock_env/bin/activate  (或输入 stock)"
echo "   镜像:   pip → 阿里云 | brew → 中科大 | git → ghfast.top"
```

---

## 版本记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0 | 2026-08-01 | 初始版本：完整环境搭建流程 + Pitfalls |

---

## 免责声明

本 skill 中的镜像地址和代理工具可能随时间变化，请以各镜像站官方文档为准。密码相关配置仅限个人开发机使用。
