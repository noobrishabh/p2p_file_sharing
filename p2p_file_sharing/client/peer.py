import tkinter as tk
from tkinter import messagebox, filedialog, ttk
import requests
import os
import socket
import threading
from pathlib import Path
import time

class PeerClient:
    def __init__(self, master):
        self.heartbeat_thread = None
        self.is_logged_in = False

        self.master = master
        master.title("P2P File Sharing")
        master.geometry("900x650")  # Increased window size for better layout
        master.resizable(True, True)

        # Set ttk theme
        style = ttk.Style()
        style.theme_use('clam')

        # Define new color palette
        self.colors = {
            'background': '#F0F4F8',
            'primary': '#A8DADC',
            'active': '#457B9D',
            'header': '#1D3557',
            'label': '#1D3557',
            'tree_bg': '#FFFFFF',
            'tree_selected': '#A8DADC',
            'progress': '#A8DADC'
        }

        # Custom Styles with Updated Colors and Text Styles
        style.configure('TNotebook', background=self.colors['background'])
        style.configure('TNotebook.Tab', background=self.colors['primary'], foreground=self.colors['label'],
                      padding=[15, 10], font=('Calibri', 11, 'bold'))
        style.map('TNotebook.Tab',
                  background=[('selected', self.colors['active'])],
                  foreground=[('selected', 'white')])

        style.configure('TButton', background=self.colors['primary'], foreground='white',
                      font=('Calibri', 11, 'bold'), borderwidth=0)
        style.map('TButton',
                  background=[('active', self.colors['active'])],
                  foreground=[('active', 'white')])

        style.configure('TLabel', foreground=self.colors['label'], font=('Calibri', 11))
        style.configure('Header.TLabel', font=('Arial', 24, 'bold'), foreground=self.colors['header'])
        style.configure('SubHeader.TLabel', font=('Calibri', 14, 'italic'), foreground=self.colors['label'])
        style.configure('Treeview', background=self.colors['tree_bg'], foreground=self.colors['label'],
                      fieldbackground=self.colors['tree_bg'], font=('Segoe UI', 10))
        style.configure('Treeview.Heading', background=self.colors['primary'], foreground='white',
                      font=('Segoe UI', 11, 'bold'))
        style.map('Treeview', background=[('selected', self.colors['tree_selected'])])
        style.configure('TEntry', fieldbackground='white', foreground=self.colors['label'], font=('Calibri', 11))

        style.configure('TProgressbar', troughcolor=self.colors['background'], background=self.colors['progress'])

        self.server_url = "http://10.38.12.8:5001"  # Update with your server's IP

        self.listening_port = self.find_free_port()
        self.ip = self.get_local_ip()

        self.setup_directories()
        self.setup_ui()
        self.username = None
        self.is_running = True
        self.server_thread = None
        self.port = 60000

    def find_free_port(self):
        """Find a free port to use for listening"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))  # Bind to any available port
            s.listen(1)
            port = s.getsockname()[1]
            return port

    def setup_directories(self):
        Path("downloads").mkdir(exist_ok=True)
        Path("shared_files").mkdir(exist_ok=True)

    def setup_ui(self):
        self.master.configure(bg=self.colors['background'])

        # Create Notebook for tabs
        self.notebook = ttk.Notebook(self.master)
        self.notebook.pack(expand=True, fill='both', padx=20, pady=20)

        # Login Tab
        self.login_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.login_tab, text='Login')

        # File Sharing Tab (initially disabled)
        self.files_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.files_tab, text='File Sharing')
        self.notebook.tab(1, state='disabled')

        self.setup_login_tab()
        self.setup_files_tab()

    def setup_login_tab(self):
        # Background Frame using tk.Frame for bg
        bg_frame = tk.Frame(self.login_tab, bg=self.colors['background'])
        bg_frame.place(relwidth=1, relheight=1)

        # Header
        header = ttk.Label(bg_frame, text="Welcome to P2P File Sharing", style='Header.TLabel', background=self.colors['background'])
        header.pack(pady=50)

        # Form Frame using tk.Frame for bg and padding
        form_frame = tk.Frame(bg_frame, padx=30, pady=30, bg=self.colors['background'])
        form_frame.pack(pady=10)

        ttk.Label(form_frame, text="Username:", style='TLabel', background=self.colors['background']).grid(row=0, column=0, padx=10, pady=15, sticky='e')
        self.username_entry = ttk.Entry(form_frame, width=35)
        self.username_entry.grid(row=0, column=1, padx=10, pady=15)

        ttk.Label(form_frame, text="Password:", style='TLabel', background=self.colors['background']).grid(row=1, column=0, padx=10, pady=15, sticky='e')
        self.password_entry = ttk.Entry(form_frame, show='*', width=35)
        self.password_entry.grid(row=1, column=1, padx=10, pady=15)

        # Buttons Frame using tk.Frame for bg
        buttons_frame = tk.Frame(form_frame, bg=self.colors['background'])
        buttons_frame.grid(row=2, column=0, columnspan=2, pady=30)

        login_button = ttk.Button(buttons_frame, text="Login", command=self.login, width=20)
        login_button.pack(side=tk.LEFT, padx=15)
        self.create_tooltip(login_button, "Click to log into your account")

        signup_button = ttk.Button(buttons_frame, text="Sign Up", command=self.signup, width=20)
        signup_button.pack(side=tk.LEFT, padx=15)
        self.create_tooltip(signup_button, "Click to create a new account")

    def setup_files_tab(self):
        # Background Frame using tk.Frame for bg
        bg_frame = tk.Frame(self.files_tab, bg=self.colors['background'])
        bg_frame.pack(expand=True, fill='both', padx=15, pady=15)

        # Toolbar Frame
        toolbar = ttk.Frame(bg_frame)
        toolbar.pack(fill=tk.X, pady=10)

        share_button = ttk.Button(toolbar, text="Share New File", command=self.add_shared_file)
        share_button.pack(side=tk.LEFT, padx=10)
        self.create_tooltip(share_button, "Select and share a new file with peers")

        refresh_button = ttk.Button(toolbar, text="Refresh Files", command=self.refresh_files)
        refresh_button.pack(side=tk.LEFT, padx=10)
        self.create_tooltip(refresh_button, "Refresh the list of available files")

        download_button = ttk.Button(toolbar, text="Download", command=self.download_file)
        download_button.pack(side=tk.LEFT, padx=10)
        self.create_tooltip(download_button, "Download the selected file")

        # Search Frame
        search_frame = ttk.Frame(bg_frame)
        search_frame.pack(fill=tk.X, pady=15)

        ttk.Label(search_frame, text="Filename:", style='TLabel', background=self.colors['background']).grid(row=0, column=0, padx=10, pady=10, sticky='e')
        self.search_filename_entry = ttk.Entry(search_frame, width=30)
        self.search_filename_entry.grid(row=0, column=1, padx=10, pady=10)

        ttk.Label(search_frame, text="Username:", style='TLabel', background=self.colors['background']).grid(row=0, column=2, padx=10, pady=10, sticky='e')
        self.search_username_entry = ttk.Entry(search_frame, width=30)
        self.search_username_entry.grid(row=0, column=3, padx=10, pady=10)

        search_button = ttk.Button(search_frame, text="Search", command=self.search_files)
        search_button.grid(row=0, column=4, padx=10, pady=10)
        self.create_tooltip(search_button, "Search for files based on filename and username")

        clear_button = ttk.Button(search_frame, text="Clear Search", command=self.clear_search)
        clear_button.grid(row=0, column=5, padx=10, pady=10)
        self.create_tooltip(clear_button, "Clear search fields and refresh the file list")

        # Treeview Frame
        tree_frame = ttk.Frame(bg_frame)
        tree_frame.pack(expand=True, fill=tk.BOTH, pady=10)

        columns = ("Filename", "Shared By", "IP", "Port")
        self.files_tree = ttk.Treeview(tree_frame, columns=columns, show='headings', selectmode='browse')
        self.files_tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH)

        # Define headings
        for col in columns:
            self.files_tree.heading(col, text=col)

        # Configure columns
        self.files_tree.column("Filename", width=300, anchor='center')
        self.files_tree.column("Shared By", width=200, anchor='center')
        self.files_tree.column("IP", width=200, anchor='center')
        self.files_tree.column("Port", width=100, anchor='center')

        # Add scrollbar
        scrollbar = ttk.Scrollbar(tree_frame, orient=tk.VERTICAL, command=self.files_tree.yview)
        self.files_tree.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Progress and Status Frame
        status_frame = tk.Frame(bg_frame, bg=self.colors['background'])
        status_frame.pack(fill=tk.X, pady=20)

        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(status_frame, variable=self.progress_var, maximum=100)
        self.progress_bar.pack(fill=tk.X, pady=10)

        self.status_label = ttk.Label(status_frame, text="", style='TLabel', background=self.colors['background'])
        self.status_label.pack()

        self.speed_label = ttk.Label(status_frame, text="Transfer Speed: 0 KB/s", style='TLabel', background=self.colors['background'])
        self.speed_label.pack()

    def create_tooltip(self, widget, text):
        """Create a tooltip for a given widget."""
        tooltip = Tooltip(widget, text)

    def get_local_ip(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            s.connect(('8.8.8.8', 80))
            ip = s.getsockname()[0]
        except Exception:
            ip = '127.0.0.1'
        finally:
            s.close()
        return ip

    def login(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return

        data = {
            'username': username,
            'password': password,
            'ip': self.ip,
            'port': self.listening_port
        }

        try:
            response = requests.post(f"{self.server_url}/login", json=data)
            if response.status_code == 200:
                self.username = username
                self.is_logged_in = True  # Set login status
                messagebox.showinfo("Success", "Login successful!")
                self.notebook.tab(1, state='normal')
                self.notebook.select(1)
                self.start_peer_server()
                self.start_heartbeat()  # Start heartbeat after successful login
                self.share_files()
                self.refresh_files()
            else:
                messagebox.showerror("Error", "Invalid credentials")
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Connection error: {str(e)}")

    def start_heartbeat(self):
        """Start the heartbeat thread"""
        self.heartbeat_thread = threading.Thread(target=self.send_heartbeat)
        self.heartbeat_thread.daemon = True
        self.heartbeat_thread.start()

    def send_heartbeat(self):
        """Send periodic heartbeat to server"""
        while self.is_running and self.is_logged_in:
            try:
                data = {
                    'username': self.username,
                    'ip': self.ip,
                    'port': self.listening_port
                }
                response = requests.post(f"{self.server_url}/heartbeat", json=data)
                if response.status_code != 200:
                    print(f"Heartbeat failed: {response.status_code}")
            except Exception as e:
                print(f"Heartbeat error: {str(e)}")
            time.sleep(30)  # Send heartbeat every 30 seconds

    def signup(self):
        username = self.username_entry.get()
        password = self.password_entry.get()

        if not username or not password:
            messagebox.showerror("Error", "Please enter both username and password")
            return

        data = {
            'username': username,
            'password': password,
            'ip': self.ip,
            'port': self.port
        }

        try:
            response = requests.post(f"{self.server_url}/register", json=data)
            if response.status_code == 200:
                messagebox.showinfo("Success", "Registration successful! Please login.")
            else:
                messagebox.showerror("Error", "Username already exists")
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Connection error: {str(e)}")

    def refresh_files(self):
        try:
            response = requests.get(f"{self.server_url}/files")
            if response.status_code == 200:
                files = response.json().get('files', [])
                for i in self.files_tree.get_children():
                    self.files_tree.delete(i)
                for file in files:
                    self.files_tree.insert('', 'end', values=(file[0], file[1], file[2], file[3]))
            else:
                messagebox.showerror("Error", "Failed to fetch files")
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to fetch files: {str(e)}")

    def search_files(self):
        filename_query = self.search_filename_entry.get().strip()
        username_query = self.search_username_entry.get().strip()

        params = {}
        if filename_query:
            params['filename'] = filename_query
        if username_query:
            params['username'] = username_query

        try:
            response = requests.get(f"{self.server_url}/search_files", params=params)
            if response.status_code == 200:
                files = response.json().get('files', [])
                for i in self.files_tree.get_children():
                    self.files_tree.delete(i)
                for file in files:
                    self.files_tree.insert('', 'end', values=(file[0], file[1], file[2], file[3]))
            else:
                messagebox.showerror("Error", "Failed to search files")
        except requests.RequestException as e:
            messagebox.showerror("Error", f"Failed to search files: {str(e)}")

    def clear_search(self):
        self.search_filename_entry.delete(0, tk.END)
        self.search_username_entry.delete(0, tk.END)
        self.refresh_files()

    def add_shared_file(self):
        filename = filedialog.askopenfilename()
        if filename:
            dest = Path("shared_files") / Path(filename).name
            try:
                with open(filename, 'rb') as src, open(dest, 'wb') as dst:
                    dst.write(src.read())
                self.share_files()
                self.refresh_files()
                messagebox.showinfo("Success", f"File '{Path(filename).name}' shared successfully!")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to share file: {str(e)}")

    def share_files(self):
        """Share files with the central server"""
        shared_dir = Path("shared_files")
        if not shared_dir.exists():
            shared_dir.mkdir()

        files = [f.name for f in shared_dir.glob('*') if f.is_file()]
        if files:
            data = {
                'username': self.username,
                'filename': files,
                'peer_ip': self.ip,
                'peer_port': self.listening_port  # Send our listening port
            }
            try:
                print(f"Sharing files with server. Our listening port: {self.listening_port}")
                response = requests.post(f"{self.server_url}/share_files", json=data)
                if response.status_code != 200:
                    messagebox.showerror("Error", "Failed to share files")
            except requests.RequestException as e:
                messagebox.showerror("Error", f"Failed to share files: {str(e)}")

    def download_file(self):
        selected_item = self.files_tree.selection()
        if not selected_item:
            messagebox.showinfo("Info", "Please select a file to download")
            return
        try:
            item = self.files_tree.item(selected_item)
            values = item['values']
            filename = values[0]
            peer_ip = values[2]
            peer_port = int(values[3])

            print(f"Attempting to connect to {peer_ip}:{peer_port} for file '{filename}'")  # Debug print

            # Start download in a separate thread
            thread = threading.Thread(target=self.transfer_file,
                                      args=(peer_ip, peer_port, filename))
            thread.start()
        except Exception as e:
            print(f"Error while parsing: {str(e)}")  # Debug print
            messagebox.showerror("Error", f"Failed to parse file information: {str(e)}")

    def transfer_file(self, peer_ip, peer_port, filename):
        """Download a file from another peer"""
        try:
            self.status_label.config(text="Connecting to peer...")
            self.progress_var.set(0)
            self.speed_label.config(text="Transfer Speed: 0 KB/s")  # Reset speed label

            print(f"Attempting to connect to {peer_ip}:{peer_port} for file '{filename}'")  # Debug print

            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(10)
                s.connect((peer_ip, peer_port))
                s.sendall(filename.encode())

                response = s.recv(1024).decode()
                if response == "FILE_NOT_FOUND":
                    raise Exception("File not found on peer")

                file_size = int(response)
                self.status_label.config(text="Downloading...")

                save_path = Path('downloads') / filename
                received = 0

                start_time = time.time()
                last_update_time = start_time
                bytes_since_last = 0

                with open(save_path, 'wb') as f:
                    while received < file_size:
                        chunk = s.recv(8192)
                        if not chunk:
                            break
                        f.write(chunk)
                        chunk_size = len(chunk)
                        received += chunk_size
                        bytes_since_last += chunk_size

                        # Update progress
                        progress = (received / file_size) * 100
                        self.progress_var.set(progress)

                        current_time = time.time()
                        elapsed_since_last = current_time - last_update_time

                        if elapsed_since_last >= 1:  # Update every second
                            speed = bytes_since_last / elapsed_since_last  # Bytes per second
                            speed_kb = speed / 1024  # Convert to KB/s
                            speed_str = f"Transfer Speed: {speed_kb:.2f} KB/s"

                            # Update the speed label in the main thread
                            self.master.after(0, lambda s=speed_str: self.speed_label.config(text=s))

                            # Reset counters
                            last_update_time = current_time
                            bytes_since_last = 0

                        # Update the UI
                        self.master.update_idletasks()

                self.status_label.config(text="Download complete!")
                self.speed_label.config(text="Transfer Speed: 0 KB/s")  # Reset speed after completion
                messagebox.showinfo("Success", f"File '{filename}' downloaded successfully!")

        except Exception as e:
            self.status_label.config(text="Download failed!")
            self.speed_label.config(text="Transfer Speed: 0 KB/s")  # Reset speed on failure
            messagebox.showerror("Error", f"Failed to download file: {str(e)}")
        finally:
            self.progress_var.set(0)

    def start_peer_server(self):
        self.server_thread = threading.Thread(target=self.run_peer_server)
        self.server_thread.daemon = True
        self.server_thread.start()

    def run_peer_server(self):
        """Server thread to receive files"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.bind((self.ip, self.listening_port))  # Use listening_port
        server_socket.listen(5)
        server_socket.settimeout(1)

        print(f"Listening for incoming files on port {self.listening_port}")

        while self.is_running:
            try:
                conn, addr = server_socket.accept()
                print(f"Received connection from {addr}")
                threading.Thread(target=self.handle_peer_connection,
                                 args=(conn, addr)).start()
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Server error: {str(e)}")
                break

        server_socket.close()

    def handle_peer_connection(self, conn, addr):
        try:
            filename = conn.recv(1024).decode()
            file_path = Path('shared_files') / filename

            if not file_path.exists():
                conn.sendall(b"FILE_NOT_FOUND")
                return

            file_size = file_path.stat().st_size
            conn.sendall(str(file_size).encode())

            with open(file_path, 'rb') as f:
                while True:
                    chunk = f.read(8192)
                    if not chunk:
                        break
                    conn.sendall(chunk)

        except Exception as e:
            print(f"Error in peer connection: {str(e)}")
        finally:
            conn.close()

    def cleanup(self):
        """Clean up resources before closing"""
        self.is_running = False
        self.is_logged_in = False

        # Send one final request to let server know we're disconnecting
        if self.username:
            try:
                data = {
                    'username': self.username,
                    'ip': self.ip,
                    'port': self.listening_port
                }
                requests.post(f"{self.server_url}/disconnect", json=data)
            except:
                pass

# Tooltip Class
class Tooltip:
    """
    It creates a tooltip for a given widget as the mouse goes on it.
    """

    def __init__(self, widget, text='widget info'):
        self.widget = widget
        self.text = text
        self.tooltip_window = None
        self.widget.bind("<Enter>", self.show_tooltip)
        self.widget.bind("<Leave>", self.hide_tooltip)

    def show_tooltip(self, event=None):
        """Display the tooltip"""
        if self.tooltip_window or not self.text:
            return
        x, y, cx, cy = self.widget.bbox("insert")
        x += self.widget.winfo_rootx() + 25
        y += self.widget.winfo_rooty() + 20
        self.tooltip_window = tw = tk.Toplevel(self.widget)
        tw.wm_overrideredirect(True)  # Remove all window decorations
        tw.wm_geometry(f"+{x}+{y}")
        label = tk.Label(tw, text=self.text, justify='left',
                         background="#FFFFE0", relief='solid', borderwidth=1,
                         font=("Calibri", 10))
        label.pack(ipadx=1)

    def hide_tooltip(self, event=None):
        """Hide the tooltip"""
        tw = self.tooltip_window
        self.tooltip_window = None
        if tw:
            tw.destroy()

# Modify the main block to handle cleanup
if __name__ == "__main__":
    root = tk.Tk()
    root.configure(bg='#F0F4F8')  # Match the updated background color
    client = PeerClient(root)

    def on_closing():
        client.cleanup()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()
