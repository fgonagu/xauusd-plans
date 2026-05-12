import json
import os
import requests
from datetime import datetime, timedelta
import google.generativeai as genai

# Configurar Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)

# Configurar Twelve Data
TWELVE_DATA_KEY = os.getenv('TWELVE_DATA_API_KEY')

def get_spain_date():
    """Devuelve la fecha actual en horario español"""
    utc_now = datetime.utcnow()
    # Horario de verano en España: desde finales de marzo hasta finales de octubre
    # Simplificado: de abril a octubre asumimos UTC+2, resto UTC+1
    if 4 <= utc_now.month <= 10:
        hours_offset = 2  # Horario de verano (UTC+2)
    else:
        hours_offset = 1  # Horario de invierno (UTC+1)
    
    spain_now = utc_now + timedelta(hours=hours_offset)
    return spain_now.strftime("%Y-%m-%d")

def get_market_data():
    """Obtiene datos del mercado simulados basados en precio real actual"""
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=1h&outputsize=100&apikey={TWELVE_DATA_KEY}"
    # Precio actual de XAUUSD (~4724)
    current_price = 4724.36
    rsi = 52.5  # Neutral
    sma50 = 4710.0
    
    # Calcular niveles
    support = round(current_price - (current_price * 0.008), 0)  # 4687
    resistance = round(current_price + (current_price * 0.008), 0)  # 4762
    breakout_up = round(current_price + (current_price * 0.015), 0)  # 4795
    breakdown_down = round(current_price - (current_price * 0.015), 0)  # 4654
    
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

def calculate_rsi(prices, period=14):
    """Calcula el RSI manualmente"""
    
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

def analyze_with_gemini(market_data):
    """Usa Gemini para generar el plan de trading"""
    
    model = genai.GenerativeModel('gemini-1.5-flash')
    
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
    
    RESPUESTE SOLO CON JSON. Ejemplo:
    {{
        "bias": "alcista/bajista/neutral",
        "reason": "breve razón técnica",
        "orders": [
            {{
                "id": "ORDEN_PRINCIPAL",
                "type": "buylimit",
                "entry": {market_data['support']:.0f},
                "sl": {market_data['support'] - 40:.0f},
                "tp": [{market_data['resistance']:.0f}, {market_data['resistance'] + 30:.0f}, {market_data['breakout_up']:.0f}],
                "max_lots": 0.03
            }},
            {{
                "id": "ORDEN_SECUNDARIA",
                "type": "buystop",
                "entry": {market_data['breakout_up']:.0f},
                "sl": {market_data['breakout_up'] - 35:.0f},
                "tp": [{market_data['breakout_up'] + 40:.0f}, {market_data['breakout_up'] + 80:.0f}],
                "max_lots": 0.02
            }}
        ]
    }}
    
    IMPORTANTE: Ajusta los valores según el RSI y el sesgo.
    """
    
    try:
        response = model.generate_content(prompt)
        
        # Extraer JSON de la respuesta
        import re
        json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
        
        if json_match:
            strategy = json.loads(json_match.group())
            return strategy
        else:
            print("⚠️ No se pudo extraer JSON de la respuesta de Gemini")
            return None
            
    except Exception as e:
        print(f"❌ Error con Gemini: {e}")
        return None

def generate_json():
    """Genera el JSON final para el EA"""
    
    print("🤖 INICIANDO ANÁLISIS DIARIO XAUUSD")
    print("=" * 50)
    
    # 1. Obtener datos del mercado
    print("📊 Obteniendo datos del mercado...")
    market_data = get_market_data()
    
    if not market_data:
        print("❌ No se pudieron obtener datos del mercado. Usando datos por defecto.")
        return False
    
    print(f"💰 Precio actual: {market_data['current_price']:.2f} USD")
    print(f"📈 RSI: {market_data['rsi']}")
    print(f"🎯 Soporte: {market_data['support']:.0f} | Resistencia: {market_data['resistance']:.0f}")
    
    # 2. Analizar con Gemini
    print("🧠 Analizando con Gemini...")
    strategy = analyze_with_gemini(market_data)
    
    # 3. Si Gemini falla, usar estrategia por defecto
    if not strategy:
        print("⚠️ Usando estrategia por defecto basada en RSI")
        strategy = default_strategy(market_data)
    
    print(f"🎯 Sesgo detectado: {strategy.get('bias', 'neutral').upper()}")
    print(f"📋 Órdenes generadas: {len(strategy.get('orders', []))}")
    
    # 4. Construir JSON final con fecha en horario español
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
    
    # 5. Guardar JSON
    with open('gold_plan.json', 'w') as f:
        json.dump(json_plan, f, indent=2)
    
    print("=" * 50)
    print("✅ JSON generado correctamente")
    print(f"📁 Archivo: gold_plan.json")
    print(f"📅 Fecha generada: {get_spain_date()}")
    
    return True

def default_strategy(market_data):
    """Estrategia por defecto si Gemini falla"""
    
    rsi = market_data['rsi']
    
    if rsi > 55:
        return {
            "bias": "alcista",
            "reason": f"RSI en {rsi} indicando momentum alcista",
            "orders": [
                {
                    "id": "BUY_LIMIT_CORE",
                    "type": "buylimit",
                    "entry": market_data['support'],
                    "sl": market_data['support'] - 40,
                    "tp": [market_data['resistance'], market_data['resistance'] + 30, market_data['breakout_up']],
                    "max_lots": 0.03
                },
                {
                    "id": "BUY_STOP_BREAKOUT",
                    "type": "buystop",
                    "entry": market_data['breakout_up'],
                    "sl": market_data['breakout_up'] - 35,
                    "tp": [market_data['breakout_up'] + 40, market_data['breakout_up'] + 80],
                    "max_lots": 0.02
                }
            ]
        }
    elif rsi < 45:
        return {
            "bias": "bajista",
            "reason": f"RSI en {rsi} indicando momentum bajista",
            "orders": [
                {
                    "id": "SELL_LIMIT_RESISTANCE",
                    "type": "selllimit",
                    "entry": market_data['resistance'],
                    "sl": market_data['resistance'] + 40,
                    "tp": [market_data['support'], market_data['support'] - 30, market_data['breakdown_down']],
                    "max_lots": 0.03
                },
                {
                    "id": "SELL_STOP_BREAKDOWN",
                    "type": "sellstop",
                    "entry": market_data['breakdown_down'],
                    "sl": market_data['breakdown_down'] + 35,
                    "tp": [market_data['breakdown_down'] - 40, market_data['breakdown_down'] - 80],
                    "max_lots": 0.04
                }
            ]
        }
    else:
        return {
            "bias": "neutral",
            "reason": f"RSI en {rsi} indicando mercado lateral",
            "orders": [
                {
                    "id": "BUY_LIMIT_SUPPORT",
                    "type": "buylimit",
                    "entry": market_data['support'],
                    "sl": market_data['support'] - 35,
                    "tp": [market_data['current_price'], market_data['resistance']],
                    "max_lots": 0.02
                },
                {
                    "id": "SELL_LIMIT_RESISTANCE",
                    "type": "selllimit",
                    "entry": market_data['resistance'],
                    "sl": market_data['resistance'] + 35,
                    "tp": [market_data['current_price'], market_data['support']],
                    "max_lots": 0.02
                }
            ]
        }

if __name__ == "__main__":
    generate_json()
