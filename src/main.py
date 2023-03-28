from flask import Blueprint, render_template
from flask_login import (login_required)

main_bp = Blueprint('main_bp', __name__)


@main_bp.route('/about', methods=['GET'])
@login_required
def about():
    TITLE = "About keybase"
    DESC = "About keybase"
    return render_template('about.html', title=TITLE, desc=DESC)


@main_bp.route('/assert-zero')
@login_required
def trigger_error():
    division_by_zero = 1 / 0


@main_bp.route('/error-page')
def custom_error():
    return render_template('500.html')