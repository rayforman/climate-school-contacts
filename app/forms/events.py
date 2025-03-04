from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import StringField, TextAreaField, DateTimeField, SelectField, SubmitField
from wtforms.validators import DataRequired, Optional, Length

class EventForm(FlaskForm):
    name = StringField('Event Name', validators=[DataRequired(), Length(max=128)])
    date = DateTimeField('Event Date/Time', format='%Y-%m-%d %H:%M', validators=[DataRequired()])
    location = StringField('Location', validators=[Optional(), Length(max=256)])
    description = TextAreaField('Description', validators=[Optional()])
    eventbrite_id = StringField('Eventbrite ID', validators=[Optional(), Length(max=64)])
    submit = SubmitField('Save Event')

class EventSearchForm(FlaskForm):
    search = StringField('Search Events', validators=[Optional()])
    date_from = DateTimeField('From Date', format='%Y-%m-%d', validators=[Optional()])
    date_to = DateTimeField('To Date', format='%Y-%m-%d', validators=[Optional()])
    submit = SubmitField('Search')

class AttendeeForm(FlaskForm):
    guest_id = SelectField('Guest', coerce=int, validators=[DataRequired()])
    notes = TextAreaField('Notes', validators=[Optional()])
    submit = SubmitField('Add Attendee')

class EventbriteImportForm(FlaskForm):
    file = FileField('Eventbrite CSV File', validators=[
        FileRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    submit = SubmitField('Import Attendees')