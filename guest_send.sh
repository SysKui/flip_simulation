#!/bin/bash
# guest_send.sh

# 获取 virtio 串口路径
VPORT_PATH=$(find /dev -name 'vport*' | head -n 1)

echo "[GUEST] Using virtio port: $VPORT_PATH"

# 检查是否提供了启动命令
if [ $# -lt 1 ]; then
  echo "[GUEST] No application command provided."
  exit 1
fi

# 如果第一个参数是 -f，则使用模糊匹配模式
if [ "$1" = "-f" ]; then
  shift  # 移除 -f
  APP_CMD="$@"
  echo "[GUEST] Running application (fuzzy match): $APP_CMD"
  $APP_CMD &
  APP_PID=$!
  echo "[GUEST] Running: python3 find_phys_ranges.py -f \"$APP_CMD\""
  python3 find_phys_ranges.py -f "$APP_CMD" > output.log 2>&1
else
  APP_CMD="$@"
  echo "[GUEST] Running application: $APP_CMD"
  $APP_CMD &
  APP_PID=$!
  echo "[GUEST] Running: python3 find_phys_ranges.py \"$APP_CMD\""
  python3 find_phys_ranges.py "$APP_CMD" > output.log 2>&1
fi

# # 等待主应用执行完成
# wait $APP_PID

# 模拟工作完成
echo "[GUEST] Work done. Signaling host..."
echo "done" > "$VPORT_PATH"
echo "[GUEST] Signal sent."
