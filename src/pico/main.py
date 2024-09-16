import network
import socket
import time
import json
from machine import UART, Pin
from Crypto.Cipher import AES
from Crypto.Random import get_random_bytes
import base64

def read_config():
    with open('config.json', 'r') as f:
        return json.load(f)

# Load network credentials and other configurations from config file
config = read_config()

# Update Network and Server details
WIFI_SSID     = config['WIFI_SSID']
WIFI_PASSWORD = config['WIFI_PASSWORD']
IP_ADDRESS    = config['IP_ADDRESS']
TCP_PORT      = config['PORT']
PICO_ID       = config['PICO_ID']
ENCRYPT       = config.get('ENCRYPT', False)  # Load ENCRYPT, could be False or a PSK string

# Determine whether encryption is enabled and set PSK
PSK = None
if ENCRYPT and isinstance(ENCRYPT, str):
    PSK = ENCRYPT[:32].ljust(32)  # Use the PSK value if encryption is enabled, pad or truncate to 32 bytes

# Initialize UART and LED
uart1 = UART(1, 19200)
uart1.init(19200, bits=8, parity=None, stop=1, tx=4, rx=5)
led = Pin("LED", Pin.OUT)

def blink_led():
    led.off()
    time.sleep(0.1)
    led.on()
    time.sleep(0.1)

def encrypt_message(message, key):
    # Generate a random initialization vector (IV)
    iv = get_random_bytes(16)
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CFB, iv=iv)
    encrypted_message = iv + cipher.encrypt(message.encode('utf-8'))
    return base64.b64encode(encrypted_message).decode('utf-8')

def decrypt_message(encrypted_message, key):
    encrypted_message = base64.b64decode(encrypted_message)
    iv = encrypted_message[:16]
    cipher = AES.new(key.encode('utf-8'), AES.MODE_CFB, iv=iv)
    return cipher.decrypt(encrypted_message[16:]).decode('utf-8')

# Connect to Wi-Fi
wlan = network.WLAN(network.STA_IF)
wlan.active(True)
wlan.connect(WIFI_SSID, WIFI_PASSWORD)

while not wlan.isconnected():
    blink_led()

led.off()
print("Connected to WiFi")

# Establish a new TCP connection
def create_tcp_connection():
    while True:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((IP_ADDRESS, TCP_PORT))
            led.on()
            return sock
        
        except Exception as e:
            print(f"Failed to connect to TCP server: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)

# 'pico_ID' packet to initiate named pipe creation
def send_hello_packet(sock):
    hello_message = f'pico_{PICO_ID}'
    if PSK:
        hello_message = encrypt_message(hello_message, PSK)
    sock.send(hello_message.encode())

# Create initial TCP socket and connect
s = create_tcp_connection()
print("Connected to TCP server")

# Send 'pico_ID' packet
send_hello_packet(s)

try:
    while True:
        # Check for incoming UART data
        if uart1.any():
            rxed = uart1.read().decode('utf-8').rstrip()
            if PSK:
                rxed = encrypt_message(rxed, PSK)
            s.send(rxed.encode())  # Send the encrypted UART received data to the TCP server
            blink_led()

        # Non-blocking mode to avoid halting the execution if no data is available.
        s.setblocking(False)
        try:
            data = s.recv(64)  # Data received from TCP Server

            if data == b'':  # Empty byte string indicates that the other side of the TCP connection has closed
                s.close()  # Closes the socket on Pico-W's side      
                led.off()
                print("TCP connection closed by server. Reconnecting...")
                s = create_tcp_connection()
                send_hello_packet(s)
                print("Reconnected to server.")
                continue

            if data:  # Valid data received from TCP Server
                cmd = data.decode()
                if PSK:
                    cmd = decrypt_message(cmd, PSK)
                uart1.write(cmd)
                blink_led()

        except Exception as e:
            pass  # No data received, normal for non-blocking call

        # Set blocking mode to block until all the data has been sent to the TCP server 
        s.setblocking(True)
        time.sleep(0.05)  # Short delay to prevent CPU overload

except Exception as e:
    print("An error occurred:", e)

finally:
    s.close()
    led.off()
    print("TCP socket closed")
