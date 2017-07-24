# -*- mode: python -*-

import os
import site
block_cipher = None

gnome_path = os.path.join(site.getsitepackages()[1], 'gnome')
typelib_path = os.path.join(gnome_path, 'lib', 'girepository-1.0')
missing_files = []

for tl in ["Atk-1.0.typelib", "cairo-1.0.typelib", "Gdk-3.0.typelib", "GdkPixbuf-2.0.typelib", "Gio-2.0.typelib", "GIRepository-2.0.typelib", "GLib-2.0.typelib", "GModule-2.0.typelib", "GObject-2.0.typelib", "Gtk-3.0.typelib", "Pango-1.0.typelib"]:
    missing_files.append((os.path.join(typelib_path, tl), "./gi_typelibs"))

missing_files.append(('./gfx/ubrobot.png', './gfx'))
missing_files.append(('./win32/bin/adb.exe', './bin'))
missing_files.append(('./win32/bin/AdbWinApi.dll', './bin'))
missing_files.append(('./win32/bin/AdbWinUsbApi.dll', './bin'))
missing_files.append(('./win32/bin/fastboot.exe', './bin'))
missing_files.append(('./cpt.ico', '.'))

a = Analysis(['cpt.py'],
             pathex=['.\\win32_exe'],
             binaries=missing_files,
             datas=[],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=False,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='CPT',
          debug=False,
          strip=False,
          upx=True,
          console=False )
coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='CPT')
