import time
import random
import pydirectinput
import ctypes

pydirectinput.FAILSAFE = True
GRID_COLS = 7
GRID_ROWS = 4
PAGE_SIZE = 28
FIRST_SLOT_X_PCT = 0.1104
FIRST_SLOT_Y_PCT = 0.2419
STEP_X_PCT = 0.0837
STEP_Y_PCT = 0.1797
MOUSEEVENTF_WHEEL = 0x0800
def raw_scroll(delta_units: int):
    ctypes.windll.user32.mouse_event(MOUSEEVENTF_WHEEL, 0, 0, int(delta_units), 0)

def click_module_slot(window_rect, index):
    page_slot = index % PAGE_SIZE
    col = page_slot % GRID_COLS
    row = page_slot // GRID_COLS
    start_x = window_rect["left"] + int(window_rect["width"] * FIRST_SLOT_X_PCT)
    start_y = window_rect["top"] + int(window_rect["height"] * FIRST_SLOT_Y_PCT)
    step_x = int(window_rect["width"] * STEP_X_PCT)
    step_y = int(window_rect["height"] * STEP_Y_PCT)
    target_x = start_x + (col * step_x)
    target_y = start_y + (row * step_y)
    pydirectinput.moveTo(target_x, target_y)
    time.sleep(0.04)
    pydirectinput.click(target_x, target_y)
    time.sleep(0.12)

def scroll_page_down(window_rect, num_rows=4):
    center_x = window_rect["left"] + int(window_rect["width"] * 0.35)
    center_y = window_rect["top"] + int(window_rect["height"] * 0.50)
    pydirectinput.moveTo(center_x, center_y)
    time.sleep(0.05)
    for _ in range(num_rows):
        raw_scroll(-720)
        time.sleep(0.05)
    time.sleep(0.35)
