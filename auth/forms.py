from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, SubmitField
from wtforms.validators import DataRequired, Regexp, Length, EqualTo


class LoginForm(FlaskForm):
    username = StringField('Username or Roll/Employee ID', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me')
    submit = SubmitField('Sign In')


class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    confirm_password = PasswordField('Confirm New Password', validators=[
        DataRequired(),
        EqualTo('new_password', message='Passwords must match.')
    ])
    submit = SubmitField('Update Password')


class StudentRegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=150)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email Address', validators=[
        DataRequired(),
        Regexp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', message='Please enter a valid email address.'),
        Length(max=120)
    ])
    roll_number = StringField('Roll Number / Reg No', validators=[DataRequired(), Length(min=3, max=50)])
    branch_id = StringField('Branch', validators=[DataRequired()])
    academic_year_id = StringField('Academic Year', validators=[DataRequired()])
    semester_id = StringField('Semester', validators=[DataRequired()])
    section_id = StringField('Section')
    admission_year = StringField('Admission Year', validators=[DataRequired()])
    phone = StringField('Phone Number', validators=[Length(max=20)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register as Student')


class FacultyRegistrationForm(FlaskForm):
    full_name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=150)])
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=80)])
    email = StringField('Email Address', validators=[
        DataRequired(),
        Regexp(r'^[^@\s]+@[^@\s]+\.[^@\s]+$', message='Please enter a valid email address.'),
        Length(max=120)
    ])
    employee_id = StringField('Employee / Faculty ID', validators=[DataRequired(), Length(min=3, max=50)])
    department_id = StringField('Department', validators=[DataRequired()])
    designation = StringField('Designation', default='Assistant Professor', validators=[Length(max=100)])
    qualification = StringField('Highest Qualification (e.g. M.Tech, Ph.D)', validators=[Length(max=100)])
    phone = StringField('Phone Number', validators=[Length(max=20)])
    password = PasswordField('Password', validators=[
        DataRequired(),
        Length(min=6, message='Password must be at least 6 characters long.')
    ])
    confirm_password = PasswordField('Confirm Password', validators=[
        DataRequired(),
        EqualTo('password', message='Passwords must match.')
    ])
    submit = SubmitField('Register as Faculty')
