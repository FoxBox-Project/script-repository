from flask import Blueprint, jsonify, request
import docker
import os
from flask_jwt_extended import jwt_required, current_user
from db.models import Project
from datetime import datetime

docker_client = docker.from_env()
volume_bp = Blueprint('volumes', __name__)

@volume_bp.route('/create_volume', methods=['POST'])
@jwt_required()
def create_volume():
    try:
        data = request.get_json()

        new_volume_name = data.get("name")
        new_volume_project = data.get("project")
        new_volume_driver = data.get("driver", "local") 
        new_volume_options = data.get("options", [])

        new_volume_driver_options = {}
        for option in new_volume_options:
            new_volume_driver_options.update(option)

        project = Project.get_project_by_name(data.get('project'))
        if project.user_id != current_user.id:
            return jsonify({"status": "error", "message": "Użytkownik nie ma dostępu do tego projektu", "error_code": "missing privigiles"}), 401
        
        volumes = docker_client.volumes.list()
        volume_exists = any(volume.name == new_volume_name for volume in volumes)

        if volume_exists:
            return jsonify({"status": "error", "message": "Wolumen o tej nazwie istnieje", "error_code": "volume with this name exists"}), 400

        docker_client.volumes.create(
            name=new_volume_name,
            driver=new_volume_driver,
            driver_opts=new_volume_driver_options,
            labels={"project_name": new_volume_project} 
        )

        return jsonify({"status": "success", "message": f"Wolumen '{new_volume_name}' został utworzony pomyślnie"}), 200
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": "Docker wykrył błąd przy próbie tworzenia nowego wolumenu", "error_code": e}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": "Wystąpił błąd przy próbie tworzenia wolumenu", "error_code": e}), 500

@volume_bp.route('/list_all_volumes', methods=['GET'])
@jwt_required()
def list_all_volumes():

    try: 

        projects = Project.get_projects_by_user_id(current_user.id)
        containers = docker_client.containers.list(all=True)

        user_volumes = []

        for project in projects:
            volumes = docker_client.volumes.list(filters={'label': f'project_name={project.name}'})
            
            for volume in volumes:
                used_by_containers = False

                for container in containers:
                    container_info = docker_client.api.inspect_container(container.id)
                    mounts = container_info['Mounts']

                    for mount in mounts:
                        if mount['Name'] == volume.name:
                            used_by_containers = True
                            break

                    if used_by_containers:
                        break

                user_volumes.append(
                    {
                        'name': volume.name,
                        'used': used_by_containers, 
                        'created_at': volume.attrs['CreatedAt'],
                        'project': project.name,
                        'driver': volume.attrs["Driver"]
                    })

        
        return jsonify({"status": "success", "message": user_volumes}), 200
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Cannot get volumes list: {e}"}), 500

@volume_bp.route('/list_project_volumes', methods=['GET'])
@jwt_required()
def list_project_volumes():
    try: 
        project_name = request.args.get('project_name')
        containers = docker_client.containers.list(all=True)

        user_volumes = []

        volumes = docker_client.volumes.list(filters={'label': f'project_name={project_name}'})
        
        for volume in volumes:
            used_by_containers = False

            for container in containers:
                container_info = docker_client.api.inspect_container(container.id)
                mounts = container_info['Mounts']

                for mount in mounts:
                    if mount['Name'] == volume.name:
                        used_by_containers = True
                        break

                if used_by_containers:
                    break

            user_volumes.append(
                {
                    'name': volume.name,
                    'used': used_by_containers, 
                    'created_at': volume.attrs['CreatedAt'],
                    'project': project_name,
                    'driver': volume.attrs["Driver"]
                })

        
        return jsonify({"status": "success", "message": user_volumes}), 200
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Cannot get volumes list: {e}"}), 500

@volume_bp.route('/show_volume', methods=['GET'])
@jwt_required()
def show_volume():
    try: 
        volume_name = request.args.get('volume_name')
        volume = docker_client.volumes.get(volume_name)

        containers = docker_client.containers.list(all=True)
        containers_list = []
        used_by_containers = False 

        for container in containers:
            container_info = docker_client.api.inspect_container(container.id)
            mounts = container_info['Mounts']

            for mount in mounts:
                if mount['Name'] == volume.name:
                    used_by_containers = True
                    containers_list.append(f'{container.name}')
                    break

            # Dodaj pełny wynik polecenia 'docker inspect' do volume_response
            volume_inspect = docker_client.api.inspect_volume(volume.name)

            volume_response = {
                'name': volume.name,
                'used': used_by_containers, 
                'created_at': volume.attrs['CreatedAt'],
                'project': volume.attrs.get('Labels', {}).get('project_name', None),
                'driver': volume.attrs["Driver"],
                'scope': volume.attrs["Scope"],
                'containers': containers_list,
                'inspect': volume_inspect  # Dodaj pełny wynik inspect do odpowiedzi
            }

        return jsonify({"status": "success", "volume": volume_response}), 200
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Cannot get volumes list: {e}"}), 500
    except docker.errors.NotFound as e:
        return jsonify({"status": "error", "message": f"Volume not exists: {e}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {e}"}), 500

@volume_bp.route('/remove_volume', methods=['DELETE'])
@jwt_required()
def remove_volume():
    try:
        volume_name = request.args.get('volume_name')
        volume = docker_client.volumes.get(volume_name)

        project = Project.get_project_by_name(volume.attrs.get('Labels', {}).get('project_name', None))
        if project.user_id != current_user.id:
            return jsonify({"status": "error", "message": "Użytkownik nie ma dostępu do tego projektu", "error_code": "missing privigiles"}), 400
        
        containers = docker_client.containers.list(all=True)
        used_by_containers = False 

        for container in containers:
            container_info = docker_client.api.inspect_container(container.id)
            mounts = container_info['Mounts']

            for mount in mounts:
                if mount['Name'] == volume.name:
                    used_by_containers = True

        if used_by_containers:
            return jsonify({"status": "error", "message": "Wolumen jest używany przez obraz dockerowy", "error_code": "Volume is used"}), 400
    

        volume.remove(force=True)
        return jsonify({"status": "success", "message": f"Wolumen '{volume_name}' został pomyślnie usunięty"}), 200
    
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": "Docker wykrył błąd przy próbie tworzenia nowego wolumenu", "error_code": e}), 500
    except docker.errors.NotFound as e:
        return jsonify({"status": "error", "message": "Wolumen nie istnieje", "error_code": e}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": "Wystąpił błąd przy próbie usuwania wolumenu", "error_code": e}), 500
