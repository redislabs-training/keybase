import urllib.parse
from flask import request

from flask import Blueprint, render_template, redirect, url_for
from flask_login import (current_user, login_required)

from .common.config import get_db
from .user import requires_access_level, Role

main_bp = Blueprint('main_bp', __name__)


@main_bp.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('index.html')
    else:
        return redirect(url_for('document_bp.browse'))


@main_bp.route('/about', methods=['GET'])
@login_required
def about():
    TITLE = "About keybase"
    DESC = "About keybase"
    return render_template('about.html', title=TITLE, desc=DESC)


@main_bp.route('/new/<doc>')
@login_required
@requires_access_level(Role.EDITOR)
def new(doc):
    TITLE = "New Document"
    DESC = "New Document"
    template = ""

    if doc == 'case':
        template = urllib.parse.quote(
            "## Applies to:\n\n\n<br>\n## Executive Summary \n\n\n<br>\n<br>\n<br>\n## Introduction \n\n\n<br>\n<br>\n<br>\n## Analysis \n\n\n<br>\n<br>\n<br>\n## Alternatives and Decision Criteria \n\n\n<br>\n<br>\n<br>\n## Recommendations and Implementation Plan \n\n\n<br>\n<br>\n<br>\n## Conclusion \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'troubleshooting':
        template = urllib.parse.quote(
            "## Applies to:\n\n\n<br>\n## Symptoms \n\n\n<br>\n<br>\n<br>\n## Changes \n\n\n<br>\n<br>\n<br>\n## Cause \n\n\n<br>\n<br>\n<br>\n## Solution \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'design':
        template = urllib.parse.quote(
            "## Applies to:\n\n\n<br>\n## Purpose \n\n\n<br>\n<br>\n<br>\n## Scope \n\n\n<br>\n<br>\n<br>\n## Details \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'howto':
        template = urllib.parse.quote(
            "## Applies to:\n\n\n<br>\n## Goal \n\n\n<br>\n<br>\n<br>\n## Solution \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'qa':
        template = urllib.parse.quote(
            "## Applies to:\n\n\n<br>\n## Question \n\n\n<br>\n<br>\n<br>\n## Answer \n\n\n<br>\n<br>\n<br>\n## References")
    return render_template('new.html', title=TITLE, desc=DESC, template=template)
