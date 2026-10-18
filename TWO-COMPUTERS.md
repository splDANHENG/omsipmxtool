# Windows / macOS 双机协作

此仓库用于源码发布和双机开发同步。公开范围仅包含项目源码与文档；
审查记录见 RELEASE-REVIEW.txt。源码许可与本地 EXE 的分发要求分别核对，
不要把本地构建产物视为已完成二进制公开发布审核。

## 首次配置另一台电脑

1. 读取公开源码不需要仓库写入权限；推送时登录拥有仓库写入权限的 GitHub 账号。
2. 在新目录克隆仓库。不要直接覆盖 Mac 上原项目：先保留旧目录和未提交内容，
   再将尚未同步的修改与新克隆逐项比较。
3. 每台电脑独立建立 `.venv-gui` 并安装依赖，不复制 Windows/Mac 虚拟环境。

macOS：

```sh
python3 -m venv .venv-gui
.venv-gui/bin/python -m pip install -e '.[gui]'
.venv-gui/bin/python -m unittest discover -s tests -v
.venv-gui/bin/python -m omsimod.gui
```

Windows PowerShell：

```powershell
py -3 -m venv .venv-gui
.\.venv-gui\Scripts\python.exe -m pip install -e ".[gui]"
.\.venv-gui\Scripts\python.exe -m unittest discover -s tests -v
.\.venv-gui\Scripts\python.exe -m omsimod.gui
```

在每台电脑设置自己的 Git 提交姓名和邮箱；可使用 GitHub 的 noreply 邮箱。
身份设置与 GitHub 登录认证是两回事。不要将令牌写入仓库或远程 URL。

## 每次换电脑

开始前先检查工作区，再获取远端更新：

```sh
git status
git pull --ff-only
```

如果有未提交修改，先检查并提交需要保留的内容，不要用强制覆盖或清理命令。
结束时检查差异、运行相应测试，然后提交并推送：

```sh
git diff
git add <本次修改的文件>
git diff --cached
git commit -m "说明此次修改"
git push
```

只有推送成功，另一台电脑才能拉到新修改。如果两台都已产生提交导致
`pull --ff-only` 失败，先检查两边历史并合并解决冲突，不要强制推送。
两台需要同时开发时使用不同功能分支，通过 Pull Request 合并。

## 哪些内容不同步

- `.venv`、`.venv-gui`、`build`、`dist`、缓存、日志和本机工具配置。
- 游戏安装目录、人物模型、贴图包、地图司机备份与用户角色库。
- 登录凭据、`.env` 等配置文件。

用户数据默认分别位于：

- Windows：`%LOCALAPPDATA%/OMSI Mod Studio`
- macOS：`~/Library/Application Support/OMSI Mod Studio`

这些数据中的角色路径与游戏路径属于各自电脑。每台电脑重新导入人物、
选择游戏路径；原地图备份留在所属电脑，不要相互覆盖。

Windows EXE 在 Windows 构建，macOS App 在 Mac 构建。
构建工具需要在对应虚拟环境中另装 PyInstaller。
