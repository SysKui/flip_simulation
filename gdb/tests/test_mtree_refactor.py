#!/usr/bin/env python3
"""
Test script to verify the refactored mtree parsing functionality.
"""

import sys
import os

# Add the gdb directory to the path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'gdb'))

from qemu_utils import _parse_mtree_output, MemoryRange, FlatView

# Sample mtree output from the terminal
SAMPLE_MTREE_OUTPUT = """FlatView #0
 AS "I/O", root: io
 Root memory region: io
  0000000000000000-000000000000ffff (prio 0, i/o): io

FlatView #1
 AS "gpex-root", root: bus master container
 AS "pvpanic-pci", root: bus master container
 Root memory region: (none)
  No rendered FlatView

FlatView #2
 AS "virtio-pci-cfg-mem-as", root: virtio-pci
 Root memory region: virtio-pci
  0000008000004000-0000008000004fff (prio 0, i/o): virtio-pci-common-virtio-9p
  0000008000005000-0000008000005fff (prio 0, i/o): virtio-pci-isr-virtio-9p

FlatView #5
 AS "memory", root: system
 AS "cpu-memory-0", root: system
 Root memory region: system
  0000000000000000-0000000003ffffff (prio 0, romd): virt.flash0
  0000000004000000-0000000007ffffff (prio 0, romd): virt.flash1
  0000000040000000-000000013fffffff (prio 0, ram): mach-virt.ram
"""

def test_memory_range_parsing():
    """Test MemoryRange.parse method."""
    print("Testing MemoryRange.parse...")
    
    # Test valid memory range line
    line = "  0000000000000000-000000000000ffff (prio 0, i/o): io"
    range_obj = MemoryRange.parse(line)
    
    assert range_obj.start == 0x0000000000000000
    assert range_obj.end == 0x000000000000ffff
    assert range_obj.priority == 0
    assert range_obj.kind == "i/o"
    assert range_obj.name == "io"
    
    # Test another valid line
    line2 = "  0000000040000000-000000013fffffff (prio 0, ram): mach-virt.ram"
    range_obj2 = MemoryRange.parse(line2)
    
    assert range_obj2.start == 0x0000000040000000
    assert range_obj2.end == 0x000000013fffffff
    assert range_obj2.priority == 0
    assert range_obj2.kind == "ram"
    assert range_obj2.name == "mach-virt.ram"
    
    print("✓ MemoryRange.parse tests passed")

def test_flatview_parsing():
    """Test FlatView.parse method."""
    print("Testing FlatView.parse...")
    
    lines = [
        "  0000000000000000-000000000000ffff (prio 0, i/o): io",
        "  0000000040000000-000000013fffffff (prio 0, ram): mach-virt.ram"
    ]
    
    flatview = FlatView.parse(lines)
    
    assert len(flatview.ranges) == 2
    assert flatview.ranges[0].name == "io"
    assert flatview.ranges[1].name == "mach-virt.ram"
    
    # Test ram_ranges method
    ram_ranges = flatview.ram_ranges()
    assert len(ram_ranges) == 1
    assert ram_ranges[0] == (0x0000000040000000, 0x000000013fffffff)
    
    print("✓ FlatView.parse tests passed")

def test_mtree_output_parsing():
    """Test the complete mtree output parsing."""
    print("Testing _parse_mtree_output...")
    
    views = _parse_mtree_output(SAMPLE_MTREE_OUTPUT)
    
    # Check that we have the expected address spaces
    expected_as = {"I/O", "virtio-pci-cfg-mem-as", "memory", "cpu-memory-0"}
    actual_as = set(views.keys())
    
    print(f"Expected address spaces: {expected_as}")
    print(f"Actual address spaces: {actual_as}")
    
    assert expected_as.issubset(actual_as), f"Missing address spaces: {expected_as - actual_as}"
    
    # Check I/O address space
    io_view = views["I/O"]
    assert len(io_view.ranges) == 1
    assert io_view.ranges[0].name == "io"
    
    # Check memory address space (should have RAM)
    memory_view = views["memory"]
    ram_ranges = memory_view.ram_ranges()
    assert len(ram_ranges) >= 1, "Memory view should have at least one RAM range"
    
    # Check that empty FlatViews are handled (gpex-root and pvpanic-pci should be removed)
    assert "gpex-root" not in views
    assert "pvpanic-pci" not in views
    
    print("✓ _parse_mtree_output tests passed")

def test_error_handling():
    """Test error handling for invalid input."""
    print("Testing error handling...")
    
    # Test invalid memory range line
    try:
        MemoryRange.parse("invalid line format")
        assert False, "Should have raised ValueError"
    except ValueError:
        pass  # Expected
    
    # Test FlatView with invalid lines (should skip them)
    lines_with_invalid = [
        "  0000000000000000-000000000000ffff (prio 0, i/o): io",
        "invalid line",
        "  0000000040000000-000000013fffffff (prio 0, ram): mach-virt.ram"
    ]
    
    flatview = FlatView.parse(lines_with_invalid)
    assert len(flatview.ranges) == 2  # Should skip the invalid line
    
    print("✓ Error handling tests passed")

def main():
    """Run all tests."""
    print("Running mtree refactor tests...\n")
    
    try:
        test_memory_range_parsing()
        test_flatview_parsing()
        test_mtree_output_parsing()
        test_error_handling()
        
        print("\n✅ All tests passed! The mtree refactor is working correctly.")
        return 0
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())
