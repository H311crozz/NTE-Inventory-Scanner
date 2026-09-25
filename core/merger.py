import json
from datetime import datetime

def make_item_signature(item, item_type="module"):
    """
    Creates a hashable signature representing the item's rolled stats
    to detect duplicate items scanned across multiple batches.
    """
    if item_type == "module":
        shape = item.get("shape_type", "")
        level = item.get("level", 0)
        main_stats = tuple(sorted((k, str(v)) for k, v in item.get("mainStats", {}).items()))
        substats = tuple(sorted(
            (s.get("name", ""), str(s.get("value", ""))) 
            for s in item.get("substats", [])
        ))
        return ("module", shape, level, main_stats, substats)
    else:
        name = item.get("name") or item.get("set_id") or item.get("cartridge_type") or ""
        level = item.get("level", 0)
        main_stat = str(item.get("main_stat", ""))
        main_stat_val = str(item.get("main_stat_value", ""))
        substats = tuple(sorted(
            (s.get("name", ""), str(s.get("value", ""))) 
            for s in item.get("substats", [])
        ))
        return ("cartridge", name, level, main_stat, main_stat_val, substats)


def merge_inventory_files(file_paths, output_path=None, deduplicate=True):
    """
    Merges multiple NTE Inventory JSON files into a single unified inventory.

    Args:
        file_paths: List of file paths to JSON files.
        output_path: Optional path to save merged JSON. If None, won't write to disk.
        deduplicate: If True, skips identical items found across multiple scans.

    Returns:
        dict with:
            - "payload": The combined JSON payload.
            - "total_modules": Count of modules in merged result.
            - "total_cartridges": Count of cartridges in merged result.
            - "duplicates_skipped": Count of duplicate items omitted.
            - "files_merged": Number of files successfully processed.
    """
    merged_modules = []
    merged_cartridges = []
    seen_signatures = set()
    duplicates_skipped = 0
    files_merged = 0

    for path in file_paths:
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"Failed to read '{path}': {e}")

        # Support both standard export dict format and raw lists
        modules = []
        cartridges = []
        if isinstance(data, dict):
            modules = data.get("modules", [])
            cartridges = data.get("cartridges", [])
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and item.get("item_type") == "cartridge":
                    cartridges.append(item)
                else:
                    modules.append(item)

        # Process modules
        for mod in modules:
            sig = make_item_signature(mod, "module")
            if deduplicate and sig in seen_signatures:
                duplicates_skipped += 1
                continue
            seen_signatures.add(sig)
            merged_modules.append(dict(mod))

        # Process cartridges
        for cart in cartridges:
            sig = make_item_signature(cart, "cartridge")
            if deduplicate and sig in seen_signatures:
                duplicates_skipped += 1
                continue
            seen_signatures.add(sig)
            merged_cartridges.append(dict(cart))

        files_merged += 1

    # Re-index unique IDs to prevent collisions between files
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
