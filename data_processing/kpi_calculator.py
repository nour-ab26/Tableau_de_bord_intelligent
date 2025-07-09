import pandas as pd
from db_connection import get_db_connection 

def get_equipments_data():
    """Récupère les données de la table 'equipments'."""
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql("SELECT * FROM equipments", conn)
            return df
        except Exception as e:
            print(f"Erreur lors de la récupération des données équipements : {e}")
            return pd.DataFrame() # Retourne un DataFrame vide en cas d'erreur
        finally:
            conn.close()
    return pd.DataFrame()

def get_downtime_data(start_time=None, end_time=None, equipment_id=None):
    """
    Récupère les logs de downtime, éventuellement filtrés par temps et équipement.
    start_time et end_time devraient être des objets datetime Python.
    """
    conn = get_db_connection()
    if conn:
        try:
            query = "SELECT * FROM downtime_logs"
            conditions = []
            params = {}

            if start_time:
                conditions.append("start_time >= %(start_time)s")
                params['start_time'] = start_time
            if end_time:
                conditions.append("end_time <= %(end_time)s")
                params['end_time'] = end_time
            if equipment_id:
                conditions.append("equipment_id = %(equipment_id)s")
                params['equipment_id'] = equipment_id

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            df = pd.read_sql(query, conn, params=params)
            return df
        except Exception as e:
            print(f"Erreur lors de la récupération des logs de downtime : {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()

def get_production_data(start_time=None, end_time=None, equipment_id=None):
    """
    Récupère les données de production, éventuellement filtrées par temps et équipement.
    start_time et end_time devraient être des objets datetime Python.
    """
    conn = get_db_connection()
    if conn:
        try:
            # Préparation de la requête SQL avec des conditions optionnelles
            # pour filtrer les données par temps et équipement
            query = "SELECT * FROM production_output"
            conditions = []
            params = {}

            if start_time:
                conditions.append("timestamp >= %(start_time)s") 
                params['start_time'] = start_time
            if end_time:
                conditions.append("timestamp <= %(end_time)s") 
                params['end_time'] = end_time
            if equipment_id:
                conditions.append("equipment_id = %(equipment_id)s")
                params['equipment_id'] = equipment_id

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            df = pd.read_sql(query, conn, params=params)
            return df
        except Exception as e:
            print(f"Erreur lors de la récupération des données de production : {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()


# def get_sensor_data(...): ...