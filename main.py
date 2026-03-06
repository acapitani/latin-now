import sys
from core.launcher import Launcher

def main():
    try:
        app = Launcher()
        app.mainloop()
    except Exception as e:
        print(f"Errore critico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()