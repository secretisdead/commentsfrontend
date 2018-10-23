import time

from flask import Blueprint, render_template, abort, request, redirect
from flask import url_for, g

from accounts.views import require_sign_in
from . import post_comment

comments_signed_in = Blueprint(
	'comments_signed_in',
	__name__,
	template_folder='templates',
)

@comments_signed_in.route('/create', methods=['GET', 'POST'])
@require_sign_in
def create_comment():
	if g.comments.create_user_comment_cooldown(
			remote_origin=str(request.remote_addr),
			user_id=g.comments.accounts.current_user.id_bytes,
		):
		abort(429, 'Please wait a bit before making another comment')
	if 'POST' != request.method:
		return render_template('create_comment.html')
	return post_comment(
		url_for('comments_signed_out.create_comment'),
		user_id=g.comments.accounts.current_user.id_bytes,
		check_forbidden_phrase=True,
	)
