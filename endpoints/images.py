from flask import Blueprint, jsonify, request
import docker
import os
from flask_jwt_extended import jwt_required, current_user
from db.models import Project
from datetime import datetime

docker_client = docker.from_env()
image_bp = Blueprint('images', __name__)

# Brakujące endpointy
# - usuwanie obrazu
# - tworzenie obrazu samodzielnie
# - logowanie do repozytorium
# - wyswietlanie obrazów przypisanych do projektu



@image_bp.route('/list_all_images', methods=['GET'])
@jwt_required()
def list_all_images():
    try: 
        containers = docker_client.containers.list(all=True)
        images = docker_client.images.list()

        image_list = []

        for image in images:
            # Sprawdzenie, czy istnieją kontenery używające danego obrazu
            containers = docker_client.containers.list(all=True, filters={"ancestor": image.id})
            repository, tag = image.tags[0].split(':', 1) if image.tags else ('Unnamed', 'latest')

            shortened_id = image.id[7:19] if image.id else 'N/A'

            if containers:
                is_used = True
            else:
                is_used = False

            image_list.append(
                    {
                        'repository': repository,
                        'tag': tag, 
                        'id': shortened_id,
                        'full_id': image.id,
                        'created': image.attrs['Created'],
                        'size': image.attrs["Size"],
                        'used': is_used
                    })

        
        return jsonify({"status": "success", "images": image_list}), 200
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Cannot get volumes list: {e}"}), 500
    
@image_bp.route('/show_image', methods=['GET'])
@jwt_required()
def show_image():
    try:
        image_id = request.args.get('image_id')
        image = docker_client.images.get(image_id)

        containers = docker_client.containers.list(all=True, filters={"ancestor": image.id})
        repository, tag = image.tags[0].split(':', 1) if image.tags else ('Unnamed', 'latest')

        containers_list = [container.name for container in containers]

        if containers:
            is_used = True
        else:
            is_used = False

        image_inspect = docker_client.api.inspect_image(image.id)

        image_response = {
            'repository': repository,
            'tag': tag,
            'full_id': image.id,
            'created': image.attrs['Created'],
            'size': image.attrs["Size"],
            'used': is_used,
            'containers': containers_list,
            'inspect': image_inspect 
        }

        return jsonify({"status": "success", "image": image_response}), 200
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Cannot get image details: {e}"}), 500
    except docker.errors.NotFound as e:
        return jsonify({"status": "error", "message": f"Image not exists: {e}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {e}"}), 500

@image_bp.route('/download_image', methods=['POST'])
@jwt_required()
def download_image():
    try:
        data = request.get_json()

        new_image_repository = data.get("repository")
        new_image_tag = data.get("tag")

        docker_client.images.pull(repository=new_image_repository, tag=new_image_tag)

        return jsonify({"status": "success", "message": "image downloaded"}), 200
    except docker.errors.ImageNotFound as e:
        return jsonify({"status": "error", "message": f"Nie znaleziono obrazu: {e}"}), 500
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Error Docker: {e}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {e}"}), 500
