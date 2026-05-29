"""`python -m kelly_ball` entry point."""
from .app import KellyBallApp


def main() -> None:
    KellyBallApp().mainloop()


if __name__ == "__main__":
    main()
