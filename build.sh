#!/usr/bin/env bash
# exit on error
set -o errexit

# --- PHẦN THÊM MỚI ---
# Di chuyển đến thư mục gốc của script, nơi chứa các file Python
cd "$(dirname "$0")"
# --------------------

# Nâng cấp pip để đảm bảo tương thích
pip install --upgrade pip

# Cài đặt tất cả các thư viện từ requirements.txt
pip install -r requirements.txt

# Chạy các lệnh khởi tạo database và dữ liệu
# Bây giờ các lệnh này sẽ được chạy từ đúng thư mục
python -m flask init-db
python seed.py
python update_images.py