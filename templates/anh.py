import os
import requests
from serpapi import GoogleSearch
import shutil

# --- DANH SÁCH TÊN MÓN ĂN - ĐỒNG BỘ VỚI seed.py ---
RECIPE_NAMES = [
    # Nhóm 1
    "Phở Bò Hà Nội", "Bún Chả", "Bánh Mì Thịt Nướng", "Gỏi Cuốn Tôm Thịt", "Bún Bò Huế",
    "Cơm Tấm Sườn Bì Chả", "Bánh Xèo Miền Tây", "Cá Kho Tộ", "Canh Chua Cá Lóc", "Gà Kho Gừng",

    # Nhóm 2
    "Bò Lúc Lắc", "Chả Cá Lã Vọng", "Nem Rán (Chả Giò)", "Mì Quảng", "Cao Lầu Hội An",
    "Bún Thang", "Lẩu Mắm", "Thịt Kho Trứng", "Cháo Lòng", "Bò Bía",
    "Salad Dầu Giấm Trứng", "Chè Hạt Sen Long Nhãn", "Sườn Xào Chua Ngọt", "Nem Lụi Huế", "Bánh Bột Lọc",

    # Nhóm 3
    "Salad Caesar Gà Nướng", "Spaghetti Carbonara", "Pizza Margherita", "Bít Tết Sốt Tiêu Xanh", "Lasagna Bò Bằm",
    "Sushi Cuộn California", "Mì Ramen Tonkotsu", "Cơm Cà Ri Nhật", "Tempura Thập Cẩm", "Kimchi Jjigae",
    "Bibimbap (Cơm Trộn)", "Gà Rán Sốt Cay Yangnyeom", "Miến Trộn Japchae", "Lẩu Thái Tom Yum Goong", "Pad Thái",
    "Gỏi Đu Đủ Som Tum", "Cà Ri Gà Xanh", "Đậu Hũ Ma Bà (Mapo Tofu)", "Gà Kung Pao", "Sườn Nướng BBQ Kiểu Mỹ",
    "Hamburger Bò Phô Mai", "Cánh Gà Chiên Buffalo", "Tiramisu", "Panna Cotta Xoài", "Bánh Brownie Socola"
]

# --- CẤU HÌNH ---
SERPAPI_API_KEY = "492bb121b261a6eacb627008927fbb0de136bf9e49d88a803ddd32d30abef1b3"  # <-- DÁN API KEY CỦA BẠN VÀO ĐÂY
OUTPUT_FOLDER = os.path.join('static', 'recipe_pics') # Lưu trực tiếp vào thư mục ảnh chính

def download_image(image_url, save_path):
    """Tải một ảnh từ URL và lưu vào đường dẫn chỉ định."""
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(image_url, stream=True, timeout=15, headers=headers)
        response.raise_for_status() 

        with open(save_path, 'wb') as f:
            response.raw.decode_content = True
            shutil.copyfileobj(response.raw, f)
        print(f"  -> Đã lưu thành công vào: {save_path}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"  -> Lỗi khi tải ảnh: {e}")
        return False

def collect_recipe_images():
    """Tìm kiếm và tải ảnh cho từng món ăn."""
    if not SERPAPI_API_KEY or "YOUR_SERPAPI_API_KEY" in SERPAPI_API_KEY:
        print("Lỗi: Vui lòng điền SerpApi API Key của bạn vào biến SERPAPI_API_KEY.")
        return

    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    print(f"Các ảnh sẽ được lưu vào thư mục: '{OUTPUT_FOLDER}'")

    for index, recipe_name in enumerate(RECIPE_NAMES):
        image_number = index + 1
        output_filename = os.path.join(OUTPUT_FOLDER, f"{image_number}.jpg")
        
        if os.path.exists(output_filename):
            print(f"({image_number}/{len(RECIPE_NAMES)}) Bỏ qua '{recipe_name}', ảnh đã tồn tại.")
            continue

        print(f"\n({image_number}/{len(RECIPE_NAMES)}) Đang tìm ảnh cho: '{recipe_name}'...")

        params = {
            "q": f"{recipe_name} food photography beautiful", # Thêm từ khóa để có ảnh đẹp
            "tbm": "isch",
            "ijn": "0",
            "api_key": SERPAPI_API_KEY
        }

        search = GoogleSearch(params)
        results = search.get_dict()
        image_results = results.get("images_results", [])

        if image_results:
            first_image_url = image_results[0].get("original")
            print(f"  -> Tìm thấy ảnh: {first_image_url[:80]}...")
            
            download_image(first_image_url, output_filename)
        else:
            print(f"  -> Không tìm thấy ảnh nào cho '{recipe_name}'.")

    # Tạo một ảnh default.jpg dự phòng
    default_image_path = os.path.join(OUTPUT_FOLDER, 'default.jpg')
    if not os.path.exists(default_image_path) and os.path.exists(os.path.join(OUTPUT_FOLDER, '1.jpg')):
        shutil.copyfile(os.path.join(OUTPUT_FOLDER, '1.jpg'), default_image_path)
        print("\nĐã tạo file 'default.jpg' dự phòng.")


    print("\n--- HOÀN TẤT THU THẬP HÌNH ẢNH! ---")

if __name__ == '__main__':
    collect_recipe_images()