import framebuf
import urandom
import st7789
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

# Display dimensions
display_width = 128
display_height = 160

# Setup display
spi = SPI(1, baudrate=40000000, polarity=0, sck=Pin(pin_scl), mosi=Pin(pin_sda), miso=None)
display = st7789.ST7789(spi, display_width, display_height, cs=Pin(pin_cs, Pin.OUT), dc=Pin(pin_dc, Pin.OUT), reset=Pin(pin_res, Pin.OUT), color_order=st7789.RGB, inversion=False)
display.init()

# Set display to black initially
display.fill(st7789.BLACK)

# Viridis color map for MicroPython
VIRIDIS_COLORS = [
    (68, 1, 84), (71, 44, 122), (59, 81, 139), (44, 113, 142),
    (33, 144, 141), (39, 173, 129), (92, 200, 99), (170, 220, 50),
    (253, 231, 37)
]

def viridis_color_map(normalized_value):
    """Map a normalized value (0.0 to 1.0) to a Viridis color"""
    # Clamp normalized value to 0-1 range
    normalized_value = max(0.0, min(1.0, normalized_value))
    
    # Find the segment in the color map
    segment_size = 1.0 / (len(VIRIDIS_COLORS) - 1)
    index = int(normalized_value / segment_size)
    index = max(0, min(index, len(VIRIDIS_COLORS) - 2))  # Clamp index
    
    # Calculate interpolation factor within the segment
    t = (normalized_value - index * segment_size) / segment_size
    
    # Linear interpolation between colors
    r1, g1, b1 = VIRIDIS_COLORS[index]
    r2, g2, b2 = VIRIDIS_COLORS[index + 1]
    
    r = int(r1 + (r2 - r1) * t)
    g = int(g1 + (g2 - g1) * t)
    b = int(b1 + (b2 - b1) * t)
    
    return r, g, b

def fill_thermal_buffer_viridis(frame, buf, min_value, value_range):
    """Fill RGB565 buffer with thermal data using Viridis colormap"""
    buf_index = 0
    
    for y in range(display_height):
        for x in range(display_width):
            # Map the current display pixel to the frame
            fx = int(x * frame_width / display_width)
            fy = int(y * frame_height / display_height)
            index = fy * frame_width + fx
            
            # Get normalized value (0.0 to 1.0)
            normalized = (frame[index] - min_value) / value_range
            normalized = max(0.0, min(1.0, normalized))  # Clamp to 0-1
            
            # Get Viridis color
            r, g, b = viridis_color_map(normalized)
            
            # Convert to RGB565
            r565 = (r >> 3) & 0x1F
            g565 = (g >> 2) & 0x3F  
            b565 = (b >> 3) & 0x1F
            color565 = (r565 << 11) | (g565 << 5) | b565
            
            # Store in buffer (big-endian format, high byte first)
            buf[buf_index] = (color565 >> 8) & 0xFF
            buf[buf_index + 1] = color565 & 0xFF
            buf_index += 2

# Create buffer once outside loop
buf = bytearray(128 * 160 * 2)

# Main loop
try:
    while True:
        time.sleep(0.1)
        time_init = time.ticks_ms()
        mlx.get_frame(frame)
        
        # Normalize frame values
        min_value = min(frame)
        max_value = max(frame)
        value_range = max_value - min_value if max_value > min_value else 1
        
        # Fill buffer with Viridis colors
        fill_thermal_buffer_viridis(frame, buf, min_value, value_range)
        
        # Display the buffer
        display.blit_buffer(buf, 0, 0, 128, 160)
        
        time_end = time.ticks_ms()
        time_elapsed = time.ticks_diff(time_end, time_init)
        print("Frame sent!")
        print(f"Elapsed time {time_elapsed}ms")
        
except KeyboardInterrupt:
    print("Stopped by user.")
    spi.deinit()
