import sys
import os

import pynrfjprog
from pynrfjprog import API, Hex
HEX_FILE_PATH = os.path.sep.join(("./lib/ppk_api/", "hex", "ppk.hex"))

def verify_firmware(nrfjprog_api, fw_hex):
    """"""
    for segment in fw_hex:
        content = nrfjprog_api.read(segment.address, len(segment.data))
        if segment.data != content:
            return False
    return True
    
def write_firmware(nrfjprog_api, fw_hex):
    """Replaces the PPK's firmware."""
    print("Replacing PPK firmware...", end='')
    nrfjprog_api.erase_all()
    for segment in fw_hex:
        nrfjprog_api.write(segment.address, segment.data, True)
    print("done")

def close_and_exit(nrfjprog_api, status):
    """"""
    if nrfjprog_api:
        nrfjprog_api.disconnect_from_emu()
        nrfjprog_api.close()
    sys.exit(status)


def connect_to_emu(device_class,serial_num=0):
    """Connects to emulator and replaces the PPK firmware if necessary."""
    nrfjprog_api = pynrfjprog.API.API(device_class)
    nrfjprog_api.open()
    if serial_num == 0:
        nrfjprog_api.connect_to_emu_without_snr()
    else:
        nrfjprog_api.connect_to_emu_with_snr(serial_num)

    fw_hex = pynrfjprog.Hex.Hex(HEX_FILE_PATH)
    if not verify_firmware(nrfjprog_api, fw_hex):
        print("PPK firmware verification failed. Writting new PKK firmware to device.")
        if not write_firmware(nrfjprog_api, fw_hex):
            print("Writing failed. Exiting")
            close_and_exit(nrfjprog_api, -1)
    return nrfjprog_api