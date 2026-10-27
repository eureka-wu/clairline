#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
长龙航空 · 智能大盘与航网规划助手 (macOS DMG 自动化封包脚本)
GitHub: https://github.com/eureka-wu/clairline

执行本脚本将在 dist/ 目录下生成：
1. dist/LoongAirHelper.app (macOS 原生独立应用包)
2. dist/LoongAirHelper-v2.0.0.dmg (标准拖拽安装镜像)
"""

import os
import sys
import shutil
import subprocess
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
ROUTES_SEED = ROOT_DIR / "backend" / "data" / "routes_seed.json"
APP_NAME = "LoongAirHelper"
VERSION = "v2.0.0"

def generate_mac_icns():
    """将 app_icon.png 转换为 macOS 原生高清 .icns 图标"""
    png_path = ROOT_DIR / "app_icon.png"
    icns_path = ROOT_DIR / "app_icon.icns"
    if icns_path.exists():
        return icns_path

    if not png_path.exists():
        return None

    try:
        iconset_dir = ROOT_DIR / "app.iconset"
        iconset_dir.mkdir(exist_ok=True)
        sizes = [16, 32, 64, 128, 256, 512]
        for s in sizes:
            subprocess.run(f"sips -z {s} {s} {png_path} --out {iconset_dir}/icon_{s}x{s}.png", shell=True, check=True)
            if s <= 256:
                subprocess.run(f"sips -z {s*2} {s*2} {png_path} --out {iconset_dir}/icon_{s}x{s}@2x.png", shell=True, check=True)
        subprocess.run(f"iconutil -c icns {iconset_dir} -o {icns_path}", shell=True, check=True)
        shutil.rmtree(iconset_dir, ignore_errors=True)
        print("[+] macOS 原生高清图标生成成功: app_icon.icns")
        return icns_path
    except Exception as ex:
        print(f"[*] 图标生成提示 (将使用默认 png): {ex}")
        shutil.rmtree(ROOT_DIR / "app.iconset", ignore_errors=True)
        return png_path

def build_mac():
    print("=" * 65)
    print(f"[*] 开始构建 长龙航空畅飞助手 (macOS {VERSION} DMG 镜像)")
    print("[*] GitHub: https://github.com/eureka-wu/clairline")
    print("=" * 65)

    # 1. 确保前端静态产物存在
    if not (FRONTEND_DIST / "index.html").exists():
        print("[!] 未检测到前端构建产物，正在执行 npm run build...")
        subprocess.run("npm run build", shell=True, cwd=str(ROOT_DIR / "frontend"), check=True)
    else:
        print("[+] 前端静态产物已就绪 (frontend/dist)")

    # 2. 准备图标
    icon_file = generate_mac_icns()

    # 3. 构造 PyInstaller 命令行 (macOS 下 add-data 路径分隔符必须为冒号 :)
    sep = os.pathsep
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "--noconfirm",
        "--clean",
        "--windowed",
        f"--name={APP_NAME}",
        "--paths=backend",
        "--paths=.",
        f"--add-data={FRONTEND_DIST}{sep}frontend/dist",
        f"--add-data={ROUTES_SEED}{sep}backend/data",
        f"--add-data={ROOT_DIR / 'backend' / 'db.py'}{sep}backend",
        f"--add-data={ROOT_DIR / 'backend' / 'db.py'}{sep}.",
        f"--add-data={ROOT_DIR / 'backend' / 'seccard_client.py'}{sep}backend",
        f"--add-data={ROOT_DIR / 'backend' / 'seccard_client.py'}{sep}.",
        f"--add-data={ROOT_DIR / 'backend' / 'loongair_client.py'}{sep}backend",
        f"--add-data={ROOT_DIR / 'backend' / 'loongair_client.py'}{sep}.",
        f"--add-data={ROOT_DIR / 'backend' / 'auto_patrol.py'}{sep}backend",
        f"--add-data={ROOT_DIR / 'backend' / 'auto_patrol.py'}{sep}.",
        f"--add-data={ROOT_DIR / 'backend' / 'scheduler.py'}{sep}backend",
        f"--add-data={ROOT_DIR / 'backend' / 'scheduler.py'}{sep}.",
        f"--add-data={ROOT_DIR / 'backend' / 'server.py'}{sep}backend",
        f"--add-data={ROOT_DIR / 'backend' / 'server.py'}{sep}.",
    ]

    if icon_file and icon_file.exists():
        cmd.append(f"--icon={icon_file}")

    cmd.extend([
        "--hidden-import=server",
        "--hidden-import=db",
        "--hidden-import=seccard_client",
        "--hidden-import=auto_patrol",
        "--hidden-import=scheduler",
        "--hidden-import=loongair_client",
        "--hidden-import=webview",
        "--hidden-import=webview.platforms.cocoa",
        "--hidden-import=bottle",
        "--hidden-import=requests",
        "--hidden-import=sqlite3",
        # 排除无用模块以极限加速
        "--exclude-module=PyQt5",
        "--exclude-module=PyQt6",
        "--exclude-module=PySide2",
        "--exclude-module=PySide6",
        "--exclude-module=tkinter",
        "--exclude-module=matplotlib",
        "--exclude-module=numpy",
        "--exclude-module=pandas",
        "--exclude-module=scipy",
        "app_desktop.py"
    ])

    print("\n[*] 正在调用 PyInstaller 编译生成 LoongAirHelper.app...")
    res = subprocess.run(cmd, cwd=str(ROOT_DIR))
    if res.returncode != 0:
        print("[!] PyInstaller 打包异常！")
        sys.exit(1)

    app_path = ROOT_DIR / "dist" / f"{APP_NAME}.app"
    if not app_path.exists():
        print(f"[!] 找不到生成的应用包: {app_path}")
        sys.exit(1)

    dmg_path = ROOT_DIR / "dist" / f"{APP_NAME}-{VERSION}.dmg"
    dmg_alias = ROOT_DIR / "dist" / f"{APP_NAME}.dmg"

    if dmg_path.exists():
        dmg_path.unlink()
    if dmg_alias.exists():
        dmg_alias.unlink()

    print(f"\n[*] 正在使用 macOS hdiutil 制作拖拽式 DMG 镜像...")
    # 临时装配目录
    dmg_temp_dir = ROOT_DIR / "dist" / "dmg_temp"
    shutil.rmtree(dmg_temp_dir, ignore_errors=True)
    dmg_temp_dir.mkdir(parents=True, exist_ok=True)

    # 复制 .app 到临时目录并软链接 /Applications
    shutil.copytree(str(app_path), str(dmg_temp_dir / f"{APP_NAME}.app"))
    os.symlink("/Applications", str(dmg_temp_dir / "Applications"))

    # 生成只读压缩 DMG
    dmg_cmd = [
        "hdiutil", "create",
        "-volname", f"{APP_NAME}-{VERSION}",
        "-srcfolder", str(dmg_temp_dir),
        "-ov",
        "-format", "UDZO",
        str(dmg_path)
    ]
    dmg_res = subprocess.run(dmg_cmd)
    shutil.rmtree(dmg_temp_dir, ignore_errors=True)

    if dmg_res.returncode == 0:
        shutil.copy2(str(dmg_path), str(dmg_alias))
        size_mb = dmg_path.stat().st_size / (1024 * 1024)
        print("\n" + "=" * 65)
        print("[SUCCESS] macOS DMG 打包圆满成功！产物已就绪：")
        print(f"[FILE 1] {dmg_path}")
        print(f"[FILE 2] {dmg_alias}")
        print(f"[INFO]   文件体积: {size_mb:.2f} MB")
        print("[TIP]    可直接双击挂载测试，或上传至 GitHub Releases")
        print("=" * 65)
    else:
        print("[!] DMG 制作失败，请检查 hdiutil 输出。")
        sys.exit(1)

if __name__ == "__main__":
    build_mac()
