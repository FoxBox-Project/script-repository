from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt, current_user
from db.models import Project
import docker

docker_client = docker.from_env()
network_bp = Blueprint('networks', __name__)

#+======+====================+======#
#|     /                      \     |
#|-----     DOCKER NETWORK     -----|
#|     \                      /     |
#+======+====================+======#



@network_bp.route('/create_network', methods=['POST'])
@jwt_required()
def create_network():
    try:
        data = request.get_json()

        # ustawienia podstawowe
        new_network_name = data.get("name")
        new_network_project = data.get("project")
        new_network_driver = data.get("driver", "bridge") 
        new_network_ipv6 = data.get("ipv6", False) 
        new_network_internal = data.get("internal", False)
        new_network_check_duplicate = data.get("check_duplicate", False)
        new_network_options = data.get("options", [])

        # ustawienia zaawansowane
        new_network_ipam_is_defined = data.get("ipam_defined", False)
        new_network_ipam_aux = data.get("aux_adressess", [])
        new_network_ipam_options = data.get("ipam_options", [])
        new_network_ipam_subnet  = data.get("subnet", None)
        new_network_ipam_iprange  = data.get("iprange", None)
        new_network_ipam_gateway  = data.get("gateway", None)
        new_network_ipam_driver  = data.get("gateway", "default")


        new_network_options_dict = {}
        for option in new_network_options:
            new_network_options_dict.update(option)

        new_network_ipam_aux_dict = {}
        for aux in new_network_ipam_aux:
            new_network_ipam_aux_dict.update(aux)        

        new_network_ipam_options_dict = {}
        for ipam_option in new_network_ipam_options:
            new_network_ipam_options_dict.update(ipam_option)  


        # Sprawdzenie czy wybrana sieć istnieje w projekcie
        project = Project.get_project_by_name(data.get('project'))
        if project.user_id != current_user.id:
            return jsonify({"status": "error", "message": "Użytkownik nie ma dostępu do tego projektu", "error_code": "missing privigiles"}), 401
        
        # Sprawdzenie czy wybrana sieć już istnieje
        networks = docker_client.networks.list()
        network_exists = any(network.name == new_network_name for network in networks)
        if network_exists:
            return jsonify({"status": "error", "message": "Sieć o tej nazwie istnieje", "error_code": "network with this name exists"}), 400


        if new_network_ipam_is_defined and (new_network_ipam_subnet is None or new_network_ipam_iprange is None or new_network_ipam_gateway is None):
            return jsonify({"status": "error", "message": "Nie podano wszystkich wymaganych zmiennych", "error_code": "IPAM driver requires subnet, iprange, and gateway"}), 400

        if new_network_ipam_is_defined:
            ipam_pool = docker.types.IPAMPool(
                subnet=new_network_ipam_subnet,
                iprange=new_network_ipam_iprange,
                gateway=new_network_ipam_gateway,
                aux_addresses=new_network_ipam_aux
            )

            ipam_config = docker.types.IPAMConfig(
                driver=new_network_ipam_driver,
                pool_configs=[ipam_pool],
                options=new_network_ipam_options_dict
            )

            docker_client.networks.create(
                name=new_network_name,
                driver=new_network_driver,
                labels={"project_name": new_network_project},
                enable_ipv6=new_network_ipv6,
                internal=new_network_internal,
                check_duplicate=new_network_check_duplicate,
                options=new_network_options_dict,
                ipam=ipam_config
            )

        else:
                docker_client.networks.create(
                name=new_network_name,
                driver=new_network_driver,
                labels={"project_name": new_network_project},
                enable_ipv6=new_network_ipv6,
                internal=new_network_internal,
                check_duplicate=new_network_check_duplicate,
                options=new_network_options_dict,
            )

        return {"status": "success", "message": f"Sieć {new_network_name} została utworzona pomyślnie"}
    except docker.errors.APIError as e:
        return {"status": "error", "message": f"Docker wykrył błąd przy próbie tworzenia nowej sieci", "error_code": e}, 500
    except Exception as e:
        return jsonify({"status": "error", "message": "Wystąpił błąd przy próbie tworzenia nowej sieci", "error_code": e}), 500


@network_bp.route('/list_all_networks', methods=['GET'])
@jwt_required()
def list_all_networks():
    try: 
        projects = Project.get_projects_by_user_id(current_user.id)
        containers = docker_client.containers.list(all=True)

        all_user_networks = []

        for project in projects:
            networks = docker_client.networks.list(filters={'label': f'project_name={project.name}'})
            
            for network in networks:
                network_info = docker_client.api.inspect_network(network.id)
                containers = network_info.get('Containers', {})

                used_by_containers = any(containers)
                    
                all_user_networks.append({
                    'name': network.name,
                    'used': used_by_containers,
                    'used_count': len(containers),
                    'project': project.name,
                    'created_at': network_info['Created'],
                    'driver': network_info['Driver'],
                })
        
        return jsonify({"status": "success", "message": f"Lista sieci zwrócona pomyślnie", "networks": all_user_networks}), 200
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Nie udało się pobrać listy.", "error_code": e}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": "Wystąpił błąd przy próbie tworzenia nowej sieci", "error_code": e}), 500

@network_bp.route('/list_project_networks', methods=['GET'])
@jwt_required()
def list_project_volumes():
    try:
        project_name = request.args.get('project_name')
        containers = docker_client.containers.list(all=True)

        project_networks = []

        networks = docker_client.networks.list(filters={'label': f'project_name={project_name}'})

        for network in networks:
            network_info = docker_client.api.inspect_network(network.id)
            containers = network_info.get('Containers', {})

            used_by_containers = any(containers)
                
            project_networks.append({
                'name': network.name,
                'used': used_by_containers,
                'used_count': len(containers),
                'project': project_name,
                'created_at': network_info['Created'],
                'driver': network_info['Driver'],
            })
            

        return jsonify({"status": "success", "networks": project_networks}), 200
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Cannot get volumes list: {e}"}), 500

@network_bp.route('/show_network', methods=['GET'])
@jwt_required()
def show_volume():
    try: 
        network_name = request.args.get('network_name')
        network = docker_client.networks.get(network_name)

        containers = docker_client.containers.list(all=True)
        network_info = docker_client.api.inspect_network(network.id)
        containers = network_info.get('Containers', {})

        used_by_containers = any(containers)


        volume_response = {
                'name': network.name,
                'ipv6': network_info.get('EnableIPv6', False),
                'internal': network_info.get('Internal', False),
                'used': used_by_containers,
                'used_count': len(containers),
                'containers': containers,
                'project': network.attrs.get('Labels', {}).get('project_name', None),
                'created_at': network_info['Created'],
                'driver': network_info['Driver'],
                'inspect': network_info
            }

        return jsonify({"status": "success", "network": volume_response}), 200
    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Cannot get network list: {e}"}), 500
    except docker.errors.NotFound as e:
        return jsonify({"status": "error", "message": f"Network not exists: {e}"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {e}"}), 500

@network_bp.route('/delete_network', methods=['DELETE'])
@jwt_required()
def delete_network():
    try: 
        network_name = request.args.get('network_name')
        network = docker_client.networks.get(network_name)

        network_info = docker_client.api.inspect_network(network.id)
        containers = network_info.get('Containers', {})
        used_by_containers = any(containers)

        if not used_by_containers:
            network.remove()
            return jsonify({"status": "success", "message": f"Sieć {network_name} została usunięta prawidłowo"}), 200
        else:
            return jsonify({"status": "error", "message": f"Sieć {network_name} jest aktualnie używana przez kontener/y"}), 400

    except docker.errors.APIError as e:
        return jsonify({"status": "error", "message": f"Cannot delete network: {e}"}), 500
    except docker.errors.NotFound as e:
        return jsonify({"status": "error", "message": f"Network not exists: {e}"}), 404
    except Exception as e:
        return jsonify({"status": "error", "message": f"Error: {e}"}), 500