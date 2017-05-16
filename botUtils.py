import logging
import models
import os

OWNER = int(os.environ.get("ID_OWNER", 0))
logger = logging.getLogger(__name__)

def checkPermission(user, level, chat=None):
    if user.id == OWNER:
        return True
    if chat:
        role = next(member for member in chat.users if member.user == user).user_role
        if role.value <= level:
            return True
        else:
            return False
    else:
        if user.general_role.value <= level:
            return True
        else:
            return False

class permissions(object):
	def __init__(self, session, user_id, permission, **kwargs):
		self.session = session
		self.user_id = user_id
		self.permission = permission
		self.chat_id = kwargs['chat_id'] if 'chat_id' in kwargs else None
		self.alternative = kwargs['alternative'] if 'alternative' in kwargs else None

	def __call__(self, f):
		def wrap(*args):
			have_permissions = False
			if 'chat_id' in kwargs:
				res = session.query(models.ChatMember).filter_by(
						user_id=self.user_id, chat_id=self.chat_id).first()
				if res is not None:
					if res.user_role.value <= self.permission.value:
						have_permissions = True
			else:
				res = session.query(models.User).filter_by(user_id=self.user_id).first()
				if res is not None:
					if res.general_role.value <= self.permission.value:
						have_permissions = True

			if have_permissions is True:
				f(*args)
			elif self.alternative is not None:
				self.alternative(*args)
