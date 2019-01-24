import math
import json
import urllib
import time

from ipaddress import ip_address
from flask import Blueprint, render_template, abort, request, redirect
from flask import url_for, g
import dateutil.parser

from pagination_from_request import pagination_from_request
from . import require_comment, post_comment
from accounts.views import require_permissions

comments_manager = Blueprint(
	'comments_manager',
	__name__,
	template_folder='templates',
)

@comments_manager.route('/comments/create', methods=['GET', 'POST'])
@require_permissions(group_names='manager')
def create_comment():
	if 'POST' != request.method:
		return render_template('create_comment.html')
	return post_comment(
		url_for('comments_manager.comments_list'),
		user_id=g.comments.accounts.current_user.id_bytes,
	)

@comments_manager.route('/comments/<comment_id>/remove')
@require_permissions(group_names='manager')
def remove_comment(comment_id):
	comment = require_comment(comment_id)
	g.comments.delete_comment(
		comment,
		g.comments.accounts.current_user.id_bytes,
	)
	if 'redirect_uri' in request.args:
		return redirect(request.args['redirect_uri'], code=303)
	return redirect(url_for('comments_manager.comments_list'), code=303)

@comments_manager.route('/comments')
@require_permissions(group_names='manager')
def comments_list():
	search = {
		'id': '',
		'created_before': '',
		'created_after': '',
		'subject_id': '',
		'remote_origin': '',
		'body': '',
		'user_id': '',
	}
	for field in search:
		if field in request.args:
			search[field] = request.args[field]

	filter = {}
	escape = lambda value: (
		value
			.replace('\\', '\\\\')
			.replace('_', '\_')
			.replace('%', '\%')
			.replace('-', '\-')
	)
	# for parsing datetime and timestamp from submitted form
	# filter fields are named the same as search fields
	time_fields = [
		'created_before',
		'created_after',
	]
	for field, value in search.items():
		if not value:
			continue
		if 'id' == field:
			filter['ids'] = value
		elif field in time_fields:
			try:
				parsed = dateutil.parser.parse(value)
			except ValueError:
				filter[field] = 'bad_query'
			else:
				search[field] = parsed.strftime('%Y-%m-%dT%H:%M:%S.%f%z')
				filter[field] = parsed.timestamp()
		elif 'subject_id' == field:
			filter['subject_ids'] = value
		elif 'remote_origin' == field:
			filter['with_remote_origins'] = value
		elif 'body' == field:
			filter['body'] = '%' + escape(value) + '%'
		elif 'user_id' == field:
			if 'guest' == value:
				value = ''
			filter['user_ids'] = value

	pagination = pagination_from_request('creation_time', 'desc', 0, 32)

	total_results = g.comments.count_comments(filter=filter)
	results = g.comments.search_comments(filter=filter, **pagination)

	return render_template(
		'comments_list.html',
		results=results,
		search=search,
		pagination=pagination,
		total_results=total_results,
		total_pages=math.ceil(total_results / pagination['perpage']),
	)
