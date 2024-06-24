from extensions import db
from sqlalchemy.orm import relationship
from uuid import uuid4
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.String(), primary_key=True, default=lambda: str(uuid4()))
    username = db.Column(db.String(), nullable=False)
    email = db.Column(db.String(), nullable=False)
    first_name = db.Column(db.String(), nullable=False)
    last_name = db.Column(db.String(), nullable=False)
    password = db.Column(db.Text())

    def __repr__(self):
        return f"<User {self.username}>"
    
    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    @classmethod
    def get_user_by_username(cls, username):
        return cls.query.filter_by(username = username).first()
    
    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

class TokenBlockList(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    jti = db.Column(db.String(), nullable=True)
    create_at = db.Column(db.DateTime(), default=datetime.utcnow)

    def __repr__(self):
        return f"<Token {self.jti}>"
    
    def save(self):
        db.session.add(self)
        db.session.commit()

class Project(db.Model):
    __tablename__ = 'projects'
    id = db.Column(db.String(), primary_key=True, default=lambda: str(uuid4()))
    user_id = db.Column(db.String(), db.ForeignKey('users.id'), nullable=False)
    name = db.Column(db.String(), nullable=False)
    status = db.Column(db.String(), nullable=False)
    
    user = relationship('User', backref='projects')

    def __repr__(self):
        return f"<Project {self.name}>"

    @classmethod
    def get_project_by_name(cls, name):
        return cls.query.filter_by(name = name).first()
    
    @classmethod
    def get_projects_by_user_id(cls, user_id):
        return cls.query.filter_by(user_id=user_id).all()
    
    def save(self):
        db.session.add(self)
        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()