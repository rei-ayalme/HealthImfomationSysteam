# modules/dpio_checker.py
import os
import subprocess
from config.settings import DPIO_CONFIG
from pydantic import BaseModel
from typing import List, Dict, Optional


# 定义DPIO检查结果模型
class DPIOCheckResult(BaseModel):
    status: bool  # 整体状态
    check_items: List[Dict]  # 各检查项结果
    hardware_info: Optional[Dict] = None  # 硬件/驱动信息
    error_msg: Optional[str] = None  # 错误信息


def exec_linux_cmd(cmd: str, timeout: int = 5) -> (str, int):
    """执行Linux系统命令，返回输出和退出码"""
    try:
        res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return res.stdout.strip(), res.returncode
    except subprocess.TimeoutExpired:
        return "命令超时", -1
    except Exception as e:
        return str(e), -2


def check_dpio_driver() -> Dict:
    """检查DPIO驱动加载状态"""
    # 检查dpio驱动是否加载
    cmd = "lsmod | grep dpio"
    output, code = exec_linux_cmd(cmd)
    if code == 0 and "dpio" in output:
        return {"status": True, "msg": f"DPIO驱动已加载：{output[:100]}"}
    else:
        return {"status": False, "msg": f"DPIO驱动未加载，命令输出：{output}"}


def check_dpio_hardware() -> Dict:
    """检查DPIO硬件设备节点和驱动绑定"""
    check_items = []
    # 检查设备节点是否存在
    if os.path.exists(DPIO_CONFIG["buffer_pool"]):
        check_items.append({"item": "设备节点", "status": True, "msg": f"存在：{DPIO_CONFIG['buffer_pool']}"})
    else:
        check_items.append({"item": "设备节点", "status": False, "msg": f"不存在：{DPIO_CONFIG['buffer_pool']}"})

    # 检查驱动与硬件绑定
    cmd = f"ls {DPIO_CONFIG['driver_path']} 2>/dev/null | grep -v 'module'"
    output, code = exec_linux_cmd(cmd)
    if code == 0 and output != "":
        check_items.append({"item": "驱动绑定", "status": True, "msg": f"硬件绑定成功：{output}"})
    else:
        check_items.append({"item": "驱动绑定", "status": False, "msg": "驱动未绑定硬件"})

    # 整体状态
    overall = all([item["status"] for item in check_items])
    return {"status": overall, "msg": check_items}


def check_dpio_frame_io() -> Dict:
    """检查DPIO帧收发（入队/出队）和数据完整性"""
    # 注：实际DPIO帧收发需调用硬件厂商提供的SDK/库，此处为通用测试逻辑（基于内核sysfs）
    test_frame = DPIO_CONFIG["test_frame_data"]
    # 模拟入队/出队（实际项目替换为厂商SDK调用）
    try:
        # 检查缓冲区可写
        if os.access(DPIO_CONFIG["buffer_pool"], os.W_OK):
            # 模拟写入测试帧
            with open(DPIO_CONFIG["buffer_pool"], "wb") as f:
                f.write(test_frame)
            # 模拟读取数据
            with open(DPIO_CONFIG["buffer_pool"], "rb") as f:
                read_data = f.read(len(test_frame))
            # 验证数据完整性
            if read_data == test_frame:
                return {"status": True, "msg": f"帧收发成功，数据完整：发送{test_frame}，接收{read_data}"}
            else:
                return {"status": False, "msg": "数据丢失/篡改，收发不一致"}
        else:
            return {"status": False, "msg": f"缓冲区{DPIO_CONFIG['buffer_pool']}不可写"}
    except Exception as e:
        return {"status": False, "msg": f"帧收发失败：{str(e)[:100]}"}


# DPIO接口统一检查入口
def check_dpio_interface() -> DPIOCheckResult:
    """DPIO接口完整检查"""
    check_items = []
    hardware_info = {}

    # 检查项1：DPIO驱动加载
    driver_check = check_dpio_driver()
    check_items.append({"item": "驱动加载", **driver_check})
    if driver_check["status"]:
        hardware_info["driver"] = driver_check["msg"]

    # 检查项2：硬件设备与驱动绑定
    hardware_check = check_dpio_hardware()
    check_items.append({"item": "硬件绑定", **hardware_check})
    if hardware_check["status"]:
        hardware_info["hardware"] = hardware_check["msg"]

    # 若驱动/硬件检查失败，直接返回
    if not all([item["status"] for item in check_items[:2]]):
        return DPIOCheckResult(
            status=False,
            check_items=check_items,
            hardware_info=hardware_info,
            error_msg="驱动/硬件检查失败，终止后续测试"
        )

    # 检查项3：帧收发与数据完整性
    frame_check = check_dpio_frame_io()
    check_items.append({"item": "帧收发与数据完整性", **frame_check})

    # 整体状态
    overall_status = all([item["status"] for item in check_items])
    return DPIOCheckResult(
        status=overall_status,
        check_items=check_items,
        hardware_info=hardware_info,
        error_msg=None if overall_status else "部分检查项失败"
    )


# 本地测试
if __name__ == "__main__":
    result = check_dpio_interface()
    print(f"DPIO接口检查结果：{'成功' if result.status else '失败'}")
    print(f"检查项详情：{result.check_items}")
    if result.hardware_info:
        print(f"硬件/驱动信息：{result.hardware_info}")