#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ETF 趋势监控 Agent - 使用 AKShare 真实数据源"""

import json
import akshare as ak
from datetime import datetime
from pathlib import Path

# 配置文件路径
CONFIG_PATH = "/root/.openclaw/workspace/config/etf-monitor.json"
DATA_DIR = Path("/root/.openclaw/workspace/data/etf-monitor")
REPORT_DIR = Path("/root/.openclaw/workspace/ports")

DATA_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

print("正在加载配置...")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

etf_list = []
for category, etfs in config['etf_list'].items():
    for etf in etfs:
        etf['category'] = category
        etf_list.append(etf)

# 加载历史数据
data_file = DATA_DIR / "historical_data.json"
if data_file.exists():
    with open(data_file, 'r', encoding='utf-8') as f:
        historical_data = json.load(f)
else:
    historical_data = {}

print(f"开始分析 {len(etf_list)} 个 ETF...")

# 分析每个 ETF
results = {'buy_signals': [], 'sell_signals': [], 'watch_list': [], 'all_analysis': []}

for etf in etf_list:
    code = etf['code']
    name = etf['name']
    
    # 获取数据
    if code.startswith('51') or code.startswith('58'):
        symbol = 'sh' + code
    else:
        symbol = 'sz' + code
    
    try:
        df = ak.fund_etf_hist_sina(symbol=symbol)
        df = df.sort_values('date')
        df = df.tail(30)
        
        if len(df) < 20:
            continue
        
        recent_prices = df['close'].tolist()
        current_price = recent_prices[-1]
        
        # 计算均线
        m5 = sum(recent_prices[-5:]) / 5
        m10 = sum(recent_prices[-10:]) / 10
        m20 = sum(recent_prices[-20:]) / 20
        yesterday_m20 = sum(recent_prices[-21:-1]) / 20 if len(recent_prices) >= 21 else m20
        
        # 买入信号
        ma_alignment = (m5 > m10) and (m10 > m20)
        ma_rising = True
        if len(recent_prices) >= 6:
            m5_prev = sum(recent_prices[-6:-1]) / 5
            m10_prev = sum(recent_prices[-11:-1]) / 10
            if m5 < m5_prev or m10 < m10_prev:
                ma_rising = False
        buy_signal = ma_alignment and ma_rising
        
        # 卖出信号
        sell_signal = m20 < yesterday_m20
        
        # 接近突破
        near_breakthrough = abs(current_price - m20) / m20 < 0.01
        
        # 检查之前状态
        last_state = historical_data.get(code, {})
        was_buy = last_state.get('last_buy_signal', False)
        was_sell = last_state.get('last_sell_signal', False)
        
        new_buy = buy_signal and not was_buy
        new_sell = sell_signal and not was_sell
        
        # 更新状态
        historical_data[code] = {
            'name': name,
            'last_price': current_price,
            'last_m5': m5,
            'last_m10': m10,
            'last_m20': m20,
            'last_buy_signal': buy_signal,
            'last_sell_signal': sell_signal,
            'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        analysis = {
            'code': code,
            'name': name,
            'price': current_price,
            'm5': m5,
            'm10': m10,
            'm20': m20,
            'm20_prev': yesterday_m20,
            'buy_signal': new_buy,
            'sell_signal': new_sell,
            'near_breakthrough': near_breakthrough,
            'category': etf['category']
        }
        
        results['all_analysis'].append(analysis)
        
        if new_buy:
            results['buy_signals'].append(analysis)
        elif new_sell:
            results['sell_signals'].append(analysis)
        elif near_breakthrough:
            results['watch_list'].append(analysis)
            
    except Exception as e:
        print(f"跳过 {name} ({code}): {e}")

# 保存历史数据
with open(data_file, 'w', encoding='utf-8') as f:
    json.dump(historical_data, f, ensure_ascii=False, indent=2)

# 格式化报告
now = datetime.now().strftime('%Y-%m-%d %H:%M')
report_lines = [
    "ETF 趋势监控报告（M5/M10/M20 多周期策略）",
    "时间: " + now,
    "",
    "================================",
    "买入信号（多周期共振向上）",
    "================================"
]

if results['buy_signals']:
    for item in results['buy_signals']:
        report_lines.append("✅ " + item['name'] + " (" + item['code'] + ")")
        report_lines.append("   - 价格: %.4f" % item['price'])
        report_lines.append("   - M5: %.4f, M10: %.4f, M20: %.4f" % (item['m5'], item['m10'], item['m20']))
        report_lines.append("")
else:
    report_lines.append("无新买入信号")
    report_lines.append("")

report_lines.extend([
    "================================",
    "卖出信号（M20 拐头向下）",
    "================================"
])

if results['sell_signals']:
    for item in results['sell_signals']:
        report_lines.append("⚠️ " + item['name'] + " (" + item['code'] + ")")
        report_lines.append("   - 价格: %.4f" % item['price'])
        report_lines.append("   - M20: %.4f ↓ (昨: %.4f)" % (item['m20'], item['m20_prev']))
        report_lines.append("")
else:
    report_lines.append("无新卖出信号")
    report_lines.append("")

report_lines.extend([
    "================================",
    "趋势关注（接近突破）",
    "================================"
])

if results['watch_list']:
    for item in results['watch_list']:
        report_lines.append("⭐ " + item['name'] + " (" + item['code'] + ")")
        report_lines.append("   - 价格: %.4f" % item['price'])
        report_lines.append("   - M20: %.4f" % item['m20'])
        report_lines.append("")
else:
    report_lines.append("无")
    report_lines.append("")

report_lines.extend([
    "================================",
    "监控汇总",
    "================================",
    "总监控 ETF 数: %d" % len(results['all_analysis']),
    "新买入信号: %d 个" % len(results['buy_signals']),
    "新卖出信号: %d 个" % len(results['sell_signals']),
    "关注列表: %d 个" % len(results['watch_list']),
    "",
    "策略说明:",
    "- 买入: M5 > M10 > M20 且每个均线都在上升",
    "- 卖出: M20 拐头向下（M20 今日值 < M20 昨日值）"
])

report = "\n".join(report_lines)

# 保存报告
report_file = REPORT_DIR / ("report_" + datetime.now().strftime('%Y%m%d') + ".txt")
with open(report_file, 'w', encoding='utf-8') as f:
    f.write(report)

print("\n" + report)
print(f"\n报告已保存: {report_file}")
