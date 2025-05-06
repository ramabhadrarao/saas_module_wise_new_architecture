"""Forms for the Notes plugin"""
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length

class NoteForm(FlaskForm):
    """Form for creating and editing notes"""
    title = StringField('Title', validators=[DataRequired(), Length(max=255)])
    content = TextAreaField('Content', validators=[DataRequired()])
    is_pinned = BooleanField('Pin Note')
    category = StringField('Category', validators=[Length(max=50)])