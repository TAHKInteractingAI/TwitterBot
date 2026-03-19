import os
import time
import random
import gspread
import requests
import pandas as pd
import time
import random
import tempfile
import threading

from flask import Flask
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from oauth2client.service_account import ServiceAccountCredentials

app = Flask(__name__)


# Schedule the bot to run every day at 9:00 AM
def run_twitter_bot():
    print("🤖 Đang khởi động bot...")

    SHEET_URL = "https://docs.google.com/spreadsheets/d/1PhLeAyLGlpq4_2fnkMIUNqpmOHIOiihfKLjE3C7vbVI/edit?usp=sharing"

    PROFILE_PATH = (
        r"C:\Users\Admin\AppData\Roaming\Mozilla\Firefox\Profiles\pb3t7nk5.twitterbot"
    )

    options = webdriver.FirefoxOptions()
    options.add_argument("-profile")
    options.add_argument(PROFILE_PATH)
    # options.profile = PROFILE_PATH

    # ❌ DO NOT use headless
    driver = webdriver.Firefox(options=options)
    driver.implicitly_wait(10)

    driver.get("https://x.com/home")
    time.sleep(5)

    if "login" in driver.current_url:
        print("❌ Not logged in — open Firefox manually and login")
    else:
        print("✅ Logged in via profile")

    def load_tweet_sheet(sheet_url):
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive",
        ]

        creds = ServiceAccountCredentials.from_json_keyfile_name(
            "service_account.json", scope
        )

        client = gspread.authorize(creds)

        # 👇 IMPORTANT: select worksheet by name
        worksheet = client.open_by_url(sheet_url).worksheet("input_tweet")

        data = worksheet.get_all_records()
        df = pd.DataFrame(data)

        return worksheet, df

    def build_main_tweet(row, max_mentions=4):
        tags = row.get("TAG", "")
        hashtags = row.get("HASHTAG", "")
        content = row.get("Tweet content", "")
        add_content = row.get("Add content", "")

        # --- Clean lists ---
        tag_list = [f"@{t.strip()}" for t in tags.split(",") if t.strip()]
        hashtag_list = [f"#{h.strip()}" for h in hashtags.split(",") if h.strip()]

        # --- Limit mentions (3–4 randomly for natural look) ---
        if len(tag_list) > max_mentions:
            random.shuffle(tag_list)
            tag_list = tag_list[: random.randint(3, max_mentions)]

        parts = []

        if content:
            parts.append(content.strip())

        if hashtag_list:
            parts.append(" ".join(hashtag_list))

        if tag_list:
            parts.append(" ".join(tag_list))

        main_text = " ".join(parts).strip()

        return main_text, add_content.strip()

    def upload_image(driver, image_path_or_url):
        if not image_path_or_url:
            return

        temp_file_path = None  # track if we create temp file

        try:
            # If it's a URL → download first
            if image_path_or_url.startswith("http"):
                print("⬇ Downloading image...")

                response = requests.get(image_path_or_url, timeout=30)
                response.raise_for_status()

                temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png")
                temp_file.write(response.content)
                temp_file.close()

                temp_file_path = temp_file.name
                image_path = temp_file_path

            else:
                image_path = os.path.abspath(image_path_or_url)

            print("🖼 Uploading image...")

            image_input = WebDriverWait(driver, 30).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )

            image_input.send_keys(image_path)

            print("✅ Image uploaded successfully")
            time.sleep(10)  # wait for upload to complete

        finally:
            # Delete temp file if we created one
            if temp_file_path and os.path.exists(temp_file_path):
                try:
                    os.remove(temp_file_path)
                    print("🧹 Temp image deleted")
                except Exception as e:
                    print("⚠ Could not delete temp file:", e)

    def validate_part(text, part_name="Tweet content", max_length=280):
        length = len(text)

        if length > max_length:
            print(f"\n❌ {part_name} TOO LONG")
            print("Length:", length)
            print("Limit :", max_length)
            print("Please adjust content in Google Sheet.\n")
            return False

        print(f"✅ {part_name} OK ({length}/{max_length})")
        return True

    def click_add_post(driver, max_attempts=2):
        for attempt in range(max_attempts):
            print(f"🔄 Attempt {attempt+1} to click Add post")

            add_button = WebDriverWait(driver, 20).until(
                EC.presence_of_element_located(
                    (By.XPATH, "//*[@aria-label='Add post']")
                )
            )

            actions = ActionChains(driver)
            actions.move_to_element(add_button).pause(0.5).click().perform()

            time.sleep(2)

        print("done trying to click Add post")

    def human_type(textbox, text):
        words = text.split(" ")

        for i, word in enumerate(words):
            textbox.send_keys(word)

            # Add space after every word except last
            if i < len(words) - 1:
                textbox.send_keys(" ")

            # Normal typing pause
            time.sleep(random.uniform(0.15, 0.4))

            # Occasional longer pause (thinking)
            if random.random() < 0.08:
                time.sleep(random.uniform(0.8, 1.5))

    def post_to_twitter(driver, main_text, image_path, add_content=None):
        driver.get("https://x.com/compose/post")
        time.sleep(10)

        textbox = WebDriverWait(driver, 45).until(
            EC.presence_of_element_located(
                (By.XPATH, "//div[@data-testid='tweetTextarea_0' and @role='textbox']")
            )
        )

        textbox.click()
        time.sleep(2)

        textbox.clear()  # optional
        human_type(textbox, main_text)
        time.sleep(2)

        if image_path:
            upload_image(driver, image_path)

        # --- If Add content exists ---
        if add_content:
            print("➕ Adding second post...")

            before_count = len(driver.find_elements(By.XPATH, "//div[@role='textbox']"))
            print("Textbox count before:", before_count)

            click_add_post(driver)

            WebDriverWait(driver, 10).until(
                lambda d: len(d.find_elements(By.XPATH, "//div[@role='textbox']"))
                > before_count
            )

            # Get second textbox (always last one)
            textboxes = driver.find_elements(By.XPATH, "//div[@role='textbox']")
            print("Textbox count:", len(textboxes))

            second_box = textboxes[-2]

            for attempt in range(3):
                print(f"🔄 Attempt {attempt+1} to click second textbox")
                actions = ActionChains(driver)
                actions.move_to_element(second_box).pause(0.5).click().perform()

            time.sleep(1)

            human_type(second_box, add_content)
            time.sleep(2)

        time.sleep(5)

        textbox.send_keys(Keys.CONTROL, Keys.ENTER)

        time.sleep(random.randint(6, 9))

    worksheet, df = load_tweet_sheet(SHEET_URL)

    try:
        for idx, row in df.iterrows():
            print(f"\n--- Processing row {idx + 2} ---")
            status = row.get("Status", "").lower()

            # skip already posted
            if status == "success":
                continue

            main_text, add_content = build_main_tweet(row)
            print("Main text length:", len(main_text))
            print("Add content length:", len(add_content))
            image_path = row.get("IMAGE", "").strip()

            if not main_text:
                continue

            # 🔎 Validate before posting
            if not validate_part(main_text):
                worksheet.update_cell(idx + 2, 6, f"too long - main")
                break

            if add_content and not validate_part(add_content, part_name="Add content"):
                worksheet.update_cell(idx + 2, 6, f"too long - add content")
                break

            try:
                post_to_twitter(driver, main_text, image_path, add_content)
                worksheet.update_cell(idx + 2, 6, "Success")  # Status column
                print(f"✅ Posted row {idx + 2}")

            except Exception as e:
                worksheet.update_cell(idx + 2, 6, f"Failed")
                print(f"❌ Failed row {idx + 2}: {e}")
                break
    finally:
        print("Closing browser...")
        time.sleep(5)
        driver.quit()

    print("Done, closing...")
    time.sleep(10)


@app.route("/trigger-bot", methods=["GET"])
def trigger_bot():
    # Sử dụng Threading để chạy bot ngầm.
    # Do cron-job.org chỉ đợi phản hồi vài chục giây, nếu bot chạy quá lâu nó sẽ báo lỗi Timeout.
    # Nên ta sẽ trả lời "OK" ngay lập tức cho cron-job, còn bot cứ âm thầm chạy.
    bot_thread = threading.Thread(target=run_twitter_bot)
    bot_thread.start()

    return "✅ Đã nhận lệnh từ cron-job.org, Bot đang chạy ngầm!", 200


if __name__ == "__main__":
    # Chạy server ở port 5000, mở ra môi trường mạng (0.0.0.0)
    app.run(host="0.0.0.0", port=5000)
