#Checkout my other projects! https://github.com/Justagwas
#The OFFICIAL Repo of this is - https://github.com/Justagwas/Media-Downloader
import tkinter as tk
from tkinter import messagebox, ttk
from yt_dlp import YoutubeDL
import threading, os, sys, time, queue, logging, requests, shutil, zipfile, subprocess
from urllib.parse import urlparse
import ctypes as ct
from packaging.version import Version, InvalidVersion
from pathvalidate import sanitize_filename

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

import win32event, win32api, winerror

mutex = win32event.CreateMutex(None, False, "MediaDownloaderMutex")
if win32api.GetLastError() == winerror.ERROR_ALREADY_EXISTS:
    sys.exit()

class MediaDownloader:
    def __init__(self, root):
        self.root = root
        self.center_window(500, 340)
        self.root.title("Media Downloader v1.1.2 (IN DEVELOPMENT)")
        self.root.geometry("500x340")
        self.root.configure(bg="#313131")
        self.root.resizable(False, False)
        self.download_thread = None
        self.ydl = None
        self.status_queue = queue.Queue()
        self.progress_queue = queue.Queue()
        self.splash_frame = None
        self.main_frame = None
        self.progress = None
        self.console = None
        self.downloading = False
        self.status_polling = True
        self.status_poll_thread = threading.Thread(target=self.poll_status_queue, daemon=True)
        self.status_poll_thread.start()
        self.show_splash()
        self.root.after(100, self.deferred_startup)

    def center_window(self, width, height):
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = int((screen_width / 2) - (width / 2))
        y = int((screen_height / 2) - (height / 2))
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def show_splash(self):
        self.splash_frame = tk.Frame(self.root, bg="#313131")
        self.splash_frame.pack(fill="both", expand=True)
        label = tk.Label(self.splash_frame, text="Media Downloader", font=("Segoe UI", 18, "bold"), fg="#FFFFFF", bg="#313131")
        label.pack(pady=40)
        sub = tk.Label(self.splash_frame, text="Loading, please wait...", font=("Segoe UI", 12), fg="#FFFFFF", bg="#313131")
        sub.pack(pady=10)
        self.progress = ttk.Progressbar(self.splash_frame, mode="indeterminate", length=250, style="WhiteOnBlack.Horizontal.TProgressbar")
        self.progress.pack(pady=20)
        self.progress.start(10)

    def deferred_startup(self):

        def startup_tasks():
            self.set_icon()
            self.check_ffmpeg()
            self.check_for_updates()
            self.root.after(0, self.show_main_ui)
        threading.Thread(target=startup_tasks, daemon=True).start()

    def show_main_ui(self):
        if self.splash_frame:
            self.splash_frame.destroy()
        self.create_widgets()

    def set_icon(self):
        script_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
        icon_path = os.path.join(script_dir, "icon.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
                return
            except Exception as e:
                logging.error(f"Failed to set application icon: {e}")
        def is_admin():
            try: return ct.windll.shell32.IsUserAnAdmin()
            except: return False
        def run_as_admin():
            try:
                exe = os.path.abspath(sys.argv[0])
                params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
                ct.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{exe}" {params}', None, 1)
                os._exit(0)
            except Exception as e:
                logging.error(f"Failed to relaunch as admin: {e}")
                messagebox.showerror("Error", "Failed to request administrator privileges.")
                return False
        if messagebox.askyesno("Download Icon", "The application's icon is missing. Would you like to download and install it?"):
            if not is_admin():
                if not run_as_admin(): return
            try:
                icon_url = "https://github.com/Justagwas/Media-Downloader/raw/master/Media-Downloader/icon.ico"
                logging.info(f"Downloading icon from {icon_url} to {icon_path}")
                response = requests.get(icon_url, stream=True, timeout=10)
                with open(icon_path, "wb") as file:
                    for chunk in response.iter_content(chunk_size=1024):
                        if chunk: file.write(chunk)
                self.root.iconbitmap(icon_path)
            except Exception as e:
                logging.error(f"Failed to download or set application icon: {e}")
                messagebox.showerror("Error", "Failed to download or set the application's icon.")

    def check_ffmpeg(self):
        ffmpeg_path = os.path.join(os.path.dirname(__file__), "ffmpeg.exe")
        ffmpeg_installed = self.is_ffmpeg_installed()
        if not ffmpeg_installed and not os.path.exists(ffmpeg_path):
            self.prompt_ffmpeg_download()

    def is_ffmpeg_installed(self):
        try:
            startupinfo = None
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            result = subprocess.run([
                "ffmpeg", "-version"
            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, startupinfo=startupinfo)
            return result.returncode == 0
        except Exception:
            return False

    def prompt_ffmpeg_download(self):
        def on_confirm():
            if checkbox_var.get():
                self.clear_ffmpeg_prompt()
            else:
                messagebox.showerror("Error", "You must check the box to proceed.")

        def on_download_choice():
            for widget in self.root.winfo_children():
                widget.destroy()

            tk.Label(
                self.root,
                text="Choose how to download FFmpeg:",
                bg="#313131",
                fg="#FFFFFF",
                wraplength=420,
                font=("Segoe UI", 12, "bold"),
                justify="center"
            ).pack(pady=10)

            tk.Label(
                self.root,
                text="Automatic (Recommended): The application will download and install FFmpeg after you are introduced to the legal disclaimer.\n\n"
                     "Manual: Follow the steps to download and install FFmpeg yourself.",
                bg="#313131",
                fg="#FFFFFF",
                wraplength=420,
                justify="left",
                font=("Segoe UI", 10)
            ).pack(pady=10)

            button_frame = tk.Frame(self.root, bg="#313131")
            button_frame.pack(pady=10)

            auto_button = ttk.Button(
                button_frame, text="Automatic", command=show_legal_disclaimer, style="Custom.TButton"
            )
            auto_button.pack(side=tk.LEFT, padx=5)

            manual_button = ttk.Button(
                button_frame, text="Manual", command=show_manual_steps, style="Custom.TButton"
            )
            manual_button.pack(side=tk.LEFT, padx=5)

        def show_legal_disclaimer():
            def is_admin():
                try:
                    return ct.windll.shell32.IsUserAnAdmin()
                except:
                    return False

            def run_as_admin():
                try:
                    script = os.path.abspath(sys.argv[0])
                    params = " ".join([f'"{arg}"' for arg in sys.argv[1:]])
                    ct.windll.shell32.ShellExecuteW(None, "runas", sys.executable, f'"{script}" {params}', None, 1)
                    os._exit(0)
                except Exception as e:
                    logging.error(f"Failed to relaunch as admin: {e}")
                    messagebox.showerror("Error", "Failed to request administrator privileges.")
                    return False

            if not is_admin():
                if messagebox.askyesno(
                    "Admin Permission Required",
                    "This action requires administrator privileges. Would you like to restart the application as an administrator?"
                ):
                    if not run_as_admin():
                        return
                else:
                    return

            for widget in self.root.winfo_children():
                widget.destroy()

            tk.Label(
                self.root,
                text="Legal Disclaimer:",
                bg="#313131",
                fg="#FFFFFF",
                font=("Segoe UI", 12, "bold"),
                justify="center"
            ).pack(pady=10)

            tk.Label(
                self.root,
                text="By proceeding, you acknowledge that FFmpeg is a third-party software.\n\n"
                     "The application will download FFmpeg from an official Windows build.\n\n"
                     "FFmpeg is licensed under the GNU Lesser General Public License (LGPL) version 2.1 or later.\n"
                     "For more details, visit:",
                bg="#313131",
                fg="#FFFFFF",
                wraplength=420,
                justify="left",
                font=("Segoe UI", 10)
            ).pack(pady=0)
            link = tk.Label(
                self.root,
                text="https://ffmpeg.org/legal.html",
                bg="#313131",
                fg="blue",
                cursor="hand2",
                wraplength=220,
                justify="left",
                anchor="w",
                font=("Segoe UI", 10, "underline")
            )
            link.pack(pady=5, padx=38, anchor="w")
            link.bind("<Button-1>", lambda e: os.startfile("https://ffmpeg.org/legal.html"))

            button_frame = tk.Frame(self.root, bg="#313131")
            button_frame.pack(pady=10)

            self.proceed_button = ttk.Button(
                button_frame, text="Proceed", style="Custom.TButton", command=lambda: [self.proceed_button.config(state=tk.DISABLED), on_download()]
            )
            self.proceed_button.pack(side=tk.LEFT, padx=5)

            cancel_button = ttk.Button(
                button_frame, text="Cancel", command=self.abort, style="Custom.TButton"
            )
            cancel_button.pack(side=tk.LEFT, padx=5)

        def show_manual_steps():
            for widget in self.root.winfo_children():
                widget.destroy()

            tk.Label(
                self.root,
                text="Manual Download Steps:",
                bg="#313131",
                fg="#FFFFFF",
                font=("Segoe UI", 12, "bold"),
                justify="center"
            ).pack(pady=10)

            tk.Label(
                self.root,
                text="1. Visit the official FFmpeg build page:",
                bg="#313131",
                fg="#FFFFFF",
                wraplength=420,
                justify="left",
                font=("Segoe UI", 10)
            ).pack(pady=0, padx=50, anchor="w")

            link = tk.Label(
                self.root,
                text="https://github.com/GyanD/codexffmpeg/releases/latest",
                bg="#313131",
                fg="blue",
                cursor="hand2",
                wraplength=420,
                justify="left",
                anchor="w",
                font=("Segoe UI", 10, "underline")
            )
            link.pack(pady=0, padx=50, anchor="w")
            link.bind("<Button-1>", lambda e: os.startfile("https://github.com/GyanD/codexffmpeg/releases/latest"))

            tk.Label(
                self.root,
                text="2. Download the file named 'ffmpeg-x.x.x-essentials_build.zip'.\n"
                     "3. Extract the downloaded ZIP file.\n"
                     "4. Locate the 'ffmpeg.exe' file within the extracted folder and its subfolders.\n"
                     "5. Move the 'ffmpeg.exe' file to the same directory as this application.",
                bg="#313131",
                fg="#FFFFFF",
                wraplength=420,
                justify="left",
                font=("Segoe UI", 10)
            ).pack(pady=5)

            tk.Label(
                self.root,
                text="Once you have completed these steps, restart the application.",
                bg="#313131",
                fg="#FFFFFF",
                wraplength=420,
                justify="left",
                font=("Segoe UI", 10, "italic")
            ).pack(pady=10)

            ok_button = ttk.Button(
                self.root, text="OK", command=self.abort, style="Custom.TButton"
            )
            ok_button.pack(pady=10)

        def on_download():
            def download_ffmpeg():
                try:
                    self.set_status("Downloading FFmpeg... (DO NOT CLOSE APPLICATION)")
                    download_url = "https://github.com/GyanD/codexffmpeg/releases/download/7.1.1/ffmpeg-7.1.1-essentials_build.zip"
                    script_dir = os.path.dirname(os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__))
                    download_path = os.path.join(script_dir, "ffmpeg-essentials.zip")
                    extract_path = os.path.join(script_dir, "ffmpeg_temp")

                    logging.info(f"Downloading FFmpeg from {download_url} to {download_path}")
                    response = requests.get(download_url, stream=True)
                    with open(download_path, "wb") as file:
                        for chunk in response.iter_content(chunk_size=1024):
                            if chunk:
                                file.write(chunk)

                    self.set_status("Extracting FFmpeg...")
                    logging.info(f"Extracting FFmpeg to {extract_path}")
                    os.makedirs(extract_path, exist_ok=True)
                    with zipfile.ZipFile(download_path, 'r') as zip_ref:
                        zip_ref.extractall(extract_path)

                    bin_folder = next(
                        (os.path.join(root, "ffmpeg.exe") for root, _, files in os.walk(extract_path) if "ffmpeg.exe" in files),
                        None
                    )
                    if bin_folder:
                        shutil.copy(bin_folder, script_dir)
                        logging.info(f"Copied ffmpeg.exe to {script_dir}")

                    os.remove(download_path)
                    shutil.rmtree(extract_path)

                    self.set_status("FFmpeg installed successfully!")
                    self.root.after(0, lambda: messagebox.showinfo("Success", "FFmpeg has been installed successfully."))
                    self.root.after(0, self.clear_ffmpeg_prompt)
                except Exception as e:
                    self.set_status("FFmpeg installation failed.")
                    self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to download and install FFmpeg: {e}"))
            threading.Thread(target=download_ffmpeg, daemon=True).start()

        for widget in self.root.winfo_children():
            widget.destroy()
        message = (
            "The FFmpeg framework, which is essential for this application to function, is missing from your system.\n\n"
            "Without this dependency, the application will not work.\n\n"
            "Would you like to download and install FFmpeg now?"
        )
        tk.Label(self.root, text=message, bg="#313131", fg="#FFFFFF", wraplength=420, justify="left", font=("Segoe UI", 10)).pack(pady=10)

        button_frame = tk.Frame(self.root, bg="#313131")
        button_frame.pack(pady=10)

        proceed_button = ttk.Button(button_frame, text="Yes", command=on_download_choice, style="Custom.TButton")
        proceed_button.pack(side=tk.LEFT, padx=5)

        confirm_button = ttk.Button(button_frame, text="Cancel", command=on_confirm, style="Custom.TButton")
        confirm_button.pack(side=tk.LEFT, padx=5)

        checkbox_var = tk.BooleanVar()
        checkbox = tk.Checkbutton(
            self.root,
            text="I understand that this application might not work without it and don't want to proceed.",
            variable=checkbox_var,
            bg="#313131",
            fg="#FFFFFF",
            selectcolor="#232323",
            activebackground="#313131",
            activeforeground="#FFFFFF",
            wraplength=420,
            justify="left",
            font=("Segoe UI", 9)
        )
        checkbox.pack(pady=5)

        tk.Label(self.root, text='\n\n\n\n\n\n\n\n\n\n\n\n\n', bg="#313131", fg="#FFFFFF", wraplength=420, justify="left", font=("Segoe UI", 10)).pack(pady=10)

    def clear_ffmpeg_prompt(self):
        for widget in self.root.winfo_children():
            widget.destroy()
        self.create_widgets()

    def create_widgets(self):
        self.main_frame = tk.Frame(self.root, bg="#313131")
        self.main_frame.pack(fill="both", expand=True, padx=10, pady=10)

        url_frame = tk.Frame(self.main_frame, bg="#313131")
        url_frame.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        url_label = tk.Label(url_frame, text="URL:", bg="#313131", fg="#FFFFFF", font=("Segoe UI", 11, "bold"))
        url_label.pack(side=tk.LEFT, padx=(0, 6))
        self.url_entry = ttk.Entry(url_frame, width=38)
        self.url_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.paste_button = ttk.Button(url_frame, text="Paste", command=self.paste_url, style="Custom.TButton" )
        self.paste_button.pack(side=tk.LEFT, padx=(6, 0))

        dropdown_frame = tk.Frame(self.main_frame, bg="#313131")
        dropdown_frame.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        dropdown_frame.columnconfigure(0, weight=1)
        dropdown_frame.columnconfigure(1, weight=1)

        self.format_var = tk.StringVar(value="Format: mp4 (Video&Audio)")
        self.format_options = [
            "Format: mp4 (Video&Audio)",
            "Format: mp3 (Audio)",
            "Format: mov (Video&Audio)",
            "Format: wav (Audio)"
        ]
        self.format_dropdown = ttk.Combobox(
            dropdown_frame,
            textvariable=self.format_var,
            values=self.format_options,
            state="readonly",
            style="WhiteOnBlack.TCombobox"
        )
        self.format_dropdown.grid(row=0, column=0, sticky="ew", padx=(0, 12), ipadx=0, ipady=6)
        def clear_format_selection(event):
            self.root.after(10, lambda: self.format_dropdown.selection_clear())
        def on_format_selected(event):
            selected = self.format_var.get()
            fmt = selected.replace("Format: ", "")
            self.prompt_format_confirmation(fmt)
            clear_format_selection(event)
            if fmt.startswith("mp3") or fmt.startswith("wav"):
                self.quality_var.set("Quality: BEST QUALITY")
                self.quality_dropdown.config(state="disabled")
            else:
                self.quality_dropdown.config(state="readonly")
        self.format_dropdown.bind("<<ComboboxSelected>>", on_format_selected)
        self.format_dropdown.bind("<FocusIn>", lambda e: self.format_dropdown.selection_clear())
        self.quality_var = tk.StringVar(value="Quality: BEST QUALITY")
        self.quality_options = [
            "Quality: BEST QUALITY",
            "Quality: 144p",
            "Quality: 240p",
            "Quality: 360p",
            "Quality: 480p",
            "Quality: 720p",
            "Quality: 1080p",
            "Quality: 1440p",
            "Quality: 2160p (4k)"
        ]
        self.quality_dropdown = ttk.Combobox(
            dropdown_frame,
            textvariable=self.quality_var,
            values=self.quality_options,
            state="readonly",
            style="WhiteOnBlack.TCombobox"
        )
        self.quality_dropdown.grid(row=0, column=1, sticky="ew", padx=(12, 0), ipadx=0, ipady=6)
        def clear_quality_selection(event):
            self.root.after(10, lambda: self.quality_dropdown.selection_clear())
        def on_quality_selected(event):
            qual = self.quality_var.get().replace("Quality: ", "")
            self.prompt_quality_change(qual)
            clear_quality_selection(event)
        self.quality_dropdown.bind("<<ComboboxSelected>>", on_quality_selected)
        self.quality_dropdown.bind("<FocusIn>", lambda e: self.quality_dropdown.selection_clear())

        button_frame = tk.Frame(self.main_frame, bg="#313131")
        button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 8))
        button_frame.columnconfigure(0, weight=1)
        button_frame.columnconfigure(1, weight=1)
        self.download_button = ttk.Button(button_frame, text="Download", command=self.start_download, style="Custom.TButton")
        self.download_button.grid(row=0, column=0, sticky="ew", padx=(0, 8), ipadx=0, ipady=6)
        self.abort_button = ttk.Button(button_frame, text="Terminate", command=self.abort, style="Custom.TButton")
        self.abort_button.grid(row=0, column=1, sticky="ew", ipadx=0, ipady=6)

        self.console = tk.Text(self.main_frame, height=5, bg="#232323", fg="#FFFFFF", insertbackground="#FFFFFF", state="disabled", wrap="word", font=("Consolas", 10))
        self.console.grid(row=3, column=0, columnspan=2, sticky="nsew", pady=(8, 0))

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        self.main_frame.rowconfigure(3, weight=1)

    def paste_url(self):
        try:
            self.url_entry.delete(0, tk.END)
            self.url_entry.insert(0, self.root.clipboard_get())
        except tk.TclError:
            messagebox.showerror("Error", "No URL found in clipboard")


    def sanitize_filename(self, name):
        return sanitize_filename(name).strip()


    def sanitize_url(self, url):
        return url if urlparse(url).netloc else None


    def prompt_quality_change(self, selected_quality):
        if selected_quality != "BEST QUALITY" and not messagebox.askyesno(
            "Quality Format Change",
            "The provided media URL might not support other formats. Do you want to proceed?"):
            self.quality_var.set("Quality: BEST QUALITY")


    def prompt_format_confirmation(self, selected_format):
        if selected_format.startswith("mp4") or selected_format.startswith("mp3"): return
        if not messagebox.askyesno(
            "Format Download Warning",
            "Downloading this format (MOV/WAV) may take significantly longer than MP4/MP3.\nDo you want to continue?"):
            self.format_var.set("Format: mp4 (Video&Audio)")

    def start_download(self):
        if self.console:
            self.console.config(state="normal")
            self.console.delete(1.0, tk.END)
            self.console.config(state="disabled")

        url = self.url_entry.get()
        if not url:
            messagebox.showerror("Error", "Please enter a media URL")
            return

        sanitized_url = self.sanitize_url(url)
        if not sanitized_url:
            messagebox.showerror("Error", "Please enter a valid media URL")
            return
        format_map = {
            "mp4": "mp4",
            "mp3": "mp3",
            "mov": "mov",
            "wav": "wav"
        }
        format_value = self.format_var.get()
        format_choice = None
        for fmt in format_map:
            if fmt in format_value:
                format_choice = fmt
                break
        if not format_choice:
            messagebox.showerror("Error", "Please select a format")
            return

        quality_value = self.quality_var.get()
        if quality_value.startswith("Quality: "):
            quality_choice = quality_value.replace("Quality: ", "")
        else:
            quality_choice = quality_value
        if quality_choice == "Select Quality":
            messagebox.showerror("Error", "Please select a quality")
            return
        self.download_button.config(state=tk.DISABLED)
        self.downloading = True
        self.poll_progress_queue()
        def check_and_download():
            downloads_dir = os.path.expanduser('~/Downloads')
            media_dl_dir = os.path.join(downloads_dir, 'Media-Downloader')
            os.makedirs(media_dl_dir, exist_ok=True)
            try:
                ydl_opts = {
                    'quiet': True,
                    'skip_download': True,
                    'no_warnings': True,
                    'simulate': True,
                }
                with YoutubeDL(ydl_opts) as ydl:
                    info_dict = ydl.extract_info(sanitized_url, download=False)
                title = info_dict.get('title', '')
                sanitized_title = self.sanitize_filename(title)
                sanitized_title = ''.join(c for c in sanitized_title if c.isalnum() or c in (' ', '.', '_', '-')).strip()
                if not sanitized_title:
                    sanitized_title = 'media_file'
                final_filename = f"{sanitized_title}.{format_choice}"
                output_path_final = os.path.join(media_dl_dir, final_filename)
                if os.path.exists(output_path_final):
                    self.append_console(f"File already exists: {output_path_final}\n")
                    def ask_redownload():
                        if messagebox.askyesno("File Exists", f"File already exists:\n{output_path_final}\nDo you want to download it again?"):
                            self.download_thread = threading.Thread(target=self.download_video, args=(sanitized_url, format_choice, quality_choice, sanitized_title))
                            self.download_thread.start()
                        else:
                            self.download_button.config(state=tk.NORMAL)
                    self.root.after(0, ask_redownload)
                    return
            except Exception as e:
                self.append_console("Failed to retrieve media info!\n")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to retrieve media info: {e}"))
                self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))
                return
            self.download_thread = threading.Thread(target=self.download_video, args=(sanitized_url, format_choice, quality_choice, sanitized_title))
            self.download_thread.start()

        threading.Thread(target=check_and_download, daemon=True).start()


    def abort(self):
        if self.ydl:
            self.ydl.download = False
            self.append_console("Download aborted!\n")
        try:
            import subprocess
            subprocess.run(["taskkill", "/F", "/IM", "ffmpeg.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass
        self.terminate_program()

    def terminate_program(self):
        self.status_polling = False
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    def download_video(self, url, format_choice, quality_choice, sanitized_title=None):
        self.append_console("Starting download...\n")
        downloads_dir = os.path.expanduser('~/Downloads')
        media_dl_dir = os.path.join(downloads_dir, 'Media-Downloader')
        os.makedirs(media_dl_dir, exist_ok=True)
        if sanitized_title is None:
            try:
                with YoutubeDL({'quiet': True, 'skip_download': True}) as ydl:
                    info_dict = ydl.extract_info(url, download=False)
                title = info_dict.get('title', '')
                sanitized_title = self.sanitize_filename(title)
                sanitized_title = ''.join(c for c in sanitized_title if c.isalnum() or c in (' ', '.', '_', '-')).strip()
                if not sanitized_title:
                    sanitized_title = 'media_file'
            except Exception as e:
                self.append_console("Failed to retrieve media info!\n")
                self.root.after(0, lambda: messagebox.showerror("Error", f"Failed to retrieve media info: {e}"))
                self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))
                return

        final_filename = f"{sanitized_title}.{format_choice}"
        output_path_final = os.path.join(media_dl_dir, final_filename)
        output_template = os.path.join(media_dl_dir, f'{sanitized_title}_TEMP.%(ext)s')

        quality_format = {
            "BEST QUALITY": "bestvideo+bestaudio/best",
            "144p": "worstvideo[height<=144]+bestaudio/best[height<=144]",
            "240p": "worstvideo[height<=240]+bestaudio/best[height<=240]",
            "360p": "worstvideo[height<=360]+bestaudio/best[height<=360]",
            "480p": "worstvideo[height<=480]+bestaudio/best[height<=480]",
            "720p": "bestvideo[height<=720]+bestaudio/best[height<=720]",
            "1080p": "bestvideo[height<=1080]+bestaudio/best[height<=1080]",
            "1440p": "bestvideo[height<=1440]+bestaudio/best[height<=1440]",
            "2160p (4k)": "bestvideo[height<=2160]+bestaudio/best[height<=2160]",
        }

        if format_choice in ['mp3', 'wav']:
            ydl_opts = {
                'format': 'bestaudio/best',
                'outtmpl': output_template,
                'progress_hooks': [self.ydl_hook],
                'postprocessors': [{
                    'key': 'FFmpegExtractAudio',
                    'preferredcodec': format_choice,
                    'preferredquality': '0',
                }],
                'concurrent_fragment_downloads': 8,
                'external_downloader_args': {
                    'aria2c': ['-x', '16', '-j', '16']
                },
                'external_downloader': 'aria2c',
                'quiet': True,
            }
        else:
            ydl_opts = {
                'format': quality_format.get(quality_choice, 'best'),
                'outtmpl': output_template,
                'progress_hooks': [self.ydl_hook],
                'postprocessors': [{
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mov',
                    'ffmpeg_args': ['-preset', 'ultrafast'],
                }] if format_choice == 'mov' else [],
                'concurrent_fragment_downloads': 8,
                'external_downloader_args': {
                    'aria2c': ['-x', '16', '-j', '16']
                },
                'external_downloader': 'aria2c',
                'quiet': True,
            }

        start_time = time.time()
        with YoutubeDL(ydl_opts) as ydl:
            self.ydl = ydl
            try:
                ydl.download([url])
                if ydl_opts.get('postprocessors'):
                    self.set_status("Converting... Please wait.")
                self.display_percent_in_console(100)
                temp_files = [f for f in os.listdir(media_dl_dir) if f.startswith(sanitized_title) and '_TEMP.' in f]
                for temp_file in temp_files:
                    temp_path = os.path.join(media_dl_dir, temp_file)
                    final_path = os.path.join(media_dl_dir, final_filename)
                    if os.path.exists(final_path):
                        try:
                            os.remove(final_path)
                        except Exception:
                            pass
                    os.rename(temp_path, final_path)
                elapsed = time.time() - start_time
                file_size = os.path.getsize(output_path_final) if os.path.exists(output_path_final) else 0
                size_mb = file_size / (1024 * 1024)
                self.append_console(f"Download completed successfully!\nSaved as: {output_path_final}\nFile size: {size_mb:.2f} MB\nTime taken: {elapsed:.2f} seconds\n")
            except Exception as e:
                if 'abort' in str(e).lower():
                    self.append_console("Download aborted!\n")
                else:
                    self.append_console("Download failed!\n")
                    self.root.after(0, lambda: messagebox.showerror("Error", str(e)))
            finally:
                self.downloading = False
                self.root.after(0, lambda: self.download_button.config(state=tk.NORMAL))

    def ydl_hook(self, d):
        if d['status'] == 'downloading':
            try:
                percent_str = d.get('_percent_str', '').strip()
                percent = percent_str.split('%')[0].strip()[-4:]
                try:
                    val = float(percent)
                except Exception:
                    val = 0
                self.progress_queue.put(val)
            except Exception:
                self.progress_queue.put(0)
        elif d['status'] == 'finished':
            self.progress_queue.put(100)
    def set(self):
        hwnd = ct.windll.user32.GetParent(self.root.winfo_id())
        value = ct.c_int(2)
        ct.windll.dwmapi.DwmSetWindowAttribute(hwnd, 20, ct.byref(value), ct.sizeof(value))

    def check_for_updates(self):
        def update_check():
            try:
                current_version = "v1.1.1"
                releases_url = "https://api.github.com/repos/Justagwas/Media-Downloader/releases/latest"
                response = requests.get(releases_url, timeout=10)
                if response.status_code == 200:
                    latest_release = response.json()
                    latest_version = latest_release.get("tag_name", "")
                    try:
                        if Version(latest_version) > Version(current_version):
                            download_url = "https://github.com/Justagwas/Media-Downloader/releases/latest/download/Media_Downloader_Setup.exe"
                            prompt_message = (
                                f"A newer version - {latest_version} is available!\n"
                                f"Would you like to download it now?"
                            )
                            if messagebox.askyesno("Update Available", prompt_message):
                                os.startfile(download_url)
                                self.abort()
                    except InvalidVersion:
                        logging.error(f"Invalid version format: {latest_version}")
                else:
                    logging.error(f"Failed to fetch release info: HTTP {response.status_code}")
            except requests.RequestException as e:
                logging.error(f"Network error during update check: {e}")
                messagebox.showerror("Update Check Failed", "Unable to check for updates. Please try again later.")

        threading.Thread(target=update_check, daemon=True).start()

    def poll_status_queue(self):
        while self.status_polling:
            try:
                while True:
                    msg = self.status_queue.get_nowait()
                    self.append_console(msg + "\n")
            except queue.Empty:
                pass
            time.sleep(0.1)

    def poll_progress_queue(self):
        if not self.downloading:
            return
        try:
            while True:
                val = self.progress_queue.get_nowait()
                self.display_percent_in_console(val)
        except queue.Empty:
            pass
        if self.downloading:
            self.root.after(100, self.poll_progress_queue)

    def terminate_program(self):
        self.status_polling = False
        try:
            self.root.destroy()
        except Exception:
            pass
        os._exit(0)

    def set_status(self, msg):
        self.status_queue.put(msg)

    def append_console(self, msg):
        if self.console:
            self.console.config(state="normal")
            self.console.insert(tk.END, msg)
            self.console.see(tk.END)
            self.console.config(state="disabled")

    def display_percent_in_console(self, percent):
        if self.console:
            self.console.config(state="normal")
            content = self.console.get("1.0", tk.END)
            lines = content.rstrip("\n").split("\n")
            if percent == 100:
                if lines and lines[-1].strip().endswith("% Done"):
                    lines = lines[:-1]
                lines.append("Process finished.")
            else:
                percent_line = f"{percent}% Done"
                if lines and lines[-1].strip().endswith("% Done"):
                    lines = lines[:-1]
                lines.append(percent_line)
            self.console.delete("1.0", tk.END)
            self.console.insert(tk.END, "\n".join(lines) + ("\n" if lines else ""))
            self.console.see(tk.END)
            self.console.config(state="disabled")

if __name__ == "__main__":
    root = tk.Tk()
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background="#313131")
    style.configure("TLabel", background="#313131", foreground="#FFFFFF")
    style.configure("Custom.TButton", background="#232323", foreground="#FFFFFF", borderwidth=1, focusthickness=2, focuscolor="#FFFFFF")
    style.map("Custom.TButton",
        background=[('active', '#444444'), ('!active', '#232323')],
        foreground=[('active', '#FFFFFF'), ('!active', '#FFFFFF')],
        relief=[('pressed', 'sunken'), ('!pressed', 'raised')],
    )
    style.configure("WhiteOnBlack.TCombobox", fieldbackground="#313131", background="#313131", foreground="#FFFFFF", selectforeground="#FFFFFF", selectbackground="#222222", arrowcolor="#FFFFFF", bordercolor="#FFFFFF")
    style.map("WhiteOnBlack.TCombobox",
        fieldbackground=[('readonly', '#313131')],
        background=[('readonly', '#313131')],
        foreground=[('readonly', '#FFFFFF')],
        selectbackground=[('readonly', '#222222')],
        selectforeground=[('readonly', '#FFFFFF')],
        arrowcolor=[('readonly', '#FFFFFF')],
    )
    app = MediaDownloader(root)
    root.mainloop()