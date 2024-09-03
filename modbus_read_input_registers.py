import sys
import time
from pymodbus.client.tcp import ModbusTcpClient as ModbusClient
from pymodbus.exceptions import ConnectionException

class MODBUS:
    def __init__(self):
        self.target_ip = "0.cloud.chals.io"
        self.client = None

    def create_client(self):
        self.client = ModbusClient(self.target_ip, port=30228)
        try:
            self.client.connect()
        except ConnectionException:
            print(f"Could not connect to Modbus port on {self.target_ip} at port 30228")
            sys.exit()

    def read_input_registers(self):
        print("Scanning input registers...")
        for address in range(0, 1000):  # Scan a range of input registers
            try:
                rr = self.client.read_input_registers(address, 1)
                if rr.isError():
                    print(f"Error reading register {address}")
                else:
                    value = rr.registers[0]
                    print(f"Register {address}: {value}")

                    if value == 20576:
                        print(f"\n\nSensor (X-764) found at address '{address}' with value '{value}'\n\n")
                    elif value == 24:
                        print(f"\n\nSensor (E-650) found at address '{address}' with value '{value}'\n\n")
                    elif value == 67:
                        print(f"\n\nSensor (L-306) found at address '{address}' with value '{value}'\n\n")
                    
                    # Add logic here to detect if the value belongs to a sensor
                    # If you detect a sensor, you can print/store the address
            except ConnectionException:
                print(f"Could not connect to Modbus port on {self.target_ip}")
                sys.exit()
            except Exception as e:
                print(f"An error occurred: {e}")
            time.sleep(0.1)  # Adjust delay if necessary

def main():
    client = MODBUS()
    client.create_client()
    client.read_input_registers()

if __name__ == "__main__":
    main()
