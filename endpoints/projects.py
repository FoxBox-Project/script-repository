from flask import Blueprint, jsonify, request, render_template, send_file
from flask_jwt_extended import create_access_token, create_refresh_token, jwt_required, get_jwt, current_user, get_jwt_identity

import docker
import os
import zipfile
from db.models import Project


project_bp = Blueprint('projects', __name__)

@project_bp.route('/create_project', methods=['POST'])
@jwt_required()
def create_project():
    try:
        data = request.get_json()
        
        project_path = f'/data/projects/{str(data.get("project_name"))}'
        project = Project.get_project_by_name(str(data.get("project_name")))

        
        if os.path.exists(project_path) or project is not None:
            return jsonify({'error': 'Project already exists'}), 400

        os.makedirs(project_path)
        new_project = Project(
            user_id = current_user.id,
            name = data.get('project_name'),
            status = "unactive"
        )

        new_project.save()
        return jsonify({'message': 'Project directory created successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@project_bp.route('/remove_project', methods=['DELETE'])
@jwt_required()
def remove_project():
    try:
        data = request.get_json()
        
        project_path = f'/data/projects/{str(data.get("project_name"))}'
        project = Project.get_project_by_name(str(data.get("project_name")))

        if not os.path.exists(project_path) or project is None:
            return jsonify({'error': 'Project does not exist'}), 404

        project.delete()
        os.rmdir(project_path)

        return jsonify({'message': 'Project directory deleted successfully'}), 200

    except Exception as e:
        return jsonify({'error': str(e) + str(project)}), 500


@project_bp.route('/list_all_user_projects', methods=['GET'])
@jwt_required()
def list_all_user_projects():
    try:
        projects = Project.get_projects_by_user_id(current_user.id)

        if projects is None:
            return jsonify({'error': 'User does not have any projects'}), 404

        project_list = []
        for project in projects:
            project_data = {
                'id': project.id,
                'name': project.name,
                'status': project.status,
            }
            project_list.append(project_data)

        return jsonify({'projects': project_list}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500