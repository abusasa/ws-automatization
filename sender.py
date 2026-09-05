import urllib.parse
import time
import logging
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
        self.logger.info("Запуск Chrome")
        self.driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        self.driver.set_page_load_timeout(page_load_timeout)
        self.wait = WebDriverWait(self.driver, 30)
    def wait_for_login(self):
        try:
            self.driver.get("https://web.whatsapp.com/")
        except TimeoutException:
            self.logger.error("Таймаут загрузки web.whatsapp.com")
            raise
        self.logger.info("Ожидание входа в WhatsApp Web")
        WebDriverWait(self.driver, 300).until(
            EC.presence_of_element_located(
                (By.XPATH, '//div[@contenteditable="true"][@data-tab="3"] | //canvas[@aria-label="Scan me!"]')
            )
        )
        try:
            WebDriverWait(self.driver, 300).until(
                EC.presence_of_element_located((By.XPATH, '//div[@id="pane-side"]'))
            )
            self.logger.info("Вход выполнен")
        except Exception:
            self.logger.error("Время входа истекло")
            raise
    def _handle_continue_to_chat(self):
        continue_xpath = (
            '//a[contains(@href, "send") and '
            '(contains(., "Continue to Chat") or contains(., "Продолжить"))] '
            '| //div[@role="button"]'
            '[contains(., "Continue to Chat") or contains(., "Продолжить")]'
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
                self.logger.warning(f"Таймаут загрузки страницы для {phone}")
                return False
            send_btn_xpath = '//span[@data-icon="send"]'
            invalid_phone_xpath = (
                '//div[contains(text(), "is invalid") '
                'or contains(text(), "не зарегистрирован") '
                'or contains(text(), "недействителен")]'
            )
            clicked_continue = False
            start_time = time.time()
            while True:
                if time.time() - start_time > 45:
                    self.logger.warning(f"Таймаут загрузки чата для {phone}")
                    return False

                if not clicked_continue:
                    clicked_continue = self._handle_continue_to_chat()
                    if clicked_continue:
                        time.sleep(2)
                        continue

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

        except WebDriverException as e:
            self.logger.error(f"Ошибка WebDriver при отправке на {phone}: {str(e)}")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка отправки на {phone}: {str(e)}")
            return False
    def close(self):
        if self.driver:
            try:
                self.driver.quit()
            except Exception:
                self.logger.warning("Ошибка при закрытии браузера (возможно, он уже был закрыт)")
