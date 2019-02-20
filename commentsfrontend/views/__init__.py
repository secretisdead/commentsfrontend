from functools import wraps
import time
import hashlib

from flask import g, make_response, render_template, redirect
from flask import request, abort

from .. import CommentsFrontend

def initialize(
		config,
		accounts,
		access_log,
		engine,
		install=False,
		connection=None,
	):
	g.comments = CommentsFrontend(
		config,
		accounts,
		access_log,
		engine,
		install=install,
		connection=connection,
	)

# require objects or abort
def require_comment(id):
	try:
		comment = g.comments.require_comment(id)
	except ValueError as e:
		abort(404, str(e))
	else:
		return comment

def post_comment(default_redirect_uri, user_id='', check_forbidden_phrase=False):
	for field in [
			'subject_id',
			'redirect_uri',
			'comment_body',
		]:
		if field not in request.form:
			abort(400, 'Missing comment creation fields')
	if request.form['redirect_uri']:
		redirect_uri = request.form['redirect_uri']
	else:
		#TODO primitive success page?
		# require home endpoint in config to redirect to?
		# users really shouldn't be here without redirect_uri prepopulated
		redirect_uri = default_redirect_uri
	errors = []
	remote_origin = str(request.remote_addr)
	if not request.form['subject_id']:
		errors.append('No subject entered')
	if not request.form['comment_body']:
		errors.append('No comment entered')
	elif check_forbidden_phrase and g.comments.contains_forbidden_phrase(
			remote_origin,
			request.form['subject_id'],
			request.form['comment_body'],
			user_id=user_id,
		):
		errors.append('Comment contained forbidden phrase')
	if not errors:
		try:
			g.comments.create_comment(
				subject_id=request.form['subject_id'],
				remote_origin=remote_origin,
				body=request.form['comment_body'],
				user_id=user_id,
			)
		except Exception:
			errors.append('Problem creating comment')
		else:
			return redirect(redirect_uri, code=303)
	return render_template(
		'create_comment.html',
		errors=errors,
		subject_id=request.form['subject_id'],
		redirect_uri=request.form['redirect_uri'],
		comment_body=request.form['comment_body'],
	)
