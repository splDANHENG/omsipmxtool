**This project was built 100% using GPT-6 Astra.** This is the project author's statement about the development process; it does not change the copyright or licensing requirements of referenced code, third-party dependencies or model assets.

# omsipmxtool

[简体中文](README.md) | English

**Bring your PMX character into OpenOMSI and put them in the driver's seat.**

omsipmxtool converts PMX character models into OpenOMSI character packages, with a desktop interface for conversion, installation, driver selection and restoration. Blender is not required.

> Experimental software targeting OpenOMSI. Compatibility with the original OMSI 2 engine is not guaranteed. Results depend on the model, vehicle and game version. The application interface is currently in Chinese; this English README includes the relevant button labels.

**Windows download: [v0.2.0 experimental release](https://github.com/splDANHENG/omsipmxtool/releases/tag/v0.2.0)**. Download `omsipmxtool-0.2.0-windows-x64.zip`, extract everything and run `omsipmxtool.exe`. Keep `_internal` beside the EXE. Python is not required. This build is unsigned.

## Features

- Export HUM, O3D meshes, PNG textures and a conversion report.
- Generate character identifiers from PMX filenames, converting Chinese characters to unaccented pinyin. Identifiers remain editable.
- Estimate full model height, with a manual override.
- Save GUI exports under `omsipmxtool_exports` in the selected OMSI content directory. Repeated names receive numbered suffixes rather than overwriting existing packages.
- Install complete character packages into the game's `Humans` directory.
- Apply a selected character across all installed maps, for vehicles supporting dynamic drivers.
- Back up and restore driver lists, refusing to overwrite detected external changes.
- Display embedded PMX comments before import. Scroll to the bottom and click Continue; models without embedded comments do not trigger this dialog.

## Detailed usage guide

### 1. Prepare the application, game and model

For Windows, download the Windows x64 ZIP from the Release linked above and extract it to a writable folder. Do not run it inside the ZIP or move the EXE without its supporting folder. Tested on Windows 10 x64; Windows 11 has not been independently tested.

For a source installation, choose **Code → Download ZIP** on GitHub and extract everything, or clone the repository:

```bash
git clone https://github.com/splDANHENG/omsipmxtool.git
cd omsipmxtool
```

Follow [Running from source](#running-from-source) below. Separately obtain a working OpenOMSI installation, legitimately acquired OMSI 2 content, and a PMX model whose applicable permissions allow your intended use. Test the target map and vehicle with a stock driver first.

Extract the complete model package, retaining relative paths between the PMX and textures. Do not copy only the PMX. Textures must be inside its directory or a subdirectory. Do not commit third-party character assets to this repository without permission.

### 2. First launch and notices

On first launch, scroll through the project copyright and usage notice, then click **继续** (Continue). No checkbox is required. Closing the dialog or choosing Exit prevents entry into the application.

The reading record is stored locally. The notice appears again if its content changes. Models with embedded PMX comments have a separate import dialog. Neither dialog verifies permission to use the model. Check the distribution page and accompanying Readme even if no comments are embedded.

### 3. Select your OMSI content directory

Under **PMX 转换** (PMX conversion), use **OMSI 目录 → 选择目录** to select a root containing both `maps` and `Vehicles`.

Do not select an individual vehicle folder or a directory containing only `openomsi.exe`. If OpenOMSI uses a separate content root, choose the one from which it actually loads the relevant maps and driver lists.

The GUI requires this root even when automatic installation is disabled, because exports are saved there. Use the command line for conversion into an arbitrary output directory.

### 4. Import a PMX and check settings

Choose **选择 PMX** (Select PMX), read its embedded comments if present, and review:

- **角色标识** (Character identifier): derived from the filename. For example, `饮月君 1708.pmx` becomes `yinyuejun_1708`. You can correct names or ambiguous Chinese pronunciations manually.
- **模型总高度** (Full model height): estimated from mesh bounds, including hair and accessories. It is not necessarily the character's stated height. Estimates outside 0.5–3 metres stop automatic conversion; disable automatic estimation and enter a value manually.
- **骨骼映射** (Bone mapping): normally leave blank. If joints cannot be identified uniquely, use **检查模型与骨骼** (Inspect model and bones) and supply a JSON mapping with exact bone names.
- **统一导出目录** (Export directory): generated automatically. Existing names receive `_2`, `_3`, and so on.

Inspection results and errors appear below the controls. Do not map several required joints to the same bone merely to bypass an error.

### 5. Convert and install

Click **生成人物包** (Generate character package) and wait. Do not force-close the application during conversion.

**转换后自动安装到 OMSI** (Automatically install after conversion) is enabled by default. The output is added to the character library and copied into the game. If unchecked, conversion and library registration still take place, but automatic installation does not.

```text
OMSI content root/
└─ omsipmxtool_exports/
   └─ MyDriver/
      ├─ Humans/
      │  └─ MyDriver/
      │     ├─ driver.hum
      │     ├─ model/       # Configuration and O3D meshes
      │     └─ texture/     # PNG textures
      ├─ conversion-report.json
      └─ INSTALL.txt
```

The installed copy uses `Humans/OMSIMod_<character ID>/`. There is no need to rename it.

If conversion succeeds but installation or library registration fails, the exported package is retained. Read the error, resolve path, permission or texture problems, then import the exported `driver.hum` through the library and try applying it. Do not delete your source model or game backups.

### 6. Apply the character

Exit the game, then open **角色库与游戏** (Character library and game):

1. Select the character.
2. Confirm the content root and choose **保存路径并扫描地图 / 车辆** (Save paths and scan maps/vehicles).
3. Click **一键应用全部车辆（全部地图）** (Apply to all vehicles / all maps).
4. Check individual map successes, failures and skipped entries. Finishing a batch does not mean every map succeeded.
5. Restart OpenOMSI normally and enter a successfully updated map with a vehicle supporting dynamic drivers.

The dedicated apply-all button always processes all currently installed maps. For one map only, uncheck **应用 / 恢复全部已安装地图**, select a map, and use **应用所选角色** (Apply selected character).

This backs up and updates each map's `drivers.txt`, placing the character first and retaining other entries. **It does not replace a vehicle's built-in static driver mesh. AI vehicles may also use the character.** Apply again after adding new maps.

The **游戏程序** (Game executable) field is only needed for the optional launch shortcut. You can continue using your normal OpenOMSI launcher.

### 7. Existing packages, reconversion and restoration

- **导入 HUM** (Import HUM): select a `.hum` inside a complete, standalone character package. Its configuration, O3D files and textures must remain available within the package.
- **Reconvert a model:** generate a new package and apply its new library entry. Existing installed copies are not automatically replaced.
- **恢复原司机** (Restore original drivers): restore one map or all maps with backups, provided no external modification conflict is detected. Maps without backups are skipped.
- **移出角色库** (Remove from library): removes the list entry only. It does not delete source files, installed characters or backups, and does not restore map driver lists.

Restoration retains installed characters to avoid breaking other maps. Do not delete an installed character directory before checking references. If a driver list was externally modified, keep both the current file and backup and investigate the conflict; deleting backups to bypass protection is not a safe workaround.

### 8. Troubleshooting

| Symptom | What to check |
| --- | --- |
| Maps not found | Select the correct root containing `maps` and `Vehicles`. |
| Missing or external texture | Extract the full model package and preserve its relative texture paths. |
| Bone identification failure | Inspect exact bone names and provide a mapping; renaming the PMX will not fix its skeleton. |
| Unexpected height | Check distant geometry and unusual units, or enter height manually. |
| No driver outside | Confirm successful application, correct map, full game restart, dynamic-driver support and the game's driver visibility setting. |
| Driver visible outside but no hands inside | Enable the cab-view option described below. |
| Previous character still shown | Apply the newly exported library entry to the actual map and restart the game fully. |
| Sleeves obscure instruments or clip | Clothing physics are not reproduced; try a model with fewer arm accessories. |
| Problems after a game update or in neutral | Compare with the previous game version and a stock driver, then report reproduction details. |

## Showing the driver's arms in the cab

OpenOMSI can display the driver's hands and arms in first-person view. Enable this in the game, not in the converter:

1. Open **Settings → Camera** in the OpenOMSI launcher.
2. Enable **Driver's hands in the cab view**.
3. Enter the driver's view, normally **F1**. In-game, look under **Esc → Options → Camera**.

If the option is unavailable in the interface, fully close the game and launcher, back up `settings.cfg`, then edit the corresponding entry without overwriting other settings:

- Windows: `%USERPROFILE%\.openomsi\settings.cfg`
- macOS / Linux: `~/.openomsi/settings.cfg`

```ini
hands_in_cab=1
```

Save and restart. Set it to `0` to disable. This was checked against OpenOMSI 0.3.33 and upstream settings code accessed on 2026-10-18. Other versions may differ. First-person rendering hides parts of the body; it is not the same as the full external-view character.

References: [settings UI](https://github.com/openOMSI-org/openOMSI/blob/741e1bc9363479315aaa1cdfb6bf21839b4735ee/launcher/ui/js/pages/settings-schema.js), [configuration reader](https://github.com/openOMSI-org/openOMSI/blob/741e1bc9363479315aaa1cdfb6bf21839b4735ee/crates/omsi-app/src/settings.rs), [official user guide](https://github.com/openOMSI-org/openOMSI/blob/main/docs/USER_GUIDE.md).

## Model support and limitations

The converter reads PMX 2.0/2.1 geometry, materials and bones and reduces weights to the target human skeleton. Common Japanese/English bone names and certain D-leg deformation chains are supported; custom mappings can resolve identification failures.

- MMD morphs, physics, IK, dynamic clothing and independent finger animation are not preserved.
- SDEF/QDEF weights are approximated with linear skinning.
- Toon shading, sphere maps and outlines are not fully reproduced.
- Automatic height uses full Y-axis mesh bounds multiplied by `0.08`, including accessories. It is not an authoritative real-world height.
- Complex poses, clothing and hair may deform or clip. Seating and steering-wheel alignment require in-game checks.
- Only materials with zero default opacity are omitted; geometry is not removed based on character, vendor or material names.

**Successful conversion means files were generated, not that every vehicle and scene will render correctly.**

### Choosing a character

Current OpenOMSI character-system and converter limitations make clothing, ribbon and accessory physics difficult to reproduce. These parts follow a simplified skeleton instead of moving or avoiding obstacles naturally.

**Unless they are your absolute favourite, consider avoiding models with large hanging sleeves, long ribbons or ornaments around the arms and cuffs.** Some outfits of Dan Heng • Imbibitor Lunae, Kaedehara Kazuha, Xiao and Keqing warrant particular attention. This depends on the actual model and does not mean those characters are universally unsupported.

Such parts may obscure instruments or clip through the steering wheel, dashboard or body during driver movements. Close-fitting cuffs and fewer arm accessories generally make it easier to keep a clear driving view.

## Running from source

Python 3.10+ is required. Run these commands in the project directory:

```powershell
# Windows
py -3 -m venv .venv-gui
.\.venv-gui\Scripts\python.exe -m pip install ".[gui]"
.\.venv-gui\Scripts\python.exe -m omsimod.gui
```

```bash
# macOS / Linux
python3 -m venv .venv-gui
.venv-gui/bin/python -m pip install '.[gui]'
.venv-gui/bin/python -m omsimod.gui
```

Platform support also depends on Python, Qt and dependency versions. The latest local source review was performed on Windows; other platforms require their own validation.

### Command line and development

Using the Python interpreter from the environment where the project is installed:

```bash
python -m omsimod inspect "path/to/model.pmx"
python -m omsimod convert "path/to/model.pmx" --output "path/to/new-package" --name MyDriver --height 1.75
python -m unittest discover -s tests
```

The output directory must not exist. `--mapping mapping.json` accepts a JSON object mapping semantic joints to exact bone names, for example `{"hips": "下半身"}`. The CLI does not show GUI reading dialogs; read applicable notices yourself before use.

`scripts/package_source.py` creates a source archive. `scripts/build_gui.py` builds a native application on the target OS with PyInstaller installed separately.

For compatibility, the internal package remains `omsimod` and user data retains the name `OMSI Mod Studio`: `%LOCALAPPDATA%/OMSI Mod Studio` on Windows, `~/Library/Application Support/OMSI Mod Studio` on macOS, and the XDG data directory on Linux. Do not delete this data if you need driver-list backups. See [two-computer development notes](TWO-COMPUTERS.md) (Chinese).

## Model copyright and usage notice

**The project is intended for personal, learning-oriented use in games. This statement does not grant permission to use any particular model.**

omsipmxtool is an unofficial conversion tool, without official affiliation, partnership or endorsement from OMSI, OpenOMSI, MMD or the rights holders of imported characters.

Application distributions do not include third-party character models, textures or game assets. Rights in models, textures, character designs and other materials remain with their respective lawful rights holders. Format conversion does not change ownership.

Before use, consult the **original PMX distribution page, accompanying Readme, embedded comments and other valid permissions**. Confirm that conversion, modification and in-game use are permitted. Other uses must also comply with applicable permissions.

**The project discourages sharing converted results—including models, textures and bundled character packages—unless you have obtained permission from the relevant rights holders covering that sharing or redistribution.**

When permission has been obtained, follow its scope and conditions, retain required author credits, license notices and source links, and identify conversions or modifications.

Free distribution, attribution, an “unofficial” label or a promise to remove infringing content does not replace required permission. Missing embedded comments do not mean unrestricted use or redistribution is allowed.

The first-launch notice and embedded-comment dialogs are reading prompts only. **Completing them, converting successfully or installing a character does not establish authorization or certify compliance.**

The full project notice and attribution template are in [MODEL-RIGHTS.txt](MODEL-RIGHTS.txt) (Chinese). Nothing in this notice excludes or limits responsibility imposed by applicable law.

## Software licenses and provenance

The main project license is **AGPL-3.0-only**. The PMX reader retains **GPL-3.0-or-later** licensing; combined distribution follows the applicable terms of both.

Development referenced OpenOMSI's human rig, pose handling and formats, and MMD Tools' PMX reader. Versions, adaptation notes and third-party notices are recorded in [LICENSE](LICENSE), [THIRD-PARTY-NOTICES.txt](THIRD-PARTY-NOTICES.txt) and [LICENSES](LICENSES/).

**The software licenses grant no rights to third-party models. The model-use guidance does not add “personal use only” or “non-commercial only” restrictions to the open-source software licenses.**

Windows Releases include application source, dependency sources and SHA-256 checksums. See [BINARY-DISTRIBUTION.txt](BINARY-DISTRIBUTION.txt) for licenses, rebuilding and library replacement, and [the review record](RELEASE-REVIEW.txt) (Chinese).

## Known issues and feedback

### OpenOMSI version compatibility

OpenOMSI is under active development. Character loading, skeletons and animation behaviour may change. **Neither the converter nor existing converted packages are guaranteed to keep working after an OpenOMSI update.** Report new-version compatibility issues with the old/new versions and whether the same model previously worked.

### Driver animation is still evolving

If hands move erratically or other animations look unnatural, first consider OpenOMSI's animation logic and vehicle configuration as possible causes; the converter is not necessarily responsible.

- **Abnormal arm movement has been observed with the vehicle in N (neutral).** The root cause has not been identified. It may involve game logic, vehicle configuration or converted-model adaptation.

Compare with a stock driver in the same vehicle and conditions. Include gear selection, reproduction steps and a video where possible.

### PMX models vary

PMX has a file-format specification, but creators use different bone names, deformation chains, materials, hidden geometry and scales. Testing has primarily used models publicly distributed by miHoYo; this does not guarantee compatibility with other models or imply permission to redistribute them.

If your model cannot be converted, [open an Issue](https://github.com/splDANHENG/omsipmxtool/issues), or ask an AI coding assistant (Agent) to help investigate error messages, reports and bone mappings. Back up originals before making changes and respect model permissions.

### What to include in a report

- Application and OpenOMSI versions.
- Original model distribution link and whether you modified it.
- Reproduction steps, expected result and actual behaviour.
- Error messages or conversion report.
- Vehicle, map and gear, plus comparison with a stock driver.

Remove personal paths from logs. **Do not upload models, textures or game files you are not authorized to redistribute.** Prefer original distribution links or a minimal example you may legally share.

Rights holders can report specific project content and original sources through Issues for review and appropriate action.
