import urllib.parse
import time
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

class WhatsAppSender:
    def __init__(self, profile_path):
        self.logger = logging.getLogger("WhatsAppSender")
        chrome_options = Options()
        chrome_options.add_argument(f"user-data-dir={profile_path}")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")

        self.logger.info("Запуск Chrome")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.wait = WebDriverWait(self.driver, 30)

    def wait_for_login(self):
        self.driver.get("https://web.whatsapp.com/")
        self.logger.info("Ожидание входа в WhatsApp Web")
        WebDriverWait(self.driver, 300).until(
            EC.presence_of_element_located((By.XPATH, '//div[@contenteditable="true"][@data-tab="3"] | //canvas[@aria-label="Scan me!"]'))
        )

        try:
            WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located((By.XPATH, '//div[@id="pane-side"]'))
            )
            self.logger.info("Вход выполнен")
        except Exception:
            self.logger.error("Время входа истекло")
            raise

    def send_message(self, phone, text):
        try:
            encoded_text = urllib.parse.quote(text)
            url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_text}"
            self.driver.get(url)
            
            send_btn_xpath = '//span[@data-icon="send"]'
            invalid_phone_xpath = '//div[contains(text(), "is invalid") or contains(text(), "не зарегистрирован")]'
            
            start_time = time.time()
            while True:
                if time.time() - start_time > 45:
                    self.logger.warning(f"Таймаут загрузки чата для {phone}")
                    return False

                send_btns = self.driver.find_elements(By.XPATH, send_btn_xpath)
                if send_btns:
                    time.sleep(2)
                    send_btns[0].click()
                    time.sleep(3)
                    return True

                invalid_alerts = self.driver.find_elements(By.XPATH, invalid_phone_xpath)
                if invalid_alerts:
                    self.logger.warning(f"Номер не зарегистрирован: {phone}")
                    return False

                time.sleep(1)

        except Exception as e:
            self.logger.error(f"Ошибка отправки на {phone}: {str(e)}")
            return False

    def close(self):
        if self.driver:
            self.driver.quit()