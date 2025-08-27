from database.db import get_db, engine
from database.models import Users, ChatThread
from sqlalchemy.orm import Session

session = Session(engine)

print('Users:')
for user in session.query(Users).all():
    print(f'User ID: {user.id}, Email: {user.email}')

print('\nChat Threads:')
for thread in session.query(ChatThread).all():
    print(f'Thread ID: {thread.id}, User ID: {thread.user_id}, Name: {thread.name}')
