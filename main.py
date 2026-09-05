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
    format='%(asctime)s - %(message)s',
    handlers=[logging.FileHandler("whatsapp_bot.log", encoding='utf-8'), logging.StreamHandler()]
)
logger = logging.getLogger("MainControl")

running = True
def signal_handler(sig, frame):
    global running
    logger.info("завершаем работу...")
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
        logger.error("в templates.json нет сообщений")
        return 1

    max_consecutive_failures = config.get('max_consecutive_failures', 5)
    page_load_timeout = config.get('page_load_timeout_seconds', 60)

    db = Database()
    sender = None
    exit_code = 0

    try:
        db.load_from_csv('contats.csv')
        stats = db.get_stats()
        logger.info(f"база: {stats}")

        interrupted = db.flag_interrupted()
        if interrupted:
            logger.warning(
                f"после сбоя остались незавершённые номера: {interrupted}. "
                f"не отправляем их повторно автоматически"
            )

        start_time = db.get_start_time()
        max_duration = config['max_execution_days'] * 24 * 3600

        if time.time() - start_time > max_duration:
            logger.error("срок работы истёк")
            return 0

        if not db.get_pending_contact():
            logger.info("очередь пуста")
            return 0

        try:
            sender = WhatsAppSender(config['browser_profile_path'], page_load_timeout=page_load_timeout)
            sender.wait_for_login()
        except Exception:
            logger.exception("не удалось открыть браузер или войти в whatsapp web")
            return 1

        consecutive_failures = 0

        while running:
            elapsed = time.time() - start_time
            if elapsed > max_duration:
                logger.info("лимит времени работы достигнут")
                break

            contact = db.get_pending_contact()
            if not contact:
                logger.info("очередь обработана")
                break

            phone = contact[0]
            text = random.choice(messages)

            db.mark_status(phone, 'sending')
            logger.info(f"отправляем: {phone}")

            try:
                success = sender.send_message(phone, text)
            except Exception:
                logger.exception(f"ошибка отправки {phone}")
                success = False

            if success:
                db.mark_status(phone, 'sent')
                consecutive_failures = 0
                logger.info(f"отправлено: {phone}")
            else:
                db.mark_status(phone, 'failed')
                consecutive_failures += 1
                logger.warning(f"не отправилось: {phone} (ошибок подряд: {consecutive_failures})")

                if consecutive_failures >= max_consecutive_failures:
                    logger.critical(
                        f"{consecutive_failures} ошибок подряд. останавливаемся... "
                        f"проверьте интернет и войдите в whatsapp web заново"
                    )
                    exit_code = 1
                    break

            base_delay = config['base_delay_seconds']
            jitter_pct = config['random_jitter_percent'] / 100.0
            jitter_val = base_delay * jitter_pct
            delay = base_delay + random.uniform(-jitter_val, jitter_val)

            logger.info(f"ждём: {timedelta(seconds=int(delay))}")

            end_wait = time.time() + delay
            while time.time() < end_wait and running:
                time.sleep(1)

    finally:
        if sender:
            logger.info("закрываем браузер...")
            sender.close()
        db.close()
        logger.info("готово")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
