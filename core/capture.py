import win32gui
import win32con
import mss
import numpy as np

def find_nte_window():
    targets = ["NTE"]
    hwnd_found = None
    def enum_windows_callback(hwnd, _):
        nonlocal hwnd_found
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd).strip()
            title_lower = title.lower()
            if not title or "scanner" in title_lower or "visual studio" in title_lower or "powershell" in title_lower:
                return True
                
            for target in targets:
                if target.lower() in title_lower:
                    hwnd_found = hwnd
                    return False
        return True
    try:
        win32gui.EnumWindows(enum_windows_callback, None)
    except Exception:
        pass
    return hwnd_found

def get_window_client_rect(hwnd):
    """
    Returns the client area (excluding title bar and window borders)
    suitable for mss screen grabbing.
    """
    if not hwnd:
        return None
    left, top, right, bottom = win32gui.GetClientRect(hwnd)
    point = win32gui.ClientToScreen(hwnd, (0, 0))
    width = right - left
    height = bottom - top
    return {
        "left": point[0],
        "top": point[1],
        "width": width,
        "height": height
    }

def capture_screen_area(sct, rect):
    raw_img = sct.grab(rect)
    img_np = np.array(raw_img)
    return img_np[:, :, :3]
