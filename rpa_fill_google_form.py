import sys
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options

def analyze_form_fields(form_url):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    driver.get(form_url)
    time.sleep(2)
    text_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
    num_fields = len(text_inputs)
    driver.quit()
    return num_fields

def fill_google_form(form_url, field_values):
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    driver = webdriver.Chrome(options=options)
    driver.get(form_url)
    time.sleep(2)

    try:
        text_inputs = driver.find_elements(By.CSS_SELECTOR, "input[type='text']")
        if len(text_inputs) < len(field_values):
            driver.quit()
            return f"⚠️ В форме меньше полей ({len(text_inputs)}), чем данных для заполнения ({len(field_values)})."

        for idx, value in enumerate(field_values):
            text_inputs[idx].send_keys(value)
            time.sleep(0.5)

        submit_button = driver.find_element(By.CSS_SELECTOR, "div[role='button']")
        submit_button.click()
        time.sleep(2)

        driver.quit()
        return "✅ Форма успешно заполнена!"
    except Exception as e:
        driver.quit()
        return f"⚠️ Произошла ошибка: {e}"

if __name__ == "__main__":
    if len(sys.argv) >= 3:
        mode = sys.argv[1]
        form_url = sys.argv[2]
        if mode == "analyze":
            result = analyze_form_fields(form_url)
            print(result)
        elif mode == "fill":
            field_values = sys.argv[3:]
            result = fill_google_form(form_url, field_values)
            print(result)
        else:
            print("⚠️ Неизвестный режим. Используй: analyze или fill.")
    else:
        print("⚠️ Недостаточно аргументов. Используй: python3 rpa_fill_google_form.py <mode> <form_url> [<values>...]")
