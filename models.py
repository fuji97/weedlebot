from sqlalchemy import create_engine, Column, BigInteger, Integer, String, ForeignKey, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
import telegram.ext
import struct
import os
import enum
import logging

# Enable logging
logger = logging.getLogger(__name__)

DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///data.db')

logger.info("Creating engine with URI: '%s'" % DATABASE_URI)
engine = create_engine(DATABASE_URI, connect_args={'check_same_thread': False})
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)
Base = declarative_base()

class ChatType(enum.Enum):
    private = 1
    group = 2
    supergroup = 3
    channel = 4

class Role(enum.Enum):
    founder = 1
    admin = 2
    moderator = 3
    user = 4
    banned = 5

class User(Base):
    __tablename__ = 'user'

    id = Column(BigInteger, primary_key=True)
    username = Column(String(255), default=None)
    first_name = Column(String(255))
    last_name = Column(String(255))
    general_role = Column(Enum(Role), default=Role.user)

    # Definizione delle relazioni
    chats = relationship('ChatMember', back_populates='user')

    def __repr__(self):
        return "<User(%s %s [@%s - %s])>" % (
            self.first_name, self.last_name, self.username, str(self.id)
        )

class Chat(Base):
    __tablename__ = 'chat'

    id = Column(BigInteger, primary_key=True)
    type = Column(Enum(ChatType), nullable=False)
    title = Column(String(255), default=None)
    username = Column(String(255), default=None)
    all_members_are_administrators = Column(Boolean, default=True)
    role = Column(Enum(Role), default=Role.user)
    old_id = Column(BigInteger, default=None)

    # Definizione delle relazioni
    users = relationship('ChatMember', back_populates='chat')

    def __repr__(self):
        return "<Chat(%s (%s) - %s [@%s] [%s])>" % (
            str(self.id), self.type.name, self.title, self.username, self.role
        )

class ChatMember(Base):
    __tablename__ = 'chat_user'

    user_id = Column(BigInteger, ForeignKey('user.id'), primary_key=True)
    chat_id = Column(BigInteger, ForeignKey('chat.id'), primary_key=True)
    user_role = Column(Enum(Role), default=Role.user)
    user = relationship('User', back_populates='chats')
    chat = relationship('Chat', back_populates='users')

    def __repr__(self):
        return "<ChatMember(%s in %s [%s])>" % (
            str(self.user_id), str(self.chat_id), self.user_role
        )

class Voice(Base):
    __tablename__ = 'voice'

    id = Column(Integer, primary_key=True)
    name = Column(String)
    command = Column(String)
    file_id = Column(String, nullable=False, unique=True)
    duration = Column(Integer)
    chat_id = Column(BigInteger, ForeignKey('chat.id'))

    def __repr__(self):
        return "<Audio(%s [/%s] %s in %i)>" % (
            self.name, self.command, self.file_id, self.chat_id
        )

class Variable(Base):
    __tablename__ = 'variable'

    id = Column(Integer, primary_key=True)
    name = Column(String, unique=True)
    value = Column(String)

    def __repr__(self):
        return "<Variable(%s = '%s')>" % (self.name, self.value)

"""
class ChatMember(Base):
    __tablename__ = 'chat_member'

    user_id = Column(BigInteger, primary_key=True, ForeignKey('user.id'))
    chat_id = Column(BigInteger, primary_key=True, ForeignKey('chat.id'))

    user = relationship('User', back_populates='chat_members')

    def __repr__(self):
        return "<User %s in chat %s>" % (str(self.user_id), str(self.chat_id))

User.chats = relationship('ChatMember', order_by=ChatMember.chat_id, back_populates)


def get_or_create(session, model, id, defaults=None, **kwargs):
    instance = session.query(model).filter_by(id=id).first()
    if instance:
        return instance, False
    else:
        params = dict((k, v) for k, v in kwargs.iteritems() if not isinstance(v, ClauseElement))
        params.update(defaults or {})
        instance = model(**params)
        session.add(instance)
    return instance, True
"""

class DataMixin():
    session = None

    def handle_update(self, update, dispatcher):
        self.session = Session()
        ret = super().handle_update(update, dispatcher)
        self.session.close()
        return ret

    def collect_optional_args(self, dispatcher, update=None):
        optional_args = super().collect_optional_args(dispatcher, update=None)
        optional_args['session'] = self.session
        return optional_args

class DataCommandHandler(DataMixin, telegram.ext.CommandHandler):
    pass

class DataMessageHandler(DataMixin, telegram.ext.MessageHandler):
    pass

def createTables():
    Base.metadata.create_all(engine)

def getChatType(type):
    if type == 'private':
        return ChatType.private
    elif type == 'group':
        return ChatType.group
    elif type == 'supergroup':
        return ChatType.supergroup
    elif type == 'channel':
        return ChatType.channel

def startSession():
    return Session()

def closeSession(session):
    logger.debug("Provo a chiudere la sessione")
    session.remove()

def getVariable(session, name):
    return session.query(Variable).filter_by(name=name).first()

def setVariable(session, name, val):
    var = getVariable(session, name)
    if var:
        var.value = val
    else:
        var = Variable(name=name, value=val)
        session.add(var)
    try:
        session.commit()
    except Exception as e:
        logger.error("Errore nell'impostazione della variabile %s='%s' - %s",
                    name, val, str(e))
        session.rollback()

def registerUpdate(session, update):
    chat = update.effective_chat
    user = update.effective_user

    if chat:
        instance = session.query(Chat).filter_by(id=chat.id).first()
        if instance:
            if instance.title != chat.title:
                instance.title = chat.title
            if instance.username != chat.username:
                instance.username = chat.username
            if instance.all_members_are_administrators != chat.all_members_are_administrators:
                instance.all_members_are_administrators = chat.all_members_are_administrators
            chat = instance
        else:
            chat = Chat(id = chat.id,
                        type = getChatType(chat.type),
                        title = chat.title,
                        username = chat.username,
                        all_members_are_administrators = chat.all_members_are_administrators)
            session.add(chat)

    if user:
        instance = session.query(User).filter_by(id=user.id).first()
        if instance:
            if instance.username != user.username:
                instance.username = user.username
            if instance.first_name != user.first_name:
                instance.first_name = user.first_name
            if instance.last_name != user.last_name:
                instance.last_name = user.last_name
            user = instance
        else:
            user = User(id = user.id,
            first_name = user.first_name,
            last_name = user.last_name,
            username = user.username)
            session.add(user)

    if chat and user:
        instance = session.query(ChatMember).filter_by(
                user_id=user.id, chat_id=chat.id).first()
        if not instance:
            session.add(ChatMember(user_id = user.id,
                    chat_id = chat.id))

    # Commit e chiudi
    try:
        session.commit()
    except Exception as e:
        logger.error("Errore nel commit dei dati: %s", str(e))
        session.rollback()


    return {'user': user, 'chat': chat}
