import pandas as pd
import numpy as np
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

from datetime import timedelta

def calculate_downtime_kpis(downtimes_df, start_time, end_time):
    """Calcule les KPIs liés aux temps d'arrêt pour une période donnée."""
    downtimes_df['start_time'] = pd.to_datetime(downtimes_df['start_time'])
    downtimes_df['end_time'] = pd.to_datetime(downtimes_df['end_time'])

    downtimes_in_period = downtimes_df[
        (downtimes_df['start_time'] < end_time) & (downtimes_df['end_time'] > start_time)
    ].copy()

    # Calculer la durée effective dans la période pour les arrêts à cheval
    downtimes_in_period['effective_start'] = downtimes_in_period['start_time'].apply(lambda x: max(x, start_time))
    downtimes_in_period['effective_end'] = downtimes_in_period['end_time'].apply(lambda x: min(x, end_time))
    downtimes_in_period['effective_duration_seconds'] = (downtimes_in_period['effective_end'] - downtimes_in_period['effective_start']).dt.total_seconds()

    total_downtime_seconds = downtimes_in_period.groupby('equipment_id')['effective_duration_seconds'].sum().reset_index(name='total_downtime_seconds')

    # Downtime par catégorie et raison
    downtime_by_reason = downtimes_in_period.groupby(['equipment_id', 'downtime_category', 'downtime_reason'])['effective_duration_seconds'].sum().reset_index(name='duration_seconds')

    return total_downtime_seconds, downtime_by_reason

def calculate_production_kpis(production_df):
    """Calcule les KPIs liés à la production et à la qualité."""
    production_df['timestamp'] = pd.to_datetime(production_df['timestamp'])

    # Total produit et rejeté par équipement
    production_summary = production_df.groupby('equipment_id').agg(
        total_produced=('quantity_produced', 'sum'),
        total_rejected=('quantity_rejected', 'sum'),
        total_running_seconds=('running_duration_seconds', 'sum') # Durée cumulée où la machine était "RUNNING" dans les logs de production
    ).reset_index()

    # Calculer la quantité bonne et le taux de rejet
    production_summary['total_good'] = production_summary['total_produced'] - production_summary['total_rejected']
    production_summary['reject_rate'] = production_summary['total_rejected'] / production_summary['total_produced'].replace(0, np.nan) # Avoid division by zero

    return production_summary


def calculate_oee_kpis(equip_df, total_downtime_df, production_summary_df, start_time, end_time):
    """Calcule les facteurs de l'OEE et l'OEE global."""
    period_duration_seconds = (end_time - start_time).total_seconds()

    # Fusionner production_summary avec les informations équipement (notamment cycle time)
    merged_df = pd.merge(production_summary_df, equip_df[['equipment_id', 'ideal_cycle_time_seconds']], on='equipment_id', how='left')
    # Fusionner avec les temps d'arrêt totaux
    merged_df = pd.merge(merged_df, total_downtime_df[['equipment_id', 'total_downtime_seconds']], on='equipment_id', how='left').fillna(0) # Remplir les NaN avec 0 si un équipement n'a pas eu d'arrêt

    # Pour les besoins de l'OEE, on doit aussi connaître les arrêts PLANIFIÉS pour calculer le Temps Planifié
    # Récupérer les arrêts planifiés
    planned_downtime_df = get_downtime_data(start_time, end_time).copy()
    planned_downtime_df = planned_downtime_df[planned_downtime_df['downtime_category'].isin(['Planned Maintenance', 'Changeover'])]

    # Calculer la durée effective dans la période pour les arrêts planifiés à cheval
    planned_downtime_df['effective_start'] = planned_downtime_df['start_time'].apply(lambda x: max(x, start_time))
    planned_downtime_df['effective_end'] = planned_downtime_df['end_time'].apply(lambda x: min(x, end_time))
    planned_downtime_df['effective_duration_seconds'] = (planned_downtime_df['effective_end'] - planned_downtime_df['effective_start']).dt.total_seconds()

    total_planned_downtime_seconds = planned_downtime_df.groupby('equipment_id')['effective_duration_seconds'].sum().reset_index(name='total_planned_downtime_seconds')

    # Fusionner les arrêts planifiés avec le reste
    merged_df = pd.merge(merged_df, total_planned_downtime_seconds, on='equipment_id', how='left').fillna(0)


    # Calculer les facteurs OEE
    merged_df['planned_production_time_seconds'] = period_duration_seconds - merged_df['total_planned_downtime_seconds']

    # S'assurer que le temps planifié est > 0 pour éviter division par zéro
    merged_df = merged_df[merged_df['planned_production_time_seconds'] > 0].copy()


    # Disponibilité = (Temps Planifié - Temps d'Arrêt Total) / Temps Planifié
    # Total downtime includes planned and unplanned
    unplanned_downtime_df = get_downtime_data(start_time, end_time).copy()
    unplanned_downtime_df = unplanned_downtime_df[~unplanned_downtime_df['downtime_category'].isin(['Planned Maintenance', 'Changeover'])]
    unplanned_downtime_df['effective_start'] = unplanned_downtime_df['start_time'].apply(lambda x: max(x, start_time))
    unplanned_downtime_df['effective_end'] = unplanned_downtime_df['end_time'].apply(lambda x: min(x, end_time))
    unplanned_downtime_df['effective_duration_seconds'] = (unplanned_downtime_df['effective_end'] - unplanned_downtime_df['effective_start']).dt.total_seconds()
    total_unplanned_downtime_seconds = unplanned_downtime_df.groupby('equipment_id')['effective_duration_seconds'].sum().reset_index(name='total_unplanned_downtime_seconds')

    merged_df = pd.merge(merged_df, total_unplanned_downtime_seconds, on='equipment_id', how='left').fillna(0)

    # Temps de Fonctionnement = Temps Planifié - Temps d'Arrêt Imprévu
    merged_df['run_time_seconds'] = merged_df['planned_production_time_seconds'] - merged_df['total_unplanned_downtime_seconds']
    # S'assurer que Run Time est non-négatif
    merged_df['run_time_seconds'] = merged_df['run_time_seconds'].apply(lambda x: max(0, x))

    # Disponibilité
    merged_df['availability'] = merged_df['run_time_seconds'] / merged_df['planned_production_time_seconds']


    # Performance = (Quantité Totale Produite * Temps Cycle Idéal) / Temps de Fonctionnement
    # S'assurer que Run Time > 0 pour éviter division par zéro
    merged_df['performance'] = merged_df.apply(
        lambda row: (row['total_produced'] * row['ideal_cycle_time_seconds']) / row['run_time_seconds'] if row['run_time_seconds'] > 0 else 0,
        axis=1
    )
    # Capper la performance à 1 (on ne peut pas aller plus vite que l'idéal par définition, même si simulation peut créer > 1)
    merged_df['performance'] = merged_df['performance'].apply(lambda x: min(1.0, x))


    # Qualité = Quantité Bonne / Quantité Totale Produite
    # S'assurer que Total Produit > 0 pour éviter division par zéro
    merged_df['quality'] = merged_df.apply(
         lambda row: row['total_good'] / row['total_produced'] if row['total_produced'] > 0 else 0,
         axis=1
    )

    # OEE = Disponibilité x Performance x Qualité
    merged_df['oee'] = merged_df['availability'] * merged_df['performance'] * merged_df['quality']

    # S'assurer que les KPIs sont entre 0 et 1 (ou 0 et 100 si vous les affichez en %)
    for col in ['availability', 'performance', 'quality', 'oee']:
         merged_df[col] = merged_df[col].apply(lambda x: max(0.0, min(1.0, x))) # Capper entre 0 et 1

    return merged_df[['equipment_id', 'availability', 'performance', 'quality', 'oee', 'total_produced', 'total_good', 'total_rejected', 'total_downtime_seconds', 'total_planned_downtime_seconds', 'total_unplanned_downtime_seconds', 'run_time_seconds', 'planned_production_time_seconds']]


# Exemple d'utilisation : Calculer les KPIs pour Janvier 2023
if __name__ == "__main__":
    equip_data = get_equipments_data()
    if not equip_data.empty:
        print("Données équipements récupérées.")

        start_date_kpi = pd.to_datetime('2023-01-01 00:00:00')
        end_date_kpi = pd.to_datetime('2023-02-01 00:00:00') # Calcul pour janvier

        downtimes_data = get_downtime_data(start_date=start_date_kpi, end_time=end_date_kpi)
        print(f"Données downtime récupérées pour la période ({len(downtimes_data)} lignes).")

        production_data = get_production_data(start_time=start_date_kpi, end_time=end_date_kpi)
        print(f"Données production récupérées pour la période ({len(production_data)} lignes).")


        # Calcul des KPIs de downtime
        total_dt, dt_by_reason = calculate_downtime_kpis(downtimes_data, start_date_kpi, end_date_kpi)
        print("\nTemps d'arrêt total par équipement (Janvier 2023) :")
        print(total_dt)
        print("\nTemps d'arrêt par raison (quelques lignes) :")
        print(dt_by_reason.head())

        # Calcul des KPIs de production
        prod_summary = calculate_production_kpis(production_data)
        print("\nRésumé production par équipement (Janvier 2023) :")
        print(prod_summary)

        # Calcul de l'OEE
        oee_results = calculate_oee_kpis(equip_data, total_dt, prod_summary, start_date_kpi, end_date_kpi)
        print("\nRésultats OEE par équipement (Janvier 2023) :")
        print(oee_results)

    else:
        print("Impossible de récupérer les données équipements. Vérifiez la connexion à la BDD.")