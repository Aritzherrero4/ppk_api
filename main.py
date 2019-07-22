"""
Simple CLI for working with the Nordic Power Profiler Kit (PPK).

NOTE: The PPK resets the DUT when python connects. The --power_cycle_dut
      option can be used to add a second DUT reset followed by a delay
      to ensure that the DUT's firmware has time to start up.

TODO: For trigger we should have voltage and sample length.
"""
import sys
import os
import argparse
import time
import csv

from ppk import ppk
import pynrfjprog
from pynrfjprog import API, Hex


HEX_FILE_PATH = os.path.sep.join((".", "hex", "ppk_nrfconnect.hex"))


def _verify_firmware(nrfjprog_api, fw_hex):
    """"""
    for segment in fw_hex:
        content = nrfjprog_api.read(segment.address, len(segment.data))
        if segment.data != content:
            return False
    return True


def _write_firmware(nrfjprog_api, fw_hex):
    """Replaces the PPK's firmware."""
    print("Replacing PPK firmware...", end='')
    nrfjprog_api.erase_all()
    for segment in fw_hex:
        nrfjprog_api.write(segment.address, segment.data, True)
    print("done")


def _close_and_exit(nrfjprog_api, status):
    """"""
    if nrfjprog_api:
        nrfjprog_api.disconnect_from_emu()
        nrfjprog_api.close()
    sys.exit(status)


def _measure_avg(ppk_api, time_s, out_file):
    """Prints the average current over the specified amount of time."""
    result, data_buf = ppk_api.measure_average(time_s)
    if out_file:
        with open(out_file, "w", newline='') as csv_file:
            csv_writer = csv.writer(csv_file, delimiter='\n')
            csv_writer.writerow(data_buf)
    else:
        print('Average: %0.2fuA' % result)


def _set_trigger(ppk_api, voltage):
    """Prints the average current after the trigger voltage is reached."""
    pass


def _connect_to_emu(args):
    nrfjprog_api = pynrfjprog.API.API('NRF52')
    nrfjprog_api.open()

    if args.serial_number:
        nrfjprog_api.connect_to_emu_with_snr(args.serial_number)
    else:
        nrfjprog_api.connect_to_emu_without_snr()

    if not args.skip_verify:
        fw_hex = pynrfjprog.Hex.Hex(HEX_FILE_PATH)
        if not _verify_firmware(nrfjprog_api, fw_hex):
            if args.force:
                _write_firmware(nrfjprog_api, fw_hex)
            else:
                print("PPK firmware verification failed. Use -f option to replace it.")
                _close_and_exit(nrfjprog_api, -1)
    return nrfjprog_api


def _main():
    """Parses arguments for the PPK CLI."""
    parser = argparse.ArgumentParser()
    parser.add_argument("-s", "--serial_number", type=int,
                        help="serial number of J-Link")
    parser.add_argument("-a", "--average", type=float,
                        help="print average current over time")
    parser.add_argument("-t", "--trigger_voltage", type=int,
                        help="print average current after trigger")
    parser.add_argument("-e", "--external_vdd", type=int,
                        help="set external regulator voltage [2100, 3600]")
    parser.add_argument("-c", "--clear_user_resistors",
                        help="clear user calibration resistors", action="store_true")
    parser.add_argument("-p", "--power_cycle_dut",
                        help="power cycle the DUT and delay", nargs='?', const=0, type=float)
    parser.add_argument("-v", "--verbose",
                        help="print logging information", action="store_true")
    parser.add_argument("-o", "--out_file",
                        help="write measurement data to file", type=str)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-k", "--skip_verify",
                       help="save time by not verifying the PPK firmware",
                       action="store_true")
    group.add_argument("-f", "--force",
                       help="program the PPK firmware if necessary",
                       action="store_true")
    args = parser.parse_args()

    if not args.trigger_voltage and not args.average:
        parser.print_usage()
        sys.exit(-1)

    nrfjprog_api = None
    try:
        nrfjprog_api = _connect_to_emu(args)

        ppk_api = ppk.API(nrfjprog_api, logprint=args.verbose)
        ppk_api.connect()

        if args.external_vdd:
            if args.external_vdd < ppk_api.VDD_SET_MIN or args.external_vdd > ppk_api.VDD_SET_MAX:
                print("Invalid external voltage regulator value (%d)." % args.external_vdd)
                _close_and_exit(nrfjprog_api, -1)
            else:
                ppk_api.vdd_set(args.external_vdd)

        if args.clear_user_resistors:
            ppk_api.clear_user_resistors()

        if args.power_cycle_dut is not None:
            ppk_api.dut_power_off()
            ppk_api.dut_power_on()
            if args.power_cycle_dut:
                time.sleep(args.power_cycle_dut)

        if args.average:
            _measure_avg(ppk_api, args.average, args.out_file)

        if args.trigger_voltage:
            _set_trigger(ppk_api, args.trigger_voltage)

        _close_and_exit(nrfjprog_api, 0)
    except Exception as ex:
        print(ex)
        _close_and_exit(nrfjprog_api, -1)


if __name__ == "__main__":
    _main()
