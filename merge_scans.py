#!/usr/bin/env python3
"""
NTE Inventory Scanner - Scan Merger Utility
Combines multiple batch scan JSON files into a single master inventory JSON
for uploading to the NTE Database Optimizer.
"""

import sys
import os
import argparse

try:
    from core.merger import merge_inventory_files
except ImportError:
    # If run standalone outside the repo folder
    import json
    from datetime import datetime

    def make_item_signature(item, item_type="module"):
        if item_type == "module":
            shape = item.get("shape_type", "")
            level = item.get("level", 0)
            main_stats = tuple(sorted((k, str(v)) for k, v in item.get("mainStats", {}).items()))
            substats = tuple(sorted((s.get("name", ""), str(s.get("value", ""))) for s in item.get("substats", [])))
            return ("module", shape, level, main_stats, substats)
        else:
            name = item.get("name") or item.get("set_id") or item.get("cartridge_type") or ""
            level = item.get("level", 0)
            main_stat = str(item.get("main_stat", ""))
            main_stat_val = str(item.get("main_stat_value", ""))
            substats = tuple(sorted((s.get("name", ""), str(s.get("value", ""))) for s in item.get("substats", [])))
            return ("cartridge", name, level, main_stat, main_stat_val, substats)

    def merge_inventory_files(file_paths, output_path=None, deduplicate=True):
        merged_modules = []
        merged_cartridges = []
        seen_signatures = set()
        duplicates_skipped = 0
        files_merged = 0

        for path in file_paths:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            modules = data.get("modules", []) if isinstance(data, dict) else []
            cartridges = data.get("cartridges", []) if isinstance(data, dict) else []
            
            for mod in modules:
                sig = make_item_signature(mod, "module")
                if deduplicate and sig in seen_signatures:
                    duplicates_skipped += 1
                    continue
                seen_signatures.add(sig)
                merged_modules.append(dict(mod))

            for cart in cartridges:
                sig = make_item_signature(cart, "cartridge")
                if deduplicate and sig in seen_signatures:
                    duplicates_skipped += 1
                    continue
                seen_signatures.add(sig)
                merged_cartridges.append(dict(cart))

            files_merged += 1

        now_ts = int(datetime.utcnow().timestamp())
        for idx, mod in enumerate(merged_modules):
            mod["id"] = f"merged_mod_{now_ts}_{idx+1}"
        for idx, cart in enumerate(merged_cartridges):
            cart["id"] = f"merged_cart_{now_ts}_{idx+1}"

        payload = {
            "version": 1,
            "exportedAt": datetime.utcnow().isoformat() + "Z",
            "modules": merged_modules,
            "cartridges": merged_cartridges
        }

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)

        return {
            "payload": payload,
            "total_modules": len(merged_modules),
            "total_cartridges": len(merged_cartridges),
            "duplicates_skipped": duplicates_skipped,
            "files_merged": files_merged
        }


def run_gui():
    import tkinter as tk
    from tkinter import filedialog, messagebox

    root = tk.Tk()
    root.withdraw()  # Hide main window

    file_paths = filedialog.askopenfilenames(
        title="Select NTE Inventory JSON files to merge (Hold Ctrl to select multiple)",
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
        messagebox.showinfo(
            "Merge Successful",
            f"Successfully merged {results['files_merged']} scan files!\n\n"
            f"• Modules: {results['total_modules']}\n"
            f"• Cartridges: {results['total_cartridges']}\n"
            f"• Duplicate items skipped: {results['duplicates_skipped']}\n\n"
            f"Saved to:\n{output_path}\n\n"
            f"Ready for upload to the NTE Database Optimizer!"
        )
    except Exception as e:
        messagebox.showerror("Error", f"Failed to merge files:\n{e}")


def main():
    if len(sys.argv) == 1:
        # User double-clicked script or ran without arguments: launch interactive GUI dialogs
        run_gui()
    else:
        parser = argparse.ArgumentParser(
            description="Merge multiple NTE Inventory Scanner JSON files into one master file."
        )
        parser.add_argument(
            "files", 
            nargs="+", 
            help="Path to two or more scan JSON files to merge."
        )
        parser.add_argument(
            "-o", "--output", 
            default="master_inventory.json", 
            help="Output path for the combined JSON (default: master_inventory.json)"
        )
        parser.add_argument(
            "--no-dedup", 
            action="store_true", 
            help="Disable deduplication of identical items across scans."
        )

        args = parser.parse_args()

        print(f"Merging {len(args.files)} files into '{args.output}'...")
        try:
            results = merge_inventory_files(
                args.files, 
                output_path=args.output, 
                deduplicate=not args.no_dedup
            )
            print("✓ Merge complete!")
            print(f"  • Modules: {results['total_modules']}")
            print(f"  • Cartridges: {results['total_cartridges']}")
            print(f"  • Duplicates skipped: {results['duplicates_skipped']}")
            print(f"  • Output saved to: {args.output}")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)


if __name__ == "__main__":
    main()
