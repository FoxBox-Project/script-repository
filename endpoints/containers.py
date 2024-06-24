from flask import Blueprint, jsonify, request
import docker
import os
from flask_jwt_extended import jwt_required, current_user
from db.models import Project
from datetime import datetime


docker_client = docker.from_env()
container_bp = Blueprint('containers', __name__)

@container_bp.route('/create_container', methods=['POST'])
def create_container():
    data = request.get_json()
    
    container_name = data.get('container_name')
    image = data.get('image')
    project = data.get('project')
    working_path = data.get('working_path')
    envs = data.get('envs')
    ports = data.get('ports')
    volumes = data.get('volumes')
    
    try:
        labels = {'project_name': project}
        ports_dict = {str(k): str(v) for k, v in ports[0].items()}
        volumes_list = [f"{host_path}:{container_path}" for host_path, container_path in volumes[0].items()]

        docker_client.containers.run(
            image,
            name=container_name,
            detach=True,
            environment=envs,
            ports=ports_dict,
            volumes=volumes_list,
            working_dir=working_path,
            labels=labels
        )
        return jsonify({'success': True, 'message': 'Container created successfully'})
    except docker.errors.APIError as e:
        return jsonify({'success': False, 'message': str(e)}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@container_bp.route('/delete_container/<container_id>', methods=['DELETE'])
def delete_container(container_id):
    try:
        container = docker_client.containers.get(container_id)
        container.stop()  # Zatrzymujemy kontener
        container.remove()  # Usuwamy kontener
        return jsonify({'success': True, 'message': 'Container deleted successfully'})
    except docker.errors.NotFound:
        return jsonify({'success': False, 'message': 'Container not found'}), 404
    except docker.errors.APIError as e:
        return jsonify({'success': False, 'message': f'Docker API Error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500
    
@container_bp.route('/start_container/<container_id>', methods=['POST'])
def start_container(container_id):
    try:
        container = docker_client.containers.get(container_id)
        container.start()
        return jsonify({'success': True, 'message': 'Container started successfully'})
    except docker.errors.NotFound:
        return jsonify({'success': False, 'message': 'Container not found'}), 404
    except docker.errors.APIError as e:
        return jsonify({'success': False, 'message': f'Docker API Error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@container_bp.route('/stop_container/<container_id>', methods=['POST'])
def stop_container(container_id):
    try:
        container = docker_client.containers.get(container_id)
        container.stop()
        return jsonify({'success': True, 'message': 'Container stopped successfully'})
    except docker.errors.NotFound:
        return jsonify({'success': False, 'message': 'Container not found'}), 404
    except docker.errors.APIError as e:
        return jsonify({'success': False, 'message': f'Docker API Error: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'success': False, 'message': f'An error occurred: {str(e)}'}), 500

@container_bp.route('/list_all_containers', methods=['GET'])
def list_all_containers():
    try:
        containers = docker_client.containers.list(all=True)

        all_containers = []

        for container in containers:
            container_info = docker_client.api.inspect_container(container.id)
            all_containers.append({
                'id': container_info['Id'],
                'name': container_info['Name'],
                'status': container_info['State']['Status'],
                'image': container_info['Config']['Image'],
                'created_at': container_info['Created'],
                'project': container_info['Config']['Labels'].get('project_name', 'N/A')
            })
        
        return jsonify({"status": "success", "containers": all_containers}), 200
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Cannot get containers list: {e}"}), 500
    
@container_bp.route('/show_volume', methods=['GET'])
def show_volume():
    container_id = request.args.get('container_id')

    try:
        container = docker_client.containers.get(container_id)
        container_info = docker_client.api.inspect_container(container.id)

        container_json = {
                'id': container_info['Id'],
                'name': container_info['Name'],
                'status': container_info['State']['Status'],
                'image': container_info['Config']['Image'],
                'created_at': container_info['Created'],
                'project': container_info['Config']['Labels'].get('project_name', 'N/A'),
                'inspect': container_info
            }
        
        return jsonify({"status": "success", "container": container_json}), 200
    except docker.errors.NotFound:
        return jsonify({"status": "error", "message": "Container not found"}), 404
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Cannot get container details: {e}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500

@container_bp.route('/containers_by_project/<project_name>', methods=['GET'])
def get_containers_by_project(project_name):
    try:
        containers = docker_client.containers.list(all=True)

        containers_by_project = []

        for container in containers:
            container_info = docker_client.api.inspect_container(container.id)
            labels = container_info['Config']['Labels']
            if 'project_name' in labels and labels['project_name'] == project_name:
                containers_by_project.append({
                    'id': container_info['Id'],
                    'name': container_info['Name'],
                    'status': container_info['State']['Status'],
                    'image': container_info['Config']['Image'],
                    'created_at': container_info['Created'],
                    'project': project_name
                })
        
        return jsonify({"status": "success", "containers": containers_by_project}), 200
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Cannot get containers list: {e}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"An error occurred: {str(e)}"}), 500