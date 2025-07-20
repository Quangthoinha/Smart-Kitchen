import os
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask_login import LoginManager, login_user, logout_user, current_user, login_required
import secrets
from PIL import Image
# Local imports
from OCR_API import FoodBillOCR 
from form import LoginForm, RegistrationForm, RecipeForm
# Correctly importing everything from models.py
from models import db, User, Recipe,Ingredient,ViewHistory,MasterIngredient, DifficultyEnum, DietEnum, CourseEnum, CuisineEnum
from sqlalchemy import or_ 
from sqlalchemy import text
import json
from collections import Counter
import re
from dotenv import load_dotenv
load_dotenv()
# Cấu hình Flask
app = Flask(__name__)
CORS(app) 

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'a_secure_default_secret_key_for_development_only') 
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024
database_uri = os.environ.get('DATABASE_URL')
if database_uri and database_uri.startswith("postgres://"):
    database_uri = database_uri.replace("postgres://", "postgresql://", 1)
app.config['SQLALCHEMY_DATABASE_URI'] = database_uri or 'sqlite:///users.db'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize extensions
db.init_app(app) 
login_manager = LoginManager(app)
login_manager.login_view = 'login' 
login_manager.login_message = 'Vui lòng đăng nhập để truy cập trang này.'
login_manager.login_message_category = 'info'
def get_openai_suggestion(cookable_recipes, view_history):
    """Hàm gọi API OpenAI để lấy gợi ý và xếp hạng."""
    # CHUẨN BỊ DỮ LIỆU GỬI ĐI
    # Chuyển danh sách món ăn thành một chuỗi dễ đọc cho AI
    recipe_list_str = "\n".join([f"- {r.name} (Ẩm thực: {r.cuisine.value}, Loại: {r.course.value})" for r in cookable_recipes])
    
    # Chuyển lịch sử xem thành một chuỗi
    history_list_str = "\n".join([f"- {h.recipe.name}" for h in view_history])
    if not history_list_str:
        history_list_str = "Người dùng này chưa có lịch sử xem."

    # TẠO PROMPT
    prompt = f"""
    Bạn là một chuyên gia ẩm thực và trợ lý nhà bếp. Dựa vào thông tin sau:

    1. DANH SÁCH CÁC MÓN ĂN NGƯỜI DÙNG CÓ THỂ NẤU NGAY LẬP TỨC:
    {recipe_list_str}

    2. LỊCH SỬ 20 MÓN ĂN GẦN ĐÂY NGƯỜI DÙNG ĐÃ XEM:
    {history_list_str}

    Nhiệm vụ của bạn là:
    - Đánh giá mức độ phù hợp của từng món ăn trong "DANH SÁCH CÁC MÓN ĂN CÓ THỂ NẤU" đối với người dùng này, dựa trên thói quen và sở thích được thể hiện qua lịch sử xem của họ.
    - Cho điểm mỗi món ăn trên thang điểm 10 (10 là phù hợp nhất).
    - Chỉ trả lời bằng một đối tượng JSON duy nhất, không có giải thích gì thêm.

    Định dạng JSON trả về phải là:
    {{
      "suggestions": [
        {{
          "name": "Tên món ăn chính xác như đã cung cấp",
          "score": điểm_số_từ_1_đến_10,
          "reason": "Giải thích ngắn gọn tại sao bạn cho điểm số đó (ví dụ: 'Phù hợp vì người dùng hay xem món Việt Nam')."
        }}
      ]
    }}
    """

    try:
        # GỌI API OPENAI
        # Giả sử bạn đã có ocr_scanner = FoodBillOCR() và API key ở đó
        # Chúng ta có thể tận dụng lại nó
        headers = {
            "Authorization": f"Bearer {ocr_scanner.openai_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "gpt-4o",
            "response_format": {"type": "json_object"},
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 1500
        }
        response = request.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            content = result['choices'][0]['message']['content']
            # Chuyển chuỗi JSON thành dictionary Python
            suggestions_data = json.loads(content)
            # Tạo một dictionary để dễ tra cứu điểm: {'Tên món ăn': điểm}
            scores = {item['name'].split(" #")[0].strip(): item['score'] for item in suggestions_data.get('suggestions', [])}
            return scores
        else:
            print(f"OpenAI API Error: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        print(f"Lỗi khi gọi OpenAI: {e}")
        return None

@app.route('/tim-cong-thuc')
# @login_required # Bỏ đi để bất kỳ ai cũng có thể tìm kiếm
def search_recipes_ingredient():
    # Lấy danh sách nguyên liệu từ URL
    ingredients_str = request.args.get('nguyenlieu', '')
    
    # Xử lý chuỗi nguyên liệu
    search_terms = [term.strip() for term in ingredients_str.split(',') if term.strip()]
    
    found_recipes = []
    if search_terms:
        # Xây dựng và thực hiện truy vấn database
        conditions = [Recipe.ingredients.like(f"%{term}%") for term in search_terms]
        found_recipes = Recipe.query.filter(or_(*conditions)).all()

    # Render trang kết quả
    return render_template(
        'search_results.html', 
        title="Kết quả tìm kiếm", 
        recipes=found_recipes,
        search_terms=search_terms
    )
@app.route('/gợi-ý-món-ăn')
@login_required
def suggest_recipes():
    # 1. Lấy nguyên liệu của người dùng
    user_ingredients = {ingredient.name.lower().strip() for ingredient in current_user.ingredients}
    if not user_ingredients:
        flash("Tủ lạnh của bạn đang trống! Hãy thêm nguyên liệu để nhận gợi ý.", "warning")
        return redirect(url_for('tu_lanh_page'))

    # 2. Lấy tất cả công thức
    all_recipes = Recipe.query.all()
    
    # 3. Lọc và tính toán độ phù hợp
    analyzed_recipes = []
    for recipe in all_recipes:
        recipe_ingredients = {ing.lower().strip() for ing in recipe.ingredients.split('\n') if ing.strip()}
        
        matched_ingredients = user_ingredients.intersection(recipe_ingredients)
        match_count = len(matched_ingredients)
        total_ingredients = len(recipe_ingredients)
        
        if total_ingredients > 0:
            analyzed_recipes.append({
                'recipe': recipe,
                'match_count': match_count,
                'total_ingredients': total_ingredients,
                'missing_count': total_ingredients - match_count
            })

    # 4. Phân loại công thức
    cookable_recipes = [r for r in analyzed_recipes if r['missing_count'] == 0]
    nearly_cookable_recipes = [r for r in analyzed_recipes if r['missing_count'] > 0]

    # 5. Xử lý logic và sắp xếp
    suggestion_type = "default" # Loại gợi ý để hiển thị trên template
    
    if len(cookable_recipes) >= 5:
        suggestion_type = "ai_powered"
        # Lấy lịch sử 20 món xem gần nhất
        view_history = current_user.view_history.order_by(ViewHistory.last_viewed.desc()).limit(20).all()
        
        # Gọi OpenAI để lấy điểm
        recipe_scores = get_openai_suggestion([r['recipe'] for r in cookable_recipes], view_history)
        
        if recipe_scores:
            # Sắp xếp các món có thể nấu theo điểm số từ OpenAI, giảm dần
            cookable_recipes.sort(
                key=lambda r: recipe_scores.get(r['recipe'].name.split(" #")[0].strip(), 0), 
                reverse=True
            )
        # Nếu API lỗi, danh sách vẫn giữ nguyên
        
        # Gộp danh sách "gần nấu được" vào cuối, sắp xếp theo số nguyên liệu thiếu tăng dần
        nearly_cookable_recipes.sort(key=lambda r: (r['missing_count'], -r['match_count']))
        final_recipes = cookable_recipes + nearly_cookable_recipes

    else:
        suggestion_type = "match_based"
        # Nếu có ít hơn 5 món nấu được, gộp tất cả và sắp xếp theo số nguyên liệu thiếu (ít nhất trước),
        # sau đó theo số nguyên liệu khớp (nhiều nhất trước)
        all_analyzed_recipes = cookable_recipes + nearly_cookable_recipes
        all_analyzed_recipes.sort(key=lambda r: (r['missing_count'], -r['match_count']))
        final_recipes = all_analyzed_recipes

    return render_template('suggestion_results.html', 
                           analyzed_recipes=final_recipes, 
                           suggestion_type=suggestion_type,
                           user_ingredients_count=len(user_ingredients))

# User loader function uses the User model imported from models.py
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create upload folder if it doesn't exist
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

ocr_scanner = FoodBillOCR()
def save_picture(form_picture):
    # Tạo một tên file ngẫu nhiên để tránh trùng lặp
    random_hex = secrets.token_hex(8)
    # Lấy đuôi file (jpg, png)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    # Đường dẫn đầy đủ để lưu file
    picture_path = os.path.join(app.root_path, 'static/recipe_pics', picture_fn)
    
    # Resize ảnh để tiết kiệm dung lượng
    output_size = (800, 800)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)
    
    return picture_fn # Trả về tên file đã lưu
def get_popular_ingredients(limit=None):
    """
    Phân tích công thức, đếm nguyên liệu và lấy thông tin (ảnh) từ bảng MasterIngredient.
    Trả về một danh sách các đối tượng MasterIngredient được bổ sung thêm thuộc tính 'count'.
    """
    all_recipes = Recipe.query.all()
    ingredient_list = []
    splitter = re.compile(r'\s*,\s*')

    for recipe in all_recipes:
        ingredients = [ing.strip().lower() for ing in splitter.split(recipe.ingredients) if ing.strip()]
        ingredient_list.extend(ingredients)
    
    ingredient_counts = Counter(ingredient_list)
    
    # Lấy ra N nguyên liệu phổ biến nhất
    if limit:
        popular_names = [name for name, count in ingredient_counts.most_common(limit)]
    else:
        popular_names = list(ingredient_counts.keys())

    # Truy vấn tất cả MasterIngredient có tên nằm trong danh sách phổ biến
    results = MasterIngredient.query.filter(MasterIngredient.name.in_(popular_names)).all()
    
    # Bổ sung thông tin 'count' vào mỗi đối tượng
    for item in results:
        item.count = ingredient_counts.get(item.name, 0)
        
    # Sắp xếp kết quả theo số lượng giảm dần
    results.sort(key=lambda x: x.count, reverse=True)
    
    return results
# === ROUTES ===
@app.route('/tat-ca-nguyen-lieu')
def all_popular_ingredients_page():
    # Lấy một danh sách lớn hơn các nguyên liệu phổ biến, ví dụ 100
    all_ingredients = get_popular_ingredients(limit=100)
    
    # Render một template mới và truyền dữ liệu vào
    return render_template(
        'all_ingredients.html', 
        title="Tất cả Nguyên liệu Phổ biến", 
        ingredients=all_ingredients
    )
@app.route('/')
@app.route('/home')
def home():
    # 1. Lấy tất cả các tham số từ URL, gán giá trị mặc định nếu không có
    page = request.args.get('page', 1, type=int)
    max_time = request.args.get('max_time', 120, type=int)
    difficulty = request.args.get('difficulty', None, type=str)
    course = request.args.get('course', None, type=str)
    cuisine = request.args.get('cuisine', None, type=str)
    diets = request.args.getlist('diet') # Lấy danh sách các chế độ ăn
    sort_by = request.args.get('sort_by', 'newest', type=str)

    # 2. Bắt đầu xây dựng câu truy vấn
    query = Recipe.query

    # 3. Áp dụng các bộ lọc dựa trên tham số
    if max_time < 120:
        query = query.filter(Recipe.cooking_time <= max_time)
    
    if difficulty:
        query = query.filter(Recipe.difficulty == DifficultyEnum[difficulty])

    if course:
        query = query.filter(Recipe.course == CourseEnum[course])

    if cuisine:
        query = query.filter(Recipe.cuisine == CuisineEnum[cuisine])

    if diets:
        # Tìm các món ăn có chế độ ăn nằm trong danh sách được chọn
        diet_conditions = [Recipe.diet == DietEnum[d] for d in diets]
        query = query.filter(or_(*diet_conditions))

    # 4. Áp dụng sắp xếp
    if sort_by == 'time':
        query = query.order_by(Recipe.cooking_time.asc())
    elif sort_by == 'relevance': # Sẽ cần logic phức tạp hơn, tạm thời sắp xếp theo tên
        query = query.order_by(Recipe.name.asc())
    else: # Mặc định là 'newest'
        query = query.order_by(Recipe.id.desc())
        
    # 5. Phân trang cho kết quả cuối cùng
    recipes_pagination = query.paginate(page=page, per_page=8)
    popular_ingredients = get_popular_ingredients(limit=6)
    
    # 6. Truyền cả kết quả và các giá trị lọc đã chọn vào template
    # Điều này giúp các ô input "nhớ" giá trị người dùng đã chọn
    return render_template(
        'DuAn.html', 
        title='Trang chủ', 
        recipes_pagination=recipes_pagination,
        # Truyền các giá trị lọc để hiển thị lại trên form
        selected_filters={
            'max_time': max_time,
            'difficulty': difficulty,
            'course': course,
            'cuisine': cuisine,
            'diets': diets,
            'sort_by': sort_by
        },
        # Truyền các Enum để tạo các lựa chọn động
        difficulty_enum=DifficultyEnum,
        course_enum=CourseEnum,
        cuisine_enum=CuisineEnum,
        diet_enum=DietEnum,
        popular_ingredients=popular_ingredients
    )

@app.route('/add-recipe', methods=['GET', 'POST'])
@login_required
def add_recipe():
    form = RecipeForm()
    if form.validate_on_submit():
        # Xử lý upload ảnh NẾU người dùng có chọn file
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            new_recipe = Recipe(
                name=form.name.data,
                image_file=picture_file, # Lưu tên file mới
                ingredients=form.ingredients.data,
                # ... các trường khác ...
                author=current_user
            )
        else:
            # Nếu không upload ảnh, sẽ dùng giá trị default='default.jpg' trong model
            new_recipe = Recipe(
                name=form.name.data,
                ingredients=form.ingredients.data,
                # ... các trường khác ...
                author=current_user
            )
        
        db.session.add(new_recipe)
        db.session.commit()
        flash('Món ăn của bạn đã được thêm thành công!', 'success')
        return redirect(url_for('home'))
        
    return render_template('add_recipe.html', title='Thêm món ăn mới', form=form)

@app.route('/tu-lanh-cua-toi', methods=['GET', 'POST'])
@login_required
def tu_lanh_page():
    # Xử lý khi người dùng thêm nguyên liệu mới
    if request.method == 'POST':
        ingredient_name = request.form.get('ingredient_name')
        if ingredient_name:
            # Kiểm tra xem nguyên liệu đã tồn tại chưa để tránh trùng lặp
            existing_ingredient = Ingredient.query.filter_by(name=ingredient_name, owner=current_user).first()
            if not existing_ingredient:
                new_ingredient = Ingredient(name=ingredient_name, owner=current_user)
                db.session.add(new_ingredient)
                db.session.commit()
                flash(f"Đã thêm '{ingredient_name}' vào tủ lạnh!", "success")
        return redirect(url_for('tu_lanh_page'))

    # Lấy tất cả nguyên liệu của người dùng hiện tại từ database
    user_ingredients = current_user.ingredients
    return render_template('indexTuLanh.html', ingredients=user_ingredients, title="Tủ lạnh của tôi")
@app.route('/delete-ingredient/<int:ingredient_id>', methods=['POST'])
@login_required
def delete_ingredient(ingredient_id):
    ingredient_to_delete = Ingredient.query.get_or_404(ingredient_id)
    # Đảm bảo người dùng chỉ có thể xóa nguyên liệu của chính mình
   
        
    db.session.delete(ingredient_to_delete)
    db.session.commit()
    flash("Đã xóa nguyên liệu.", "info")
    return redirect(url_for('tu_lanh_page'))
@app.route('/recipe/<int:recipe_id>')
def recipe_detail(recipe_id):
    # Lấy thông tin món ăn từ database, nếu không có sẽ báo lỗi 404
    recipe = Recipe.query.get_or_404(recipe_id)

    # Nếu có người dùng đang đăng nhập, ghi lại lịch sử xem
    if current_user.is_authenticated:
        # Tìm xem user này đã xem món ăn này trước đây chưa
        history_entry = ViewHistory.query.filter_by(user_id=current_user.id, recipe_id=recipe.id).first()
        
        if history_entry:
            # Nếu đã xem, tăng số lần xem lên 1 (cột last_viewed sẽ tự cập nhật)
            history_entry.view_count += 1
        else:
            # Nếu đây là lần xem đầu tiên, tạo một entry lịch sử mới
            history_entry = ViewHistory(user_id=current_user.id, recipe_id=recipe.id)
            db.session.add(history_entry)
            
        # Lưu thay đổi vào database
        db.session.commit()

    return render_template('recipe_detail.html', title=recipe.name, recipe=recipe)
@app.route('/tim-cong-thuc')
@login_required # Chỉ người dùng đã đăng nhập mới được tìm
def search_recipes():
    # 1. Lấy danh sách nguyên liệu từ URL mà JavaScript đã gửi
    # Ví dụ: /tim-cong-thuc?nguyenlieu=Thịt%20bò,Trứng
    ingredients_str = request.args.get('nguyenlieu', '')
    
    # 2. Xử lý chuỗi nguyên liệu
    # Tách chuỗi thành một danh sách các nguyên liệu
    search_terms = [term.strip() for term in ingredients_str.split(',') if term.strip()]
    
    found_recipes = []
    if search_terms:
        # 3. Xây dựng truy vấn database
        # Tạo một list các điều kiện "LIKE"
        # Ví dụ: Recipe.ingredients.like('%Thịt bò%')
        conditions = [Recipe.ingredients.like(f"%{term}%") for term in search_terms]
        
        # 4. Thực hiện truy vấn: Tìm các món ăn có chứa BẤT KỲ nguyên liệu nào trong danh sách
        # or_(*conditions) sẽ tạo ra câu lệnh SQL: WHERE ingredients LIKE ... OR ingredients LIKE ...
        found_recipes = Recipe.query.filter(or_(*conditions)).all()

    # 5. Render một template mới để hiển thị kết quả
    return render_template(
        'search_results.html', 
        title="Kết quả tìm kiếm", 
        recipes=found_recipes,
        search_terms=search_terms
    )

@app.route('/bo-suu-tap')
@login_required
def collection_page():
    # Lấy tất cả các món ăn trong bộ sưu tập của người dùng hiện tại
    saved_recipes = current_user.saved_collection.order_by(Recipe.name).all()
    return render_template('collection.html', title="Bộ sưu tập của tôi", recipes=saved_recipes)

@app.route('/save-recipe/<int:recipe_id>', methods=['POST'])
@login_required
def save_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    current_user.save_recipe(recipe)
    db.session.commit()
    flash(f"Đã lưu '{recipe.name}' vào bộ sưu tập của bạn!", 'success')
    return redirect(request.referrer or url_for('recipe_detail', recipe_id=recipe.id))

@app.route('/unsave-recipe/<int:recipe_id>', methods=['POST'])
@login_required
def unsave_recipe(recipe_id):
    recipe = Recipe.query.get_or_404(recipe_id)
    current_user.unsave_recipe(recipe)
    db.session.commit()
    flash(f"Đã xóa '{recipe.name}' khỏi bộ sưu tập.", 'info')
    return redirect(request.referrer or url_for('collection_page'))

@app.route('/quenmatkhau')
def quen_page():
    return render_template('indexQuenMatKhau.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember.data)
            flash('Đăng nhập thành công!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Đăng nhập thất bại. Vui lòng kiểm tra lại tên đăng nhập và mật khẩu.', 'danger')
    return render_template('login.html', title='Đăng nhập', form=form)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(
            username=form.username.data, 
            fullname=form.fullname.data,
            email=form.email.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Tài khoản của bạn đã được tạo thành công! Bây giờ bạn có thể đăng nhập.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', title='Đăng ký', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Bạn đã đăng xuất.', 'info')
    return redirect(url_for('home'))

# --- THE REDUNDANT User CLASS HAS BEEN REMOVED FROM HERE ---

@app.route('/scan-bill', methods=['POST'])
@login_required # Đảm bảo chỉ user đã đăng nhập mới được quét
def scan_bill_api():
    if 'bill_image' not in request.files:
        flash('Không có file nào được gửi lên.', 'danger')
        return redirect(url_for('tu_lanh_page'))

    file = request.files['bill_image']
    if file.filename == '':
        flash('Bạn chưa chọn file nào.', 'danger')
        return redirect(url_for('tu_lanh_page'))

    if file:
        # 1. Lưu file ảnh tạm thời
        filename = secure_filename(file.filename)
        # Tạo một thư mục 'uploads' nếu chưa có
        upload_folder = os.path.join(app.root_path, 'uploads')
        os.makedirs(upload_folder, exist_ok=True)
        image_path = os.path.join(upload_folder, filename)
        file.save(image_path)

        try:
            # 2. Gọi OCR để xử lý ảnh
            # Bạn có thể chọn API ưu tiên, ví dụ "openai"
            result = ocr_scanner.process_bill(image_path, preferred_api="openai") 
            
            # 3. Xử lý kết quả và lưu vào Database
            if result and result.get('items'):
                items_added_count = 0
                new_items = [item['name'].strip() for item in result['items']]
                
                for item_name in new_items:
                    if item_name:
                        # Kiểm tra xem nguyên liệu đã có trong tủ lạnh của user chưa
                        existing = Ingredient.query.filter_by(name=item_name, owner=current_user).first()
                        if not existing:
                            # Nếu chưa có, tạo mới và thêm vào database
                            new_ingredient = Ingredient(name=item_name, owner=current_user)
                            db.session.add(new_ingredient)
                            items_added_count += 1
                
                # Commit tất cả thay đổi vào database
                if items_added_count > 0:
                    db.session.commit()
                    flash(f"Quét thành công! Đã thêm {items_added_count} nguyên liệu mới vào tủ lạnh.", "success")
                else:
                    flash("Quét thành công, nhưng không có nguyên liệu nào mới được thêm (có thể đã có sẵn).", "info")
            else:
                flash("Không thể nhận diện được nguyên liệu từ hóa đơn. Vui lòng thử ảnh khác.", "warning")

        except Exception as e:
            print(f"Lỗi khi quét hóa đơn: {e}")
            flash("Đã xảy ra lỗi trong quá trình xử lý hóa đơn.", "danger")
        finally:
            # 4. Xóa file ảnh tạm sau khi xử lý xong
            if os.path.exists(image_path):
                os.remove(image_path)
    
    # 5. Chuyển hướng người dùng về lại trang Tủ lạnh để thấy kết quả
    return redirect(url_for('tu_lanh_page'))

@app.cli.command("init-db")
def init_db_command():
    """Xóa database hiện tại (nếu có) và tạo lại từ đầu."""
    db.drop_all()
    db.create_all()
    print("Initialized the database.")

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)