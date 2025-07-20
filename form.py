from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, TextAreaField, IntegerField, SelectField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError, Email
from models import User, DifficultyEnum, DietEnum, CourseEnum, CuisineEnum
from flask_wtf.file import FileField, FileRequired, FileAllowed

class RegistrationForm(FlaskForm):
    fullname = StringField('Họ và tên', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email(message="Địa chỉ email không hợp lệ.")]) 
    username = StringField('Tên đăng nhập', validators=[DataRequired(), Length(min=4, max=25)])
    password = PasswordField('Mật khẩu', validators=[DataRequired(), Length(min=6, message="Mật khẩu phải có ít nhất 6 ký tự.")])
    confirm_password = PasswordField('Nhập lại mật khẩu', 
                                     validators=[DataRequired(), EqualTo('password', message='Mật khẩu nhập lại không khớp.')])
    submit = SubmitField('Đăng ký')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Tên đăng nhập này đã có người sử dụng. Vui lòng chọn tên khác.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('Email này đã được sử dụng. Vui lòng chọn email khác.')

class LoginForm(FlaskForm):
    username = StringField('Tên đăng nhập', validators=[DataRequired()])
    password = PasswordField('Mật khẩu', validators=[DataRequired()])
    remember = BooleanField('Ghi nhớ đăng nhập')
    submit = SubmitField('Đăng nhập')
    
class RecipeForm(FlaskForm):
    name = StringField('Tên món ăn', validators=[DataRequired()])
    picture = FileField('Ảnh minh họa món ăn', validators=[FileAllowed(['jpg', 'png', 'jpeg'])])
    ingredients = TextAreaField('Nguyên liệu (mỗi nguyên liệu một dòng)', validators=[DataRequired()])
    cooking_time = IntegerField('Thời gian nấu (phút)', validators=[DataRequired()])
    instructions = TextAreaField('Hướng dẫn nấu (mỗi bước một dòng)', validators=[DataRequired()])

    difficulty = SelectField('Độ khó', 
        choices=[(d.name, d.value) for d in DifficultyEnum], 
        validators=[DataRequired()], coerce=str)
    
    diet = SelectField('Chế độ ăn', 
        choices=[(d.name, d.value) for d in DietEnum], 
        validators=[DataRequired()], coerce=str)
        
    course = SelectField('Loại món', 
        choices=[(c.name, c.value) for c in CourseEnum], 
        validators=[DataRequired()], coerce=str)
        
    cuisine = SelectField('Ẩm thực', 
        choices=[(c.name, c.value) for c in CuisineEnum], 
        validators=[DataRequired()], coerce=str)
        
    submit = SubmitField('Thêm món ăn')