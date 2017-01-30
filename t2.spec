# -*- mode: python -*-

block_cipher = None


a = Analysis(['autoconfig.py'],
             pathex=['C:\\Users\\user\\dev\\autoConfig'],
             binaries=None,
             datas=[('template.xml','.'),
                    ('resources/blank.png','resources/'),
                    ('resources/complete.png','resources/'),
                    ('resources/failure.png','resources/'),
                    ('resources/spinning.png','resources/')
             ],
             hiddenimports=[],
             hookspath=[],
             runtime_hooks=[],
             excludes=[],
             win_no_prefer_redirects=False,
             win_private_assemblies=True,
             cipher=block_cipher)
pyz = PYZ(a.pure, a.zipped_data,
             cipher=block_cipher)
exe = EXE(pyz,
          
          a.scripts,
          a.binaries,
          a.zipfiles,
          a.datas,
          name='autoConfig',
          debug=False,
          strip=False,
          upx=True,
          console=False )
'''
exe = EXE(pyz,
          a.scripts,
          exclude_binaries=True,
          name='autoconfig',
          debug=False,
          strip=False,
          upx=True,
          console=True )

coll = COLLECT(exe,
               a.binaries,
               a.zipfiles,
               a.datas,
               strip=False,
               upx=True,
               name='autoconfig')
'''
