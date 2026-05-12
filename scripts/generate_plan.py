import json
import requests
from datetime import datetime
import pandas as pd
import numpy as np

def get_ohlcv_data():
    """Obtiene datos de XAUUSD desde una API gratuita"""
    
    # Usando Twelve Data API (gratis 800 requests/día)
    # Regístrate en: https://twelvedata.com/apikey
    
    api_key = "tu_api_key_aqui"  # Lo pondremos como secreto
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=1h&outputsize=100&apikey={api_key}"
    
    response = requests.get(url)
    data = response.json()
    
    prices = [float(c['close']) for c in data['values']]
    return prices

def calculate_indicators(prices):
    """Calcula indicadores técnicos básicos"""
    
    close = np.array(prices)
    
    # RSI
    delta = np.diff(close)
    gain = np.where(delta > 0, delta, 0)
    loss = np.where(delta < 0, -delta, 0)
    
    avg_gain = np.mean(gain[:14])
    avg_loss = np.mean(loss[:14])
    rs = avg_gain / avg_loss if avg_loss != 0 else 100
    rsi = 100 - (100 / (1 + rs))
    
    # SMA50 y SMA200
    sma50 = np.mean(close[-50:]) if len(close) >= 50 else close[-1]
    sma200 = np.mean(close[-200:]) if len(close) >= 200 else close[-1]
    
    # Precio actual
    current_price = close[-1]
    
    return {
        'current_price': current_price,
        'rsi': rsi,
        'sma50': sma50,
        'sma200': sma200
    }

def determine_strategy(indicators):
    """Determina la estrategia basada en indicadores"""
    
    current_price = indicators['current_price']
    rsi = indicators['rsi']
    sma50 = indicators['sma50']
    
    # Niveles clave
    support_zone = round(current_price - 30, 0)  # 30 pips por debajo
    resistance_zone = round(current_price + 30, 0)  # 30 pips por encima
    breakout_up = round(current_price + 80, 0)  # 80 pips por encima
    breakdown_down = round(current_price - 80, 0)  # 80 pips por debajo
    
    # Determinar sesgo del mercado
    # RSI > 55 alcista, RSI < 45 bajista, entre 45-55 neutral
    
    if rsi > 55:
        # Sesgo ALCISTA
        return {
            'bias': 'bullish',
            'orders': [
                {
                    "id": "BUY_LIMIT_CORE",
                    "type": "buylimit",
                    "entry": support_zone,
                    "sl": round(support_zone - 40, 0),
                    "tp": [round(current_price + 30, 0), round(current_price + 60, 0), round(current_price + 90, 0)],
                    "max_lots": 0.03
                },
                {
                    "id": "BUY_STOP_BREAKOUT",
                    "type": "buystop",
                    "entry": breakout_up,
                    "sl": round(breakout_up - 35, 0),
                    "tp": [round(breakout_up + 40, 0), round(breakout_up + 80, 0), round(breakout_up + 120, 0)],
                    "max_lots": 0.02
                }
            ],
            'main_order': 'BUY'
        }
    elif rsi < 45:
        # Sesgo BAJISTA
        return {
            'bias': 'bearish',
            'orders': [
                {
                    "id": "SELL_LIMIT_RESISTANCE",
                    "type": "selllimit",
                    "entry": resistance_zone,
                    "sl": round(resistance_zone + 40, 0),
                    "tp": [round(current_price - 30, 0), round(current_price - 60, 0), round(current_price - 90, 0)],
                    "max_lots": 0.03
                },
                {
                    "id": "SELL_STOP_BREAKDOWN",
                    "type": "sellstop",
                    "entry": breakdown_down,
                    "sl": round(breakdown_down + 35, 0),
                    "tp": [round(breakdown_down - 40, 0), round(breakdown_down - 80, 0), round(breakdown_down - 120, 0)],
                    "max_lots": 0.04
                }
            ],
            'main_order': 'SELL'
        }
    else:
        # Sesgo NEUTRAL (rango)
        return {
            'bias': 'neutral',
            'orders': [
                {
                    "id": "BUY_LIMIT_SUPPORT",
                    "type": "buylimit",
                    "entry": support_zone,
                    "sl": round(support_zone - 40, 0),
                    "tp": [round(current_price + 30, 0), round(current_price + 60, 0)],
                    "max_lots": 0.02
                },
                {
                    "id": "SELL_LIMIT_RESISTANCE",
                    "type": "selllimit",
                    "entry": resistance_zone,
                    "sl": round(resistance_zone + 40, 0),
                    "tp": [round(current_price - 30, 0), round(current_price - 60, 0)],
                    "max_lots": 0.02
                }
            ],
            'main_order': 'RANGE'
        }

def generate_json():
    """Genera el JSON final para el EA"""
    
    print("📊 Obteniendo datos de XAUUSD...")
    
    try:
        # Obtener precios (ejemplo con datos simulados)
        # En producción, aquí usarías una API real
        prices = [4650 + i * 2 for i in range(100)]  # Simulado
        indicators = calculate_indicators(prices)
        
        print(f"💰 Precio actual: {indicators['current_price']:.2f}")
        print(f"📈 RSI: {indicators['rsi']:.1f}")
        print(f"📊 SMA50: {indicators['sma50']:.2f}")
        
        strategy = determine_strategy(indicators)
        
        print(f"🎯 Sesgo detectado: {strategy['bias'].upper()}")
        
        # Construir JSON final
        json_plan = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "symbols": [
                {
                    "symbol": "XAUUSD..",
                    "orders": strategy['orders']
                }
            ],
            "management": {
                "breakeven_trigger_pips": 200.0,
                "breakeven_lock_pips": 40.0,
                "trailing_start_pips": 250.0,
                "trailing_step_pips": 70.0,
                "delete_pending_at_end_of_day": True,
                "trade_start_hour": 6,
                "trade_end_hour": 21,
                "max_risk_per_trade_percent": 1.0,
                "max_daily_loss_percent": 100.0
            }
        }
        
        # Guardar JSON
        with open('gold_plan.json', 'w') as f:
            json.dump(json_plan, f, indent=2)
        
        print("✅ JSON generado correctamente")
        print(f"📋 Órdenes: {len(strategy['orders'])}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    generate_json()
