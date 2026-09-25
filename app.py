import threading
import time
import customtkinter as ctk
from tkinter import filedialog, messagebox
import mss
from core.capture import find_nte_window, get_window_client_rect, capture_screen_area
from core.detector import parse_module_card
from core.navigator import click_module_slot, scroll_page_down
from core.exporter import export_inventory_json
from core.merger import merge_inventory_files
import ctypes
import win32api
import win32con
import win32gui
import pydirectinput

def is_left_shift_pressed():
    return bool((win32api.GetAsyncKeyState(win32con.VK_LSHIFT) & 0x8000) or 
                (win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000))

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class NTEScannerApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("NTE Inventory Scanner")
        self.geometry("640x540")
        self.resizable(False, False)
        self.is_scanning = False
        self.scanned_modules = []
        self.scanned_cartridges = []
        self._build_ui()

    def _build_ui(self):
        self.header_frame = ctk.CTkFrame(self, corner_radius=4, fg_color="#101526", border_width=1, border_color="#2d3856", height=160)
        self.header_frame.pack(fill='both', padx=8, pady=4)

        self.title_label = ctk.CTkLabel(
            self.header_frame, 
            text="About:", 
            font=ctk.CTkFont(family="Consolas", size=15, weight="bold"),
            text_color="#00f3ff"
        )
        self.title_label.pack(anchor="w", padx=14, pady=(10, 2))

        self.subtitle_label = ctk.CTkLabel(
            self.header_frame,
            text="NTE Inventory Scanner is a non-invasive scanning tool that automatically takes screenshots of your Inventory\nand exports both Modules and Cartridges to JSON for the NTE Database site.",
            font=ctk.CTkFont(size=11),
            text_color="#9ca3af"
        )
        self.subtitle_label.pack(anchor="w", padx=14, pady=(0, 10))

        self.ctrl_frame = ctk.CTkFrame(self, corner_radius=4, fg_color="#161b2e")
        self.ctrl_frame.pack(fill="x", padx=8, pady=4)

        self.status_row = ctk.CTkFrame(self.ctrl_frame, fg_color="transparent")
        self.status_row.pack(fill="x", padx=14, pady=10)

        self.window_status_badge = ctk.CTkLabel(
            self.status_row,
            text="● GAME CLIENT: NOT DETECTED",
            font=ctk.CTkFont(family="Consolas", size=12, weight="bold"),
            text_color="#ef4444"
        )
        self.window_status_badge.pack(side="left")

        self.refresh_btn = ctk.CTkButton(
            self.status_row,
            text="Detect Window",
            width=110,
            height=28,
            fg_color="#1e293b",
            hover_color="#334155",
            command=self.check_game_window
        )
        self.refresh_btn.pack(side="right")

        self.options_frame = ctk.CTkFrame(self.ctrl_frame, fg_color="#0f1322", corner_radius=8)
        self.options_frame.pack(fill="x", padx=14, pady=(0, 12))

        self.item_count_label = ctk.CTkLabel(self.options_frame, text="Total Items to Scan:", font=ctk.CTkFont(size=12))
        self.item_count_label.pack(side="left", padx=12, pady=8)

        self.item_count_entry = ctk.CTkEntry(self.options_frame, width=70, height=28)
        self.item_count_entry.insert(0, "40")
        self.item_count_entry.pack(side="left", padx=6, pady=8)

        self.hint_label = ctk.CTkLabel(self.options_frame, text="<========= Scans both Modules & Cartridges", text_color="#4AF262", font=ctk.CTkFont(size=12))
        self.hint_label.pack(side="left", padx=12, pady=8)

        self.console_box = ctk.CTkTextbox(
            self, 
            height=40, 
            corner_radius=4, 
            fg_color="#090c16", 
            text_color="#34d399",
            font=ctk.CTkFont(family="Consolas", size=11)
        )
        self.console_box.pack(fill="both", expand=True, padx=8, pady=10)

        self.log("Ready. Please open Neverness to Everness on your inventory screen and click 'Detect Window'.")

        self.actions_row = ctk.CTkFrame(self, fg_color="transparent")
        self.actions_row.pack(fill="x", padx=16, pady=(0, 14))

        self.start_btn = ctk.CTkButton(
            self.actions_row,
            text="⚡ START SCAN",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            fg_color="#2563eb",
            hover_color="#1d4ed8",
            height=38,
            command=self.toggle_scan
        )
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.export_btn = ctk.CTkButton(
            self.actions_row,
            text="📥 EXPORT JSON",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            fg_color="#1e293b",
            hover_color="#334155",
            state="disabled",
            height=38,
            command=self.export_data
        )
        self.export_btn.pack(side="left", fill="x", expand=True, padx=4)

        self.merge_btn = ctk.CTkButton(
            self.actions_row,
            text="🔀 MERGE JSONs",
            font=ctk.CTkFont(family="Consolas", size=13, weight="bold"),
            fg_color="#0f766e",
            hover_color="#115e59",
            height=38,
            command=self.merge_data
        )
        self.merge_btn.pack(side="right", fill="x", expand=True, padx=(6, 0))

        self.after(500, self.check_game_window)

    def log(self, message):
        self.console_box.insert("end", f"[{time.strftime('%H:%M:%S')}] {message}\n")
        self.console_box.see("end")

    def check_game_window(self):
        hwnd = find_nte_window()
        if hwnd:
            rect = get_window_client_rect(hwnd)
            self.window_status_badge.configure(
                text=f"● GAME CLIENT FOUND ({rect['width']}x{rect['height']})",
                text_color="#10b981"
            )
            self.log(f"Detected game client at resolution: {rect['width']}x{rect['height']}")
            return hwnd
        else:
            self.window_status_badge.configure(
                text="● GAME CLIENT: NOT FOUND",
                text_color="#ef4444"
            )
            return None

    def toggle_scan(self):
        if self.is_scanning:
            self.is_scanning = False
            self.start_btn.configure(text="⚡ START SCAN", fg_color="#2563eb")
            self.log("Scan stopped by user.")
        else:
            hwnd = self.check_game_window()
            if not hwnd:
                messagebox.showerror("Error", "Could not find 'Neverness to Everness' window!\nPlease launch the game first.")
                return
            try:
                count = int(self.item_count_entry.get())
            except ValueError:
                count = 20
            self.is_scanning = True
            self.scanned_modules.clear()
            self.scanned_cartridges.clear()
            self.start_btn.configure(text="🛑 STOP SCAN", fg_color="#dc2626")
            self.export_btn.configure(state="disabled")
            threading.Thread(target=self._run_scan_thread, args=(hwnd, count), daemon=True).start()

    def _run_scan_thread(self, hwnd, total_count):
        self.log(f"Starting scan for {total_count} items in 3 seconds... Click into game!")
        time.sleep(3)

        # Focus the game window
        try:
            win32gui.SetForegroundWindow(hwnd)
            time.sleep(0.15)
        except Exception:
            pass

        def watch_for_abort():
            while self.is_scanning:
                if is_left_shift_pressed():
                    self.log("🛑 Emergency Left Shift detected! Aborting scan...")
                    self.is_scanning = False
                    break
                time.sleep(0.02)

        threading.Thread(target=watch_for_abort, daemon=True).start()

        try:
            with mss.mss() as sct:
                rect = get_window_client_rect(hwnd)
                card_rect = {
                    "left": int(rect["left"] + rect["width"] * 0.678),
                    "top": int(rect["top"] + rect["height"] * 0.145),
                    "width": int(rect["width"] * 0.278),
                    "height": int(rect["height"] * 0.730)
                }

                for i in range(total_count):
                    if not self.is_scanning:
                        break

                    if i > 0 and i % 28 == 0:
                        self.log(f"📜 Finished page! Scrolling down to page {(i // 28) + 1}...")
                        scroll_page_down(rect, num_rows=4)

                    if not self.is_scanning:
                        break

                    click_module_slot(rect, i)

                    if not self.is_scanning:
                        break

                    self.log(f"Scanning Item [{i+1}/{total_count}]... (Press Left Shift to abort)")
                    frame = capture_screen_area(sct, card_rect)
                    data = parse_module_card(frame)

                    if data:
                        if data.get("item_type") == "cartridge":
                            self.scanned_cartridges.append(data)
                            subs_str = ", ".join([f"{s['name']}: {s['value']}" for s in data.get('substats', [])])
                            self.log(f"✓ [Cartridge: {data['name']}] Lv.{data['level']} | Main: {data['main_stat']} ({data['main_stat_value']}) | Subs: [{subs_str}]")
                        else:
                            self.scanned_modules.append(data)
                            subs_str = ", ".join([f"{s['name']}: {s['value']}" for s in data.get('substats', [])])
                            self.log(f"✓ [Module: {data['shape_type']}] Lv.{data['level']} | Subs: [{subs_str}]")
                    else:
                        self.log("⚠ Could not detect item card, skipping...")

        except pydirectinput.FailSafeException:
            self.log("🛑 Mouse moved to corner (Failsafe triggered)! Aborting scan...")
        except Exception as err:
            self.log(f"❌ Error during scan: {err}")
        finally:
            self.is_scanning = False
            self.start_btn.configure(text="⚡ START SCAN", fg_color="#2563eb")
            total_scanned = len(self.scanned_modules) + len(self.scanned_cartridges)
            self.export_btn.configure(state="normal" if total_scanned > 0 else "disabled")
            self.log(f"🎉 Scan finished! Total items scanned: {len(self.scanned_modules)} Modules, {len(self.scanned_cartridges)} Cartridges.")

    def export_data(self):
        total_items = len(self.scanned_modules) + len(self.scanned_cartridges)
        if total_items == 0:
            messagebox.showinfo("Export", "No scanned items to export!")
            return

        file_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile="nte_inventory.json"
        )
        if file_path:
            export_inventory_json(self.scanned_modules, self.scanned_cartridges, file_path)
            self.log(f"✓ Exported inventory to: {file_path}")
            messagebox.showinfo(
                "Success", 
                f"Saved {len(self.scanned_modules)} Modules and {len(self.scanned_cartridges)} Cartridges!\n\nUpload this JSON on the NTE Database Optimizer page."
            )

    def merge_data(self):
        file_paths = filedialog.askopenfilenames(
            title="Select Scan JSON Files to Merge (Hold Ctrl to select multiple)",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        if not file_paths:
            return

        if len(file_paths) < 2:
            ans = messagebox.askyesno(
                "Notice",
                f"You only selected {len(file_paths)} file.\nDo you still want to proceed?"
            )
            if not ans:
                return

        output_path = filedialog.asksaveasfilename(
            title="Save Combined Master Inventory As...",
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile="master_inventory.json"
        )
        if not output_path:
            return

        try:
            results = merge_inventory_files(file_paths, output_path=output_path, deduplicate=True)
            self.log(f"🔀 Merged {results['files_merged']} files into: {output_path}")
            self.log(f"   ✓ Total Modules: {results['total_modules']}")
            self.log(f"   ✓ Total Cartridges: {results['total_cartridges']}")
            self.log(f"   ✓ Duplicates skipped: {results['duplicates_skipped']}")
            messagebox.showinfo(
                "Merge Success",
                f"Successfully merged {results['files_merged']} scan files!\n\n"
                f"• Modules: {results['total_modules']}\n"
                f"• Cartridges: {results['total_cartridges']}\n"
                f"• Duplicates skipped: {results['duplicates_skipped']}\n\n"
                f"Saved to:\n{output_path}\n\n"
                f"You can now upload this combined file to the NTE Database site!"
            )
        except Exception as e:
            self.log(f"❌ Error merging files: {e}")
            messagebox.showerror("Merge Error", f"Failed to merge files:\n{e}")

if __name__ == "__main__":
    app = NTEScannerApp()
    app.mainloop()
