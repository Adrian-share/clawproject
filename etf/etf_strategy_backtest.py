#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""ETF ETF Strategy Backtest - Compare two buy signal strategies"""

import json
import akshare as ak
from datetime import datetime, timedelta
from pathlib import Path

# Config path
CONFIG_PATH = "/root/.openclaw/workspace/config/etf-monitor.json"

print("Loading config...")
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    config = json.load(f)

etf_list = []
for category, etfs in config['etf_list'].items():
    for etf in etfs:
        etf['category'] = category
        etf_list.append(etf)

print(f"Starting backtest on {len(etf_list)} ETFs...\n")

# Backtest parameters
LOOKBACK_DAYS = 90  # 90 days backtest

# Strategy 1: Original - M5 > M10 > M20 and all MAs are rising
def strategy_original(m5, m10, m20, m5_prev, m10_prev, m20_prev):
    """Original strategy: MA alignment up + all MAs rising"""
    ma_alignment = (m5 > m10) and (m10 > m20)
    ma_rising = (m5 > m5_prev) and (m10 > m10_prev) and (m20 > m20_prev)
    return ma_alignment and ma_rising

# Strategy 2: New - M5, M10, M20 all higher than previous day
def strategy_new(m5, m10, m20, m5_prev, m10_prev, m20_prev):
    """New strategy: all MAs higher than previous day"""
    return (m5 > m5_prev) and (m10 > m10_prev) and (m20 > m20_prev)

# Statistics
stats = {
    'original': {'signals': 0, 'avg_gain_3d': 0, 'avg_gain_5d': 0, 'valid_gains_3d': 0, 'valid_gains_5d': 0, 'details': []},
    'new': {'signals': 0, 'avg_gain_3d': 0, 'avg_gain_5d': 0, 'valid_gains_3d': 0, 'valid_gains_5d': 0, 'details': []},
}

count = 0
for etf in etf_list[:30]:  # Test first 30 ETFs
    code = etf['code']
    name = etf['name']
    count += 1
    print(f"Progress: {count}/{min(30, len(etf_list))} - {name} ({code})")
    
    # Get data
    if code.startswith('51') or code.startswith('58'):
        symbol = 'sh' + code
    else:
        symbol = 'sz' + code
    
    try:
        df = ak.fund_etf_hist_sina(symbol=symbol)
        df = df.sort_values('date')
        df = df.tail(LOOKBACK_DAYS + 10)  # Get more data for calculation
        
        if len(df) < 30:
            continue
        
        prices = df['close'].tolist()
        dates = df['date'].tolist()
        
        # Calculate daily MAs
        ma_data = []
        for i in range(len(prices)):
            if i < 19:  # Need at least 20 days for M20
                ma_data.append(None)
                continue
            
            # Calculate current day MAs
            m5 = sum(prices[i-4:i+1]) / 5
            m10 = sum(prices[i-9:i+1]) / 10
            m20 = sum(prices[i-19:i+1]) / 20
            
            # Calculate previous day MAs (if possible)
            m5_prev = None
            m10_prev = None
            m20_prev = None
            if i >= 20:
                m5_prev = sum(prices[i-5:i]) / 5
                m10_prev = sum(prices[i-10:i]) / 10
                m20_prev = sum(prices[i-20:i]) / 20
            
            ma_data.append({
                'date': dates[i],
                'price': prices[i],
                'm5': m5,
                'm10': m10,
                'm20': m20,
                'm5_prev': m5_prev,
                'm10_prev': m10_prev,
                'm20_prev': m20_prev,
            })
        
        # Backtest strategies
        for i in range(len(ma_data)):
            if ma_data[i] is None or i < 20:
                continue
            
            data = ma_data[i]
            
            # Check original strategy signal
            if strategy_original(data['m5'], data['m10'], data['m20'], 
                                data['m5_prev'], data['m10_prev'], data['m20_prev']):
                stats['original']['signals'] += 1
                
                # Calculate future gains
                gain_3d = None
                gain_5d = None
                
                if i + 3 < len(prices):
                    gain_3d = (prices[i+3] - data['price']) / data['price'] * 100
                    stats['original']['avg_gain_3d'] += gain_3d
                    stats['original']['valid_gains_3d'] += 1
                
                if i + 5 < len(prices):
                    gain_5d = (prices[i+5] - data['price']) / data['price'] * 100
                    stats['original']['avg_gain_5d'] += gain_5d
                    stats['original']['valid_gains_5d'] += 1
                
                stats['original']['details'].append({
                    'etf': name,
                    'code': code,
                    'date': data['date'],
                    'price': data['price'],
                    'gain_3d': gain_3d,
                    'gain_5d': gain_5d,
                })
            
            # Check new strategy signal
            if strategy_new(data['m5'], data['m10'], data['m20'], 
                           data['m5_prev'], data['m10_prev'], data['m20_prev']):
                stats['new']['signals'] += 1
                
                # Calculate future gains
                gain_3d = None
                gain_5d = None
                
                if i + 3 < len(prices):
                    gain_3d = (prices[i+3] - data['price']) / data['price'] * 100
                    stats['new']['avg_gain_3d'] += gain_3d
                    stats['new']['valid_gains_3d'] += 1
                
                if i + 5 < len(prices):
                    gain_5d = (prices[i+5] - data['price']) / data['price'] * 100
                    stats['new']['avg_gain_5d'] += gain_5d
                    stats['new']['valid_gains_5d'] += 1
                
                stats['new']['details'].append({
                    'etf': name,
                    'code': code,
                    'date': data['date'],
                    'price': data['price'],
                    'gain_3d': gain_3d,
                    'gain_5d': gain_5d,
                })
                
    except Exception as e:
        print(f"Skip {name} ({code}): {e}")

# Calculate averages
for strategy in ['original', 'new']:
    if stats[strategy]['valid_gains_3d'] > 0:
        stats[strategy]['avg_gain_3d'] = stats[strategy]['avg_gain_3d'] / stats[strategy]['valid_gains_3d']
    if stats[strategy]['valid_gains_5d'] > 0:
        stats[strategy]['avg_gain_5d'] = stats[strategy]['avg_gain_5d'] / stats[strategy]['valid_gains_5d']
    
    # Calculate win rate
    stats[strategy]['win_rate_3d'] = 0
    stats[strategy]['win_rate_5d'] = 0
    
    if stats[strategy]['valid_gains_3d'] > 0:
        wins_3d = sum(1 for d in stats[strategy]['details'] if d['gain_3d'] is not None and d['gain_3d'] > 0)
        stats[strategy]['win_rate_3d'] = wins_3d / stats[strategy]['valid_gains_3d'] * 100
    
    if stats[strategy]['valid_gains_5d'] > 0:
        wins_5d = sum(1 for d in stats[strategy]['details'] if d['gain_5d'] is not None and d['gain_5d'] > 0)
        stats[strategy]['win_rate_5d'] = wins_5d / stats[strategy]['valid_gains_5d'] * 100

# Output results
print()
print("=" * 60)
print("ETF Buy Strategy Backtest Report")
print("Backtest Period: 90 days")
print("=" * 60)
print()

print("【Strategy 1: Original】")
print("Condition: M5 > M10 > M20 and all MAs are rising")
print(f"Total signals: {stats['original']['signals']}")
print(f"3-day avg gain: {stats['original']['avg_gain_3d']:.2f}%")
print(f"3-day win rate: {stats['original']['win_rate_3d']:.1f}%")
print(f"5-day avg gain: {stats['original']['avg_gain_5d']:.2f}%")
print(f"5-day win rate: {stats['original']['win_rate_5d']:.1f}%")
print()

print("【Strategy 2: New】")
print("Condition: M5, M10, M20 all higher than previous day")
print(f"Total signals: {stats['new']['signals']}")
print(f"3-day avg gain: {stats['new']['avg_gain_3d']:.2f}%")
print(f"3-day win rate: {stats['new']['win_rate_3d']:.1f}%")
print(f"5-day avg gain: {stats['new']['avg_gain_5d']:.2f}%")
print(f"5-day win rate: {stats['new']['win_rate_5d']:.1f}%")
print()

# Comparison analysis
print("=" * 60)
print("【Comparison Analysis】")
print("=" * 60)
print()

signal_diff = stats['new']['signals'] - stats['original']['signals']
print(f"Signal count: New strategy is {'more' if signal_diff > 0 else 'less'} by {abs(signal_diff)}")
print()

gain_3d_diff = stats['new']['avg_gain_3d'] - stats['original']['avg_gain_3d']
print(f"3-day gain: New strategy is {'higher' if gain_3d_diff > 0 else 'lower'} by {abs(gain_3d_diff):.2f}%")
print()

gain_5d_diff = stats['new']['avg_gain_5d'] - stats['original']['avg_gain_5d']
print(f"5-day gain: New strategy is {'higher' if gain_5d_diff > 0 else 'lower'} by {abs(gain_5d_diff):.2f}%")
print()

win_rate_3d_diff = stats['new']['win_rate_3d'] - stats['original']['win_rate_3d']
print(f"3-day win rate: New strategy is {'higher' if win_rate_3d_diff > 0 else 'lower'} by {abs(win_rate_3d_diff):.1f}%")
print()

win_rate_5d_diff = stats['new']['win_rate_5d'] - stats['original']['win_rate_5d']
print(f"5-day win rate: New strategy is {'higher' if win_rate_5d_diff > 0 else 'lower'} by {abs(win_rate_5d_diff):.1f}%")
print()

# Conclusion
print("=" * 60)
print("【Conclusion】")
print("=" * 60)
print()

if stats['new']['avg_gain_3d'] > stats['original']['avg_gain_3d'] and \
   stats['new']['win_rate_3d'] > stats['original']['win_rate_3d']:
    print("✅ Recommend [New Strategy]")
    print("   New strategy performs better in both gain and win rate")
elif stats['original']['avg_gain_3d'] > stats['new']['avg_gain_3d'] and \
     stats['original']['win_rate_3d'] > stats['new']['win_rate_3d']:
    print("✅ Recommend [Original Strategy]")
    print("   Original strategy performs better in both gain and win rate")
else:
    print("⚠️  Both strategies have pros and cons")
    print("   Choose based on your preference:")
    if stats['new']['signals'] > stats['original']['signals']:
        print("   - New strategy: More signals, more opportunities")
    else:
        print("   - Original strategy: Fewer signals, more strict")
    if stats['new']['win_rate_3d'] > stats['original']['win_rate_3d']:
        print("   - New strategy: Higher win rate")
    else:
        print("   - Original strategy: Higher win rate")

print()
print("=" * 60)
