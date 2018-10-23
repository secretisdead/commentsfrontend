import time

from flask import Blueprint, render_template, abort, request, redirect
from flask import url_for, g

from . import post_comment

comments_signed_out = Blueprint(
	'comments_signed_out',
	__name__,
	template_folder='templates',
)

@comments_signed_out.route('/create/guest', methods=['GET', 'POST'])
def create_comment():
	if not g.comments.config['allow_guest_comments']:
		abort(401, 'You must be signed in to comment')
	if g.comments.create_guest_comment_cooldown(
			remote_origin=str(request.remote_addr),
		):
		abort(429, 'Please wait a bit before making another comment')
	if 'POST' != request.method:
		return render_template('create_comment.html')
	return post_comment(
		url_for('comments_signed_out.create_comment'),
		check_forbidden_phrase=True,
	)
