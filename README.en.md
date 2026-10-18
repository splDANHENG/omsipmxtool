**This project was built 100% using GPT-6 Astra.** This is the project author's statement about the development process; it does not change the copyright or licensing requirements of referenced code, third-party dependencies or model assets.

# omsipmxtool

[简体中文](README.md) | English

> **Reporting guidance: please do not report problems with this mod in any official OpenOMSI channel. Report them to [this project's Issues](https://github.com/splDANHENG/omsipmxtool/issues) first. If you suspect an OpenOMSI bug, restore the stock driver and reproduce it in the same vehicle and conditions. Only after confirming that the stock driver has the same issue should you report it through official OpenOMSI channels, including the version and reproduction steps.**

**Bring your PMX character into OpenOMSI and put them in the driver's seat.**

omsipmxtool converts PMX character models into OpenOMSI character packages, with a desktop interface for conversion, installation, driver selection and restoration. Blender is not required.

> Experimental software targeting OpenOMSI. Compatibility with the original OMSI 2 engine is not guaranteed. Results depend on the model, vehicle and game version. The application interface is currently in Chinese; this English README includes the relevant button labels.

**Windows download: [v0.3.2 experimental release](https://github.com/splDANHENG/omsipmxtool/releases/tag/v0.3.2)**. Download `omsipmxtool-0.3.2-windows-x64.zip`, extract everything and run `omsipmxtool.exe`. Keep `_internal` beside the EXE. Python is not required. This build is unsigned.

## Changelog

### v0.3.2 · 2026-10-19

- **Added:** local, offline generation of help prompts to copy into an AI/agent, available on the converter and character-library pages. Prompts include the version, operation, recent error and relevant guidance. Preview with paths hidden, review the text, then paste it into your chosen AI/agent for help. The application does not include or run an AI model. Generating prompts requires no API key, network requests or automatic uploads; the external AI/agent handles connectivity and data according to the service you choose.

- **Fixed:** share one exported texture across materials with identical baked output, including identical results from different source files. Update mesh and material references together, preserving differences in tint and alpha.
- **Migration:** regenerate and reinstall existing character packages to apply this fix; do not manually delete their duplicate textures.
- **Validation:** the v0.3.2 release records 77 passing automated tests and successful Windows EXE startup and preview-mapping checks. No additional in-game or Windows 11 hardware validation was performed.

### v0.3.1 · 2026-10-19

- **Security:** reject symlinks, Windows junctions and other reparse points during character import/install. Recheck entries and their directory boundaries while copying. Validate installation destinations and character identifiers too.
- **Fixed:** selecting D leg pivots now retains weights from ordinary parallel leg chains and their descendants, instead of assigning some leg vertices to the hips.
- **Performance:** preview rendering yields between batches and cancels obsolete frames after camera changes. Models exceeding 80,000 triangles or 120,000 vertices use a skeleton-only preview without changing full exports. Models with more than 4,096 bones must use JSON mapping.
- **Validation:** 68 automated tests passed, including junction rejection, mixed leg-chain weights and responsive preview rendering.
- **Documentation:** added security scope, release verification and detection-report handling below.

### v0.3.0 · 2026-10-19

- **Added:** visual bone mapping with name search, JSON import/export, automatic reset and direct application to conversion.
- **Added:** untextured model preview with rotation, zoom, pan and bone highlighting. Pick a bone to assign it to a target role; overlapping bones have a candidate selector.
- **Fixed:** automatically select a unique D leg counterpart when its rest position differs from the ordinary leg bone. Explicit mappings retain precedence.
- **Fixed:** scrolling over mapping dropdowns no longer changes their selection. Switching PMX files clears the current mapping.
- **UI:** explain the tool's supported binding roles and manual mapping steps.
- **Validation:** 62 automated tests passed, covering picking, overlapping bones, camera interaction and exported mappings.
- **Limitations:** no textures, animation or physics in the preview; in-game results still require model- and vehicle-specific checks.

### v0.2.0 · 2026-10-18

- Released the Windows x64 experimental package with no separate Python installation required.
- Provided corresponding application/dependency sources, license notices and SHA-256 checksums.

## Security and detection reports

- **Scope:** the main application reads selected model resources, exports character packages and, when requested, installs characters and updates map driver lists with recovery backups. Catalogue data, backups and logs default to `%LOCALAPPDATA%\OMSI Mod Studio` on Windows. Launching the game runs the executable configured by the user.
- **Excluded behavior:** the main converter implements no telemetry uploads, startup persistence, antivirus disabling or process-memory injection. Separate local experimental tools are not included in the official EXE or corresponding source ZIP.
- **Verify downloads:** use this project's GitHub Releases and compare the ZIP's SHA-256 with `SHA256SUMS.txt`, e.g. `Get-FileHash .\omsipmxtool-0.3.2-windows-x64.zip -Algorithm SHA256`. Per-file manifests, build information and corresponding sources are supplied. Matching hashes prove file identity, not the absence of vulnerabilities or malware.
- **Limits:** the EXE is unsigned. Unknown-publisher/reputation warnings differ from malware detections. Tests, review and individual antivirus scans are not guarantees of safety or complete third-party dependency audits.
- **Reports:** pause use and provide the download URL, version, detected file's SHA-256, detection name and screenshot in [Issues](https://github.com/splDANHENG/omsipmxtool/issues). Do not post private models, credentials or sensitive paths. Maintainers should verify and investigate; confirmed issues require stopping affected distribution, fixing and announcing the issue. Suspected false positives should be submitted to the vendor for review with the outcome disclosed.
- **Keep protection enabled:** do not disable antivirus, whitelist entire drives or elevate privileges to bypass alerts. Microsoft provides a [file review portal](https://www.microsoft.com/en-us/wdsi/filesubmission) and [SmartScreen guidance](https://learn.microsoft.com/en-us/windows/apps/package-and-deploy/smartscreen-reputation).
- **Trust boundary:** import trusted standalone character folders only. Installation copies their regular files; it does not establish that unrelated accompanying files are trustworthy. Path checks do not fully isolate a concurrent attacker with equivalent local write access. Do not modify the source package during installation.

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
  When an ordinary leg bone and its unique D deformation counterpart have different rest positions, the D bone is selected automatically. Explicit mappings still take precedence.
  Use **图形化编辑** (Visual editor) to view automatic matches, search bone names, and apply selections directly to conversion. The editor can load/save JSON and reset all roles to automatic. Switching PMX files clears the current mapping.
  The left pane previews the untextured mesh and skeleton. Drag with the left button to rotate, scroll to zoom, and drag with the right button to pan. Click a role button to highlight its mapping, or pick a bone and assign it to the selected target role. Overlapping bones appear in a candidate list. Yellow marks the selected bone; orange marks D leg bones. Lines represent parent connections. The preview does not simulate animation or physics and never modifies the source PMX.
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

## Future direction

Current development prioritizes capabilities that **do not require modifying or recompiling OpenOMSI**, including model conversion, character-package management and compatibility diagnostics. Improvements remain within the game's existing resource formats and configuration mechanisms.

**Features requiring modification and recompilation of OpenOMSI are outside the current development plan.** Each request will be evaluated against the target version's capabilities. Resource conversion and configuration cannot replace runtime features or guarantee fixes for problems caused by internal game behavior.

If OpenOMSI reaches a version suitable for long-term use, with sufficiently stable interfaces and behavior, and sustained maintenance is feasible, the project may assess deeper extensions based on a specific stable version. Any distribution of modified builds requires prior review of applicable licenses, source-availability obligations and permissions for bundled assets.

These statements describe research directions only. **They are not commitments to specific features, release dates or distribution of modified builds, and do not represent OpenOMSI's official development plans.**

**Please direct feature suggestions and compatibility reports for this project to this repository first. Where upstream support is needed, maintainers will assess the technical requirements before communicating through normal collaboration channels as appropriate.**

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

### macOS usage (launch the GUI from Terminal)

macOS users can run from source without first building an `.app`. Terminal is used to install dependencies and launch the graphical interface. The Windows `.exe` distribution cannot run directly on macOS.

1. Install Python 3.10 or newer, for example using an installer suitable for your system from [Python's website](https://www.python.org/downloads/macos/). Check the version with `python3 --version` in Terminal.
2. Download and extract this repository using **Code → Download ZIP** into your user directory. Type `cd ` in Terminal (including the trailing space), drag the extracted project folder into the window, and press Return. The folder should contain `pyproject.toml`.
3. Run these commands from that folder:

```bash
python3 -m venv .venv-gui
.venv-gui/bin/python -m pip install --upgrade pip
.venv-gui/bin/python -m pip install '.[gui]'
.venv-gui/bin/python -m omsimod.gui
```

The initial dependency installation requires internet access. For subsequent launches, enter the same project directory and run only the final command. Keep Terminal open while using the application. Environment activation and `sudo` are not required.

In the character-library/game tab, select your OMSI content directory containing resources such as `Humans`, `Maps` and `Vehicles`. To launch the game through this tool, select the actual executable inside the OpenOMSI app bundle, commonly `/Applications/openOMSI.app/Contents/MacOS/openomsi`; use your actual installation location. In Finder, right-click the application and choose **Show Package Contents**.

For command-line inspection or conversion, after the installation above, run from the project directory:

```bash
.venv-gui/bin/python -m omsimod inspect "/path/to/model.pmx"
.venv-gui/bin/python -m omsimod convert "/path/to/model.pmx" --output "/path/to/new-package" --name MyDriver --height 1.75
```

Replace the example paths. The height `1.75` is an example full-mesh height in metres; adjust it for your model. The output directory must not already exist. CLI conversion creates a package without installing it into the game; use the GUI for automatic installation and batch assignment. Compatibility across macOS versions, processors and dependency combinations still requires testing on the respective systems.

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

**The project is intended for personal, learning-oriented use in games. This statement does not replace the model author's permission, and personal, non-commercial or educational use does not automatically exempt users from applicable restrictions.**

omsipmxtool is an unofficial conversion tool, without official affiliation, partnership or endorsement from OMSI, OpenOMSI, MMD or the rights holders of imported characters.

Application distributions do not include third-party character models, textures or game assets. Rights in models, textures, character designs and other materials remain with their respective lawful rights holders. Format conversion does not change ownership.

Obtain models you have permission to use. Before conversion, consult the **original PMX distribution page, accompanying Readme, embedded comments and other valid permissions**. Confirm whether format conversion, model modification and use in other games are permitted, and follow attribution, usage and redistribution requirements. Embedded comments may not contain the complete or latest terms; consult the rights holder's applicable permissions. If permission is unclear or the intended use is prohibited, contact the rights holder and obtain the necessary permission before proceeding.

**The project discourages sharing converted results—including models, textures and bundled character packages—unless you have obtained permission from the relevant rights holders covering that sharing or redistribution.**

Possessing a model file does not grant redistribution rights. Before sharing converted results, commercial use or other uses, confirm the scope of permission. Follow its conditions, retain required author credits, license notices and source links, and identify conversions or modifications.

Free distribution, attribution, an “unofficial” label or a promise to remove infringing content does not replace required permission. Missing embedded comments do not mean unrestricted use or redistribution is allowed.

The project cannot individually verify permissions for user-imported assets. The first-launch notice and embedded-comment dialogs are reading prompts only; see [First launch and notices](#2-first-launch-and-notices) for the workflow. **Completing them, converting successfully or installing a character does not establish authorization or certify compliance.**

If you find unauthorized content in this repository or its release packages, report it through a [GitHub Issue](https://github.com/splDANHENG/omsipmxtool/issues), including relevant links, an explanation of rights ownership and the specific concern so maintainers can investigate and address it. Do not upload complete models or textures to public Issues without permission; see [What to include in a report](#what-to-include-in-a-report) for troubleshooting information.

The full project notice and attribution template are in [MODEL-RIGHTS.txt](MODEL-RIGHTS.txt) (Chinese). Nothing in this notice excludes or limits responsibility imposed by applicable law.

## Software licenses and provenance

The main project license is **AGPL-3.0-only**. The PMX reader retains **GPL-3.0-or-later** licensing; combined distribution follows the applicable terms of both.

Development referenced OpenOMSI's human rig, pose handling and formats, and MMD Tools' PMX reader. Versions, adaptation notes and third-party notices are recorded in [LICENSE](LICENSE), [THIRD-PARTY-NOTICES.txt](THIRD-PARTY-NOTICES.txt) and [LICENSES](LICENSES/).

**The software licenses grant no rights to third-party models. The model-use guidance does not add “personal use only” or “non-commercial only” restrictions to the open-source software licenses.**

Windows Releases include application source, dependency sources and SHA-256 checksums. See [BINARY-DISTRIBUTION.txt](BINARY-DISTRIBUTION.txt) for licenses, rebuilding and library replacement, and [the review record](RELEASE-REVIEW.txt) (Chinese).

## Known issues and feedback

### OpenOMSI version compatibility

This tool is built as a standalone Python/Qt application; its build does not compile or bundle the OpenOMSI executable. Development references and upstream release status are recorded separately (checked on 2026-10-18):

- **Latest official non-prerelease:** [OpenOMSI v0.3.33](https://github.com/openOMSI-org/openOMSI/releases/tag/v0.3.33). This is an upstream release designation, not evidence of comprehensive compatibility testing with this tool or a long-term support commitment.
- **Primary implementation reference:** [`1ca88e6bb6c5d70c9b690978a7e26a8ac5096710`](https://github.com/openOMSI-org/openOMSI/commit/1ca88e6bb6c5d70c9b690978a7e26a8ac5096710). See [third-party notices](THIRD-PARTY-NOTICES.txt) for reference and adaptation scope. This commit must not be conflated with the stable release above.
- **Driver animation analysis reference:** [v0.3.37](https://github.com/openOMSI-org/openOMSI/releases/tag/v0.3.37) (`b5e4acc`), officially marked **Pre-release / Beta**, not a stable release.

Available records do not establish a single OpenOMSI stable version with complete in-game validation for the Windows distribution. Consult the release notes and [release review](RELEASE-REVIEW.txt) for the actual test scope.

OpenOMSI is under active development. Character loading, skeletons and animation behaviour may change. **Neither the converter nor existing converted packages are guaranteed to keep working after an OpenOMSI update.** Report new-version compatibility issues with the old/new versions and whether the same model previously worked.

### Driver animation and vehicle detection limitations

This tool converts character models. **OpenOMSI's own animation system** generates the driver's movements during driving.

The inspected source corresponding to OpenOMSI 0.3.37 includes these driver movements and pose adjustments:

- **Seating adjustment:** adjusts the seated pose, forward lean and seat position to help the arms reach the wheel.
- **Steering:** hands follow the wheel, with release, regripping and alternating grip adjustments.
- **Hand grip:** adjusts palm orientation and finger curling around the wheel or gear lever; this is not full MMD animation of individual fingers.
- **Gear shifting:** after identifying a lever, the hand on that side reaches for it, follows its movement and returns to the wheel. A brief procedural push may also be generated.
- **Resting a hand while stopped:** after stopping for a while, a hand may leave the wheel and rest on the identified gear lever.
- **Seated lower-body adjustment:** adjusts bent legs and foot placement. The inspected driver code does not animate pedal presses from accelerator, brake or clutch input; clutch input can help trigger the shifting hand movement.

This summarizes the inspected source, not a guarantee that every vehicle supports every movement or that later versions behave identically. No dedicated hand movements for operating indicators, wipers or dashboard buttons were found in the inspected driver animation code.

Source references (pinned to `b5e4acc`): [driver animation](https://github.com/openOMSI-org/openOMSI/blob/b5e4acc/crates/omsi-scene/src/driver.rs), [wheel and gear-lever detection](https://github.com/openOMSI-org/openOMSI/blob/b5e4acc/crates/omsi-scene/src/driver/rig.rs).

#### Why do movements differ between vehicles?

OpenOMSI identifies vehicle parts and computes hand movements rather than simply playing a driver's animation supplied with the vehicle. **Gear-lever detection uses keywords in animation-variable and mesh-file names, along with distance and reachability checks.** Wheel detection also considers steering variables, rotation factors and position.

This can produce missed detections or false positives:

- **Unrecognised gear lever:** in the inspected ПАЗ 3205R configuration, gears and the lever move normally, but the driver's hand does not perform a shifting movement. Its lever filename and animation-variable names do not match the inspected detection rules.
- **Another stalk mistaken for a gear lever:** the WG120FK was observed with the driver's right hand reaching separately towards a stalk. Source and vehicle-configuration analysis found that its right-hand wiper stalk variable, `cockpit_wischer_drehschalter`, contains the gear-lever keyword `schalt`, making it a potential false positive. The stopped-hand-resting logic could also produce an apparent stalk-operating movement. **This remains an inference, not fully confirmed by runtime detection logs or a controlled comparison. It is not evidence of a dedicated turn-signal hand animation.**
- **Abnormal movement in neutral:** unusual arm movement has been observed in N. Its cause remains unresolved and may involve game logic, vehicle configuration or converted-model adaptation.

These symptoms do not necessarily indicate a PMX conversion error. Restore the stock driver and compare in the same vehicle, gear and operating conditions, then report the results to this project to help distinguish model adaptation issues from game or vehicle-configuration issues.

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
