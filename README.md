# Twitter/X Auto-Post Bot (Selenium + GitHub Actions)

Dự án bot tự động đăng bài lên Twitter (X) hoàn toàn miễn phí. Bot đọc nội dung văn bản từ **Google Sheets**, tự động tải ảnh ngẫu nhiên từ **Google Drive** và sử dụng **Selenium** để mô phỏng hành vi đăng bài của người thật. Hệ thống được thiết kế để chạy tự động trên **GitHub Actions** và điều khiển lịch trình qua **cron-job.org**.

## Tính năng nổi bật

- **Tự động hóa hoàn toàn:** Đọc dữ liệu (Content, Hashtag, Mention) từ Google Sheets.
- **Tích hợp Google Drive:** Tự động trích xuất Folder ID từ link Drive và chọn ngẫu nhiên 1 bức ảnh trong thư mục để đính kèm vào bài viết.
- **Chống Spam (Anti-Ban):** - Mô phỏng tốc độ gõ phím ngẫu nhiên của người thật.
  - Sử dụng Cookie để đăng nhập thay vì nhập tài khoản/mật khẩu.
  - Đăng 1 bài/lần chạy rồi tự động ngắt máy chủ để tránh bị Twitter đánh dấu IP spam.
- **Ghi log thông minh:** Tự động ghi lại trạng thái (`Success` / `Failed`), URL bài đăng và thời gian đăng (theo múi giờ Việt Nam UTC+7) ngược lại vào Google Sheets.
- **Tiết kiệm tài nguyên:** Được thiết kế tối ưu hóa để sử dụng dưới giới hạn 2000 phút miễn phí/tháng của GitHub Actions.

---

## Cấu trúc Google Sheet yêu cầu

File Google Sheet cần có một trang tính (worksheet) tên là `input_tweet` với các cột tiêu đề sau:

- `TAG`: Tên các tài khoản muốn tag (cách nhau bằng dấu phẩy).
- `HASHTAG`: Các hashtag muốn gắn (cách nhau bằng dấu phẩy).
- `Tweet content`: Nội dung bài viết chính (Giới hạn < 280 ký tự).
- `Add content`: Nội dung bài viết phụ (Reply/Thread - tùy chọn).
- `IMAGE`: Link thư mục Google Drive chứa ảnh.
- `Status`: Trạng thái (Bot sẽ điền `Success` hoặc `Failed`).
- `Link bài đã post`: URL của bài Tweet sau khi đăng thành công.
- `Date post`: Thời gian đăng bài (Múi giờ VN).

---

## Hướng dẫn cài đặt (Setup Guide)

### Bước 1: Chuẩn bị API Google

1. Truy cập [Google Cloud Console](https://console.cloud.google.com/), bật **Google Sheets API** và **Google Drive API**.
2. Tạo một **Service Account** và tải file JSON (Credentials) về máy.
3. Chia sẻ quyền truy cập (Edit) file Google Sheet và các thư mục Google Drive cho địa chỉ email của Service Account.

### Bước 2: Lấy Cookie Twitter (X)

1. Đăng nhập vào Twitter trên trình duyệt (Chrome/Firefox).
2. Sử dụng tiện ích mở rộng (như *Cookie-Editor* hoặc *EditThisCookie*) để Export toàn bộ Cookie của trang `x.com` dưới dạng JSON.

### Bước 3: Cấu hình GitHub Repository

1. Upload file code `TwitterAutoPost.py` và `requirements.txt` lên kho lưu trữ này.
2. Truy cập **Settings > Secrets and variables > Actions**.
3. Thêm 2 biến bảo mật (New repository secret):
   - `GOOGLE_CREDENTIALS`: Dán toàn bộ nội dung file JSON của Service Account vào đây.
   - `TWITTER_COOKIES`: Dán toàn bộ chuỗi JSON Cookie của Twitter vào đây.

### Bước 4: Thiết lập GitHub Actions Workflow

Tạo file `.github/workflows/run-bot.yml` với nội dung sau để cho phép bot nhận lệnh từ bên ngoài:

```yaml
name: Run Twitter Bot
on:
  repository_dispatch:
    types: [trigger-bot]
jobs:
  post-tweet:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v3
      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install dependencies
        run: pip install -r requirements.txt
      - name: Run Bot
        env:
          GOOGLE_CREDENTIALS: ${{ secrets.GOOGLE_CREDENTIALS }}
          TWITTER_COOKIES: ${{ secrets.TWITTER_COOKIES }}
        run: python -u TwitterAutoPost.py
```

### Bước 5: Lên lịch bằng Cron-job.org

1. Tạo một **Personal Access Token (PAT)** trên GitHub (cấp quyền   `repo`).

2. Truy cập cron-job.org tạo một Job mới với tần suất **Mỗi 30 phút/lần** (Every 30 minutes).

3. Tab Common: Điền URL `https://api.github.com/repos/<USERNAME_CỦA_BẠN>/<TÊN_REPO_CỦA_BẠN>/dispatches`.

4. Tab Advanced:

- HTTP Method: `POST`

- Bổ sung 3 Headers:

  - `Accept`: `application/vnd.github.v3+json`

  - `Authorization`: `Bearer <MÃ_PAT_CỦA_BẠN>`

  - `User-Agent`: `cron-job`

- Request Body (chọn Raw): `{"event_type": "trigger-bot"}`
