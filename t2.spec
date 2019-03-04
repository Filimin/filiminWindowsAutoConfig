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
          manifest_override="autoConfig.exe.manifest",
          uac_admin=True, # get elevated privs
          icon='filiminSetupIcon.ico',
          console=False) # , manifest='autoConfig.exe.manifest')

# the below seems to solve an apparent bug where the manifest file is not created
# the manifest file seems necessary only when uac_admin=True (above)
coll = COLLECT(exe,
               strip=False,
               upx=True,
               name='autoConfig'
)
