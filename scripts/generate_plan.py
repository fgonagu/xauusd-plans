import json
import os
import requests
from datetime import datetime, timedelta
from google import genai
from google.genai import types

# Configurar Gemini con la NUEVA librería
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
client = genai.Client(api_key=GEMINI_API_KEY)

# Configurar Twelve Data
TWELVE_DATA_KEY = os.getenv('TWELVE_DATA_API_KEY')

def get_spain_date():
    """Devuelve la fecha actual en horario español"""
    utc_now = datetime.utcnow()
    if 4 <= utc_now.month <= 10:
        hours_offset = 2
    else:
        hours_offset = 1
    spain_now = utc_now + timedelta(hours=hours_offset)
    return spain_now.strftime("%Y-%m-%d")

def get_market_data():
    """Obtiene datos actuales del mercado desde Twelve Data"""
    try:
        # Probar diferentes formatos de símbolo
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
                    
                    # Niveles dinámicos
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
    """Usa Gemini (gemini-2.5-flash) para generar el plan de trading profesional"""
    
    prompt = f"""
    ACTÚA COMO UN PROP TRADER EXPERTO EN XAUUSD (ORO) CON 15 AÑOS DE EXPERIENCIA.
    
    ========================================
    📊 DATOS ACTUALES DEL MERCADO
    ========================================
    • Precio actual: {market_data['current_price']:.2f} USD
    • RSI (14 períodos): {market_data['rsi']}
    • SMA 50: {market_data['sma50']:.2f} USD
    
    🎯 NIVELES TÉCNICOS CLAVE:
    • Soporte inmediato: {market_data['support']:.0f} USD
    • Resistencia inmediata: {market_data['resistance']:.0f} USD
    • Breakout alcista (confirmación): {market_data['breakout_up']:.0f} USD
    • Breakdown bajista (confirmación): {market_data['breakdown_down']:.0f} USD
    
    ========================================
    📈 ANÁLISIS TÉCNICO PROFESIONAL
    ========================================
    
    Basándote en estos datos, realiza un análisis completo:
    
    1. **ESTRUCTURA DEL MERCADO**
       - ¿Tendencia alcista, bajista o lateral?
       - ¿Hay divergencias entre precio e indicadores?
       - ¿El RSI indica sobrecompra/sobreventa?
    
    2. **CONFLUENCIA DE NIVELES**
       - Identifica zonas de soporte y resistencia significativas
       - Señala niveles de Fibonacci relevantes si aplica
       - Determina puntos de inflexión probables
    
    3. **ESCENARIOS DE TRADING**
       - Escenario principal (mayor probabilidad)
       - Escenario alternativo (si falla el principal)
       - Zonas de invalidación
    
    ========================================
    🎯 GENERACIÓN DE ÓRDENES
    ========================================
    
    Crea un plan de trading que INCLUYA LAS ÓRDENES QUE CONSIDERES OPORTUNAS SEGÚN TU ANÁLISIS.
    
    REGLAS PARA ÓRDENES:
    • Mínimo 0 órdenes, máximo 6 órdenes (dependiendo de las oportunidades)
    • Para CADA orden incluye: ID, tipo, entry, SL, TP (2-3 niveles), max_lots
    • Los lotes deben variar según la confianza de la operación (0.01 a 0.05)
    • Tipos permitidos: buylimit, selllimit, buystop, sellstop
    
    ESTRATEGIAS POSIBLES:
    • Pullback en tendencia (LIMIT en soporte/resistencia)
    • Breakout confirmado (STOP tras ruptura)
    • Rango (LIMIT en ambos extremos)
    • Scalping en niveles clave (entradas rápidas)
    • Swing con stops amplios
    
    ========================================
    📋 FORMATO DE RESPUESTA (SOLO JSON)
    ========================================
    
    {{
        "bias": "alcista/bajista/neutral",
        "strength": "fuerte/moderado/débil",
        "analysis_summary": "Resumen ejecutivo del análisis en 1 línea",
        "market_phase": "tendencia/rango/transición",
        "volatility_assessment": "alta/media/baja",
        "key_levels": {{
            "main_support": {market_data['support']:.0f},
            "main_resistance": {market_data['resistance']:.0f},
            "critical_stop": 0
        }},
        "orders": [
            {{
                "id": "NOMBRE_DESCRIPTIVO",
                "type": "selllimit",
                "entry": 0,
                "sl": 0,
                "tp": [0, 0, 0],
                "max_lots": 0.00,
                "confidence": "alta/media/baja",
                "strategy": "pullback/breakout/rango/swing"
            }}
        ]
    }}
    
    IMPORTANTE:
    - Ajusta el número de órdenes a las oportunidades REALES del mercado
    - Si el mercado no ofrece oportunidades claras, genera 0 órdenes
    - Si hay múltiples oportunidades, genera hasta 6 órdenes
    - Prioriza calidad sobre cantidad
    """
    
    try:
        # Usar gemini-2.5-flash con temperatura baja para consistencia
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.2,
                top_p=0.95,
                top_k=40
            )
        )
        
        if response.text:
            import re
            # Buscar JSON en la respuesta
            json_match = re.search(r'\{.*\}', response.text, re.DOTALL)
            if json_match:
                strategy = json.loads(json_match.group())
                bias = strategy.get('bias', 'neutral')
                order_count = len(strategy.get('orders', []))
                print(f"✨ [Gemini] Estrategia {bias.upper()} - {order_count} órdenes generadas")
                if 'analysis_summary' in strategy:
                    print(f"📝 Resumen: {strategy['analysis_summary']}")
                return strategy
            else:
                print("⚠️ No se pudo extraer JSON de la respuesta de Gemini")
                print(f"Respuesta recibida: {response.text[:300]}...")
                return None
        else:
            print("⚠️ Respuesta vacía de Gemini")
            return None
            
    except Exception as e:
        print(f"❌ Error con Gemini: {e}")
        return None
def generate_json():
    """Genera el JSON final para el EA"""
    
    print("🤖 INICIANDO ANÁLISIS DIARIO XAUUSD")
    print("=" * 50)
    
    # 1. Obtener datos del mercado (Twelve Data)
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
        print("⚠️ Gemini falló, usando estrategia por defecto basada en RSI")
        strategy = default_strategy(market_data)
    
    print(f"🎯 Sesgo detectado: {strategy.get('bias', 'neutral').upper()}")
    print(f"📋 Órdenes generadas: {len(strategy.get('orders', []))}")
    
    # 4. Construir JSON final
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
        json.dump(json_plan, f, separators=(',', ':'))
    
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

if __name__ == "__main__":
    generate_json()
