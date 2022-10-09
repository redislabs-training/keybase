from redis.commands.search.query import Query
from redis import RedisError
import urllib.parse
from datetime import datetime
import time
import json
import math
from flask import Response, stream_with_context
from flask import Flask, Blueprint, render_template, redirect, url_for, request, jsonify, session
from flask_login import (LoginManager,current_user,login_required,login_user,logout_user)
from flask_paginate import Pagination, get_page_args
import shortuuid

from user import requires_access_level, Role
from common.config import get_db
from common.utils import get_analytics, pretty_title

app = Blueprint('app', __name__)


@app.route('/')
def index():
    if not current_user.is_authenticated:
        return render_template('index.html')
    else:
        return redirect(url_for('document_bp.browse'))


@app.route('/about', methods=['GET'])
@login_required
def about():
    TITLE="About keybase"
    DESC="About keybase"
    return render_template('about.html', title=TITLE, desc=DESC)


@app.route('/new/<doc>')
@login_required
@requires_access_level(Role.EDITOR)
def new(doc):
    TITLE="New Document"
    DESC="New Document"
    template = ""

    if doc == 'case':
        template=urllib.parse.quote("## Applies to:\n\n\n<br>\n## Executive Summary \n\n\n<br>\n<br>\n<br>\n## Introduction \n\n\n<br>\n<br>\n<br>\n## Analysis \n\n\n<br>\n<br>\n<br>\n## Alternatives and Decision Criteria \n\n\n<br>\n<br>\n<br>\n## Recommendations and Implementation Plan \n\n\n<br>\n<br>\n<br>\n## Conclusion \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'troubleshooting':
        template=urllib.parse.quote("## Applies to:\n\n\n<br>\n## Symptoms \n\n\n<br>\n<br>\n<br>\n## Changes \n\n\n<br>\n<br>\n<br>\n## Cause \n\n\n<br>\n<br>\n<br>\n## Solution \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'design':
        template=urllib.parse.quote("## Applies to:\n\n\n<br>\n## Purpose \n\n\n<br>\n<br>\n<br>\n## Scope \n\n\n<br>\n<br>\n<br>\n## Details \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'howto':
        template=urllib.parse.quote("## Applies to:\n\n\n<br>\n## Goal \n\n\n<br>\n<br>\n<br>\n## Solution \n\n\n<br>\n<br>\n<br>\n## References")
    elif doc == 'qa':
        template=urllib.parse.quote("## Applies to:\n\n\n<br>\n## Question \n\n\n<br>\n<br>\n<br>\n## Answer \n\n\n<br>\n<br>\n<br>\n## References")
    return render_template('new.html', title=TITLE, desc=DESC, template=template)