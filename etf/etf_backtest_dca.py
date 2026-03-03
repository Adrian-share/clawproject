#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ETF 策略回测：单次买入 vs 每天定投"""

import json
import akshare as ak
from datetime import datetime, timedelta
from pathlib import Path

# 配置文件路径
CONFIG_PATH = "/root/.openclaw/workspace/config/etf-monitor.json"

print("正在加载配置...")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

etf_list = []
for category, etfs in config['etf_list'].items():
    for etf in etfs:
        etf['category'] = category
        etf_list.append(etf)

# 回测参数
DCA_DAILY_AMOUNT = 100  # 每天定投股数
BUY_ONE_AMOUNT = 100    # 单次买入股数
BACKTEST_DAYS = 90      # 回测天数

print(f"\n回测参数:")
print(f"- 回测周期: {BACKTEST_DAYS} 天")
print(f"- 策略A（单次买入）: 信号出现当天买入 {BUY_ONE_AMOUNT} 股")
print(f"- 策略B（每天定投）: 信号期间每天买入 {DCA_DAILY_AMOUNT} 股")
print(f"\n开始回测 {len(etf_list)} 个 ETF...\n")

results = []

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
        df = df.tail(BACKTEST_DAYS + 50)  # 多取一些数据用于计算均线
        
        if len(df) < BACKTEST_DAYS:
            continue
        
        # 转换为列表便于处理
        dates = df['date'].tolist()
        prices = df['close'].tolist()
        
        # 回测
        strategy_a = {'cash': 0, 'shares': 0, 'investments': []}
        strategy_b = {'cash': 0, 'shares': 0, 'investments': [], 'in_position': False}
        
        for i in range(30, len(prices)):  # 从第30天开始，确保有足够数据计算均线
            current_price = prices[i]
            current_date = dates[i]
            
            # 计算均线
            m5 = sum(prices[i-4:i+1]) / 5
            m10 = sum(prices[i-9:i+1]) / 10
            m20 = sum(prices[i-19:i+1]) / 20
            m20_prev = sum(prices[i-20:i]) / 20 if i >= 20 else m20
            
            # 买入信号
            ma_alignment = (m5 > m10) and (m10 > m20)
            ma_rising = True
            if i >= 5:
                m5_prev = sum(prices[i-5:i]) / 5
                m10_prev = sum(prices[i-10:i]) / 10
                if m5 < m5_prev or m10 < m10_prev:
                    ma_rising = False
            buy_signal = ma_alignment and ma_rising
            
            # 卖出信号
            sell_signal = m20 < m20_prev
            
            # 策略A：单次买入
            if buy_signal and strategy_a['shares'] == 0:
                cost = current_price * BUY_ONE_AMOUNT
                strategy_a['shares'] = BUY_ONE_AMOUNT
                strategy_a['cash'] -= cost
                strategy_a['investments'].append({
                    'date': current_date,
                    'price': current_price,
                    'shares': BUY_ONE_AMOUNT,
                    'type': 'buy'
                })
            
            if sell_signal and strategy_a['shares'] > 0:
                revenue = current_price * strategy_a['shares']
                strategy_a['cash'] += revenue
                strategy_a['investments'].append({
                    'date': current_date,
                    'price': current_price,
                    'shares': strategy_a['shares'],
                    'type': 'sell'
                })
                strategy_a['shares'] = 0
            
            # 策略B：每天定投
            # 首次买入信号触发，进入定投状态
            if buy_signal and not strategy_b['in_position']:
                strategy_b['in_position'] = True
            
            # 卖出信号触发，退出定投状态并清仓
            if sell_signal and strategy_b['in_position']:
                if strategy_b['shares'] > 0:
                    revenue = current_price * strategy_b['shares']
                    strategy_b['cash'] += revenue
                    strategy_b['investments'].append({
                        'date': current_date,
                        'price': current_price,
                        'shares': strategy_b['shares'],
                        'type': 'sell'
                    })
                    strategy_b['shares'] = 0
                strategy_b['in_position'] = False
            
            # 定投期间，每天买入
            if strategy_b['in_position']:
                cost = current_price * DCA_DAILY_AMOUNT
                strategy_b['shares'] += DCA_DAILY_AMOUNT
                strategy_b['cash'] -= cost
                strategy_b['investments'].append({
                    'date': current_date,
                    'price': current_price,
                    'shares': DCA_DAILY_AMOUNT,
                    'type': 'buy_dca'
                })
        
        # 计算最终价值（如果还持有，按最后价格计算）
        final_price = prices[-1]
        
        # 策略A
        if strategy_a['shares'] > 0:
            strategy_a['cash'] += strategy_a['shares'] * final_price
        
        # 策略B
        if strategy_b['shares'] > 0:
            strategy_b['cash'] += strategy_b['shares'] * final_price
        
        # 统计
        a_trades = len([x for x in strategy_a['investments'] if x['type'] in ['buy', 'sell']])
        b_buys = len([x for x in strategy_b['investments'] if x['type'] == 'buy_dca'])
        b_sells = len([x for x in strategy_b['investments'] if x['type'] == 'sell'])
        
        results.append({
            'code': code,
            'name': name,
            'strategy_a_profit': strategy_a['cash'],
            'strategy_a_trades': a_trades,
            'strategy_b_profit': strategy_b['cash'],
            'strategy_b_buys': b_buys,
            'strategy_b_sells': b_sells,
            'final_price': final_price
        })
        
    except Exception as e:
        print(f"跳过 {name} ({code}): {e}")
        continue

# 输出结果
print("\n" + "="*90)
print(f"回测结果对比（过去 {BACKTEST_DAYS} 天）")
print("="*90 + "\n")

print(f"{'ETF代码':<10} {'ETF名称':<18} {'策略A收益':<10} {'交易次数':<8} {'策略B收益':<10} {'定投天数':<8} {'优势':<8}")
print("-"*100)

for r in results:
    a_profit = r['strategy_a_profit']
    b_profit = r['strategy_b_profit']
    
    if a_profit > b_profit:
        advantage = "A更好"
    elif b_profit > a_profit:
        advantage = "B更好"
    else:
        advantage = "持平"
    
    print(f"{r['code']:<10} {r['name']:<18} {a_profit:>8.2f}   {r['strategy_a_trades']:^6}   {b_profit:>8.2f}   {r['strategy_b_buys']:^6}   {advantage:^6}")

# 汇总统计
total_a = sum(r['strategy_a_profit'] for r in results)
total_b = sum(r['strategy_b_profit'] for r in results)
win_a = sum(1 for r in results if r['strategy_a_profit'] > r['strategy_b_profit'])
win_b = sum(1 for r in results if r['strategy_b_profit'] > r['strategy_a_profit'])
draw = sum(1 for r in results if r['strategy_a_profit'] == r['strategy_b_profit'])

print("\n" + "="*90)
print("汇总统计")
print("="*90)
print(f"策略A（单次买入）总收益: {total_a:.2f}")
print(f"策略B（每天定投）总收益: {total_b:.2f}")
print(f"策略A胜出: {win_a} 次")
print(f"策略B胜出: {win_b} 次")
print(f"平局: {draw} 次")
print(f"策略A平均收益: {total_a/len(results):.2f}")
print(f"策略B平均收益: {total_b/len(results):.2f}")

if total_b > total_a:
    improvement = ((total_b - total_a) / abs(total_a)) * 100
    print(f"\n✅ 每天定投策略整体优于单次买入，提升 {improvement:.2f}%")
elif total_a > total_b:
    decline = ((total_a - total_b) / abs(total_b)) * 100
    print(f"\n⚠️ 单次买入策略整体优于每天定投，定投下降 {decline:.2f}%")
else:
    print(f"\n➖ 两种策略收益持平")
