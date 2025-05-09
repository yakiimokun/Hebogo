from tkinter import Tk
from src import GoGameApp

if __name__ == "__main__":
    root = Tk()
    app = GoGameApp(root, board_size=9, komi=0)
    root.mainloop()