#!/usr/bin/env python3
"""
Simplified test script for argparse functionality
"""

import argparse
import shlex
import sys
from io import StringIO

def parse_args_safely(parser, args_str):
    """Safely parse arguments using argparse without causing system exit."""
    try:
        # Split the arguments string properly handling quotes
        args_list = shlex.split(args_str.strip()) if args_str.strip() else []
        
        # Capture stderr to avoid argparse printing to terminal
        old_stderr = sys.stderr
        sys.stderr = StringIO()
        
        try:
            result = parser.parse_args(args_list)
            return result
        finally:
            # Restore stderr
            error_output = sys.stderr.getvalue()
            sys.stderr = old_stderr
            if error_output:
                print(error_output.strip())
                
    except SystemExit:
        # argparse calls sys.exit() on error, we catch it and return None
        return None
    except Exception as e:
        print("Error parsing arguments: %s" % str(e))
        return None

def parse_time(s):
    """Parse time string with units"""
    time_units = {
        "": 1,
        "ns": 1,
        "us": 1000,
        "ms": 1000 * 1000,
        "s": 1000 * 1000 * 1000,
        "m": 60 * 1000 * 1000 * 1000,
    }
    
    for unit, mul in sorted(time_units.items()):
        if s.endswith(unit):
            try:
                res = int(s[:-len(unit)])
            except ValueError:
                continue  # try the next unit
            if res <= 0:
                raise ValueError("expected positive number of %s in %r" % (unit, s))
            return res * mul
    raise ValueError("could not parse units in %r" % s)

def test_parse_args_safely():
    """Test the parse_args_safely function"""
    print("Testing parse_args_safely function...")
    
    # Test case 1: Valid arguments
    parser = argparse.ArgumentParser()
    parser.add_argument('count', type=int)
    parser.add_argument('--verbose', action='store_true')
    
    result = parse_args_safely(parser, "10 --verbose")
    if result and result.count == 10 and result.verbose:
        print("✓ Test 1 passed: Valid arguments parsed correctly")
    else:
        print("✗ Test 1 failed: Valid arguments not parsed correctly")
    
    # Test case 2: Invalid arguments
    result = parse_args_safely(parser, "invalid_number")
    if result is None:
        print("✓ Test 2 passed: Invalid arguments handled gracefully")
    else:
        print("✗ Test 2 failed: Invalid arguments should return None")
    
    # Test case 3: Empty arguments with required parameters
    result = parse_args_safely(parser, "")
    if result is None:
        print("✓ Test 3 passed: Empty arguments handled gracefully")
    else:
        print("✗ Test 3 failed: Empty arguments should return None")

def test_inject_command_parser():
    """Test the inject command argument parsing"""
    print("\nTesting inject command parser...")
    
    parser = argparse.ArgumentParser(description="Inject a bitflip at an address",
                                   prog="inject")
    parser.add_argument('address', nargs='?', help='Address to inject bitflip')
    parser.add_argument('bytewidth', type=int, nargs='?', help='Byte width')
    parser.add_argument('bit', type=int, nargs='?', help='Bit index')
    
    # Test various argument combinations
    test_cases = [
        ("0x1000 4 3", "address with bytewidth and bit"),
        ("0x2000", "address only"),
        ("", "no arguments"),
        ("0x3000 8", "address with bytewidth"),
    ]
    
    for args_str, description in test_cases:
        result = parse_args_safely(parser, args_str)
        print(f"  {description}: {'✓' if result is not None else '✗'}")

def test_autoinject_parser():
    """Test the autoinject command argument parsing"""
    print("\nTesting autoinject command parser...")
    
    parser = argparse.ArgumentParser(description="Automatically inject faults into the VM",
                                   prog="autoinject")
    parser.add_argument('total_fault_number', type=int, help='Total number of faults to inject')
    parser.add_argument('min_interval', help='Minimum interval between injections')
    parser.add_argument('max_interval', help='Maximum interval between injections')
    parser.add_argument('fault_type', choices=['ram', 'reg'], help='Type of fault to inject')
    
    test_cases = [
        ("10 100ms 200ms ram", "valid autoinject command"),
        ("5 50us 100us reg", "valid register injection"),
        ("10 100ms 200ms invalid", "invalid fault type"),
        ("invalid 100ms 200ms ram", "invalid count"),
    ]
    
    for args_str, description in test_cases:
        result = parse_args_safely(parser, args_str)
        success = result is not None
        print(f"  {description}: {'✓' if success else '✗'}")

def test_time_parsing():
    """Test the time parsing function"""
    print("\nTesting time parsing...")
    
    test_cases = [
        ("100ns", 100),
        ("50us", 50000),
        ("10ms", 10000000),
        ("2s", 2000000000),
        ("1m", 60000000000),
        ("500", 500),  # no unit defaults to ns
    ]
    
    for time_str, expected in test_cases:
        try:
            result = parse_time(time_str)
            if result == expected:
                print(f"  {time_str} -> {result} ns: ✓")
            else:
                print(f"  {time_str} -> {result} ns (expected {expected}): ✗")
        except Exception as e:
            print(f"  {time_str} -> Error: {e}: ✗")

if __name__ == "__main__":
    print("Testing argparse modifications")
    print("=" * 40)
    
    test_parse_args_safely()
    test_inject_command_parser()
    test_autoinject_parser()
    test_time_parsing()
    
    print("\nTest completed!")
