import json
from datetime import datetime

def export_inventory_json(modules_list, cartridges_list=None, output_path="nte_inventory.json"):
    """
    Exports scanned Modules and Cartridges into the exact JSON format
    taken by the NTE Database Optimizer (Upload Inventory).
    """
    actual_modules = []
    actual_cartridges = list(cartridges_list or [])
    for item in (modules_list or []):
        if isinstance(item, dict) and item.get("item_type") == "cartridge":
            actual_cartridges.append(item)
        else:
            actual_modules.append(item)
    formatted_modules = []
    for idx, mod in enumerate(actual_modules):
        mod_id = f"scan_{int(datetime.utcnow().timestamp())}_{idx+1}"
        formatted_modules.append({
            "id": mod_id,
            "shape_type": mod.get("shape_type", "type_2a"),
            "level": mod.get("level", 20),
            "mainStats": mod.get("mainStats", {}),
            "substats": mod.get("substats", [])
        })
    formatted_cartridges = []
    for idx, cart in enumerate(actual_cartridges):
        cart_id = f"cart_scan_{int(datetime.utcnow().timestamp())}_{idx+1}"
        set_id = cart.get("set_id") or cart.get("cartridge_type") or "lost_radiance"
        formatted_cartridges.append({
            "id": cart_id,
            "name": cart.get("name", "Lost Radiance"),
            "set_id": set_id,
            "cartridge_type": set_id,
            "level": cart.get("level", 20),
            "main_stat": cart.get("main_stat", "crit_rate"),
            "main_stat_value": cart.get("main_stat_value", 30.0),
            "substats": cart.get("substats", [])
        })
    payload = {
        "version": 1,
        "exportedAt": datetime.utcnow().isoformat() + "Z",
        "modules": formatted_modules,
        "cartridges": formatted_cartridges
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2)

    return payload
