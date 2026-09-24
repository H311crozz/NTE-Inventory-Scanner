import re
import cv2
import numpy as np
from rapidocr_onnxruntime import RapidOCR

ocr_engine = RapidOCR()

LEVEL_MAIN_STATS = {
    "type_2": {
        0: {"atk_flat": 8, "hp_flat": 112},
        20: {"atk_flat": 42, "hp_flat": 560}
    },
    "type_3": {
        0: {"atk_flat": 12, "hp_flat": 168},
        20: {"atk_flat": 63, "hp_flat": 840}
    },
    "type_4": {
        0: {"atk_flat": 16, "hp_flat": 224},
        20: {"atk_flat": 84, "hp_flat": 1120}
    }
}

CARTRIDGE_SETS = {
    "crimson twin butterflies": ("Crimson Twin Butterflies", "crimson_twin_butterflies"),
    "devil's blood": ("Devil's Blood: Curse", "devils_blood_curse"),
    "devils blood": ("Devil's Blood: Curse", "devils_blood_curse"),
    "diabolos": ("Diabolos", "diabolos"),
    "fireflies and the forest": ("Fireflies and the Forest", "fireflies_and_the_forest"),
    "kingdom's guard": ("Kingdom's Guard", "kingdoms_guard"),
    "kingdoms guard": ("Kingdom's Guard", "kingdoms_guard"),
    "lost radiance": ("Lost Radiance", "lost_radiance"),
    "quiet manor": ("Quiet Manor", "quiet_manor"),
    "shadow creed": ("Shadow Creed", "shadow_creed"),
    "speedy hedgehog": ("Speedy Hedgehog", "speedy_hedgehog"),
    "street boxer": ("Street Boxer", "street_boxer"),
    "thea's night tavern": ("Thea's Night Tavern", "theas_night_tavern"),
    "theas night tavern": ("Thea's Night Tavern", "theas_night_tavern"),
    "tiny big adventure": ("Tiny Big Adventure", "tiny_big_adventure"),
}


STAT_NAME_MAP = {
    "atk": "atk",
    "attack": "atk",
    "hp": "hp",
    "health": "hp",
    "def": "def",
    "defense": "def",
    "crit rate": "crit_rate",
    "crit dmg": "crit_dmg",
    "crit damage": "crit_dmg",
    "dmg": "dmg_pct",
    "damage": "dmg_pct",
    "break intensity": "break_intensity",
    "cycle intensity": "cycle_intensity",
    "cosmos": "cosmos_dmg",
    "chaos": "chaos_dmg",
    "lakshana": "lakshana_dmg",
    "anima": "anima_dmg",
    "incantation": "incantation_dmg",
    "psyche": "psyche_dmg",
    "mental": "mental_dmg",
    "healing": "healing_bonus",
}

def detect_shape_from_card(card_image_bgr, shape_family="type_2"):
    h, w = card_image_bgr.shape[:2]
    crop = card_image_bgr[int(h * 0.10):int(h * 0.35), int(w * 0.02):int(w * 0.42)]
    ch, cw = crop.shape[:2]
    inner = crop[int(ch * 0.18):int(ch * 0.82), int(cw * 0.18):int(cw * 0.82)]
    blue = inner[:, :, 0]
    tile_mask = cv2.inRange(blue, 75, 255)
    contours, _ = cv2.findContours(tile_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    valid = [c for c in contours if cv2.contourArea(c) > 300]
    if valid:
        all_pts = np.vstack(valid)
        bx, by, bw, bh = cv2.boundingRect(all_pts)
        aspect_ratio = bw / float(bh)
        if shape_family == "type_2":
            return "type_2b" if aspect_ratio >= 1.15 else "type_2a"
        elif shape_family == "type_3":
            if aspect_ratio > 2.0:
                return "type_3a"  
            elif aspect_ratio < 0.5:
                return "type_3b" 
            else:
                cell_w = bw / 2.0
                cell_h = bh / 2.0
                blue_means = {}
                for r in range(2):
                    for c in range(2):
                        x1 = int(bx + c * cell_w + cell_w * 0.2)
                        x2 = int(bx + (c + 1) * cell_w - cell_w * 0.2)
                        y1 = int(by + r * cell_h + cell_h * 0.2)
                        y2 = int(by + (r + 1) * cell_h - cell_h * 0.2)
                        patch = inner[y1:y2, x1:x2]
                        blue_means[(r, c)] = np.mean(patch[:, :, 0]) if patch.size > 0 else 0

                empty_quad = min(blue_means, key=blue_means.get)
                corner_map = {
                    (0, 0): "type_3c",  
                    (0, 1): "type_3d", 
                    (1, 0): "type_3e",  
                    (1, 1): "type_3f"  
                }
                return corner_map.get(empty_quad, "type_3c")
        elif shape_family == "type_4":
            if aspect_ratio > 2.2:
                return "type_4a"  
            elif aspect_ratio < 0.45:
                return "type_4b"  
            elif aspect_ratio >= 1.05:
                return "type_4c"  
            else:
                return "type_4d"  
    return "type_2a" if shape_family == "type_2" else f"{shape_family}a"

def parse_module_card(card_image_bgr):
    results, _ = ocr_engine(card_image_bgr)
    if not results:
        return None
    extracted_lines = [r[1].strip() for r in results]
    full_text = " ".join(extracted_lines)
    level = 0
    lvl_match = re.search(r"\+\s*(\d{1,2})", full_text)
    if lvl_match:
        try:
            level = int(lvl_match.group(1))
        except ValueError:
            level = 0
    if "cartridge" in full_text.lower():
        set_name = "Lost Radiance"
        set_id = "lost_radiance"
        for line in extracted_lines:
            ll = line.lower()
            for key, (sname, sid) in CARTRIDGE_SETS.items():
                if key in ll:
                    set_name = sname
                    set_id = sid
                    break
        section = "header"
        main_stat_key = "crit_rate"
        main_stat_val = 30.0
        pending_main_label = None
        substats = []

        for line in extracted_lines:
            ll = line.lower()
            if "main attributes" in ll:
                section = "main"
                continue
            elif "sub attributes" in ll:
                section = "sub"
                continue
            elif section == "sub" and ("piece" in ll or "tier" in ll or "set" in ll):
                break

            if section == "main":
                for label, key in STAT_NAME_MAP.items():
                    if label in ll:
                        pending_main_label = key
                        break
                nums = re.findall(r"(\d+(?:\.\d+)?)", line)
                if nums:
                    main_stat_val = float(nums[0])
                    is_pct = "%" in line
                    if pending_main_label:
                        main_stat_key = pending_main_label
                        if main_stat_key in ["atk", "hp", "def"]:
                            main_stat_key = f"{main_stat_key}_pct" if is_pct else f"{main_stat_key}_flat"
            elif section == "sub":
                nums = re.findall(r"(\d+(?:\.\d+)?)", line)
                if not nums:
                    continue
                val = float(nums[0])
                is_pct = "%" in line
                for label, key in STAT_NAME_MAP.items():
                    if label in ll:
                        final_key = key
                        if final_key in ["atk", "hp", "def"]:
                            final_key = f"{final_key}_pct" if is_pct else f"{final_key}_flat"
                        substats.append({"name": final_key, "value": val})
                        break
        return {
            "item_type": "cartridge",
            "name": set_name,
            "set_id": set_id,
            "cartridge_type": set_id,
            "level": level,
            "main_stat": main_stat_key,
            "main_stat_value": main_stat_val,
            "substats": substats[:4]
        }

    else:
        substats = []
        main_stats = {}
        is_in_substats = False

        for line in extracted_lines:
            line_lower = line.lower()
            if "sub attributes" in line_lower:
                is_in_substats = True
                continue

            num_matches = re.findall(r"(\d+(?:\.\d+)?)", line)
            if not num_matches:
                continue

            val = float(num_matches[0])
            is_pct = "%" in line

            for label, key in STAT_NAME_MAP.items():
                if label in line_lower:
                    final_key = key
                    if final_key in ["atk", "hp", "def"]:
                        final_key = f"{final_key}_pct" if is_pct else f"{final_key}_flat"

                    if not is_in_substats and "main" not in line_lower:
                        main_stats[final_key] = int(val)
                    elif is_in_substats:
                        substats.append({"name": final_key, "value": val})
                    break
        shape_family = None
        atk_val = main_stats.get("atk_flat", 0)
        hp_val = main_stats.get("hp_flat", 0)
        if atk_val in [84, 16] or hp_val in [1120, 224]:
            shape_family = "type_4"
        elif atk_val in [63, 12] or hp_val in [840, 168]:
            shape_family = "type_3"
        elif atk_val in [42, 8] or hp_val in [560, 112]:
            shape_family = "type_2"
        if not shape_family:
            if re.search(r"Type\s*(?:IV|4)\b", full_text, re.IGNORECASE):
                shape_family = "type_4"
            elif re.search(r"Type\s*(?:III|3)\b", full_text, re.IGNORECASE):
                shape_family = "type_3"
            elif re.search(r"Type\s*(?:II|2)\b", full_text, re.IGNORECASE):
                shape_family = "type_2"
            else:
                shape_family = "type_2"
        shape_type = detect_shape_from_card(card_image_bgr, shape_family)

        family_table = LEVEL_MAIN_STATS.get(shape_family, LEVEL_MAIN_STATS["type_2"])
        expected_main = family_table.get(level) or (family_table[20] if level >= 20 else family_table[0])

        final_main_stats = {
            "atk_flat": main_stats.get("atk_flat", expected_main["atk_flat"]),
            "hp_flat": main_stats.get("hp_flat", expected_main["hp_flat"])
        }
        return {
            "item_type": "module",
            "shape_type": shape_type,
            "level": level,
            "mainStats": final_main_stats,
            "substats": substats[:4]
        }
