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

# Function to read a sensor value
def read_sensor(sock, initial_partial_key, sensor_id):
    # Construct READ-SENSOR request (Message Code 0x03)
    command_data = b'\x03' + bytes([sensor_id])  # Command and Sensor ID
    padded_command = pad(command_data, AES.block_size)
    full_aes_key = initial_partial_key + initial_partial_key  # Combine partial keys
    
    # Encrypt the command with the full AES key
    encrypted_command = AES.new(full_aes_key, AES.MODE_ECB).encrypt(padded_command)
    
    # Calculate the length of the full message to set the correct data length
    total_length = len(initial_partial_key) + len(encrypted_command) + 2  # Header length + data length
    
    # Construct the full message with correct data length
    pre_data = total_length.to_bytes(2, 'big') + initial_partial_key
    encrypted_data = pre_data + encrypted_command

    # Send the encrypted READ-SENSOR command and receive the response
    response = send_receive(sock, encrypted_data)
    print(f"Sensor ID: {sensor_id}, Response: {response.hex()}")

    if len(response) < 18:
        print("Incomplete response received.")
        return None

    # Extract the new partial key from the response
    response_partial_key = response[2:10]
    full_aes_key_response = initial_partial_key + response_partial_key

    # Decrypt the payload part of the response
    decrypted_response = decrypt_aes_ecb(full_aes_key_response, response[10:])
    if decrypted_response:
        print(f"Decrypted Response: {decrypted_response.hex()}")
        
        # Check for the READ-SENSOR success response (0x00) at the expected position
        if len(decrypted_response) > 1 and decrypted_response[1] == 0x00:
            sensor_value = int.from_bytes(decrypted_response[4:8], 'big')  # Extract sensor value bytes
            print(f"Sensor ID: {sensor_id}, Value: {sensor_value}")
            return sensor_value

    return None

def main():
    sock, initial_partial_key = establish_connection()
    mysensors = dict()
    sensorids= list()

    # Example of reading sensor values in the range (0 to 255)
    for sensor_id in range(256):
        value = read_sensor(sock, initial_partial_key, sensor_id)
        if value is not None:
            print(f"Sensor ID {sensor_id}: Value = {value}")
            mysensors[sensor_id] = value
            sensorids.append(sensor_id)

    sock.close()
    print(mysensors)
    print(sensorids)

if __name__ == "__main__":
    main()
