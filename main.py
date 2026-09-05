import json
import time
import random
import logging
import signal
import sys
from datetime import timedelta
from db import Database
from sender import WhatsAppSender

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("whatsapp_bot.log", encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger("MainControl")

running = True

def signal_handler(sig, frame):
    global running
    logger.info("инициализация...")
    running = False

def load_json(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)

def main():
    global running
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    config = load_json('config.json')
    templates = load_json('templates.json')
    messages = [text for text in templates.values() if text]
    if not messages:
        logger.error("Нет сообщений в templates.json")
        return
    db = Database()

    db.load_from_csv('contats.csv')
    stats = db.get_stats()
    logger.info(f"База: {stats}")

    start_time = db.get_start_time()
    max_duration = config['max_execution_days'] * 24 * 3600

    if time.time() - start_time > max_duration:
        logger.error("Срок работы истек")
        sys.exit(0)

    pending = db.get_pending_contact()
    if not pending:
        logger.info("Очередь пуста")
        sys.exit(0)

    sender = WhatsAppSender(config['browser_profile_path'])
    try:
        sender.wait_for_login()
    except Exception:
        sender.close()
        sys.exit(1)

    while running:
        elapsed = time.time() - start_time
        if elapsed > max_duration:
            logger.info("Лимит времени работы достигнут")
            break

        contact = db.get_pending_contact()
        if not contact:
            logger.info("Очередь обработана")
            break

        phone = contact[0]
        text = random.choice(messages)
        logger.info(f"Отправка: {phone}")

        success = sender.send_message(phone, text)
        if success:
            db.mark_status(phone, 'sent')
            logger.info(f"Успешно отправлено: {phone}")
        else:
            db.mark_status(phone, 'failed')
            logger.warning(f"Не удалось отправить: {phone}")

        base_delay = config['base_delay_seconds']
        jitter_pct = config['random_jitter_percent'] / 100.0
        jitter_val = base_delay * jitter_pct
        delay = base_delay + random.uniform(-jitter_val, jitter_val)

        logger.info(f"Пауза: {timedelta(seconds=int(delay))}")

        end_wait = time.time() + delay
        while time.time() < end_wait and running:
            time.sleep(1)

    logger.info("Закрытие браузера...")
    sender.close()
    logger.info("Готово")

if __name__ == "__main__":
    main()