import urllib.parse
import time
import logging
from pathlib import Path
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
from webdriver_manager.chrome import ChromeDriverManager
class WhatsAppSender:
    def __init__(self, profile_path, page_load_timeout=60):
        self.logger = logging.getLogger("WhatsAppSender")
        self.driver = None
        chrome_options = Options()
        chrome_options.add_argument(f"--user-data-dir={profile_path}")
        chrome_options.add_argument("--disable-infobars")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--no-sandbox")
        driver_path = Path(ChromeDriverManager().install())
        if driver_path.name.lower() != "chromedriver.exe":
            driver_files = list(driver_path.parent.rglob("chromedriver.exe"))
            if not driver_files:
                raise FileNotFoundError("chromedriver.exe не найден")
            driver_path = driver_files[0]
        self.logger.info("драйвер chrome готов")
        self.driver = webdriver.Chrome(service=Service(driver_path), options=chrome_options)
        self.driver.set_page_load_timeout(page_load_timeout)
        self.wait = WebDriverWait(self.driver, 30)
    def wait_for_login(self):
        try:
            self.driver.get("https://web.whatsapp.com/")
        except TimeoutException:
            self.logger.error("страница whatsapp не загрузилась вовремя")
            raise
        self.logger.info("ждём вход в whatsapp web...")
        try:
            WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located(
                    (By.XPATH, '//div[@id="pane-side"] | '
                     '//*[@data-testid="chat-list"] | '
                     '//div[@aria-label="Chat list"]')
                )
            )
            self.logger.info("вход выполнен")
        except TimeoutException:
            self.logger.error("время входа истекло")
            raise
    def _handle_continue_to_chat(self):
        button_text = 'translate(., "ABCDEFGHIJKLMNOPQRSTUVWXYZАБВГДЕЁЖЗИЙКЛМНОПРСТУФХЦЧШЩЪЫЬЭЮЯ", "abcdefghijklmnopqrstuvwxyzабвгдеёжзийклмнопрстуфхцчшщъыьэюя")'
        continue_xpath = (
            '//a[contains(@href, "send") and '
            f'contains({button_text}, "continue to chat") or '
            f'contains({button_text}, "продолжить")] '
            '| //div[@role="button"]'
            f'[contains({button_text}, "continue to chat") or '
            f'contains({button_text}, "продолжить")]'
        )
        buttons = self.driver.find_elements(By.XPATH, continue_xpath)
        if buttons:
            try:
                buttons[0].click()
                return True
            except Exception:
                return False
        return False
    def send_message(self, phone, text):
        try:
            encoded_text = urllib.parse.quote(text)
            url = f"https://web.whatsapp.com/send?phone={phone}&text={encoded_text}"

            try:
                self.driver.get(url)
            except TimeoutException:
                self.logger.warning(f"страница для {phone} не загрузилась вовремя")
                return False
            send_btn_xpath = (
                '//button[@aria-label="Send" or @aria-label="Отправить" or '
                '@title="Send" or @title="Отправить"] | '
                '//*[@data-testid="send"] | //span[@data-icon="send"]'
            )
            invalid_phone_xpath = (
                '//div[contains(text(), "is invalid") '
                'or contains(text(), "не зарегистрирован") '
                'or contains(text(), "недействителен")]'
            )
            clicked_continue = False
            start_time = time.time()
            while True:
                if time.time() - start_time > 45:
                    self.logger.warning(f"чат для {phone} не загрузился вовремя")
                    return False

                if not clicked_continue:
                    clicked_continue = self._handle_continue_to_chat()
                    if clicked_continue:
                        time.sleep(2)
                        continue

                send_btns = self.driver.find_elements(By.XPATH, send_btn_xpath)
                if send_btns:
                    for send_btn in send_btns:
                        try:
                            if send_btn.is_displayed() and send_btn.is_enabled():
                                send_btn.click()
                                time.sleep(3)
                                return True
                        except WebDriverException:
                            continue

                invalid_alerts = self.driver.find_elements(By.XPATH, invalid_phone_xpath)
                if invalid_alerts:
                    self.logger.warning(f"номер не зарегистрирован: {phone}")
                    return False
                time.sleep(1)

        except WebDriverException as e:
            self.logger.error(f"ошибка webdriver при отправке на {phone}: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"ошибка отправки на {phone}: {str(e)}")
            return False
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                self.logger.warning("не удалось закрыть браузер")
