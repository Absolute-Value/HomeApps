from sqlalchemy import Column, Integer, String, BLOB, Boolean, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy import ForeignKey

Base = declarative_base()
DATABASE_URL = "sqlite:///../data/free_chat.db"

class chats(Base):
  __tablename__ = 'chats'
  id = Column(String, primary_key=True, unique=True, index=True)
  title = Column(String)

class messages(Base):
  __tablename__ = 'messages'
  id = Column(Integer, primary_key=True, index=True, autoincrement=True)
  chat_id = Column(String, ForeignKey('chats.id'))
  role = Column(String)
  content = Column(String)
  image = Column(BLOB, nullable=True)
  model_id = Column(Integer, ForeignKey('models.id'))

class models(Base):
  __tablename__ = 'models'
  id = Column(Integer, primary_key=True, index=True, autoincrement=True)
  name = Column(String)
  display = Column(String)
  image = Column(Boolean, default=False)

def get_engine():
  return create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
  
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=get_engine())

def create_db_and_tables():
  engine = get_engine()
  Base.metadata.create_all(bind=engine)

def save_chat_and_message(chat_id: str, title: str, role: str, content: str, image: bytes = None, model_id: int = None):
  db: Session = SessionLocal()
  db_chat = db.query(chats).filter(chats.id == chat_id).first()
  if not db_chat:
    db_chat = chats(id=chat_id, title=title)
    db.add(db_chat)
    db.commit()
    db.refresh(db_chat)

  # Always insert the message
  db_message = messages(chat_id=chat_id, role=role, content=content, image=image, model_id=model_id)
  db.add(db_message)
  db.commit()
  db.refresh(db_message)
  db.close()
  return db_chat, db_message

def load_chats():
  db: Session = SessionLocal()
  chs = db.query(chats).order_by(chats.id.desc()).all()
  db.close()
  return chs

def load_messages(chat_id: str):
  db: Session = SessionLocal()
  msgs = db.query(messages).filter(messages.chat_id == chat_id).all()
  db.close()
  return msgs

def delete_chat(chat_id: str):
  db: Session = SessionLocal()
  db.query(messages).filter(messages.chat_id == chat_id).delete()
  db.query(chats).filter(chats.id == chat_id).delete()
  db.commit()
  db.close()

def chat_exists(chat_id: str) -> bool:
  db: Session = SessionLocal()
  exists = db.query(chats).filter(chats.id == chat_id).first() is not None
  db.close()
  return exists

def get_chat_title(chat_id: str) -> str:
  db: Session = SessionLocal()
  chat = db.query(chats).filter(chats.id == chat_id).first()
  db.close()
  return chat.title if chat else "Untitled Chat"