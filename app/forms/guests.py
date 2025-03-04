from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length, ValidationError
from app.models import Guest

class GuestForm(FlaskForm):
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    organization = StringField('Organization', validators=[Optional(), Length(max=128)])
    title = StringField('Title', validators=[Optional(), Length(max=128)])
    bio = TextAreaField('Bio', validators=[Optional()])
    photo = FileField('Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])
    donor_capacity = SelectField('Donor Capacity', choices=[
        ('', 'Unknown'),
        ('low', 'Low (<$1,000)'),
        ('medium', 'Medium ($1,000-$10,000)'),
        ('high', 'High ($10,000-$100,000)'),
        ('very_high', 'Very High (>$100,000)')
    ], validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Save Guest')
    
    def validate_email(self, email):
        if not email.data:
            return
        
        # Get the current guest if we're editing
        current_id = getattr(self, 'id', None)
        query = Guest.query.filter_by(email=email.data)
        
        if current_id:
            query = query.filter(Guest.id != current_id)
        
        if query.first():
            raise ValidationError('This email is already registered to another guest.')

class GuestSearchForm(FlaskForm):
    search = StringField('Search', validators=[Optional()])
    submit = SubmitField('Search')