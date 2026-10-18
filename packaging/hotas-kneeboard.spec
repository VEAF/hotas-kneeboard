# PyInstaller: one HOTAS-Kneeboard.exe holding Python, the server, the Lua engine, the template
# library and the built UI. Build with packaging/build.ps1 (the UI must be built first).
from pathlib import Path

ROOT = Path(SPECPATH).parent
PACKAGE = ROOT / "hotas_kneeboard"
if not (PACKAGE / "web" / "index.html").is_file():
    raise SystemExit("the UI is not built: run `npm run build` in web/ first")

a = Analysis(
    [str(ROOT / "packaging" / "launcher.py")],
    pathex=[str(ROOT)],
    datas=[
        (str(PACKAGE / "lua"), "hotas_kneeboard/lua"),
        (str(PACKAGE / "library"), "hotas_kneeboard/library"),
        (str(PACKAGE / "web"), "hotas_kneeboard/web"),
    ],
    hiddenimports=["uvicorn.logging", "uvicorn.loops.auto", "uvicorn.protocols.http.auto", "uvicorn.lifespan.on"],
    excludes=["tkinter", "test", "unittest", "pydoc"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    name="HOTAS-Kneeboard",
    # a console: the server runs as long as it is open, and closing it quits the app
    console=True,
    upx=False,
)
