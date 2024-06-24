from flask import Flask, jsonify
from flask_cors import CORS  # Dodaj import

from extensions import db, jwt
from endpoints.auth import auth_bp
from endpoints.users import user_bp
from endpoints.projects import project_bp
from endpoints.volumes import volume_bp
from endpoints.networks import network_bp
from endpoints.containers import container_bp
from endpoints.images import image_bp
from db.models import User, TokenBlockList

def create_app():
    app = Flask(__name__)
    app.config.from_prefixed_env()
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://foxbox:test@localhost/foxboxdb'
    app.config['JWT_SECRET_KEY'] = '785c73f0b9ac882ad0e2ddce'
    db.init_app(app)
    jwt.init_app(app)
    CORS(app)

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(user_bp, url_prefix='/users')
    app.register_blueprint(project_bp, url_prefix='/projects')
    app.register_blueprint(network_bp, url_prefix='/networks')
    app.register_blueprint(volume_bp, url_prefix='/volumes')
    app.register_blueprint(image_bp, url_prefix='/images')
    app.register_blueprint(container_bp, url_prefix='/containers')

    # =============================================== #

    @jwt.user_lookup_loader
    def user_lookup_loader(_jwt_headers, jwt_data):
        identity = jwt_data['sub']
        print(identity)
        return User.query.filter_by(username=identity).one_or_none()

    @jwt.additional_claims_loader
    def make_additional_claims(identity):
        if identity == "user":
            return{"is_staff": True}
        return{"is_staff": False}

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_data):
        return jsonify({"message":"Token has expired", "error":"token_expired"}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(error):
        return jsonify({"message":"Signature verification failed", "error":"invalid_token"}), 401  

    @jwt.unauthorized_loader
    def missing_token_callback(error):
        return jsonify({"message": "Request doesnt contain vaild token", "error": "auth_header"}), 401
    

    @jwt.token_in_blocklist_loader
    def token_in_blocklist_callback(jwt_header, jwt_data):
        jti = jwt_data['jti']
        token = db.session.query(TokenBlockList).filter(TokenBlockList.jti == jti).scalar()
        return token is not None

    return app
