import argparse
import os
import random
import sys
import time
import uuid

import gdb

# add path to sys.path to find modules in the same dir.
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from parser import parse_args_safely

from buildcmd import BuildCmd
from logger import init_logger
from qemu_utils import *


@BuildCmd
def listram(args):
    """List all RAM ranges allocated by QEMU."""

    print("QEMU RAM list:")
    memory = mtree()["memory"]
    for start, end in memory.ram_ranges():
        print("  RAM allocated from 0x%x to 0x%x" % (start, end))
    print("Sampled index: 0x%x" % memory.random_address())


@BuildCmd
def listreg(args):
    """List all CPU registers available in QEMU."""

    print("QEMU CPU register list:")
    register = Registers()
    lr = register.list_registers()
    maxlen = max(len(r.name) for r, nb in lr)
    print("  REG:", "Name".rjust(maxlen), "->", "Bytes")
    for register, num_bytes in lr:
        print("  REG:", register.name.rjust(maxlen), "->", num_bytes)


@BuildCmd
def stop_delayed(args):
    """Stop the QEMU instance after a delay of the input nano-seconds."""

    parser = argparse.ArgumentParser(
        description="Stop the QEMU instance after a delay", prog="stop_delayed"
    )
    parser.add_argument(
        "--ns", required=True, help="Nanoseconds to delay before stopping"
    )

    parsed = parse_args_safely(parser, args)
    if parsed is None:
        return

    step_ns(parsed.ns)


@BuildCmd
def inject(args):
    """Inject a bitflip at an address."""

    parser = argparse.ArgumentParser(
        description="Inject a bitflip at an address", prog="inject"
    )
    parser.add_argument(
        "--address",
        required=True,
        help="Address to inject bitflip (if not specified, randomly selected)",
    )
    parser.add_argument(
        "--bytewidth",
        required=True,
        type=int,
        help="Byte width (default: 4 if address specified, 1 if random)",
    )
    parser.add_argument(
        "--bit", required=True, type=int, help="Bit index within the integer to flip"
    )

    parsed = parse_args_safely(parser, args)
    if parsed is None:
        return

    if parsed.address:
        # Support argument like "inject --address 0x1234+0x11 --bytewidth 4 --bit 3"
        try:
            address = int(gdb.parse_and_eval(parsed.address))
        except Exception as e:
            print("Error parsing address: %s" % str(e))
            return
        bytewidth = parsed.bytewidth if parsed.bytewidth is not None else 4
        if bytewidth < 1 or address < 0:
            print("invalid bytewidth or address")
            return
    else:
        address = sample_address()
        bytewidth = 1

    bit = parsed.bit

    inject_bitflip(address, bytewidth, bit)


@BuildCmd
def inject_reg(args):
    """Inject a bitflip into a register.
    usage: inject_reg [--register <register name>] [--bit <bit index>]
    if no register specified, will be randomly selected,
    a pattern involving wildcards can be specified if desired
    """

    parser = argparse.ArgumentParser(
        description="Inject a bitflip into a register",
        prog="inject_reg",
    )
    parser.add_argument(
        "--register",
        required=True,
        help="Register name (supports wildcards, if not specified, randomly selected)",
    )
    parser.add_argument("--bit", required=True, type=int, help="Bit index to flip")

    parsed = parse_args_safely(parser, args)
    if parsed is None:
        return

    inject_reg_internal(parsed.register, parsed.bit)


# @BuildCmd
# def task_restart(args):
#     """Inject a UDF instruction to force a task restart."""
#     if args.strip():
#         print("usage: task_restart")
#         return

#     inject_instant_restart()


@BuildCmd
def loginject(args):
    """Log the injection of a bitflip"""

    parser = argparse.ArgumentParser(
        description="Log the injection of a bitflip to a CSV file",
        prog="loginject",
    )
    parser.add_argument(
        "--filename", required=True, help="CSV filename to log bitflip injections"
    )

    parsed = parse_args_safely(parser, args)
    if parsed is None:
        return

    init_logger(parsed.filename)


@BuildCmd
def autoinject(args):
    """Automatically inject fault into the VM accroding to the provided inject type.
    Cause `total_fault_number` faults with a random cycle between `min_interval` and `max_interval`,
    fault type is `fault_type`

    Usage: `autoinject --total-fault-number <num> --min-interval <time> --max-interval <time> --fault-type <type>`

    Supported types:
    1. ram: inject fault in RAM
    2. reg: inject fault in Registers"""

    parser = argparse.ArgumentParser(
        description="Automatically inject faults into the VM",
        prog="autoinject",
    )
    parser.add_argument(
        "--total-fault-number",
        type=int,
        required=True,
        help="Total number of faults to inject",
    )
    parser.add_argument(
        "--min-interval",
        required=True,
        help="Minimum interval between injections (with unit: ns, us, ms, s, m)",
    )
    parser.add_argument(
        "--max-interval",
        required=True,
        help="Maximum interval between injections (with unit: ns, us, ms, s, m)",
    )
    parser.add_argument(
        "--fault-type",
        choices=["ram", "reg"],
        required=True,
        help="Type of fault to inject",
    )

    parsed = parse_args_safely(parser, args)
    if parsed is None:
        return

    try:
        times = getattr(parsed, "total_fault_number")
        assert times >= 1, "fatal: times < 1"
        mint = parse_time(getattr(parsed, "min_interval"))
        maxt = parse_time(getattr(parsed, "max_interval"))
        assert 0 < mint <= maxt, "fatal: min_interval > max_interval"
        ftype = getattr(parsed, "fault_type")
    except (ValueError, AssertionError) as e:
        print("Error: %s" % str(e))
        return

    stime = time.time()
    autoinject_inner(times, mint, maxt, ftype)
    etime = time.time()
    duration = etime - stime
    print("Total injection duration: %.3f s" % duration)

@BuildCmd
def snapinject(args):
    """Record the current VM state, then automatically inject faults according to the user-provided fault count, fault location, and fault interval.
    After the faults are injected, wait for a while and then revert to the previous VM state, delete the tmp checkpoint.
    Usage: snapinject --total-fault-number <num> --min-interval <time> --max-interval <time> --fault-type <type> --fault-location <location> --bit-index <bit> --observe-time <time> [--snapshot-tag <tag>]
    Example:
        snapinject --total-fault-number 10 --min-interval 100ms --max-interval 200ms --fault-type ram --fault-location 0x00500000 --bit-index 1 --observe-time 10s
        snapinject --total-fault-number 10 --min-interval 100ms --max-interval 100ms --fault-type reg --fault-location pc --bit-index 3 --observe-time 10s --snapshot-tag my_snapshot

    Supported time units: default is ns. Time format: 10s, 244ms and etc.
    1. ns: nanosecond
    2. us: microsecond
    3. ms: millisecond
    4. s: second
    5. m: minute
    Supported fault type and fault location:
    1. ram, address: inject fault in RAM, location is "address"
    2. reg, regname: inject fault in Registers, target is "regname"
    """
    parser = argparse.ArgumentParser(
        description="Custom snapshot-based fault injection with specific location",
        prog="snapinject",
    )
    parser.add_argument(
        "--total-fault-number",
        type=int,
        required=True,
        help="Total number of faults to inject",
    )
    parser.add_argument(
        "--min-interval",
        required=True,
        help="Minimum interval between injections (with unit: ns, us, ms, s, m)",
    )
    parser.add_argument(
        "--max-interval",
        required=True,
        help="Maximum interval between injections (with unit: ns, us, ms, s, m)",
    )
    parser.add_argument(
        "--fault-type",
        choices=["ram", "reg"],
        required=True,
        help="Type of fault to inject",
    )
    parser.add_argument(
        "--fault-location",
        required=False,
        help="Fault location (address for RAM, register name for REG)",
    )
    parser.add_argument(
        "--bit-index", type=int, required=False, help="Bit index to flip"
    )
    parser.add_argument(
        "--observe-time",
        required=True,
        help="Time to observe after injection (with unit: ns, us, ms, s, m)",
    )
    parser.add_argument(
        "--snapshot-tag",
        help="Optional snapshot tag (if not provided, creates temporary snapshot)",
    )

    parsed = parse_args_safely(parser, args)
    if parsed is None:
        return

    try:
        times = getattr(parsed, "total_fault_number")
        assert times >= 1, "fatal: times < 1"
        mint = parse_time(getattr(parsed, "min_interval"))
        maxt = parse_time(getattr(parsed, "max_interval"))
        assert 0 < mint <= maxt, "fatal: min_interval > max_interval"
        ftype = getattr(parsed, "fault_type")
        obtime = parse_time(getattr(parsed, "observe_time"))
    except (ValueError, AssertionError) as e:
        print("Error: %s" % str(e))
        return

    tmpname = uuid.uuid4()
    location = getattr(parsed, "fault_location")
    bit_index = getattr(parsed, "bit_index")

    if (location is None and bit_index is not None) and (location is not None and bit_index is None):
        print("Error: --bit-index and --fault-location must be both specified or both omitted.")
        return

    snapname = getattr(parsed, "snapshot_tag") if getattr(parsed, "snapshot_tag") else tmpname
    if snapname == tmpname:
        qemu_hmp("savevm %s" % snapname)
        print("Create a tmp checkpoint %s" % snapname)
    else:
        qemu_hmp("loadvm %s" % snapname)
        print("Load checkpoint %s" % snapname)

    stime = time.time()
    if location is None and bit_index is None:
        autoinject_inner(times, mint, maxt, ftype)
    else:
        for _ in range(times):
            step_ns(random.randint(mint, maxt))
            if ftype == "ram":
                try:
                    address = int(location, 16)
                    inject_bitflip(address, 1, bit_index)  # Use 1 byte width and specify bit_index
                except ValueError as e:
                    print("Error parsing RAM address: %s" % str(e))
                    return
            elif ftype == "reg":
                inject_register_bitflip(location, bit_index)
    etime = time.time()
    duration = etime - stime
    print("Total injection duration: %.3f s" % duration)

    print("Observing VM %s" % getattr(parsed, "observe_time"))
    step_ns(obtime)
    print("time up.")

    if snapname == tmpname:
        # Revert to the previous VM state
        qemu_hmp("loadvm %s" % snapname)
        print("Back to checkpoint %s finished." % snapname)
        # Del this tmp VM checkpoint
        qemu_hmp("delvm %s" % tmpname)
        print("Delete tmp VM checkpoint")
    
    # Send a ret to qemu serial, make sure prompt is back
    send_to_qemu_serial("\r")

def parse_address_ranges_file(path):
    """
    Parse an address range file of the following format and return a list of all injectable addresses:
        0x0000000002800000-0x0000000002a00000
        0x0000000003400000-0x0000000003800000
    """
    address_list = []
    with open(path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or "-" not in line:
                continue
            try:
                start_str, end_str = line.split("-")
                start = int(start_str, 16)
                end = int(end_str, 16)
                address_list.extend(range(start, end, 1))  # 每 1 字节为单位注入
            except Exception as e:
                print(f"Invalid line in range file: {line} ({e})")
    return address_list


@BuildCmd
def loop(args):
    """Loop a action for provide times
    Usage: loop --times <num> --command <cmd> [--command-args <args>...]
    """
    parser = argparse.ArgumentParser(
        description="Loop an action for the specified number of times",
        prog="loop",
    )
    parser.add_argument(
        "--times", type=int, required=True, help="Number of times to repeat the command"
    )
    parser.add_argument("--command", required=True, help="Command to execute")
    parser.add_argument("--command-args", nargs="*", help="Arguments for the command")

    parsed = parse_args_safely(parser, args)
    if parsed is None:
        return

    times = parsed.times
    # Reconstruct the full command with arguments
    actions = parsed.command
    if getattr(parsed, "command_args"):
        actions += " " + " ".join(getattr(parsed, "command_args"))

    for _ in range(times):
        gdb.execute(actions)


@BuildCmd
def appinject(args):
    # TODO: Use argparse to parse the param here
    """Inject bitflips at addresses loaded from a file.

        Need to be used with find_phys_ranges.py
    Usage:
        appinject <count> <range_file>
            <count>: number of random bitflip injections to perform
            <range_file>: path to the file that contains address ranges

    """

    parser = (
        argparse.ArgumentParser(
            description="Inject bitflips at address loaded from a file",
            prog="appinject",
        )
        .add_argument(
            "--total-fault-number", type=int, help="total fault number", required=True
        )
        .add_argument(
            "--range-file", help="Description file of app memory map", required=True
        )
    )

    parsed = parse_args_safely(parser, args)
    if parsed is None:
        return

    path = parsed.range_file
    try:
        count = int(parsed.total_fault_number)
        if count <= 0:
            raise ValueError
    except ValueError:
        print("Invalid count")
        return

    addresses = parse_address_ranges_file(path)
    if len(addresses) == 0:
        print("No valid addresses found in file.")
        return
    if count > len(addresses):
        print(
            f"Requested {count} injections, but only {len(addresses)} addresses found."
        )
        return

    print(
        f"Performing {count} bitflip injections from {len(addresses)} available addresses..."
    )
    targets = random.sample(addresses, count)
    for address in targets:
        try:
            inject_bitflip(address, 1)
        except Exception as e:
            print(f"Injection failed at 0x{address:x}: {e}")
