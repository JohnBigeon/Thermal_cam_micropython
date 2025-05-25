import urandom
from ST7735 import TFT, TFTColor
import machine
from machine import SPI, Pin
from mlx90640 import MLX90640, RefreshRate, init_float_array
import time


# Declare pins
pin_cam_sda = 20
pin_cam_scl = 21
pin_scl = 5
pin_sda = 2
pin_res = 0
pin_dc  = 3
pin_cs  = 9

# Setup thermal cam
i2c = machine.I2C(-1, sda=machine.Pin(pin_cam_sda), scl=machine.Pin(pin_cam_scl), freq=400000)
print(i2c.scan())              	# scan for devices: should return 51
mlx = MLX90640(i2c)
mlx.refresh_rate = RefreshRate.REFRESH_4_HZ
frame = init_float_array(768) 	# width * height

# Frame dimensions
frame_width = 32
frame_height = 24
 
# Setup display
spi = SPI(1, baudrate=20000000, polarity=0, phase=0, sck=Pin(pin_scl), mosi=Pin(pin_sda), miso=None)
tft = TFT(spi, pin_dc, pin_res, pin_cs)
tft.initr()
tft.rgb(True)

# Set display to black initially
tft.fill(TFT.BLACK)

# Display dimensions
display_width = 128
display_height = 160


# Viridis color map for MicroPython
VIRIDIS_COLORS = [
    (68, 1, 84), (71, 44, 122), (59, 81, 139), (44, 113, 142),
    (33, 144, 141), (39, 173, 129), (92, 200, 99), (170, 220, 50),
    (253, 231, 37)
]

# Function to map float to color
# Uses linear interpolation between defined Viridis points

def float_to_color(value, min_value, value_range):
    normalized = (value - min_value) / value_range  # Normalize to 0.0 - 1.0
    index = int(normalized * (len(VIRIDIS_COLORS) - 1))  # Find segment index
    index = max(0, min(index, len(VIRIDIS_COLORS) - 2))  # Clamp index
    
    # Linear interpolation between points
    t = (normalized * (len(VIRIDIS_COLORS) - 1)) % 1
    r1, g1, b1 = VIRIDIS_COLORS[index]
    r2, g2, b2 = VIRIDIS_COLORS[index + 1]
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    
    return TFTColor(r, g, b)

# Main loop to send the frame every 5 seconds
try:
    while True:
        time.sleep(0.1)
        time_init = time.ticks_ms()
        mlx.get_frame(frame)
        #print(frame[0:5])
        time.sleep(0.001)
        # Normalize frame values
        min_value = min(frame)
        max_value = max(frame)
        value_range = max_value - min_value if max_value > min_value else 1

        # Set the full display window
        tft._setwindowloc((0, 0), (display_width - 1, display_height - 1))

        # Upscale and display frame
        for y in range(display_height):
            for x in range(display_width):
                # Map the current display pixel to the frame
                fx = int(x * frame_width / display_width)
                fy = int(y * frame_height / display_height)
                index = fy * frame_width + fx
                color = float_to_color(frame[index], min_value, value_range)
                tft._pushcolor(color)

        time_end = time.ticks_ms()
        time_elapsed = time.ticks_diff(time_end, time_init)
        print("Frame sent!")
        print(f"Elapsed time {time_elapsed}ms")
        #time.sleep(5)

except KeyboardInterrupt:
    print("Stopped by user.")
    spi.deinit()
