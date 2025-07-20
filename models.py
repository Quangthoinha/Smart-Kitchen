from enum import Enum as PyEnum 
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
# Initialize the db instance here. It will be configured in the main app.
db = SQLAlchemy()

# Định nghĩa các Enums
class DifficultyEnum(PyEnum):
    EASY = "Dễ"
    MEDIUM = "Trung bình"
    HARD = "Khó"

class DietEnum(PyEnum):
    NONE = "Không có"
    VEGETARIAN = "Ăn chay"
    VEGAN = "Thuần chay"
    GLUTEN_FREE = "Không gluten"
    DAIRY_FREE = "Không sữa"

class CourseEnum(PyEnum):
    MAIN_COURSE = "Món chính"
    APPETIZER = "Khai vị"
    DESSERT = "Tráng miệng"
    SOUP = "Canh/Súp"
    SALAD = "Salad"

class CuisineEnum(PyEnum):
    VIETNAMESE = "Việt Nam"
    AMERICAN = "Mỹ"
    CHINESE = "Trung Hoa"
    JAPANESE = "Nhật Bản"
    KOREAN = "Hàn Quốc"
    ITALIAN = "Ý"
    THAI = "Thái Lan"
saved_recipes = db.Table('saved_recipes',
    db.Column('user_id', db.Integer, db.ForeignKey('user.id'), primary_key=True),
    db.Column('recipe_id', db.Integer, db.ForeignKey('recipe.id'), primary_key=True)
)
# Định nghĩa Model User
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)

    # Relationship to Recipe model
    # user.recipes will return all recipes by this user
    recipes = db.relationship('Recipe', backref='author', lazy=True)
    saved_collection = db.relationship('Recipe', secondary=saved_recipes, lazy='dynamic',
                                     backref=db.backref('saved_by_users', lazy=True))
    ingredients = db.relationship('Ingredient', backref='owner', lazy=True, cascade="all, delete-orphan")
    def save_recipe(self, recipe):
        """Lưu một món ăn vào bộ sưu tập của user."""
        if not self.is_saving(recipe):
            self.saved_collection.append(recipe)

    def unsave_recipe(self, recipe):
        """Xóa một món ăn khỏi bộ sưu tập của user."""
        if self.is_saving(recipe):
            self.saved_collection.remove(recipe)

    def is_saving(self, recipe):
        """Kiểm tra xem user đã lưu món ăn này chưa."""
        return self.saved_collection.filter(
            saved_recipes.c.recipe_id == recipe.id).count() > 0

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

# Model cho Món ăn (Recipe)
class Recipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), nullable=False)
    ingredients = db.Column(db.Text, nullable=False)
    cooking_time = db.Column(db.Integer, nullable=False)
    instructions = db.Column(db.Text, nullable=False)
    image_file = db.Column(db.String(30), nullable=False, default='default.jpg')
    difficulty = db.Column(db.Enum(DifficultyEnum), nullable=False, default=DifficultyEnum.EASY)
    diet = db.Column(db.Enum(DietEnum), nullable=False, default=DietEnum.NONE)
    course = db.Column(db.Enum(CourseEnum), nullable=False, default=CourseEnum.MAIN_COURSE)
    cuisine = db.Column(db.Enum(CuisineEnum), nullable=False, default=CuisineEnum.VIETNAMESE)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Foreign key to the User who created the recipe
# models.py

# ... (các import và model khác đã có) ...

# Model cho từ điển Nguyên liệu chung (Master Ingredient Dictionary)
class MasterIngredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # Tên nguyên liệu, chuẩn hóa (viết thường, không dấu...) để dễ tìm kiếm
    name = db.Column(db.String(100), unique=True, nullable=False)
    # Tên hiển thị cho đẹp (viết hoa chữ cái đầu)
    display_name = db.Column(db.String(100), nullable=False)
    # URL ảnh minh họa cho nguyên liệu
    image_url = db.Column(db.String(500), nullable=True)

    def __repr__(self):
        return f"MasterIngredient('{self.display_name}')"

# ... (phần còn lại của file) ...
    
class Ingredient(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    
    # Mối quan hệ: Nguyên liệu này thuộc về ai?
    # 'user.id' trỏ đến bảng 'user', cột 'id'
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Ingredient('{self.name}')"
class ViewHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    
    # Khóa ngoại trỏ đến User đã xem
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    # Khóa ngoại trỏ đến Recipe được xem
    recipe_id = db.Column(db.Integer, db.ForeignKey('recipe.id'), nullable=False)
    
    # Các thông tin bổ sung
    view_count = db.Column(db.Integer, nullable=False, default=1) # Số lần xem
    last_viewed = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow) # Thời gian xem lần cuối

    # --- Định nghĩa các mối quan hệ để truy cập tiện lợi ---
    # Giúp từ ViewHistory có thể truy cập user và recipe tương ứng
    user = db.relationship('User', back_populates='view_history')
    recipe = db.relationship('Recipe', back_populates='view_history')

    # --- Đảm bảo một user chỉ có một dòng lịch sử cho mỗi recipe ---
    __table_args__ = (db.UniqueConstraint('user_id', 'recipe_id', name='_user_recipe_uc'),)

    def __repr__(self):
        return f"<ViewHistory user='{self.user.username}' recipe='{self.recipe.name}' count={self.view_count}>"
# Mở class User và thêm vào mối quan hệ với ViewHistory
User.view_history = db.relationship('ViewHistory', back_populates='user', lazy='dynamic', cascade="all, delete-orphan")

# Mở class Recipe và thêm vào mối quan hệ với ViewHistory
Recipe.view_history = db.relationship('ViewHistory', back_populates='recipe', lazy='dynamic', cascade="all, delete-orphan")