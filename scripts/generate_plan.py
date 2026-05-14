import json
import os
import requests
import time
from datetime import datetime, timedelta
import google.generativeai as genai

# Configurar Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# Configurar Twelve Data
TWELVE_DATA_KEY = os.getenv('TWELVE_DATA_API_KEY')

def get_spain_date():
    utc_now = datetime.utcnow()
    if 4 <= utc_now.month <= 10:
        hours_offset = 2
    else:
        hours_offset = 1
    spain_now = utc_now + timedelta(hours=hours_offset)
    return spain_now.strftime("%Y-%m-%d")

def get_market_data():
    try:
        symbols_to_try = ["XAU/USD", "XAUUSD", "GOLD", "XAU"]
        for symbol in symbols_to_try:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval=1h&outputsize=100&apikey={TWELVE_DATA_KEY}"
            print(f"📡 Probando símbolo: {symbol}")
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'values' in data and data['values']:
                    print(f"✅ Conectado con símbolo: {symbol}")
                    prices = [float(c['close']) for c in data['values']]
                    current_price = prices[-1]
                    rsi = calculate_rsi(prices)
                    sma50 = sum(prices[-50:]) / 50 if len(prices) >= 50 else current_price
                    support = round(current_price - 40, 0)
                    resistance = round(current_price + 40, 0)
                    breakout_up = round(current_price + 80, 0)
                    breakdown_down = round(current_price - 80, 0)
                    return {
                        'current_price': current_price,
                        'rsi': rsi,
                        'sma50': sma50,
                        'support': support,
                        'resistance': resistance,
                        'breakout_up': breakout_up,
                        'breakdown_down': breakdown_down,
                        'timestamp': datetime.now().isoformat()
                    }
            else:
                print(f"⚠️ {symbol} - Código: {response.status_code}")
        print("❌ No se pudo conectar con ningún símbolo")
        return None
    except Exception as e:
        print(f"❌ Excepción: {type(e).__name__}: {e}")
        return None

def calculate_rsi(prices, period=14):
    if len(prices) < period + 1:
        return 50
    deltas = [prices[i] - prices[i-1] for i in range(1, period + 1)]
    gain = sum(d for d in deltas if d > 0) / period
    loss = abs(sum(d for d in deltas if d < 0) / period)
    if loss == 0:
        return 100
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 1)

def analyze_with_gemini_with_retry(market_data, max_retries=5, retry_delay=60):
    """Intenta usar Gemini con reintentos en caso de error 503"""
    
    for attempt in range(1, max_retries + 1):
        try:
            print(f"🧠 Intentando Gemini (intento {attempt}/{max_retries})...")
            
            model = genai.GenerativeModel('gemini-2.0-flash')
            
            prompt = f"""
            Eres un experto trader de XAUUSD (oro). Basado en estos datos actuales:
            
            📊 PRECIO ACTUAL: {market_data['current_price']:.2f} USD
            📈 RSI (14 períodos): {market_data['rsi']}
            📉 SMA 50: {market_data['sma50']:.2f} USD
            
            🎯 Niveles calculados automáticamente:
            - SOPORTE: {market_data['support']:.0f} USD
            - RESISTENCIA: {market_data['resistance']:.0f} USD
            - BREAKOUT ALCISTA: {market_data['breakout_up']:.0f} USD
            - BREAKDOWN BAJISTA: {market_data['breakdown_down']:.0f} USD
            
            GENERA UN PLAN DE TRADING CON:
            
            1. Sesgo del mercado (alcista si RSI > 55, bajista si RSI < 45)
            2. Si es ALCISTA: da prioridad a órdenes de COMPRA
            3. Si es BAJISTA: da prioridad a órdenes de VENTA
            4. Siempre incluye stop loss y 2-3 take profits
            5. Máximo 4 órdenes, mínimo 0
            
            RESPUESTE SOLO CON JSON.
            """
            
            response = model.generate_content(prompt)
            
            if response.text:
                import re
                json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
                if json_match:
                    strategy = json.loads(json_match.group())
                    print(f"✨ Gemini ha generado la estrategia: {strategy.get('bias', 'neutral')}")
                    return strategy
                else:
                    print("⚠️ No se pudo extraer JSON de la respuesta de Gemini")
            else:
                print("⚠️ Respuesta vacía de Gemini")
                
        except Exception as e:
            error_msg = str(e)
            if "503" in error_msg or "UNAVAILABLE" in error_msg:
                print(f"⚠️ Gemini está saturado (intento {attempt}/{max_retries})")
                if attempt < max_retries:
                    print(f"   Esperando {retry_delay} segundos antes de reintentar...")
                    time.sleep(retry_delay)
                else:
                    print("❌ Gemini falló después de todos los reintentos")
            else:
                print(f"❌ Error con Gemini: {e}")
                if attempt < max_retries:
                    print(f"   Reintentando en {retry_delay} segundos...")
                    time.sleep(retry_delay)
    
    return None

def default_strategy(market_data):
    rsi = market_data['rsi']
    if rsi > 55:
        return {
            "bias": "alcista",
            "reason": f"RSI en {rsi} indicando momentum alcista",
            "orders": [
                {"id": "BUY_LIMIT_CORE", "type": "buylimit", "entry": market_data['support'], "sl": market_data['support'] - 40, "tp": [market_data['resistance'], market_data['resistance'] + 30, market_data['breakout_up']], "max_lots": 0.03},
                {"id": "BUY_STOP_BREAKOUT", "type": "buystop", "entry": market_data['breakout_up'], "sl": market_data['breakout_up'] - 35, "tp": [market_data['breakout_up'] + 40, market_data['breakout_up'] + 80], "max_lots": 0.02}
            ]
        }
    elif rsi < 45:
        return {
            "bias": "bajista",
            "reason": f"RSI en {rsi} indicando momentum bajista",
            "orders": [
                {"id": "SELL_LIMIT_RESISTANCE", "type": "selllimit", "entry": market_data['resistance'], "sl": market_data['resistance'] + 40, "tp": [market_data['support'], market_data['support'] - 30, market_data['breakdown_down']], "max_lots": 0.03},
                {"id": "SELL_STOP_BREAKDOWN", "type": "sellstop", "entry": market_data['breakdown_down'], "sl": market_data['breakdown_down'] + 35, "tp": [market_data['breakdown_down'] - 40, market_data['breakdown_down'] - 80], "max_lots": 0.04}
            ]
        }
    else:
        return {
            "bias": "neutral",
            "reason": f"RSI en {rsi} indicando mercado lateral",
            "orders": [
                {"id": "BUY_LIMIT_SUPPORT", "type": "buylimit", "entry": market_data['support'], "sl": market_data['support'] - 35, "tp": [market_data['current_price'], market_data['resistance']], "max_lots": 0.02},
                {"id": "SELL_LIMIT_RESISTANCE", "type": "selllimit", "entry": market_data['resistance'], "sl": market_data['resistance'] + 35, "tp": [market_data['current_price'], market_data['support']], "max_lots": 0.02}
            ]
        }

def generate_json():
    print("🤖 INICIANDO ANÁLISIS DIARIO XAUUSD")
    print("=" * 50)
    
    print("📊 Obteniendo datos del mercado...")
    market_data = get_market_data()
    
    if not market_data:
        print("❌ No se pudieron obtener datos del mercado.")
        return False
    
    print(f"💰 Precio actual: {market_data['current_price']:.2f} USD")
    print(f"📈 RSI: {market_data['rsi']}")
    print(f"🎯 Soporte: {market_data['support']:.0f} | Resistencia: {market_data['resistance']:.0f}")
    
    print("🧠 Analizando con Gemini (con reintentos)...")
    strategy = analyze_with_gemini_with_retry(market_data, max_retries=5, retry_delay=60)
    
    if not strategy:
        print("⚠️ Gemini falló, usando estrategia por defecto basada en RSI")
        strategy = default_strategy(market_data)
    
    print(f"🎯 Sesgo detectado: {strategy.get('bias', 'neutral').upper()}")
    print(f"📋 Órdenes generadas: {len(strategy.get('orders', []))}")
    
    json_plan = {
        "date": get_spain_date(),
        "symbols": [
            {
                "symbol": "XAUUSD..",
                "orders": strategy.get('orders', [])
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
    
    with open('gold_plan.json', 'w') as f:
        json.dump(json_plan, f, indent=2)
    
    print("=" * 50)
    print("✅ JSON generado correctamente")
    print(f"📁 Archivo: gold_plan.json")
    print(f"📅 Fecha generada: {get_spain_date()}")
    
    return True

if __name__ == "__main__":
    generate_json()
