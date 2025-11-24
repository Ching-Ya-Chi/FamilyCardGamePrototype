import tkinter as tk
from tkinter import messagebox
import socket, json
from src.common import protocol

SERVER_HOST = '127.0.0.1'
SERVER_PORT = 5000


def send_recv(msg: str) -> str:
    with socket.create_connection((SERVER_HOST, SERVER_PORT), timeout=5) as s:
        s.sendall((msg + '\n').encode('utf-8'))
        resp = s.recv(4096)
        return resp.decode().strip()


class LoginView(tk.Frame):
    def __init__(self, parent, controller):
        super().__init__(parent)
        self.controller = controller

        tk.Label(self, text='Username:').grid(row=0, column=0, sticky='e')
        self.entry_user = tk.Entry(self)
        self.entry_user.grid(row=0, column=1)

        tk.Label(self, text='Password:').grid(row=1, column=0, sticky='e')
        self.entry_pass = tk.Entry(self, show='*')
        self.entry_pass.grid(row=1, column=1)

        btn_login = tk.Button(self, text='Login', command=self.on_login)
        btn_login.grid(row=2, column=0, columnspan=2, pady=6)

    def on_login(self):
        username = self.entry_user.get().strip()
        password = self.entry_pass.get().strip()
        if not username or not password:
            messagebox.showwarning('Input', '請輸入帳號密碼')
            return
        msg = protocol.build_login_request(username, password)
        try:
            resp_raw = send_recv(msg)
            resp = json.loads(resp_raw)
            payload = resp.get('payload', {})
            if resp.get('action') == protocol.ACTION_LOGIN_RESPONSE and payload.get('ok'):
                # store user in controller
                self.controller.user['user_id'] = payload.get('user_id')
                self.controller.user['username'] = username
                self.controller.user['gold'] = payload.get('gold', 0)  # 補上這行
                self.controller.user['gems'] = payload.get('gems', 0)  # 補上這行
                messagebox.showinfo('登入成功', f"User ID: {payload.get('user_id')}, Gold: {payload.get('gold')}")
                self.controller.show_frame('LobbyView')
            else:
                messagebox.showerror('登入失敗', payload.get('error', 'unknown'))
        except Exception as e:
            messagebox.showerror('Network Error', str(e))
