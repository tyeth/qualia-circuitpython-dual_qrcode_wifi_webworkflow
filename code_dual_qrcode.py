# SPDX-FileCopyrightText: 2021 Jose David M.
# SPDX-FileCopyrightText: 2023 Melissa LeBlanc-Williams for Adafruit Industries
# SPDX-FileCopyrightText: 2023 Tyeth Gundry messing around
#
# SPDX-License-Identifier: MIT

# NOTE: Make sure you've set up your settings.toml file before running this example
# https://learn.adafruit.com/getting-started-with-web-workflow-using-the-code-editor/
"""
This example shows a wifi connection and a web address QR on the display, along with a help page fallback, and image display that hide/shows on touch
"""

import time
import adafruit_qualia
import os
import gc
import json
from adafruit_qualia.graphics import Graphics, Displays
from adafruit_qualia.peripherals import Peripherals
import displayio
import terminalio
import vectorio


base = adafruit_qualia.Qualia(Displays.BAR320X820, rotation=90)

# Background Information
graphics = base.graphics

# Set up Peripherals
peripherals = base.peripherals

# Set display to show
display = base.display

# display.auto_refresh=False

def display_qr_and_text(qr_data, text, x=0, y=0, relative_x_from_center=None, relative_y_from_center=None, scale=10, include_qr_offset=False, include_text_x_offset=-20, label_index=None, qr_group=None):
    global graphics, display, base
    qr_size = scale
    if relative_x_from_center is not None:
        x = (display.width // 2) + relative_x_from_center
    if relative_y_from_center is not None:
        y = display.height // 2 + relative_y_from_center
    if include_qr_offset:
        x_offset = (qr_size + 5) * scale
        y_offset = (qr_size + 4) * scale
        x -= x_offset
        y -= y_offset
    if qr_group is not None:
        display.auto_refresh=False
        display.root_group.remove(qr_group)
    qr_group = graphics.qrcode(qr_data, qr_size=scale, x=x, y=y, qr_color=0x121212, qr_bg_color=0x0000aa, return_group=True)
    display.root_group.append(qr_group)
    if label_index is not None:
        base.set_text(label_index, text)
    else:
        label_index = base.add_text(text_position=(x + include_text_x_offset, 0.9 * display.height), text=text, text_scale=3, text_wrap=0, text_maxlen=180, text_color=0xFFFFFF)
    display.auto_refresh=True
    return (x,y, label_index, qr_group)

def get_item_at(x, y, group):
    for item in group:
        if not hasattr(item, "x") or not hasattr(item, "y"):
            continue
        #print("item pos+size", item.x, item.y, item.width if hasattr(item,"width") else item.tile_width if hasattr(item,"tile_width") else "unknown", item.height if hasattr(item,"height") else item.tile_height if hasattr(item,"tile_height") else "unknown")
        print("item position:", x,y)
        print("item tile_width:", item.tile_width if hasattr(item,"tile_width") else "unknown")
        print("item tile_height:", item.tile_height if hasattr(item,"tile_height") else "unknown")
        print("item width:", item.width if hasattr(item,"width") else "unknown")
        print("item height:", item.height if hasattr(item,"height") else "unknown")
        if isinstance(item, displayio.TileGrid):
            print("Checking TileGrid", json.dumps(item))
            if item.x <= x and x < (item.x + item.tile_width if hasattr(item,"tile_width") else item.width) and item.y <= y and y < (item.y + item.tile_height if hasattr(item,"tile_height") else item.height):
                print("Touched TileGrid", json.dumps(item))
                return item
        elif isinstance(item, displayio.Group):
            print("Checking Group", json.dumps(item))
            data = get_item_at(x, y, item)
            if data is not None:
                return data
    return None

def print_items(group):
    print("Printing items in group", json.dumps(group))
    for item in group:
        if not hasattr(item, "x") or not hasattr(item, "y"):
            continue
        elif isinstance(item, displayio.TileGrid):
            print("printing TileGrid", json.dumps(item), json.dumps(dir(item)))
        if isinstance(item, displayio.Group):
            print("Checking Group", json.dumps(item))
            print_items(item)
        else:
            print("Skipping", json.dumps(item), json.dumps(dir(item)))
    print("Finished printing items in group", json.dumps(group), json.dumps(dir(group)))


callbacks = {}

# Define the triggerTouch function or import it from a module
def triggerTouch(x, y, finger):
    global display
    print("Touched", x, y, finger)
    #iterate through the tilegrids and groups (which contain tilegrids) inside root_group, testing the x,y against the bounding box of each tilegrid
    item = get_item_at(x, y, display.root_group)
    if item is None:
        print("No item found")
        return False
    print("Found item", json.dumps(item), json.dumps(dir(item)))        
    gc.collect()
    if item in callbacks:
        callbacks[item](item, x, y, finger)
        return True
    return False

def example_touch_callback(item, x, y, finger):
    print("Touched Example Callback, toggling hidden status")
    item.hidden = not item.hidden

wifi = adafruit_qualia.network.WiFi()

if wifi.is_connected and wifi.ip_address in (None, "0.0.0.0"):
    print("Wifi almost connected, Waiting for IP")
    counter=5
    while not wifi.is_connected:
        print(".", end="")
        time.sleep(0.1)
        if(counter==0):
            break


if not wifi.is_connected and wifi.ip_address not in (None, "0.0.0.0"):
    # using circuitpython get portalbase wifi information so we can construct the url from IP and port and password (both read from settings.toml using os.getenv("field", default_value) )
    ip = wifi.ip_address
    port = os.getenv("CIRCUITPY_WEB_API_PORT", "80")
    password = os.getenv("CIRCUITPY_WEB_API_PASSWORD", "password")

    # WebPage to show in the QR
    webpage = f"http://{ip}:{port}/"
else:
    # if not then craft a fake url that starts with http:// but infact has a clever use of @ (%40) and :(%3a) etc to really just link to about:blank except about:wifi_not_connected, like a low grade url escape that only a QR reader would fall for as it's technically not a valid url; be better if it was a javascript: type url that supported alerts etc, maybe just a website with good customisation, a bit like lmgtfy.com or a meme generator
    #webpage="http://%40%3a%2f%2fabout%3awifi_not_connected"
    webpage = "https://learn.adafruit.com/circuitpython-with-esp32-quick-start/setting-up-web-workflow"
    ip=None


# QR size Information
qr_size = 9  # Pixels
scale = 8


# Generate QR code bitmap for webpage
(webpage_x,webpage_y,webpage_label_index,webpage_qr_group) = display_qr_and_text(webpage, "IP: " + str(ip) if ip else "", relative_x_from_center=100,y=10, scale=scale, include_text_x_offset=-30)


if not ip:
    bitmap_file = open("/circuitpythonlogo-color888.bmp", 'rb')
    bitmap = displayio.OnDiskBitmap(bitmap_file)
    pixel_shader = getattr(bitmap, 'pixel_shader', displayio.ColorConverter())
    tilegrid = displayio.TileGrid(bitmap, pixel_shader=pixel_shader, x=x, y=y)

    # image_bitmap = displayio.Bitmap(270,240 , 2)
    # image_bitmap.blit(0, 0, image_data)
    # image_palette = displayio.Palette(2)
    # image_palette[0] = 0x000000
    # image_palette[1] = 0xFFFFFF
    # image_sprite = displayio.TileGrid(image_bitmap, pixel_shader=image_palette, x=0, y=0)
    # tilegrid = image_sprite

    bitmap_tilegrid = tilegrid

    direction_y = -1
    direction_x = -1
    # # Create a Bitmap from a PNG file
    # image = displayio.OnDiskBitmap("/circuitpythonlogo-color888.bmp")

    # palette = displayio.ColorConverter(input_colorspace=displayio.Colorspace.RGB888)

    # # Create a TileGrid
    # tilegrid = displayio.TileGrid(
    #     bitmap=image,
    #     pixel_shader=palette,
    #     x=x,
    #     y=y,
    # )
    #
    callbacks[tilegrid] = example_touch_callback


    img_group = displayio.Group()
    img_group.append(tilegrid)

    display.auto_refresh=False
    # Add the TileGrid to the display
    display.root_group.append(img_group)
else:
    
    # Generate Wifi joining QR code
    qrdata=f"WIFI:S:{os.getenv('CIRCUITPY_WIFI_SSID', '*Unset*')};T:{os.getenv('CIRCUITPY_WIFI_TYPE', 'WPA')};P:{os.getenv('CIRCUITPY_WIFI_PASSWORD', '*Unset*')};" if ip else "https://www.adafruit.com"
    (qrcode_x,qrcode_y,qrcode_label_index,qrcode_qr_group)=display_qr_and_text(qrdata, "SSID: " + os.getenv("CIRCUITPY_WIFI_SSID", "*Unset* read help->"), relative_x_from_center=-330,y=10, scale=scale, include_text_x_offset=-30)

    bitmap_tilegrid = None
    for item in display.root_group:
        if isinstance(item, displayio.TileGrid):
            callbacks[item] = example_touch_callback
        elif isinstance(item, displayio.Group):
            for subitem in item:
                if isinstance(subitem, displayio.TileGrid):
                    callbacks[subitem] = example_touch_callback
                elif isinstance(subitem, displayio.Group):
                    for subsubitem in subitem:
                        if isinstance(subsubitem, displayio.TileGrid):
                            callbacks[subsubitem] = example_touch_callback



# display.refresh()
# display.auto_refresh=True

def fix_x_y_for_rotation(x,y):
    global graphics
    if graphics.display.rotation == 90:
        return (y, graphics.display.height- x -1)
    elif graphics.display.rotation == 180:
        return (graphics.display.width - x -1, graphics.display.height - y -1)
    elif graphics.display.rotation == 270:
        return (graphics.display.width - y -1, x)
    else:
        return (x,y)

print_items(display.root_group)

display.auto_refresh=True
counter=0
old_ip=ip
while True:
    counter+=1
    ip = wifi.ip_address
    if old_ip != ip:
        ip = wifi.ip_address
        port = os.getenv("CIRCUITPY_WEB_API_PORT", "80")
        password = os.getenv("CIRCUITPY_WEB_API_PASSWORD", "password")

        # WebPage to show in the QR
        webpage = f"http://{ip}:{port}/"
        # Generate QR code bitmap for webpage
        (webpage_x,webpage_y,webpage_label_index,webpage_qr_group) = display_qr_and_text(webpage, "IP: " + str(ip) if ip else "", relative_x_from_center=100,y=10, scale=scale, include_text_x_offset=-30, label_index=webpage_label_index, qr_group=webpage_qr_group)
    old_ip=ip

    if graphics.touch.touched:
        try:
            finger=-1
            for touch in graphics.touch.touches:
                finger+=1
                print("touch", touch)
                x = touch["x"]
                y = touch["y"]
                # todo: refactor this into a PR for qualia graphics or touch directly
                print("touch before fix")
                print(graphics.display.width, graphics.display.height, x, y)
                (x,y) = fix_x_y_for_rotation(x,y)
                print("touch after fix")
                print(graphics.display.width, graphics.display.height, x, y)
                continue
                if (
                    not 0 <= x < graphics.display.width
                    or not 0 <= y < graphics.display.height
                ):
                    print("skipping out of bounds touch")
                    continue  # Skip out of bounds touches
                triggerTouch(x, y, finger)
        except Exception as e:
            print(e)
            pass
    if peripherals.button_up:
        peripherals.backlight = True
    if peripherals.button_down:
        peripherals.backlight = False

    # if bitmap_tilegrid is not None:
    #     if direction_x > 10:
    #         direction_x = -1
    #     elif direction_x < -10:
    #         direction_x = 1
    #     if direction_y > 10:
    #         direction_y = -1
    #     elif direction_y < -10:
    #         direction_y = 1
    #     bitmap_tilegrid.x = direction_x + bitmap_tilegrid.x
    #     bitmap_tilegrid.y = direction_y + bitmap_tilegrid.y
    time.sleep(0.1)