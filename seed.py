import random
from app import app
from models import db, User, Recipe, Ingredient, ViewHistory, MasterIngredient
from models import DifficultyEnum, DietEnum, CourseEnum, CuisineEnum
import re
# --- BỘ DỮ LIỆU 50 MÓN ĂN THẬT - ĐÃ SẮP XẾP LẠI THEO YÊU CẦU ---
# Mỗi tuple chứa: (Tên, Nguyên liệu, Thời gian nấu, Ẩm thực, Loại món)

RECIPE_DATA = [
    # Nhóm 1
    ("Phở Bò Hà Nội", "Thịt bò, Bánh phở, Hành lá, Rau mùi, Hồi, Quế, Thảo quả", 180, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Bún Chả", "Bún, Thịt ba chỉ, Chả băm, Rau sống, Nước mắm chua ngọt, Đu đủ", 45, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Bánh Mì Thịt Nướng", "Bánh mì, Thịt nướng, Pate, Đồ chua, Dưa leo, Rau mùi, Sốt", 25, CuisineEnum.VIETNAMESE, CourseEnum.APPETIZER),
    ("Gỏi Cuốn Tôm Thịt", "Bánh tráng, Tôm, Thịt luộc, Bún, Hẹ, Xà lách, Tương đen", 30, CuisineEnum.VIETNAMESE, CourseEnum.APPETIZER),
    ("Bún Bò Huế", "Bún, Bắp bò, Giò heo, Mắm ruốc, Sả, Ớt, Huyết", 240, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Cơm Tấm Sườn Bì Chả", "Gạo tấm, Sườn cốt lết, Bì, Chả trứng, Nước mắm, Mỡ hành", 90, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Bánh Xèo Miền Tây", "Bột gạo, Nước cốt dừa, Tôm, Thịt ba chỉ, Giá đỗ, Nước mắm chua ngọt", 40, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Cá Kho Tộ", "Cá lóc hoặc cá basa, Nước mắm, Đường, Nước màu, Tỏi, Ớt, Tiêu", 50, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Canh Chua Cá Lóc", "Cá lóc, Me, Dứa, Cà chua, Giá đỗ, Bạc hà, Ngò gai", 35, CuisineEnum.VIETNAMESE, CourseEnum.SOUP),
    ("Gà Kho Gừng", "Thịt gà, Gừng, Nước mắm, Đường, Hành khô", 45, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),

    # Nhóm 2
    ("Bò Lúc Lắc", "Thịt bò thăn, Ớt chuông, Hành tây, Tỏi, Dầu hào, Khoai tây chiên", 30, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Chả Cá Lã Vọng", "Cá lăng, Thì là, Hành lá, Mắm tôm, Bún, Lạc rang", 60, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Nem Rán (Chả Giò)", "Thịt băm, Mộc nhĩ, Miến, Trứng, Cà rốt, Su hào, Bánh đa nem", 50, CuisineEnum.VIETNAMESE, CourseEnum.APPETIZER),
    ("Mì Quảng", "Mì quảng, Tôm, Thịt heo, Trứng cút, Bánh đa, Đậu phộng, Rau sống", 75, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Cao Lầu Hội An", "Mì cao lầu, Thịt xá xíu, Da heo chiên giòn, Giá, Rau thơm", 120, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Bún Thang", "Bún, Gà xé, Giò lụa, Trứng chiên, Nấm hương, Củ cải khô, Mắm tôm", 90, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Lẩu Mắm", "Mắm cá sặc, Thịt ba rọi, Tôm, Mực, Cá hú, Rau đắng, Bông súng", 100, CuisineEnum.VIETNAMESE, CourseEnum.SOUP),
    ("Thịt Kho Trứng", "Thịt ba chỉ, Trứng vịt, Nước dừa tươi, Nước mắm, Hành khô", 70, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Cháo Lòng", "Gạo, Lòng lợn (tim, gan, cật, dồi), Huyết, Hành lá, Gía, Rau thơm", 80, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Bò Bía", "Bánh tráng, Củ sắn, Lạp xưởng, Trứng, Tôm khô, Rau thơm, Tương", 30, CuisineEnum.VIETNAMESE, CourseEnum.APPETIZER),
    ("Salad Dầu Giấm Trứng", "Xà lách, Cà chua, Dưa leo, Trứng luộc, Dầu oliu, Giấm", 15, CuisineEnum.VIETNAMESE, CourseEnum.SALAD),
    ("Chè Hạt Sen Long Nhãn", "Hạt sen, Long nhãn, Đường phèn", 60, CuisineEnum.VIETNAMESE, CourseEnum.DESSERT),
    ("Sườn Xào Chua Ngọt", "Sườn non, Cà chua, Dứa, Hành tây, Giấm, Đường", 45, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Nem Lụi Huế", "Thịt heo xay, Bì heo, Sả, Mè, Bánh tráng, Rau sống, Nước lèo", 60, CuisineEnum.VIETNAMESE, CourseEnum.MAIN_COURSE),
    ("Bánh Bột Lọc", "Bột năng, Tôm, Thịt ba chỉ, Mộc nhĩ, Nước mắm cay ngọt", 75, CuisineEnum.VIETNAMESE, CourseEnum.APPETIZER),

    # Nhóm 3
    ("Salad Caesar Gà Nướng", "Xà lách Roman, Ức gà, Bánh mì, Phô mai Parmesan, Sốt Caesar", 20, CuisineEnum.AMERICAN, CourseEnum.SALAD),
    ("Spaghetti Carbonara", "Mì Ý, Trứng, Phô mai Pecorino, Thịt má heo Guanciale, Tiêu đen", 25, CuisineEnum.ITALIAN, CourseEnum.MAIN_COURSE),
    ("Pizza Margherita", "Bột pizza, Sốt cà chua San Marzano, Phô mai Mozzarella, Húng quế tươi", 30, CuisineEnum.ITALIAN, CourseEnum.MAIN_COURSE),
    ("Bít Tết Sốt Tiêu Xanh", "Thịt bò thăn ngoại, Tiêu xanh, Kem tươi, Rượu Brandy, Khoai tây", 40, CuisineEnum.AMERICAN, CourseEnum.MAIN_COURSE),
    ("Lasagna Bò Bằm", "Lá lasagna, Thịt bò băm, Sốt cà chua, Sốt béchamel, Phô mai", 120, CuisineEnum.ITALIAN, CourseEnum.MAIN_COURSE),
    ("Sushi Cuộn California", "Cơm sushi, Rong biển, Thanh cua, Bơ, Dưa leo, Trứng cá tobiko", 35, CuisineEnum.JAPANESE, CourseEnum.APPETIZER),
    ("Mì Ramen Tonkotsu", "Mì ramen, Nước hầm xương heo, Thịt heo Chashu, Trứng lòng đào, Măng, Rong biển", 360, CuisineEnum.JAPANESE, CourseEnum.MAIN_COURSE),
    ("Cơm Cà Ri Nhật", "Thịt gà hoặc bò, Khoai tây, Cà rốt, Hành tây, Viên cà ri Nhật", 50, CuisineEnum.JAPANESE, CourseEnum.MAIN_COURSE),
    ("Tempura Thập Cẩm", "Tôm, Các loại rau củ (bí đỏ, cà tím), Bột tempura, Nước tương", 30, CuisineEnum.JAPANESE, CourseEnum.APPETIZER),
    ("Kimchi Jjigae", "Kim chi cải thảo, Đậu phụ, Thịt ba chỉ heo, Hành lá, Nấm kim châm", 30, CuisineEnum.KOREAN, CourseEnum.SOUP),
    ("Bibimbap (Cơm Trộn)", "Cơm, Thịt bò, Trứng ốp la, Rau củ các loại (cải bó xôi, cà rốt, giá), Sốt gochujang", 25, CuisineEnum.KOREAN, CourseEnum.MAIN_COURSE),
    ("Gà Rán Sốt Cay Yangnyeom", "Cánh gà, Bột chiên, Sốt gochujang, Mật ong, Tỏi", 40, CuisineEnum.KOREAN, CourseEnum.MAIN_COURSE),
    ("Miến Trộn Japchae", "Miến khoai lang, Thịt bò, Cải bó xôi, Nấm, Cà rốt, Dầu mè", 35, CuisineEnum.KOREAN, CourseEnum.MAIN_COURSE),
    ("Lẩu Thái Tom Yum Goong", "Tôm sú, Nấm rơm, Sả, Riềng, Lá chanh, Nước cốt dừa, Ớt sa tế", 45, CuisineEnum.THAI, CourseEnum.SOUP),
    ("Pad Thái", "Bánh phở, Tôm hoặc gà, Đậu phụ, Giá đỗ, Trứng, Sốt me, Lạc rang", 20, CuisineEnum.THAI, CourseEnum.MAIN_COURSE),
    ("Gỏi Đu Đủ Som Tum", "Đu đủ xanh, Tôm khô, Đậu phộng, Chanh, Ớt, Nước mắm", 15, CuisineEnum.THAI, CourseEnum.SALAD),
    ("Cà Ri Gà Xanh", "Thịt gà, Nước cốt dừa, Sốt cà ri xanh, Măng, Húng quế Thái", 35, CuisineEnum.THAI, CourseEnum.MAIN_COURSE),
    ("Đậu Hũ Ma Bà (Mapo Tofu)", "Đậu phụ non, Thịt heo băm, Tương đậu cay Doubanjiang, Xuyên tiêu", 25, CuisineEnum.CHINESE, CourseEnum.MAIN_COURSE),
    ("Gà Kung Pao", "Thịt gà, Đậu phộng, Ớt khô, Hành lá, Giấm, Đường", 30, CuisineEnum.CHINESE, CourseEnum.MAIN_COURSE),
    ("Sườn Nướng BBQ Kiểu Mỹ", "Sườn heo, Sốt BBQ, Bột ớt Paprika, Bột tỏi", 180, CuisineEnum.AMERICAN, CourseEnum.MAIN_COURSE),
    ("Hamburger Bò Phô Mai", "Thịt bò xay, Bánh hamburger, Phô mai Cheddar, Xà lách, Cà chua", 20, CuisineEnum.AMERICAN, CourseEnum.MAIN_COURSE),
    ("Cánh Gà Chiên Buffalo", "Cánh gà, Bơ, Sốt ớt Frank's RedHot", 45, CuisineEnum.AMERICAN, CourseEnum.APPETIZER),
    ("Tiramisu", "Bánh ladyfinger, Cà phê Espresso, Phô mai Mascarpone, Trứng, Rượu Marsala, Bột cacao", 30, CuisineEnum.ITALIAN, CourseEnum.DESSERT),
    ("Panna Cotta Xoài", "Kem tươi, Sữa, Đường, Gelatin, Xoài xay nhuyễn", 20, CuisineEnum.ITALIAN, CourseEnum.DESSERT),
    ("Bánh Brownie Socola", "Socola đen, Bơ, Trứng, Đường, Bột mì", 40, CuisineEnum.AMERICAN, CourseEnum.DESSERT),
]

# --- PHẦN CÒN LẠI CỦA SCRIPT GIỮ NGUYÊN ---

USER_INGREDIENTS = [
    "Thịt bò", "Thịt heo", "Thịt gà", "Trứng", "Cá", "Tôm", "Hành tây", "Tỏi",
    "Gừng", "Sả", "Ớt", "Hành lá", "Rau mùi", "Xà lách", "Cà chua", "Dưa leo",
    "Khoai tây", "Cà rốt", "Nấm", "Đậu phụ", "Gạo", "Bún", "Mì Ý", "Phô mai",
    "Sữa tươi", "Bơ", "Dầu ăn", "Nước mắm", "Đường", "Muối", "Tiêu", "Dứa",
    "Chanh", "Giá đỗ", "Bột mì", "Bột gạo", "Kim chi", "Rong biển", "Sốt cà chua"
]

INSTRUCTIONS_TEXT = "Bước 1: Sơ chế tất cả nguyên liệu. Rửa sạch thịt/cá, thái vừa ăn. Nhặt và rửa sạch các loại rau củ.\nBước 2: Tẩm ướp gia vị trong khoảng 15-20 phút để món ăn thêm đậm đà.\nBước 3: Chế biến chính. Xào, nấu, hoặc kho theo công thức.\nBước 4: Nêm nếm lại cho vừa ăn, thêm hành lá, rau thơm và trình bày ra đĩa."

def seed_master_ingredients():
    """Phân tích các công thức và tạo ra một danh sách nguyên liệu gốc."""
    print("Đang tạo danh sách nguyên liệu gốc (Master Ingredients)...")
    db.session.query(MasterIngredient).delete()
    db.session.commit()

    all_recipes = Recipe.query.all()
    unique_ingredient_names = set()
    splitter = re.compile(r'\s*,\s*')

    for recipe in all_recipes:
        ingredients = [ing.strip().lower() for ing in splitter.split(recipe.ingredients) if ing.strip()]
        unique_ingredient_names.update(ingredients)

    for name in sorted(list(unique_ingredient_names)):
        # Tạo URL ảnh minh họa một lần và lưu lại
        # Sử dụng urlencode để xử lý các ký tự đặc biệt
        from urllib.parse import urlencode
        query_params = urlencode({'query': f'Fresh {name} on a clean white background'})
        image_url = f"https://readdy.ai/api/search-image?{query_params}&width=300&height=200"

        master_ingredient = MasterIngredient(
            name=name,
            display_name=name.capitalize(),
            image_url=image_url
        )
        db.session.add(master_ingredient)
    
    db.session.commit()
    print(f"Đã tạo {len(unique_ingredient_names)} nguyên liệu gốc.")
def seed_database():
    """Xóa dữ liệu cũ và tạo dữ liệu mẫu cho toàn bộ database."""
    with app.app_context():
        print("Đang xóa dữ liệu cũ...")
        db.session.query(ViewHistory).delete()
        db.session.query(Ingredient).delete()
        db.session.query(Recipe).delete()
        db.session.query(User).delete()
        db.session.commit()
        print("Đã xóa dữ liệu cũ thành công.")

        print("Đang tạo User...")
        user1 = User(fullname="An Nguyễn", email="an@example.com", username="annguyen")
        user1.set_password("123456")
        user2 = User(fullname="Bình Trần", email="binh@example.com", username="binhtran")
        user2.set_password("123456")
        db.session.add_all([user1, user2])
        db.session.commit()
        users = [user1, user2]
        print("Đã tạo 2 user: 'annguyen' và 'binhtran' (mật khẩu: 123456)")

        print("Đang tạo nguyên liệu mẫu...")
        for i in range(50):
            ingredient_name = random.choice(USER_INGREDIENTS)
            owner = random.choice(users)
            existing_ingredient = Ingredient.query.filter_by(name=ingredient_name, owner=owner).first()
            if not existing_ingredient:
                new_ingredient = Ingredient(name=ingredient_name, owner=owner)
                db.session.add(new_ingredient)
        db.session.commit()
        print("Đã tạo nguyên liệu mẫu.")

        print("Đang tạo 50 món ăn...")
        created_recipes = []
        for index, (name, ingredients, time, cuisine, course) in enumerate(RECIPE_DATA):
            image_number = index + 1
            new_recipe = Recipe(
                name=name,
                ingredients=ingredients,
                cooking_time=time,
                instructions=INSTRUCTIONS_TEXT,
                difficulty=random.choice(list(DifficultyEnum)),
                diet=random.choice(list(DietEnum)),
                course=course,
                cuisine=cuisine,
                author=random.choice(users),
                image_file=f"{image_number}.jpg" # Sẽ liên kết với 1.jpg, 2.jpg, ..., 50.jpg
            )
            db.session.add(new_recipe)
            created_recipes.append(new_recipe)
        db.session.commit()
        print("Đã tạo 50 món ăn.")

        print("Đang tạo 20 lịch sử xem...")
        if created_recipes:
            for user in users:
                recipes_to_view = random.sample(created_recipes, k=10)
                for recipe in recipes_to_view:
                    new_history = ViewHistory(
                        user_id=user.id,
                        recipe_id=recipe.id,
                        view_count=random.randint(1, 15)
                    )
                    db.session.add(new_history)
            db.session.commit()
            print("Đã tạo 20 lịch sử xem (10 cho mỗi user).")
        seed_master_ingredients()

        print("\n--- HOÀN TẤT TẠO DỮ LIỆU MẪU! ---")

if __name__ == '__main__':
    seed_database()