# client/ui/connection_dialog.py

import tkinter as tk
from tkinter import simpledialog

class ConnectionDialog(tk.Toplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("P2P Connection")
        self.geometry("300x150")
        self.result = None

        tk.Label(self, text="Choose Mode:").pack(pady=10)

        btn_host = tk.Button(self, text="Host (Wait for peer)", command=self.on_host)
        btn_host.pack(pady=5)

        btn_join = tk.Button(self, text="Join (Connect to peer)", command=self.on_join)
        btn_join.pack(pady=5)
        
        self.transient(parent)
        self.grab_set()
        self.wait_window()

    def on_host(self):
        # 詢問 Port
        port = simpledialog.askinteger("Host", "Listen Port:", initialvalue=6001, parent=self)
        if port:
            self.result = ("HOST", port)
            self.destroy()

    def on_join(self):
        # 詢問 IP:Port
        target = simpledialog.askstring("Join", "Target IP:Port", initialvalue="127.0.0.1:6001", parent=self)
        if target:
            try:
                ip, port = target.split(':')
                self.result = ("JOIN", ip, int(port))
                self.destroy()
            except:
                pass