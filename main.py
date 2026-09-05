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
    logger.info("Завершение...")
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
        return 1

    max_consecutive_failures = config.get('max_consecutive_failures', 5)
    page_load_timeout = config.get('page_load_timeout_seconds', 60)

    db = Database()
    sender = None
    exit_code = 0

    try:
        db.load_from_csv('contats.csv')
        stats = db.get_stats()
        logger.info(f"База: {stats}")

        interrupted = db.flag_interrupted()
        if interrupted:
            logger.warning(
                f"Обнаружено {len(interrupted)} контакт(ов) со статусом 'sending' от "
                f"прерванного предыдущего запуска (аварийное завершение/kill/сбой "
                f"питания). Нет способа достоверно узнать, было ли сообщение "
                f"фактически доставлено, поэтому они помечены как 'interrupted' и "
                f"НЕ будут отправлены повторно автоматически. Проверьте вручную: {interrupted}"
            )

        start_time = db.get_start_time()
        max_duration = config['max_execution_days'] * 24 * 3600

        if time.time() - start_time > max_duration:
            logger.error("Срок работы истек")
            return 0

        if not db.get_pending_contact():
            logger.info("Очередь пуста")
            return 0

        try:
            sender = WhatsAppSender(config['browser_profile_path'], page_load_timeout=page_load_timeout)
            sender.wait_for_login()
        except Exception:
            logger.exception("Не удалось запустить браузер или выполнить вход в WhatsApp Web")
            return 1

        consecutive_failures = 0

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

            db.mark_status(phone, 'sending')
            logger.info(f"Отправка: {phone}")

            try:
                success = sender.send_message(phone, text)
            except Exception:
                logger.exception(f"Неожиданная ошибка при отправке {phone}")
                success = False

            if success:
                db.mark_status(phone, 'sent')
                consecutive_failures = 0
                logger.info(f"Успешно отправлено: {phone}")
            else:
                db.mark_status(phone, 'failed')
                consecutive_failures += 1
                logger.warning(f"Не удалось отправить: {phone} (подряд неудач: {consecutive_failures})")

                if consecutive_failures >= max_consecutive_failures:
                    logger.critical(
                        f"{consecutive_failures} неудач(и) подряд. Вероятно, изменился "
                        f"интерфейс WhatsApp Web, слетела сессия входа или пропал "
                        f"интернет. Останавливаемся, чтобы не потратить впустую весь "
                        f"5-дневный лимит на заведомо неудачные попытки. Проверьте лог "
                        f"и браузер вручную, затем перезапустите."
                    )
                    exit_code = 1
                    break

            base_delay = config['base_delay_seconds']
            jitter_pct = config['random_jitter_percent'] / 100.0
            jitter_val = base_delay * jitter_pct
            delay = base_delay + random.uniform(-jitter_val, jitter_val)

            logger.info(f"Пауза: {timedelta(seconds=int(delay))}")

            end_wait = time.time() + delay
            while time.time() < end_wait and running:
                time.sleep(1)

    finally:
        if sender:
            logger.info("Закрытие браузера...")
            sender.close()
        db.close()
        logger.info("Готово")

    return exit_code


if __name__ == "__main__":
    sys.exit(main())
