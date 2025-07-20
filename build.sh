#!/usr/bin/env bash
# exit on error
set -o errexit

# Nâng cấp pip để đảm bảo tương thích
pip install --upgrade pip

# Cài đặt tất cả các thư viện từ requirements.txt
pip install -r requirements.txt

# Chạy các lệnh khởi tạo database và dữ liệu
# Sử dụng 'flask' trực tiếp từ môi trường ảo
python -m flask init-db
python seed.py
python update_images.py