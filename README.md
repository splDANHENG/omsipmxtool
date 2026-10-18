# omsimod — PMX 司机转换器（实验原型）

把 PMX 人物转换为 OpenOMSI 人物包：`.hum` + `model.cfg` + O3D + PNG 贴图。
不修改游戏程序，不自动覆盖地图配置，也不要求安装 Blender。

**当前只完成文件转换和结构检查，尚未在 OpenOMSI 中验证显示和动作。**
输出面向已研究的 openOMSI 提交 `1ca88e6bb6c5d70c9b690978a7e26a8ac5096710`，不承诺原版 OMSI 2 兼容性。

## 安装和运行

要求 Python 3.10+，依赖 Pillow（图像解码和颜色/透明度烘焙）。
Windows、macOS、Linux 使用同一份代码；Windows 还未在真实机器测试。
仓库提供三平台 CI 配置，需推送 GitHub 后才会运行。

Windows PowerShell，在解压后的项目目录执行：

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install .
.\.venv\Scripts\python.exe -m omsimod inspect "D:\Models\人物.pmx"
.\.venv\Scripts\python.exe -m omsimod convert "D:\Models\人物.pmx" --output "D:\Converted\MyDriver" --name MyDriver --height 1.75
```

macOS / Linux：

```sh
python3 -m venv .venv
.venv/bin/python -m pip install .
.venv/bin/python -m omsimod convert "/path/to/人物.pmx" --output ./dist/MyDriver --name MyDriver --height 1.75
```

`--height` 是完整网格包围盒高度（米），包含头发和饰品。输出目录必须不存在，防止覆盖已有结果。
保留 PMX 原文件和相对路径贴图；贴图须位于 PMX 所在目录内（允许子目录）。

## 骨骼识别

自动识别常见日文和英文骨骼名，缺失或有歧义时停止，不猜测关键关节。
`inspect` 列出所有骨骼。通过 `--mapping mapping.json` 覆盖个别关节：

```json
{
  "hips": "自定义骨盆",
  "torso": "自定义脊柱",
  "right_hand": "自定义右手腕"
}
```

可用键：`hips`, `torso`, `head`, `neck`，以及 `left_` / `right_` 加
`thigh`, `shin`, `arm`, `elbow`, `hand`。值为精确的日文或英文骨骼名称。

## 已实现的转换

- 读取 PMX 2.0 / 2.1 的几何、材质和骨骼部分；读取 BDEF1/2/4、SDEF、QDEF 权重。
- SDEF/QDEF 降级为线性混合蒙皮，不保留原始变形算法。
- 将直臂 A 姿态旋转烘焙为 T 姿态；明显弯曲手肘的基础姿态暂时拒绝。
- 归并到 13 个目标人体骨骼，同目标权重求和后归一化。
- 附加骨骼跟随最近的已识别祖先；没有匹配祖先的骨骼退回躯干并报告。
- 根据解剖学左右腿确定左右轴；按 PMX 约定处理前后朝向，不支持任意旋转的源人物。
- 按材质分块输出 O3D v1，限制块大小以满足 16 位顶点/三角形/权重计数。
- 双面材质生成反面三角形和反向法线。
- 材质基础颜色和透明度乘入 PNG 像素；根据输出 alpha 选择不透明、裁切或混合模式。
- 自动生成 `.hum` 的 22 个关节数值、坐高等初始参数。

## 表情与隐藏层策略（不依赖供应商）

不按模型厂商、文件名、材质名（如“颜”“脸”“表情”）删除几何。
只省略 PMX **默认材质 alpha 为 0** 的部分，并记录材质名；可见层保留。
不执行 morph：不保留顶点表情、材质表情、骨骼表情或动画。
这不是自动“去表情”算法：某些模型把表情层放在远处或通过其他约定隐藏，
本版本仍会保留这些默认可见的网格，可能需要人工处理。
隐藏层不再要求对应贴图存在。

## 限制

- 无 MMD 物理、IK/附加变换、Toon、球面反射、描边、动态衣服或独立手指动作。
- 衣服与头发权重只做简化归并，不优化变形质量或穿模。
- 引擎会镜像右侧关节；左右不对称网格保留，骨架无法完全表达不对称人体。
- 坐高、指端、步态是初始估计，方向盘贴合、朝向和材质仍须游戏内验证。
- 不把资源“能解析”当成“游戏内正常”。`conversion-report.json` 明确记录 `game_verified: false`。
- 解析器只读取所需前缀，未验证后续 morph/物理数据；不是完整 PMX 文件校验器。

## 安装输出到游戏

生成目录中含 `Humans/<name>/driver.hum`，模型配置和贴图位于它的子目录。
把整个 `Humans` 目录合并到 OpenOMSI 内容根目录中。
备份目标地图 `maps/<map>/drivers.txt`，把下面的路径放在第一行，保留其余条目：

```text
Humans\MyDriver\driver.hum
```

完全重启游戏，使用有 `[drivpos]` 的车辆，在外部视角和后视镜检查。
司机列表也供 AI 使用；本方式不是玩家专属外观设置。
卸载时恢复列表并移除自己安装的角色目录。命令行转换只导出文件；图形界面可自动安装，
并在点击应用后更新地图司机列表。

## 测试

```sh
python -m unittest discover -s tests -v
```

测试包括合成 PMX -> CLI -> 独立 O3D 解码、权重归并、透明度烘焙、
双面几何、跨目录贴图拒绝、输入截断、歧义骨骼、输出不覆盖及厂商无关的隐藏层规则。
用户提供的调试模型不包含在源码/测试分发中。

接口依据：
- https://github.com/openOMSI-org/openOMSI/blob/1ca88e6bb6c5d70c9b690978a7e26a8ac5096710/crates/omsi-sim/src/human/rig.rs
- https://github.com/openOMSI-org/openOMSI/blob/1ca88e6bb6c5d70c9b690978a7e26a8ac5096710/crates/omsi-scene/src/driver.rs
- https://github.com/openOMSI-org/openOMSI/blob/1ca88e6bb6c5d70c9b690978a7e26a8ac5096710/docs/FORMATS.md

## 图形界面（源码运行方式）

采用跨平台 Qt/PySide6，直接从 Python 源码运行。Mac 双击项目里的
`启动界面.command`；Windows 双击 `Start-GUI.bat`。启动器优先使用 `.venv-gui`，其次 `.venv`。
当前机器已配置 `.venv-gui`，可以直接启动。复制项目到其他机器时，虚拟环境不能一起搬走，需重新安装：

macOS / Linux（Python 3.10+）：

```sh
python3 -m venv .venv-gui
.venv-gui/bin/python -m pip install '.[gui]'
.venv-gui/bin/python -m omsimod.gui
```

Windows PowerShell：

```powershell
py -3 -m venv .venv-gui
.\.venv-gui\Scripts\python.exe -m pip install ".[gui]"
.\.venv-gui\Scripts\python.exe -m omsimod.gui
```

界面支持文件选择、模型/骨骼检查、角色标识、身高、可选骨骼映射 JSON、后台转换、
错误报告和打开输出文件夹。选择“输出位置”时会在选中的父目录下追加当前角色标识；
可直接编辑完整路径，路径必须尚不存在。转换中会锁定设置，完成后才能关闭窗口，
避免中途退出留下不完整结果。当前不含 3D 预览。

PySide6 的系统要求取决于所安装版本及 Qt 支持的操作系统；旧版 macOS 可能需要
安装兼容的 PySide6 版本。未进行 Windows 实机验证。

## 角色库与游戏管理

### 0.2：自动安装与一键应用

转换页默认勾选“转换后自动安装到 OMSI”，选择包含 `maps` 和 `Vehicles`
的 OMSI 内容目录后，转换结果会连同 HUM、O3D 和贴图一起安装至
`Humans/OMSIMod_<角色ID>/`。输出目录仍保留完整导出包；安装失败不会删除它，
界面和 `conversion-report.json` 会记录安装结果。取消勾选可只导出文件。

安装成功后，在“角色库与游戏”点击“一键应用全部车辆（全部地图）”。
它独立于单地图范围设置，会备份并更新全部已安装地图的司机列表。
重启 OpenOMSI 后，这些地图内支持动态司机的车辆即可共用该角色；
不替换车辆自带的固定人物模型，AI 也可能使用所选角色。
新增地图后需再次应用。仍可使用“恢复原司机”恢复此前备份。
已安装人物可在原导出目录移除后继续应用到同一游戏目录。

界面的第二个标签页可导入独立人物包中的 `.hum`，移出角色列表（不删除文件），
选择游戏可执行文件、OMSI 内容目录、地图和车辆。转换成功后自动将结果加入角色库。
导入会检查 `.hum` -> 模型配置 -> 网格文件；暂不支持跨人物目录引用资源，
也不是全量贴图依赖或游戏兼容性检查。

1. 选择角色，默认勾选“应用 / 恢复全部已安装地图”，点击“应用所选角色”。取消勾选则仅处理所选地图。
2. 工具复制人物目录到 `Humans/OMSIMod_<角色ID>`，保存原司机列表，再把新人物放在列表首位。
3. 完全退出原游戏后，从桌面或游戏启动器正常启动即可；不需要通过本工具启动，也不需要为每辆车重新应用。界面的启动按钮只是指定地图 / 车辆的可选快捷入口。
4. 点击“恢复原司机”按勾选范围逐字节恢复此前的 `drivers.txt`（原本不存在则删除新建文件）；没有备份的地图会跳过。

全部地图指当前所选内容目录 `maps/` 下已安装的地图。以后新增地图，再点击一次应用即可。
批量操作逐张报告成功与失败，遇到外部修改会保留冲突文件及备份，并继续处理其他地图。
游戏必须开启可见司机；车辆需要支持游戏的司机显示。此功能不改变车辆自带的静态人物网格。

角色库、游戏路径和备份现在保存在系统用户数据目录（macOS 为 `~/Library/Application Support/OMSI Mod Studio/`）。
旧项目 `userdata/` 已迁移；不要删除系统数据目录，否则会失去恢复记录。
应用后如果其他程序修改司机列表，工具会拒绝自动覆盖/恢复，备份仍保留。
恢复不会删除已安装角色，以免破坏其他地图引用。重新转换人物建议使用新输出目录重新导入；
已安装的同一角色目录不会被自动覆盖更新。请勿同时打开多个管理窗口修改同一地图。

安装采用临时目录完成复制，再提交最终人物目录；源目录和安装目录不得重叠。
应用 / 恢复时写入操作记录，中断后可再次应用或恢复；外部修改仍会被拒绝覆盖。
同一个 App 内的角色库写入已串行化，多个 App 进程同时管理同一目录仍不支持。

### Windows 便携包

`dist/OMSI-Mod-Studio-Windows-x64.zip`：完整解压后双击 `Start.bat`。
包含 Windows x64 Python、Qt 和 Pillow，无需另外安装 Python；启动期间请保留控制台窗口。
目标系统为 Windows 10/11 x64。当前在 macOS 上组装，尚未完成 Windows 实机启动验证。
`Diagnose.bat` 可检查 GUI 依赖与窗口构造。不包含人物、游戏数据或本机备份。
构建脚本为 `scripts/build_windows_portable.py`，依赖下载至 `build/windows-wheels/`，
使用 Python 官方 `python-3.12.10-embed-amd64.zip`，输入校验值随压缩包保存。

实机记录（2026-10-17）：macOS，openOMSI 0.3.36，Grundorf / MAN SD80。
ZIP 挂载本身成功，但地图司机列表未覆盖；改用备份后直接应用，日志确认加载 `driver.hum`，
近景截图确认饮月君在驾驶位可见。尚未验证行驶时全范围转向、全部车辆或 Windows 实机。


## macOS 点击即用 App

打包产物：`dist/OMSI Mod Studio.app`。双击打开，或拖到“应用程序”后打开。
Python、Qt 和 Pillow 已包含，无需用户安装 Python 或运行终端命令。
本次构建为 **Apple Silicon / arm64**，在本机验证启动、角色库和游戏路径读取。
没有 Developer ID 公证；跨机器分发可能遇到系统验证提示，Intel Mac 需另行构建。

现有饮月君资源已复制到系统数据目录的 `characters/`，现有司机列表备份也已保留。
新导入人物仍记录用户选择的文件路径，请不要移动它们；转换结果亦需保留其输出目录。
Windows 数据目录使用 `%LOCALAPPDATA%/OMSI Mod Studio`；Linux 使用 XDG 数据目录。
可以通过 `OMSIMOD_DATA_DIR` 指定测试目录。

开发者重新构建（在目标系统上执行）：

```sh
.venv-gui/bin/python -m pip install pyinstaller
.venv-gui/bin/python scripts/build_gui.py
```

应用包不包含本机角色、游戏数据或备份。`dist/OMSI-Mod-Studio-macOS-arm64.zip`
仅包含 App，可用作分发包。

## Windows 原生构建记录（2026-10-18）

本机 Windows 10 x64 使用 Python 3.14.0、PySide6 6.12.0、Pillow 12.3.0
和 PyInstaller 6.22.3 构建。29 项测试通过；EXE 原生窗口启动自检通过。
尚未进行 Windows 游戏内人物显示与动画验证。

双击 `dist/OMSI Mod Studio/OMSI Mod Studio.exe` 启动，无需另外安装 Python。
分发时复制整个 `OMSI Mod Studio` 文件夹，必须保留旁边的 `_internal`，
或完整解压 `dist/OMSI-Mod-Studio-Windows-x64.zip` 后启动。

构建命令：`.venv-gui\Scripts\python.exe scripts/build_gui.py`。
构建脚本隔离 Windows DLL 搜索路径，避免收集其他软件的同名动态库。
启动异常保存到用户数据目录中的 `startup-error.log`。
打包后的自动启动检查可执行 `"OMSI Mod Studio.exe" --smoke-test report.json`，
它使用临时角色库，记录原生窗口状态并自动退出。
