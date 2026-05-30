"""PyInstaller / run.sh entry point.

A separate name from the ``kelly_ball`` package prevents PyInstaller from
confusing the entry script with the package and silently bundling nothing.
Launches the 3D (pywebview + Three.js) front-end.
"""
from kelly_ball.__main__ import main


if __name__ == "__main__":
    main()
