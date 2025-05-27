#!/usr/bin/env python3
"""测试脚本，验证 argparse 参数解析是否正确工作"""

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

def test_inject_command():
    """测试 inject 命令的参数解析"""
    print("Testing inject command:")
    
    parser = argparse.ArgumentParser(description="Inject a bitflip at an address",
                                   prog="inject")
    parser.add_argument('--address', help='Address to inject bitflip (if not specified, randomly selected)')
    parser.add_argument('--bytewidth', type=int, 
                       help='Byte width (default: 4 if address specified, 1 if random)')
    parser.add_argument('--bit', type=int, help='Bit index within the integer to flip')
    
    # 测试用例
    test_cases = [
        "",  # 空参数
        "--address 0x1234",  # 只有地址
        "--address 0x1234 --bytewidth 4",  # 地址和字节宽度
        "--address 0x1234 --bytewidth 4 --bit 3",  # 所有参数
        "--bit 5",  # 只有位索引
        "--invalid-arg test",  # 无效参数
    ]
    
    for test_case in test_cases:
        print(f"  Input: '{test_case}'")
        result = parse_args_safely(parser, test_case)
        if result:
            print(f"    Result: address={result.address}, bytewidth={result.bytewidth}, bit={result.bit}")
        else:
            print("    Result: Failed to parse")
        print()

def test_autoinject_command():
    """测试 autoinject 命令的参数解析"""
    print("Testing autoinject command:")
    
    parser = argparse.ArgumentParser(description="Automatically inject faults into the VM",
                                   prog="autoinject")
    parser.add_argument('--total-fault-number', type=int, required=True, help='Total number of faults to inject')
    parser.add_argument('--min-interval', required=True, help='Minimum interval between injections (with unit: ns, us, ms, s, m)')
    parser.add_argument('--max-interval', required=True, help='Maximum interval between injections (with unit: ns, us, ms, s, m)')
    parser.add_argument('--fault-type', choices=['ram', 'reg'], required=True, help='Type of fault to inject')
    
    # 测试用例
    test_cases = [
        "--total-fault-number 10 --min-interval 100ms --max-interval 200ms --fault-type ram",  # 完整参数
        "--total-fault-number 5 --min-interval 50us --max-interval 100us --fault-type reg",  # 完整参数（reg类型）
        "--total-fault-number 10",  # 缺少必需参数
        "--total-fault-number 10 --min-interval 100ms --max-interval 200ms --fault-type invalid",  # 无效fault-type
    ]
    
    for test_case in test_cases:
        print(f"  Input: '{test_case}'")
        result = parse_args_safely(parser, test_case)
        if result:
            print(f"    Result: total_fault_number={getattr(result, 'total_fault_number')}, "
                  f"min_interval={getattr(result, 'min_interval')}, "
                  f"max_interval={getattr(result, 'max_interval')}, "
                  f"fault_type={getattr(result, 'fault_type')}")
        else:
            print("    Result: Failed to parse")
        print()

def test_loop_command():
    """测试 loop 命令的参数解析"""
    print("Testing loop command:")
    
    parser = argparse.ArgumentParser(description="Loop an action for the specified number of times",
                                   prog="loop")
    parser.add_argument('--times', type=int, required=True, help='Number of times to repeat the command')
    parser.add_argument('--command', required=True, help='Command to execute')
    parser.add_argument('--command-args', nargs='*', help='Arguments for the command')
    
    # 测试用例
    test_cases = [
        "--times 5 --command 'echo hello'",  # 简单命令
        "--times 3 --command ls --command-args -la /tmp",  # 带参数的命令
        "--times 10 --command inject --command-args --address 0x1234",  # 复杂命令
        "--times 2",  # 缺少命令
    ]
    
    for test_case in test_cases:
        print(f"  Input: '{test_case}'")
        result = parse_args_safely(parser, test_case)
        if result:
            print(f"    Result: times={result.times}, command={result.command}, "
                  f"command_args={getattr(result, 'command_args')}")
        else:
            print("    Result: Failed to parse")
        print()

if __name__ == "__main__":
    print("=== 测试 argparse 参数解析 ===\n")
    
    test_inject_command()
    test_autoinject_command()
    test_loop_command()
    
    print("=== 测试完成 ===")
