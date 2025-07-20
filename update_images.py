# update_images.py

import time
import requests
import os
from sqlalchemy import or_

# Import các thành phần cần thiết từ ứng dụng Flask của bạn
from app import app
from models import db, MasterIngredient

# Tải các biến môi trường từ file .env

# --- CẤU HÌNH ---
# Lấy Access Key từ biến môi trường
UNSPLASH_ACCESS_KEY = ("yhRxo1_x0SSFbow6hth2Fa7FlfBnoz8XJ3k9kLaiwbg")
# Thời gian chờ giữa các lần gọi API (giây) để tuân thủ rate limit
API_CALL_DELAY = 1.5 

def find_and_update_images():
    """
    Script cuối cùng, sử dụng API chính thức của Unsplash để tìm ảnh,
    đảm bảo độ tin cậy và tránh lỗi 503.
    """
    if not UNSPLASH_ACCESS_KEY:
        print("LỖI: Không tìm thấy UNSPLASH_ACCESS_KEY trong file .env.")
        print("Vui lòng đăng ký key tại https://unsplash.com/developers và thêm vào file .env.")
        return

    with app.app_context():
        print("Bắt đầu tìm kiếm các nguyên liệu chưa có ảnh (sử dụng API Unsplash)...")
        
        ingredients_to_update = MasterIngredient.query.filter(
            or_(MasterIngredient.image_url == None, MasterIngredient.image_url == '')
        ).all()
        
        if not ingredients_to_update:
            print("Tất cả nguyên liệu đã có ảnh. Không có gì để cập nhật.")
            return

        total_ingredients = len(ingredients_to_update)
        print(f"Tìm thấy {total_ingredients} nguyên liệu cần cập nhật ảnh.")
        
        updated_count = 0
        
        for index, ingredient in enumerate(ingredients_to_update):
            display_name = ingredient.display_name
            print(f"\n[{index + 1}/{total_ingredients}] Đang tìm ảnh cho: '{display_name}'")
            
            try:
                # 1. Xây dựng URL cho API tìm kiếm của Unsplash
                api_url = "https://api.unsplash.com/search/photos"
                params = {
                    'query': f'{display_name} food ingredient',
                    'per_page': 1, # Chỉ cần 1 ảnh đẹp nhất
                    'orientation': 'landscape'
                }
                headers = {
                    'Authorization': f'Client-ID {UNSPLASH_ACCESS_KEY}'
                }

                # 2. Gọi API
                response = requests.get(api_url, params=params, headers=headers, timeout=20)
                
                # Ném lỗi nếu có vấn đề (4xx, 5xx)
                response.raise_for_status() 

                data = response.json()
                
                # 3. Xử lý kết quả
                if data['results']:
                    # Lấy URL của ảnh với chất lượng vừa phải (small)
                    image_url = data['results'][0]['urls']['small']
                    ingredient.image_url = image_url
                    print(f"   + Thành công! Đã gán ảnh cho '{display_name}'.")
                    updated_count += 1
                else:
                    print(f"   - Không tìm thấy kết quả nào cho '{display_name}'.")

            except requests.exceptions.HTTPError as e:
                # Lỗi từ phía Unsplash (ví dụ: 403 Rate Limit Exceeded)
                print(f"   ! Lỗi HTTP: {e.response.status_code} - {e.response.text}")
                if e.response.status_code == 403:
                    print("   ! Rất có thể đã hết hạn ngạch 50 yêu cầu/giờ. Vui lòng chờ hoặc dùng key khác.")
                    # Nếu hết hạn ngạch, dừng script luôn để không lãng phí
                    break 
            except requests.exceptions.RequestException as e:
                # Lỗi mạng
                print(f"   ! Lỗi mạng: {e}")
            except Exception as e:
                print(f"   ! Đã xảy ra lỗi không xác định: {e}")

            # 4. Chờ một chút trước khi gọi API tiếp theo để đảm bảo không vi phạm rate limit
            time.sleep(API_CALL_DELAY)
        
        # 5. Lưu tất cả các thay đổi vào database
        if updated_count > 0:
            print(f"\n--- Đang lưu {updated_count} thay đổi vào cơ sở dữ liệu... ---")
            db.session.commit()
            print("Hoàn tất!")
        else:
            print("\nKhông có nguyên liệu nào được cập nhật trong lần chạy này.")


# Chạy hàm chính khi script được thực thi
if __name__ == "__main__":
    find_and_update_images()