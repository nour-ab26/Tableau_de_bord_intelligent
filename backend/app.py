from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

# Assurez-vous que data_processing est accessible depuis le backend
# Vous devrez peut-être ajuster le chemin d'importation selon la structure exacte
# Si 'data_processing' est un dossier à côté de 'backend', vous pouvez l'ajouter au PYTHONPATH
# ou utiliser une importation relative si les deux sont des modules dans un package parent.
# Pour un démarrage rapide, on peut simplifier en supposant qu'ils sont dans le même niveau de packages
# ou que data_processing est un module sibling.
# Solution simple pour le développement : ajouter le dossier parent au sys.path
import sys
import os
# Obtenir le chemin du dossier parent (celui qui contient backend, data_processing, etc.)
parent_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
sys.path.append(parent_dir)

from data_processing.kpi_calculator import calculate_all_kpis, count_downtimes_by_reason, get_downtime_data, get_all_equipment_details, get_sensor_data

app = Flask(__name__)
CORS(app) 

@app.route('/')
def home():
    return "API du Tableau de Bord Intelligent de Production est en cours d'exécution !"

@app.route('/api/kpis', methods=['GET'])
def get_kpis():
    # Récupérer les paramètres de requête pour la période (start_date, end_date)
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    equipment_id = request.args.get('equipment_id') 

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Les paramètres start_date et end_date sont requis."}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Format de date invalide. Utilisez YYYY-MM-DD."}), 400

   
    kpis_df = calculate_all_kpis(start_date, end_date, equipment_id)

    return jsonify(kpis_df.to_dict(orient='records'))

@app.route('/api/downtime-reasons', methods=['GET'])
def get_downtime_reasons():
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    equipment_id = request.args.get('equipment_id')

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Les paramètres start_date et end_date sont requis."}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
    except ValueError:
        return jsonify({"error": "Format de date invalide. Utilisez YYYY-MM-DD."}), 400

    # Il faut d'abord récupérer les données brutes de downtime pour la fonction count_downtimes_by_reason
    from data_processing.kpi_calculator import get_downtime_data # Importer la fonction raw data getter
    downtimes_raw = get_downtime_data(start_time=start_date, end_time=end_date, equipment_id=equipment_id)

    downtime_reasons_df = count_downtimes_by_reason(downtimes_raw, start_date, end_date, equipment_id)
    return jsonify(downtime_reasons_df.to_dict(orient='records'))

@app.route('/api/equipments', methods=['GET'])
def get_equipments():
    """
    Endpoint pour récupérer la liste de tous les équipements.
    """
    equipments_df = get_all_equipment_details()
    return jsonify(equipments_df.to_dict(orient='records'))

@app.route('/api/sensor-data', methods=['GET'])
def api_get_sensor_data():
    """
    Endpoint pour récupérer les relevés de capteurs.
    Paramètres: start_date, end_date (requis), equipment_id, sensor_type (optionnels)
    """
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    equipment_id = request.args.get('equipment_id')
    sensor_type = request.args.get('sensor_type')

    if not start_date_str or not end_date_str:
        return jsonify({"error": "Les paramètres start_date et end_date sont requis."}), 400

    try:
        start_date = datetime.strptime(start_date_str, '%Y-%m-%d %H:%M:%S') # Inclure l'heure
        end_date = datetime.strptime(end_date_str, '%Y-%m-%d %H:%M:%S')     # Inclure l'heure
    except ValueError:
        return jsonify({"error": "Format de date/heure invalide. Utilisez YYYY-MM-DD HH:MM:SS."}), 400

    sensor_df = get_sensor_data(start_date, end_date, equipment_id, sensor_type)

    return jsonify(sensor_df.to_dict(orient='records'))

if __name__ == '__main__':
    app.run(debug=True, port=5000) 