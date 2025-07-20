import requests
import base64
import json
import re
from typing import Dict, List, Tuple
import os
from PIL import Image
import io
from dotenv import load_dotenv

load_dotenv()

class FoodBillOCR:
    def __init__(self):

        self.openai_api_key = os.environ.get("OPENAI_API_KEY")
        
    def encode_image_to_base64(self, image_path: str) -> str:
        """Chuyển đổi ảnh thành base64"""
        with Image.open(image_path) as img:
            # Resize ảnh nếu quá lớn để tiết kiệm chi phí API
            if img.width > 1024 or img.height > 1024:
                img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
            
            buffer = io.BytesIO()
            img.save(buffer, format='JPEG', quality=85)
            img_bytes = buffer.getvalue()
            return base64.b64encode(img_bytes).decode('utf-8')
    
    def ocr_with_openai(self, image_path: str) -> Dict:
        """OCR sử dụng OpenAI GPT-4 Vision"""
        try:
            base64_image = self.encode_image_to_base64(image_path)
            
            headers = {
                "Authorization": f"Bearer {self.openai_api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4o",  # hoặc gpt-4-vision-preview
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": """Phân tích hóa đơn mua sắm này và trích xuất thông tin thực phẩm theo định dạng JSON:
                                {
                                    "items": [
                                        {
                                            "name": "tên thực phẩm",
                                            "quantity": số lượng,
                                            "unit": "đơn vị",
                                            "price": giá đơn vị,
                                            "total": tổng tiền
                                        }
                                    ],
                                    "total_amount": tổng tiền,
                                    "store_name": "tên cửa hàng",
                                    "date": "ngày"
                                }
                                Chỉ trả về JSON."""
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{base64_image}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 1000
            }
            
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                content = result['choices'][0]['message']['content']
                return self.parse_json_response(content)
            else:
                print(f"OpenAI API Error: {response.status_code}")
                return None
                
        except Exception as e:
            print(f"Lỗi OpenAI OCR: {str(e)}")
            return None
    

    
    def parse_json_response(self, content: str) -> Dict:
        """Parse JSON từ response của AI"""
        try:
            # Tìm JSON trong response
            json_match = re.search(r'\{.*\}', content, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                return json.loads(json_str)
            else:
                print("Không tìm thấy JSON trong response")
                return None
        except json.JSONDecodeError as e:
            print(f"Lỗi parse JSON: {str(e)}")
            return None
    
    def extract_food_info_from_text(self, text: str) -> Dict:
        """Trích xuất thông tin thực phẩm từ text thô (cho Google Vision)"""
        lines = text.strip().split('\n')
        items = []
        
        # Patterns để tìm thực phẩm và giá
        food_patterns = [
            r'(.+?)\s+(\d+(?:,\d+)*(?:\.\d+)?)\s*(?:VND|VNĐ|đ)',
            r'(.+?)\s+(\d+(?:,\d+)*(?:\.\d+)?)',
        ]
        
        for line in lines:
            line = line.strip()
            if not line or len(line) < 3:
                continue
                
            for pattern in food_patterns:
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    name = match.group(1).strip()
                    price_str = match.group(2).replace(',', '')
                    
                    # Lọc các dòng không phải thực phẩm
                    if any(skip in name.lower() for skip in ['tổng', 'total', 'tax', 'thuế', 'giảm giá']):
                        continue
                    
                    try:
                        price = float(price_str)
                        items.append({
                            "name": name,
                            "quantity": 1,
                            "unit": "món",
                            "price": price,
                            "total": price
                        })
                    except ValueError:
                        continue
                    break
        
        total_amount = sum(item['total'] for item in items)
        
        return {
            "items": items,
            "total_amount": total_amount,
            "store_name": "Không xác định",
            "date": "Không xác định"
        }
    
    def process_bill(self, image_path: str, preferred_api: str = "openai") -> Dict:
        """Xử lý hóa đơn với API được chọn"""
        if not os.path.exists(image_path):
            print(f"Không tìm thấy file: {image_path}")
            return None
        
        print(f"Đang xử lý hóa đơn với {preferred_api.upper()}...")

        if preferred_api.lower() == "openai":
            result = self.ocr_with_openai(image_path)
        
        if not result:
            print("API đầu tiên thất bại, đang thử các API khác...")
            apis = ["deepseek", "openai", "google"]
            apis.remove(preferred_api.lower() if preferred_api.lower() in apis else "deepseek")
            
            for api in apis:
                print(f"Đang thử {api.upper()}...")
                if api == "deepseek":
                    result = self.ocr_with_deepseek(image_path)
                elif api == "openai":
                    result = self.ocr_with_openai(image_path)
                elif api == "google":
                    result = self.ocr_with_google_vision(image_path)
                
                if result:
                    break
        
        return result
    
    def save_result(self, result: Dict, output_file: str = "food_bill_result.json"):
        """Lưu kết quả ra file JSON"""
        if result:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(result, f, ensure_ascii=False, indent=2)
            print(f"Đã lưu kết quả vào {output_file}")
        else:
            print("Không có kết quả để lưu")
    
    def print_result(self, result: Dict):
        """In kết quả ra console"""
        if not result:
            print("Không có kết quả để hiển thị")
            return
        
        print("\n" + "="*50)
        print("KẾT QUẢ PHÂN TÍCH HÓA ĐỚN")
        print("="*50)
        
        if result.get('store_name'):
            print(f"Cửa hàng: {result['store_name']}")
        if result.get('date'):
            print(f"Ngày: {result['date']}")
        
        print("\nDanh sách thực phẩm:")
        print("-" * 30)
        
        for i, item in enumerate(result.get('items', []), 1):
            print(f"{i}. {item.get('name', 'N/A')}")
            print(f"   Số lượng: {item.get('quantity', 'N/A')} {item.get('unit', '')}")
            print(f"   Đơn giá: {item.get('price', 0):,.0f} VNĐ")
            print(f"   Thành tiền: {item.get('total', 0):,.0f} VNĐ")
            print()
        
        print(f"TỔNG CỘNG: {result.get('total_amount', 0):,.0f} VNĐ")
        print("="*50)

# Sử dụng
def main():
    # Khởi tạo OCR
    ocr = FoodBillOCR()
    
    # Đường dẫn đến ảnh hóa đơn
    image_path = "C:/Users/Kwangthoi/bill2.jpg"
    
    # Xử lý hóa đơn (ưu tiên DeepSeek)
    result = ocr.process_bill(image_path, preferred_api="openai")
    
    if result:
        # Hiển thị kết quả
        ocr.print_result(result)
        
        # Lưu kết quả
        ocr.save_result(result)
        
    else:
        print("Không thể xử lý hóa đơn với tất cả các API")

if __name__ == "__main__":
    main()

