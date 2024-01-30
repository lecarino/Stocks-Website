from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, URL
from flask_ckeditor import CKEditorField


class StockForm(FlaskForm):
    symbol = StringField("Stock Symbol", validators=[DataRequired()])
    submit = SubmitField("Add Stock")