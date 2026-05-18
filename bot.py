import os
import time
import logging
from dotenv import load_dotenv
import requests
import threading

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = os.getenv("CHANNEL_ID")

DEXSCREENER_API_URL = "https://api.dexscreener.com/latest/dex/pairs/ton/eqco9ndt4il25_4zphiogmaubrjvpsi9plzqhd8x7etvb7x_"

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

# Хранилище последней цены
last_price_usd = None


def get_mtonga_price():
    try:
        r = requests.get(DEXSCREENER_API_URL, timeout=15)
        r.raise_for_status()
        data = r.json()
        pair = data.get("pair")

        if not pair:
            return None

        return {
            "price_usd": float(pair.get("priceUsd", 0)),
            "price_ton": float(pair.get("priceNative", 0)),
            "fdv": float(pair.get("fdv", 0)),
        }

    except Exception as e:
        logging.error(f"Ошибка получения цены: {e}")
        return None


def format_number(num):
    """Форматирует число с запятыми как разделителями тысяч"""
    return f"{num:,.0f}"


def get_trend_symbol(current_price, last_price):
    """Возвращает символ состояния цены"""
    if last_price is None:
        return "⚪"  # Белый кружок (первый запуск)
    elif current_price > last_price:
        return "🟢"  # Зеленый кружок (рост)
    elif current_price < last_price:
        return "🔴"  # Красный кружок (падение)
    else:
        return "⚪"  # Белый кружок (без изменений)


def format_message(data):
    global last_price_usd
    
    price_usd = data['price_usd']
    price_ton = data['price_ton']
    mc = data['fdv']
    
    # Получаем символ состояния
    trend = get_trend_symbol(price_usd, last_price_usd)
    
    # Форматируем цену USD (4 знака после запятой)
    price_usd_str = f"{price_usd:.4f}"
    
    # Форматируем цену TON (6 знаков после запятой)
    price_ton_str = f"{price_ton:.6f}"
    
    # Форматируем MC с запятыми
    mc_str = format_number(mc)
    
    # Формат с значком состояния в начале
    text = f"{trend} ${price_usd_str} | {price_ton_str} TON\nMC: ${mc_str}"
    
    # Сохраняем текущую цену для следующего сравнения
    last_price_usd = price_usd
    
    return text


def send_telegram_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    
    payload = {
        "chat_id": CHANNEL_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        logging.info("✅ Сообщение отправлено")
        return True
    except Exception as e:
        logging.error(f"❌ Ошибка отправки: {e}")
        if 'r' in locals():
            logging.error(f"Ответ: {r.text}")
        return False


def send_ad_for_utya():
    """Отправляет рекламу UTYA раз в 30 минут"""
    text = "🔥 Торгуй MTONGA: @mtonga_price"
    send_telegram_message(text)
    # Запускаем следующий запуск через 30 минут (1800 секунд)
    threading.Timer(1800, send_ad_for_utya).start()


if __name__ == "__main__":
    logging.info("🚀 Бот запущен")
    
    # Проверяем переменные окружения
    if not BOT_TOKEN:
        logging.error("❌ BOT_TOKEN не найден в .env файле!")
        exit(1)
    
    if not CHANNEL_ID:
        logging.error("❌ CHANNEL_ID не найден в .env файле!")
        exit(1)
    
    # Запускаем рекламный поток (первый запуск через 10 секунд после старта)
    threading.Timer(10, send_ad_for_utya).start()
    
    # Основной цикл
    while True:
        try:
            data = get_mtonga_price()
            
            if data:
                text = format_message(data)
                send_telegram_message(text)
                logging.info(f"💰 Отправлена цена: ${data['price_usd']:.4f} | {data['price_ton']:.6f} TON")
            else:
                logging.warning("⚠️ Не удалось получить данные о цене")
            
            time.sleep(60)
            
        except KeyboardInterrupt:
            logging.info("🛑 Бот остановлен")
            break
        except Exception as e:
            logging.error(f"❌ Ошибка: {e}")
            time.sleep(60)