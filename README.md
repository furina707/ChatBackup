# 微信 & QQ 本地聊天记录保存系统 (纯无线免 ADB 联动版)

一套专为已 Root（支持 **SukiSU / KernelSU / Magisk**）设备打造的聊天记录保存与导出工具，由 **手机端 Agent (APK)** 与 **电脑端终端交互控制台 (Python TUI)** 联动协同工作。

**特点：彻底告别数据线与 ADB 限制，手机 App 借助 SukiSU Root 权限直接在局域网内与电脑全无线互联！支持通过 HTTPS 在线检查与更新！**

---

## 核心工作原理

```mermaid
graph LR
    subgraph 手机端 (Android SukiSU)
        SU[SukiSU 内核级Root] --> AgentApp[ChatBackup Agent App]
        AgentApp --> RawData[su -c cat 管道流式读取<br/>微信 EnMicroMsg.db + QQ 数据库]
        AgentApp --> Beacon[UDP 局域网无感广播 :28889]
        AgentApp --> HTTPServer[内置轻量极速 HTTP 服务 :28888]
    end

    subgraph 局域网 Wi-Fi / 热点
        Beacon -.->|自动发现| TUI
        HTTPServer <==>|TCP 高速直连流式传输| TUI
    end

    subgraph 电脑端 (无需数据线 / 无需 ADB)
        TUI[Python Textual TUI 控制台]
        TUI --> DecryptEngine[SQLCipher 解密引擎]
        TUI --> Explorer[树状好友/群聊瀑布流]
        TUI --> ExportHTML[单文件离线 HTML / CSV 导出]
        TUI --> Updater[HTTPS 检查与下载更新]
    end

    subgraph 云端 (GitHub)
        GHAction[GitHub Actions] --> GHR[GitHub Releases 资产库]
        GHR -.->|HTTPS 安全分发| Updater
    end
```

---

## 快速使用流程 (全程无线操作)

### 1. 手机端操作
1. 在已 Root（SukiSU）手机上安装并打开 **ChatBackup Agent** 应用。
2. 在 SukiSU 管理器中为该 App 授予 Root 权限。
3. 点击 **“启动无线备份服务 (免数据线)”**。
   - 此时 App 会自动在局域网内广播本机信息（例如 `192.168.1.100:28888`）。

### 2. 电脑端操作
1. 确保电脑与手机连接在同一个 Wi-Fi（或者手机开热点电脑连上）。
2. 直接双击运行根目录下的：
   ```bash
   run_desktop.bat
   ```
3. 电脑端 TUI 控制台会在第一页 **“局域网自动发现”** 列表中瞬间捕获到你的手机设备！
4. 点击 **“选中设备一键连接”**（或者直接核对手机界面显示的 IP，点击直连）。
5. 切换到 **“2. 数据同步与解密”** 分页，点击 **“拉取并解密微信数据”** 或 **“拉取 QQ 数据库”**。
6. 切换到 **“3. 聊天浏览器”**，自由查看历史记录或导出离线 HTML。

### 3. 软件升级与版本更新 (HTTPS)
1. 在电脑端 TUI 中切换至 **“4. 软件升级 (HTTPS)”** 选项卡。
2. 确认仓库地址（默认 `furina707/ChatBackup`），点击 **“检查新版本 (HTTPS)”**。
3. 控制台将自动查询最新发布版本，比对本地版本并在右侧展示完整的发布更新日志 (Release Notes)。
4. 在可用资产列表（APK / Windows 压缩包）中选择目标项，点击 **“下载选中的更新包”**。
5. 程序通过安全 HTTPS 协议流式下载更新文件，并实时显示下载速率与进度。

---

## GitHub Actions 自动构建与发布

本项目已配置完整的 CI/CD 流程（`.github/workflows/build.yml`）：

- **代码提交自动构建**：向 `main` 分支提交代码时，GitHub Actions 会自动编译 Android Debug APK 及 Windows TUI 打包程序，并上传为 Actions Artifacts。
- **打标签自动发布 Release**：
  ```bash
  git tag v1.0.0
  git push origin v1.0.0
  ```
  推送 `v*` 格式的版本标签后，GitHub Actions 将自动创建 GitHub Release，将 `ChatBackup-Agent.apk` 与 `ChatBackup-Windows-Desktop.zip` 作为附件发布。
