"""PyInstaller / run.sh entry point.

A separate name from the ``kelly_ball`` package prevents PyInstaller from
confusing the entry script with the package and silently bundling nothing.
"""
from kelly_ball import KellyBallApp


if __name__ == "__main__":
    KellyBallApp().mainloop()
