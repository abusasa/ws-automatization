1. клонирование
```text
git clone https://github.com/abusasa/ws-automatization.git
cd .\ws-automatization\
```
2. установите зависимости:
```text
pip install -r requirements.txt
```
3. заполните `contats.csv`:
```csv
phone
79991234567
```
4. добавьте 4 сообщения в `templates.json` и запустите:
```text
python main.py
```

при первом запуске отсканируйте qr-код в whatsapp web. дальше вход сохранится автоматически.
