#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ETF 策略回测：计算每天定投的收益率"""

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
BACKTEST_DAYS = 90      # 回测天数

print(f"\n回测参数:")
print(f"- 回测周期: {BACKTEST_DAYS} 天")
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
        strategy_b = {
            'cash': 0, 
            'shares': 0, 
            'investments': [], 
            'in_position': False,
            'total_invested': 0
        }
        
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
                strategy_b['total_invested'] += cost
                strategy_b['investments'].append({
                    'date': current_date,
                    'price': current_price,
                    'shares': DCA_DAILY_AMOUNT,
                    'type': 'buy_dca',
                    'cost': cost
                })
        
        # 计算最终价值（如果还持有，按最后价格计算）
        final_price = prices[-1]
        
        # 如果还持有，清仓计算收益
        if strategy_b['shares'] > 0:
            revenue = strategy_b['shares'] * final_price
            strategy_b['cash'] += revenue
            strategy_b['shares'] = 0
        
        # 统计
        total_invested = strategy_b['total_invested']
        total_profit = strategy_b['cash']
        return_rate = (total_profit / total_invested * 100) if total_invested > 0 else 0
        
        results.append({
            'code': code,
            'name': name,
            'total_invested': total_invested,
            'total_profit': total_profit,
            'return_rate': return_rate,
            'buy_days': len([x for x in strategy_b['investments'] if x['type'] == 'buy_dca']),
            'final_price': final_price
        })
        
    except Exception as e:
        print(f"跳过 {name} ({code}): {e}")
        continue

# 输出结果
print("\n" + "="*90)
print(f"策略B（每天定投100股）收益率分析（过去 {BACKTEST_DAYS} 天）")
print("="*90 + "\n")

print(f"{'ETF代码':<10} {'ETF名称':<18} {'投入资金':<12} {'总收益':<10} {'收益率':<10} {'定投天数':<8}")
print("-"*80)

for r in results:
    if r['total_invested'] > 0:
        print(f"{r['code']:<10} {r['name']:<18} {r['total_invested']:>10.2f}   {r['total_profit']:>8.2f}   {r['return_rate']:>7.2f}%   {r['buy_days']:^6}")

# 汇总统计
results_with_investment = [r for r in results if r['total_invested'] > 0]
total_invested = sum(r['total_invested'] for r in results_with_investment)
total_profit = sum(r['total_profit'] for r in results_with_investment)
avg_return_rate = sum(r['return_rate'] for r in results_with_investment) / len(results_with_investment) if results_with_investment else 0
avg_invested = total_invested / len(results_with_investment) if results_with_investment else 0

print("\n" + "="*90)
print("汇总统计")
print("="*90)
print(f"回测 ETF 数量: {len(results_with_investment)}")
print(f"总投入资金: {total_invested:.2f}")
print(f"总收益: {total_profit:.2f}")
print(f"综合收益率: {(total_profit / total_invested * 100):.2f}%" if total_invested > 0 else "综合收益率: N/A")
print(f"平均单只ETF投入: {avg_invested:.2f}")
print(f"平均收益率: {avg_return_rate:.2f}%")

# 收益率分布
positive_returns = [r for r in results_with_investment if r['return_rate'] > 0]
negative_returns = [r for r in results_with_investment if r['return_rate'] < 0]

print(f"\n收益率分布:")
print(f"- 盈利 ETF: {len(positive_returns)} 只 ({len(positive_returns)/len(results_with_investment)*100:.1f}%)")
print(f"- 亏损 ETF: {len(negative_returns)} 只 ({len(negative_returns)/len(results_with_investment)*100:.1f}%)")
print(f"- 平均盈利: {sum(r['return_rate'] for r in positive_returns)/len(positive_returns):.2f}%" if positive_returns else "- 平均盈利: N/A")
print(f"- 平均亏损: {sum(r['return_rate'] for r in negative_returns)/len(negative_returns):.2f}%" if negative_returns else "- 平均亏损: N/A")

# 前5和后5
results_sorted = sorted(results_with_investment, key=lambda x: x['return_rate'], reverse=True)

print(f"\n收益 TOP 5:")
for i, r in enumerate(results_sorted[:5], 1):
    print(f"{i}. {r['name']} ({r['code']}): {r['return_rate']:.2f}%")

print(f"\n亏损 TOP 5:")
for i, r in enumerate(results_sorted[-5:], 1):
    print(f"{i}. {r['name']} ({r['code']}): {r['return_rate']:.2f}%")
