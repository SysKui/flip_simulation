from qemu_utils import Registers

def test_singleton():
    """测试单例模式"""
    print("test singleton started")
    # 测试 Registers 单例
    reg1 = Registers()
    reg2 = Registers()
    
    assert reg1 is reg2
    assert reg1.list_registers() != None and len(reg1.list_registers()) > 0
    print("test pass")
    
test_singleton()