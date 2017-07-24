# -*- mode: python -*-

block_cipher = None

missing_binaries = []
missing_data = []

missing_data.append(('./gfx/ubrobot.png', './gfx'))
missing_binaries.append(('./osx/bin/adb', './bin'))
missing_binaries.append(('./osx/bin/fastboot', './bin'))


a = Analysis(['cpt.py'],
             pathex=['./cpt/'],
             binaries=missing_binaries,
             datas=missing_data,
             hiddenimports=None,
             hookspath=None,
             runtime_hooks=['osx_rthook.py'])
pyz = PYZ(a.pure)
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='cpt',
          debug=False,
          strip=None,
          upx=True,
          console=False )

base_dir = '.'
gtks = ['./osx/loaders.cache']
data_files = [(x, os.path.join(base_dir, x), 'DATA') for x in gtks]

more_binaries = []
pixbuf_dir = '/usr/local/lib/gdk-pixbuf-2.0/2.10.0/loaders'
for pixbuf_type in os.listdir(pixbuf_dir):
    if pixbuf_type.endswith('.so'):
        more_binaries.append((pixbuf_type, os.path.join(pixbuf_dir, pixbuf_type), 'BINARY'))

coll = COLLECT(exe, data_files,
               a.binaries + more_binaries,
               a.zipfiles,
               a.datas,
               strip=None,
               upx=True,
               name='cpt')

app = BUNDLE(coll,
             name='cpt.app',
             icon='cpt.ico')


