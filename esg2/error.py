from flask import (
    Blueprint, render_template, request, session, url_for
)

bp = Blueprint('error', __name__, url_prefix='')

@bp.app_errorhandler(400)
def forbidden(e):
    kwargs = {
        'error_title':"400",
        'error_text':"Bad request. Was an outdated form submitted?"
    }
    return render_template('error.html', **kwargs), 400


@bp.app_errorhandler(403)
def forbidden(e):
    kwargs = {
        'error_title':"403",
        'error_text':"The active account does not have authorization to view that page."
    }
    return render_template('error.html', **kwargs), 403

@bp.app_errorhandler(404)
def page_not_found(e):
    kwargs = {
        'error_title':"404",
        'error_text':"Page not found."
    }
    return render_template('error.html', **kwargs), 404

@bp.app_errorhandler(405)
def method_not_allowed(e):
    kwargs = {
        'error_title':"405",
        'error_text':"Request method not allowed. Did you attempt to directly access a pageless URL?"
    }
    return render_template('error.html', **kwargs), 404

@bp.app_errorhandler(418)
def im_a_teapot(e):
    kwargs = {
        'error_title':"418",
        'error_text':"Don't be ridiculous."
    }
    return render_template('error.html', **kwargs), 404


@bp.app_errorhandler(500)
def internal_server_error(e):
    kwargs = {
        'error_title':"500",
        'error_text':"Internal server error. Something has gone wrong."
    }
    return render_template('error.html', **kwargs), 500
