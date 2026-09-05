1. зависимости:
```text
pip install -r requirements.txt
```
2. 
```csv
phone
79991234567
```
3. варианты собщениалардн в `templates.json`:
```text
python main.py
```

A commercial Python project for WhatsApp automation that processes a queue of numbers through a local database in real-time with pending, sent, and failed statuses. It ensures strict uniqueness of sending, rotates four text variants, simulates human typing, supports state persistence, and automatically recovers from crashes or computer reboots. It uses a floating randomized interval of about 800 seconds to avoid bans and has a work limit of five days.

Коммерческий Python-проект для автоматизации WhatsApp, который обрабатывает очередь номеров через локальную базу данных в реальном времени (со статусами pending, sent, failed), гарантирует строгую уникальность отправки, ротирует 4 варианта текста, имитирует человеческий набор, поддерживает персистентность состояния и автовосстановление после любых сбоев/перезагрузок компьютера, использует плавающий рандомизированный интервал около 800 секунд для обхода банов и имеет лимит работы в 5 дней.

Проект использует неофициальную автоматизацию WhatsApp Web (click-to-chat ссылки), а не официальный WhatsApp Business API: нет подтверждений доставки, нет официальных гарантий стабильности интерфейса, есть риск ограничения номера при массовой рассылке. Никакой имитации "человеческого" набора текста в коде нет - сообщение подставляется в ссылку целиком.