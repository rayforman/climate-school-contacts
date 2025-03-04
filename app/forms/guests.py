# Update to app/forms/guests.py - GuestForm class
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, SubmitField
from wtforms.validators import DataRequired, Email, Optional, Length, ValidationError
from app.models import Guest

class GuestForm(FlaskForm):
    # Name and title fields
    prefix = StringField('Prefix', validators=[Optional(), Length(max=20)])
    first_name = StringField('First Name', validators=[DataRequired(), Length(max=64)])
    middle_name = StringField('Middle Name', validators=[Optional(), Length(max=64)])
    last_name = StringField('Last Name', validators=[DataRequired(), Length(max=64)])
    nickname = StringField('Nickname(s)', validators=[Optional(), Length(max=64)])
    descriptor = StringField('Descriptor', validators=[Optional(), Length(max=256)],
                           description="Additional information to display after the name, e.g., 'Jr.', 'MD', etc.")
    
    # Contact information
    email = StringField('Email', validators=[Optional(), Email(), Length(max=120)])
    phone = StringField('Phone', validators=[Optional(), Length(max=20)])
    
    # Professional information
    organization = StringField('Organization', validators=[Optional(), Length(max=128)])
    title = StringField('Title', validators=[Optional(), Length(max=128)])
    
    # Columbia-specific fields
    athena_id = StringField('Athena ID', validators=[Optional(), Length(max=64)], 
                         description="Columbia University internal ID")
    prospect_manager = StringField('Prospect Manager', validators=[Optional(), Length(max=128)],
                                description="Name of the development officer managing this relationship")
    
    # Bio and notes
    bio = TextAreaField('Bio', validators=[Optional()])
    photo = FileField('Photo', validators=[
        Optional(),
        FileAllowed(['jpg', 'png', 'jpeg'], 'Images only!')
    ])
    
    # Changed from SelectField to StringField for more flexibility
    donor_capacity = StringField('Donor Capacity', validators=[Optional(), Length(max=64)],
                               description="e.g., Low, Medium, High, Very High, TBD")
    
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