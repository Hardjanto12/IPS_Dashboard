import tkinter as tk
from tkinter import scrolledtext
import threading
import sys
import uvicorn
from main import app  # Import the FastAPI app

class RedirectText:
    def __init__(self, text_ctrl):
        self.output = text_ctrl

    def write(self, string):
        self.output.insert(tk.END, string)
        self.output.see(tk.END)

    def flush(self):
        pass

    def isatty(self):
        return False

class ServerApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Nuctech BPM API Server")
        self.root.geometry("600x400")
        self.root.configure(bg="#1e1e1e")
        
        self.server_thread = None
        self.is_running = False
        
        # Header
        header = tk.Frame(self.root, bg="#1e1e1e")
        header.pack(fill=tk.X, padx=10, pady=10)
        
        self.status_label = tk.Label(header, text="Status: STOPPED", fg="#ff3366", bg="#1e1e1e", font=("Helvetica", 14, "bold"))
        self.status_label.pack(side=tk.LEFT)
        
        self.btn_start = tk.Button(header, text="Start Server", bg="#00FF88", fg="black", font=("Helvetica", 10, "bold"), command=self.start_server)
        self.btn_start.pack(side=tk.RIGHT, padx=5)
        
        self.btn_stop = tk.Button(header, text="Stop Server", bg="#ff3366", fg="white", font=("Helvetica", 10, "bold"), state=tk.DISABLED, command=self.stop_server)
        self.btn_stop.pack(side=tk.RIGHT, padx=5)
        
        # Log Text Area
        log_frame = tk.Frame(self.root, bg="#2d2d2d")
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        self.log_area = scrolledtext.ScrolledText(log_frame, bg="#0d0d0d", fg="#00ff00", font=("Consolas", 10))
        self.log_area.pack(fill=tk.BOTH, expand=True)
        
        # Redirect stdout and stderr
        redir = RedirectText(self.log_area)
        sys.stdout = redir
        sys.stderr = redir
        
        print("BPM API Server Wrapper initialized.")
        print("Starting server automatically...")
        
        # Auto-start the server
        self.root.after(100, self.start_server)

    def run_uvicorn(self):
        config = uvicorn.Config(app, host="0.0.0.0", port=8000, log_config=None)
        self.server = uvicorn.Server(config)
        self.server.run()
        
    def start_server(self):
        if not self.is_running:
            self.is_running = True
            self.status_label.config(text="Status: RUNNING", fg="#00FF88")
            self.btn_start.config(state=tk.DISABLED)
            self.btn_stop.config(state=tk.NORMAL)
            
            print("Starting server on http://0.0.0.0:8000 ...")
            
            self.server_thread = threading.Thread(target=self.run_uvicorn, daemon=True)
            self.server_thread.start()

    def stop_server(self):
        if self.is_running:
            print("Stopping server...")
            if hasattr(self, 'server'):
                self.server.should_exit = True
            
            self.is_running = False
            self.status_label.config(text="Status: STOPPED", fg="#ff3366")
            self.btn_start.config(state=tk.NORMAL)
            self.btn_stop.config(state=tk.DISABLED)

if __name__ == "__main__":
    root = tk.Tk()
    app_win = ServerApp(root)
    
    # Handle window close
    def on_closing():
        if app_win.is_running:
            app_win.stop_server()
        root.destroy()
        
    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
