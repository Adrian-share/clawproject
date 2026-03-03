#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ETF 趋势监控 Agent - 运行并发送报告"""

import subprocess
from datetime import datetime

# 用户 ID
USER_ID = "ou_4a33c49696cfcfd08b9df1e1a5c06df5"

# 脚本路径
SCRIPT_PATH = "/root/.openclaw/workspace/scripts/etf_monitor.py"

print(f"开始运行 ETF 监控...")

# 运行监控脚本
result = subprocess.run(
    ['python3', SCRIPT_PATH],
    capture_output=True,
    text=True,
    timeout=120
)

if result.returncode == 0:
    report = result.stdout
    
    # 发送给用户
    print(f"发送报告给用户 {USER_ID}...")
    # 这里只是模拟发送，实际通过飞书消息工具发送
    print(f"\n{report}")
    print("\n报告已生成，需要通过消息工具发送给用户")
else:
    print(f"错误: {result.stderr}")
