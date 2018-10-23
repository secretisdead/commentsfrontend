import time
import re

from comments import Comments

class CommentsFrontend(Comments):
	def __init__(self, config, accounts, access_log, engine, install=False):
		super().__init__(engine, config['db_prefix'], install)

		self.config = config
		self.accounts = accounts
		self.access_log = access_log

		self.config['maximum_note_length'] = min(
			self.body_length,
			self.config['maximum_body_length'],
		)

		self.callbacks = {}

	def add_callback(self, name, f):
		if name not in self.callbacks:
			self.callbacks[name] = []
		self.callbacks[name].append(f)

	# cooldowns
	def create_guest_comment_cooldown(self, remote_origin):
		return self.access_log.cooldown(
			'create_comment',
			self.config['create_guest_comment_cooldown_amount'],
			self.config['create_guest_comment_cooldown_period'],
			remote_origin=remote_origin,
		)

	def create_user_comment_cooldown(self, remote_origin, user_id):
		return self.access_log.cooldown(
			'create_comment',
			self.config['create_user_comment_cooldown_amount'],
			self.config['create_user_comment_cooldown_period'],
			remote_origin=remote_origin,
			subject_id=user_id,
		)

	# require object or raise
	def require_comment(self, id):
		comment = self.get_comment(id)
		if not comment:
			raise ValueError('Comment not found')
		return comment

	# extend comments methods
	def get_comment(self, comment_id):
		comment = super().get_comment(comment_id)
		if comment:
			user_ids = []
			if comment.user_id:
				user_ids.append(comment.user_id)
			users = self.accounts.search_users(filter={'ids': user_ids})
			if comment.user_id in users:
				comment.user = users.get(comment.user_id_bytes)
		return comment

	def search_comments(self, **kwargs):
		comments = super().search_comments(**kwargs)
		user_ids = []
		for comment in comments.values():
			if comment.user_id:
				user_ids.append(comment.user_id)
		users = self.accounts.search_users(filter={'ids': user_ids})
		for comment in comments.values():
			if comment.user_id in users:
				comment.user = users.get(comment.user_id_bytes)
		return comments

	def contains_forbidden_phrase(
			self,
			remote_origin,
			subject_id,
			comment_body,
		):
		contains_forbidden_phrase = False
		comment_body_lower = comment_body.lower()
		for forbidden_string in self.config['forbidden']['strings']:
			if -1 != comment_body_lower.find(forbidden_string):
				contains_forbidden_phrase = True
				break
		for forbidden_re in self.config['forbidden']['res']:
			if None != re.search(forbidden_re, comment_body_lower):
				contains_forbidden_phrase = True
				break
		if not contains_forbidden_phrase:
			return False
		user_id = ''
		if self.accounts.current_user:
			user_id = self.accounts.current_user.id_bytes
		if 'sent_forbidden_phrase' in self.callbacks:
			for f in self.callbacks:
				f(
					remote_origin,
					subject_id,
					comment_body,
					user_id,
				)
		self.access_log.create_log(
			scope='sent_forbidden_phrase',
			subject_id=user_id,
			object_id=subject_id,
		)
		return True

	def create_comment(self, **kwargs):
		comment = super().create_comment(**kwargs)
		subject_id = ''
		if comment.user_id:
			subject_id = comment.user_id
		self.access_log.create_log(
			scope='create_comment',
			subject_id=subject_id,
			object_id=comment.id,
		)
		return comment

	def delete_comment(self, comment, user_id):
		super().delete_comment(comment.id_bytes)
		self.access_log.create_log(
			scope='delete_comment',
			subject_id=user_id,
			object_id=comment.id_bytes,
		)
