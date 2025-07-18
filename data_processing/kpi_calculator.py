import pandas as pd
import numpy as np
from datetime import timedelta
from data_processing.db_connection import get_db_connection


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
                conditions.append("end_time > %(period_start_time)s")
                params['period_start_time'] = start_time
            if end_time:
                conditions.append("start_time < %(period_end_time)s")
                params['period_end_time'] = end_time
            if equipment_id:
                conditions.append("equipment_id = %(equipment_id)s")
                params['equipment_id'] = equipment_id

            if conditions:
                query += " WHERE " + " AND ".join(conditions)
            
            query += " ORDER BY equipment_id, start_time"

            df = pd.read_sql(query, conn, params=params)
            df['start_time'] = pd.to_datetime(df['start_time'])
            df['end_time'] = pd.to_datetime(df['end_time'])
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
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            return df
        except Exception as e:
            print(f"Erreur lors de la récupération des données de production : {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()


def calculate_effective_downtime_in_period(downtimes_df, start_time, end_time):
    """
    Calcule la durée effective des downtimes à l'intérieur d'une période donnée.
    Retourne un DataFrame avec equipment_id, downtime_category, downtime_reason, effective_duration_seconds.
    """
    downtimes_df['start_time'] = pd.to_datetime(downtimes_df['start_time'])
    downtimes_df['end_time'] = pd.to_datetime(downtimes_df['end_time'])

    # Filtre initial pour les arrêts qui ont une intersection avec la période
    downtimes_in_period = downtimes_df[
        (downtimes_df['start_time'] < end_time) & (downtimes_df['end_time'] > start_time)
    ].copy()

    # Calculer la durée effective dans la période pour les arrêts à cheval
    downtimes_in_period['effective_start'] = downtimes_in_period['start_time'].apply(lambda x: max(x, start_time))
    downtimes_in_period['effective_end'] = downtimes_in_period['end_time'].apply(lambda x: min(x, end_time))
    downtimes_in_period['effective_duration_seconds'] = (downtimes_in_period['effective_end'] - downtimes_in_period['effective_start']).dt.total_seconds()

    effective_downtime_summary = downtimes_in_period.groupby(['equipment_id', 'downtime_category', 'downtime_reason'])['effective_duration_seconds'].sum().reset_index(name='duration_seconds')

    return effective_downtime_summary


def calculate_downtime_kpis(effective_downtime_summary):
    """
    Calcule les KPIs liés aux temps d'arrêt à partir du résumé des temps d'arrêt effectifs.
    """
    # Total downtime par équipement (toutes catégories confondues)
    total_downtime_seconds = effective_downtime_summary.groupby('equipment_id')['duration_seconds'].sum().reset_index(name='total_downtime_seconds')

    # Séparer planned vs unplanned for MTBF/MTTR calculation later
    planned_downtime_seconds = effective_downtime_summary[
        effective_downtime_summary['downtime_category'].isin(['Planned Maintenance', 'Changeover'])
    ].groupby('equipment_id')['duration_seconds'].sum().reset_index(name='total_planned_downtime_seconds')

    unplanned_downtime_seconds = effective_downtime_summary[
        ~effective_downtime_summary['downtime_category'].isin(['Planned Maintenance', 'Changeover'])
    ].groupby('equipment_id')['duration_seconds'].sum().reset_index(name='total_unplanned_downtime_seconds')
    return total_downtime_seconds, planned_downtime_seconds, unplanned_downtime_seconds, effective_downtime_summary



def calculate_production_kpis(production_df, equip_df):
    """Calcule les KPIs liés à la production, à la qualité et la performance."""
    production_df['timestamp'] = pd.to_datetime(production_df['timestamp'])

    # Total produit et rejeté par équipement
    production_summary = production_df.groupby('equipment_id').agg(
        total_produced=('quantity_produced', 'sum'),
        total_rejected=('quantity_rejected', 'sum'),
        total_running_seconds=('running_duration_seconds', 'sum') # Durée cumulée où la machine était "RUNNING" dans les logs de production
    ).reset_index()

    # Calculer la quantité bonne et le taux de rejet
    production_summary['total_good'] = production_summary['total_produced'] - production_summary['total_rejected']
    production_summary['reject_rate'] = production_summary['total_rejected'] / production_summary['total_produced']
    production_summary['reject_rate'] = production_summary['reject_rate'].replace([np.inf, -np.inf], np.nan).fillna(0)
    
    # Calculer le Temps Production Net (Net Run Time) et le Temps Complètement Productif (Fully Productive Time)
    production_summary = pd.merge(production_summary, equip_df[['equipment_id', 'ideal_cycle_time_seconds']], on='equipment_id', how='left')
    production_summary['net_run_time_seconds'] = production_summary['total_good'] * production_summary['ideal_cycle_time_seconds']
    production_summary['fully_productive_time_seconds'] = production_summary['total_produced'] * production_summary['ideal_cycle_time_seconds']
    
    
    # Calculer le Temps de Cycle Réel Moyen
    production_summary['average_actual_cycle_time_seconds'] = production_summary['total_running_seconds'] / production_summary['total_produced']
    production_summary['average_actual_cycle_time_seconds'] = production_summary['average_actual_cycle_time_seconds'].replace([np.inf, -np.inf], np.nan)
    
    # Calculer le Débit Horaire
    production_summary['throughput_per_hour'] = production_summary['total_produced'] / (production_summary['total_running_seconds'] / 3600)
    production_summary['throughput_per_hour'] = production_summary['throughput_per_hour'].replace([np.inf, -np.inf], np.nan)
    
    return production_summary[['equipment_id', 'total_produced', 'total_rejected', 'total_good', 'reject_rate','total_running_seconds', 'net_run_time_seconds', 'fully_productive_time_seconds','average_actual_cycle_time_seconds', 'throughput_per_hour']]


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

def calculate_mtbf_mttr(downtimes_df, run_time_seconds_df, start_time, end_time):
    """
    Calcule le MTBF et le MTTR basés sur les arrêts IMPRÉVUS.
    run_time_seconds_df doit contenir 'equipment_id' et 'run_time_seconds'.
    """
    # Filter for unplanned downtimes that *start* within the period for COUNTING incidents
    unplanned_downtimes_starting_in_period = downtimes_df[
        (downtimes_df['start_time'] >= start_time) &
        (downtimes_df['start_time'] < end_time) &
        (~downtimes_df['downtime_category'].isin(['Planned Maintenance', 'Changeover']))].copy()

    # Count the number of unplanned incidents starting in the period
    unplanned_incident_counts = unplanned_downtimes_starting_in_period.groupby('equipment_id').size().reset_index(name='num_unplanned_incidents')

    # Sum effective duration for MTTR calculation (use effective duration from the period)
    effective_unplanned_downtime_in_period = calculate_effective_downtime_in_period(downtimes_df, start_time, end_time)
    total_unplanned_downtime_effective_seconds = effective_unplanned_downtime_in_period[
         ~effective_unplanned_downtime_in_period['downtime_category'].isin(['Planned Maintenance', 'Changeover'])
    ].groupby('equipment_id')['duration_seconds'].sum().reset_index(name='total_unplanned_downtime_effective_seconds')


    # Fusionner les données nécessaires
    mtbf_mttr_df = pd.merge(run_time_seconds_df[['equipment_id', 'run_time_seconds']], unplanned_incident_counts, on='equipment_id', how='left').fillna(0)
    mtbf_mttr_df = pd.merge(mtbf_mttr_df, total_unplanned_downtime_effective_seconds, on='equipment_id', how='left').fillna(0)


    # Calculer MTBF : Temps Fonctionnement Total / Nombre d'Arrêts Imprévus
    mtbf_mttr_df['mtbf_seconds'] = mtbf_mttr_df.apply(
        lambda row: row['run_time_seconds'] / row['num_unplanned_incidents'] if row['num_unplanned_incidents'] > 0 else np.nan,
        axis=1
    )

    # Calculer MTTR : Temps Total d'Arrêt Imprévu (effectif dans la période) / Nombre d'Arrêts Imprévus (commençant dans la période)
    mtbf_mttr_df['mttr_seconds'] = mtbf_mttr_df.apply(
        lambda row: row['total_unplanned_downtime_effective_seconds'] / row['num_unplanned_incidents'] if row['num_unplanned_incidents'] > 0 else np.nan,
        axis=1
    )

    # Convertir en heures pour une meilleure lisibilité
    mtbf_mttr_df['mtbf_hours'] = mtbf_mttr_df['mtbf_seconds'] / 3600
    mtbf_mttr_df['mttr_hours'] = mtbf_mttr_df['mttr_seconds'] / 3600


    return mtbf_mttr_df[['equipment_id', 'mtbf_hours', 'mttr_hours', 'num_unplanned_incidents', 'total_unplanned_downtime_effective_seconds']]


# --- Fonction pour Calculer TOUS les KPIs ---

def calculate_all_kpis(start_time, end_time, equipment_id=None):
    """
    Calcule l'ensemble des KPIs pour une période et potentiellement un équipement spécifique.
    Retourne un DataFrame consolidé.
    """
    equip_data = get_equipments_data()
    if equip_data.empty:
         print("Attention : Impossible de récupérer les données équipements.")
         return pd.DataFrame()
     
    if equipment_id:
        equip_data_filtered = equip_data[equip_data['equipment_id'] == equipment_id].copy()
        if equip_data_filtered.empty:
            print(f"Attention : Équipement {equipment_id} non trouvé dans les données équipements.")
            return pd.DataFrame()
    else:
        equip_data_filtered = equip_data.copy()
    

    downtimes_data_raw = get_downtime_data(start_time=start_time, end_time=end_time, equipment_id=equipment_id)
    production_data_raw = get_production_data(start_time=start_time, end_time=end_time, equipment_id=equipment_id)
    
    equipments_in_scope = equip_data_filtered[['equipment_id', 'equipment_name', 'equipment_type', 'production_line_id', 'ideal_cycle_time_seconds']].copy()
    
    if downtimes_data_raw.empty and production_data_raw.empty:
        print("Attention : Aucune donnée de downtime ou de production trouvée pour la période/équipement spécifié.")
        

        # Create columns with default NaN/0 values
        kpi_cols_defaults = {
            'oee': 0.0, 'availability': 0.0, 'performance': 0.0, 'quality': 0.0,
            'total_produced': 0, 'total_good': 0, 'total_rejected': 0, 'reject_rate': np.nan, # Use NaN for rates/means where denominator is zero
            'total_downtime_seconds': 0, 'total_planned_downtime_seconds': 0, 'total_unplanned_downtime_seconds': 0,
            'run_time_seconds': 0, 'planned_production_time_seconds': 0,
            'average_actual_cycle_time_seconds': np.nan, 'throughput_per_hour': np.nan,
            'mtbf_seconds': np.nan, 'mttr_seconds': np.nan, 'num_unplanned_incidents': 0
        }
        for col, default_val in kpi_cols_defaults.items():
             equipments_in_scope[col] = default_val

        # Convert durations to hours for final output
        equipments_in_scope['total_downtime_hours'] = equipments_in_scope['total_downtime_seconds'] / 3600
        equipments_in_scope['run_time_hours'] = equipments_in_scope['run_time_seconds'] / 3600
        equipments_in_scope['planned_production_time_hours'] = equipments_in_scope['planned_production_time_seconds'] / 3600

        output_cols = [ # Define order for final output
            'equipment_id', 'equipment_name', 'production_line_id', 'equipment_type',
            'oee', 'availability', 'performance', 'quality',
            'total_produced', 'total_good', 'total_rejected', 'reject_rate',
            'total_downtime_hours',
            'mtbf_hours', 'mttr_hours', 'num_unplanned_incidents',
            'average_actual_cycle_time_seconds', 'throughput_per_hour',
            'run_time_hours', 'planned_production_time_hours'
        ]
        # Ensure all columns exist in the result
        output_cols = [col for col in output_cols if col in equipments_in_scope.columns]

        return equipments_in_scope[output_cols]


    # --- Étape 1 : Calculer les durées d'arrêt effectives ---
    effective_downtime_summary = calculate_effective_downtime_in_period(downtimes_data_raw, start_time, end_time)

    # --- Étape 2 : Calculer les KPIs de temps d'arrêt (totaux, planifiés, imprévus, par raison) ---
    # Note: dt_by_reason_df is not directly used in calculate_all_kpis final output dataframe,
    # but the intermediate planned/unplanned summaries are.
    total_dt_df, planned_dt_df, unplanned_dt_df, dt_by_reason_df = calculate_downtime_kpis(effective_downtime_summary)

    # --- Étape 3 : Calculer les KPIs de production et performance brute ---
    # Pass equip_data_filtered here as it might be filtered by equipment_id
    prod_kpis_df = calculate_production_kpis(production_data_raw, equip_data_filtered) # Pass equipment data here

    # --- Étape 4 : Calculer les facteurs OEE ---
    # Fusionner les dataframes intermédiaires pour avoir toutes les infos nécessaires
    # Start with prod_kpis_df as it contains 'total_produced', 'total_running_seconds', etc.
    oee_intermediate_df = prod_kpis_df.merge(planned_dt_df, on='equipment_id', how='left').fillna(0)
    oee_intermediate_df = pd.merge(oee_intermediate_df, unplanned_dt_df, on='equipment_id', how='left').fillna(0)

    # *** FIX IS HERE: Merge equipment data to get ideal_cycle_time_seconds ***
    # We need ideal_cycle_time_seconds and total_good for performance/quality
    # We already have total_good in prod_kpis_df
    # We need ideal_cycle_time_seconds from equip_data_filtered
    oee_intermediate_df = pd.merge(oee_intermediate_df, equip_data_filtered[['equipment_id', 'ideal_cycle_time_seconds']], on='equipment_id', how='left')

    # Ensure ideal_cycle_time_seconds is not NaN for calculations, though merging from equip_data_filtered
    # should ensure it's present for equipments that exist in prod_kpis_df.
    # If an equipment has production but ideal_cycle_time_seconds is missing in equip_data, that's an data issue.
    # Let's assume ideal_cycle_time_seconds is available for equipments that produce.


    period_duration_seconds = (end_time - start_time).total_seconds()
    oee_intermediate_df['planned_production_time_seconds'] = period_duration_seconds - oee_intermediate_df['total_planned_downtime_seconds']
    oee_intermediate_df['run_time_seconds'] = oee_intermediate_df['planned_production_time_seconds'] - oee_intermediate_df['total_unplanned_downtime_seconds']

    # S'assurer que Run Time est non-négatif
    oee_intermediate_df['run_time_seconds'] = oee_intermediate_df['run_time_seconds'].apply(lambda x: max(0, x))


    # Calcul des 3 facteurs OEE et de l'OEE global
    # Disponibilité = Run Time / Planned Time
    oee_intermediate_df['availability'] = oee_intermediate_df.apply(
        lambda row: row['run_time_seconds'] / row['planned_production_time_seconds'] if row['planned_production_time_seconds'] > 0 else np.nan, axis=1
    )

    # Performance = (Total Produced * Ideal Cycle Time) / Run Time
    # 'ideal_cycle_time_seconds' is now available in oee_intermediate_df due to the merge above
    oee_intermediate_df['performance'] = oee_intermediate_df.apply(
        lambda row: (row['total_produced'] * row['ideal_cycle_time_seconds']) / row['run_time_seconds'] if row['run_time_seconds'] > 0 else np.nan, axis=1
    )
    oee_intermediate_df['performance'] = oee_intermediate_df['performance'].apply(lambda x: min(1.0, x) if pd.notna(x) else x) # Cap performance at 1

    # Qualité = Total Good / Total Produced
    oee_intermediate_df['quality'] = oee_intermediate_df.apply(
        lambda row: row['total_good'] / row['total_produced'] if row['total_produced'] > 0 else np.nan, axis=1
    )

    # OEE = Avail * Perf * Qual
    oee_intermediate_df['oee'] = oee_intermediate_df['availability'] * oee_intermediate_df['performance'] * oee_intermediate_df['quality']


    # --- Étape 5 : Calculer MTBF/MTTR ---
    # MTBF/MTTR nécessitent le Run Time (calculé dans l'étape OEE) et le *nombre* d'incidents imprévus commençant dans la période
    # Pass the already calculated run_time_seconds from oee_intermediate_df
    mtbf_mttr_df = calculate_mtbf_mttr(downtimes_data_raw, oee_intermediate_df[['equipment_id', 'run_time_seconds']], start_time, end_time)


    # --- Étape 6 : Consolider tous les résultats dans un seul DataFrame ---
    # Start with the main OEE intermediate dataframe as it has most columns
    final_kpis_df = oee_intermediate_df.copy()

    # Merge remaining KPIs that weren't already in oee_intermediate_df
    # total_downtime_seconds is in total_dt_df
    final_kpis_df = final_kpis_df.merge(total_dt_df, on='equipment_id', how='left').fillna(0)

    # MTBF/MTTR are in mtbf_mttr_df
    final_kpis_df = final_kpis_df.merge(mtbf_mttr_df, on='equipment_id', how='left')

    # Add equipment info for context (name, type, line)
    final_kpis_df = final_kpis_df.merge(equip_data[['equipment_id', 'equipment_name', 'equipment_type', 'production_line_id']], on='equipment_id', how='left')

    # Add remaining KPIs from prod_kpis_df that were not already in oee_intermediate_df
    # These include: reject_rate, average_actual_cycle_time_seconds, throughput_per_hour
    final_kpis_df = final_kpis_df.merge(
        prod_kpis_df[['equipment_id', 'reject_rate', 'average_actual_cycle_time_seconds', 'throughput_per_hour']],
        on='equipment_id', how='left'
    )


    # Convert durations from seconds to hours for display
    final_kpis_df['total_downtime_hours'] = final_kpis_df['total_downtime_seconds'] / 3600
    final_kpis_df['run_time_hours'] = final_kpis_df['run_time_seconds'] / 3600
    final_kpis_df['planned_production_time_hours'] = final_kpis_df['planned_production_time_seconds'] / 3600


    # Define the desired order and subset of columns for the final output
    output_cols = [
        'equipment_id', 'equipment_name', 'production_line_id', 'equipment_type',
        'oee', 'availability', 'performance', 'quality',
        'total_produced', 'total_good', 'total_rejected', 'reject_rate',
        'total_downtime_hours', # Use hours for display
        'mtbf_hours', 'mttr_hours', 'num_unplanned_incidents',
        'average_actual_cycle_time_seconds', 'throughput_per_hour',
        'run_time_hours', 'planned_production_time_hours'
        # Add other columns as needed for the dashboard
    ]

    # Ensure all output columns exist in the final DataFrame (handle potential missing columns after merges)
    # Fill missing essential columns with default values before selecting final columns
    cols_to_fill_zero = ['total_produced', 'total_good', 'total_rejected', 'num_unplanned_incidents',
                         'total_downtime_seconds', 'total_planned_downtime_seconds', 'total_unplanned_downtime_seconds',
                         'run_time_seconds', 'planned_production_time_seconds']
    for col in cols_to_fill_zero:
         if col in final_kpis_df.columns:
              final_kpis_df[col] = final_kpis_df[col].fillna(0)
         elif col in [c.replace('_hours', '_seconds') for c in output_cols if '_hours' in c]: # Ensure underlying seconds cols are also handled
             pass # Will be calculated from seconds later

    # Recalculate hours based on filled seconds to be safe
    final_kpis_df['total_downtime_hours'] = final_kpis_df['total_downtime_seconds'] / 3600
    final_kpis_df['run_time_hours'] = final_kpis_df['run_time_seconds'] / 3600
    final_kpis_df['planned_production_time_hours'] = final_kpis_df['planned_production_time_seconds'] / 3600


    # Fill NaN for ratios/means only where the denominator was zero, otherwise leave NaN if data was truly missing
    # Simpler approach: fill remaining NaNs with 0 for display purposes, but be aware this might hide missing data issues
    # A more nuanced approach is to keep NaN for ratios like OEE if the base data (planned time, total produced) is zero.
    # Let's fill with 0 for simplicity in the prototype where NaN might arise from a machine having no activity in the period.

    # Fill NaNs with 0 for numeric columns that are part of the output, except specific cases where NaN is intended (e.g., MTBF/MTTR if num_incidents is 0)
    numeric_cols = final_kpis_df.select_dtypes(include=np.number).columns.tolist()
    for col in numeric_cols:
        if col in output_cols: # Only fill if it's in the final output
             if col in ['mtbf_hours', 'mttr_hours', 'average_actual_cycle_time_seconds', 'throughput_per_hour', 'reject_rate']:
                 # These can legitimately be NaN if denominator is 0. Fill with 0 for display or handle in frontend.
                 # Let's fill with 0 for display convenience, but be mindful.
                 final_kpis_df[col] = final_kpis_df[col].fillna(0)
             else:
                  final_kpis_df[col] = final_kpis_df[col].fillna(0)


    # Capper les KPIs entre 0 et 1 (pourcentages) - refaire après lesfillna si nécessaire
    for col in ['oee', 'availability', 'performance', 'quality', 'reject_rate']:
         if col in final_kpis_df.columns:
              # Apply capping only if the value is not NaN *before* filling, or handle 0 appropriately
              final_kpis_df[col] = final_kpis_df[col].apply(lambda x: max(0.0, min(1.0, x)) if pd.notna(x) else 0.0) # Cap between 0 and 1, fill NaN with 0.0

    # Ensure output_cols only contains columns actually present in the final DataFrame
    output_cols_present = [col for col in output_cols if col in final_kpis_df.columns]


    # Retourner un DataFrame avec les KPIs agrégés par équipement pour la période
    return final_kpis_df[output_cols_present]


def count_downtimes_by_reason(downtimes_df, start_time, end_time, equipment_id=None):
    """
    Compte le nombre d'incidents de downtime par catégorie et raison pour une période.
    Utilise les arrêts qui COMMENCENT dans la période pour le comptage.
    """
    # Assurez-vous que les timestamps sont des objets datetime
    downtimes_df['start_time'] = pd.to_datetime(downtimes_df['start_time'])

    # Filter for downtimes starting within the period
    downtimes_in_period = downtimes_df[
        (downtimes_df['start_time'] >= start_time) & (downtimes_df['start_time'] < end_time)
    ].copy()

    if equipment_id:
        downtimes_in_period = downtimes_in_period[downtimes_in_period['equipment_id'] == equipment_id]

    # Count incidents by grouping
    downtime_counts = downtimes_in_period.groupby(['equipment_id', 'downtime_category', 'downtime_reason']).size().reset_index(name='incident_count')

    effective_downtime_summary = calculate_effective_downtime_in_period(downtimes_df, start_time, end_time)
    downtime_counts = pd.merge(downtime_counts, effective_downtime_summary, on=['equipment_id', 'downtime_category', 'downtime_reason'], how='left').fillna(0)


    return downtime_counts


def get_all_equipment_details():
    """Récupère tous les equipment_id et equipment_name."""
    conn = get_db_connection()
    if conn:
        try:
            df = pd.read_sql("SELECT equipment_id, equipment_name, production_line_id FROM equipments ORDER BY equipment_id", conn)
            return df
        except Exception as e:
            print(f"Erreur lors de la récupération des détails équipements : {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()

def get_sensor_data(start_time=None, end_time=None, equipment_id=None, sensor_type=None):
    """
    Récupère les relevés de capteurs, éventuellement filtrés par temps, équipement et type de capteur.
    start_time et end_time devraient être des objets datetime Python.
    """
    conn = get_db_connection()
    if conn:
        try:
            query = "SELECT timestamp, equipment_id, sensor_type, value, unit FROM sensor_readings"
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
            if sensor_type:
                conditions.append("sensor_type = %(sensor_type)s")
                params['sensor_type'] = sensor_type

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY timestamp" # Ordonner par temps pour les séries temporelles

            df = pd.read_sql(query, conn, params=params)
            df['timestamp'] = pd.to_datetime(df['timestamp']) # S'assurer que le timestamp est un objet datetime
            return df
        except Exception as e:
            print(f"Erreur lors de la récupération des données de capteurs : {e}")
            return pd.DataFrame()
        finally:
            conn.close()
    return pd.DataFrame()


# Exemple d'utilisation : Calculer les KPIs pour Janvier 2023
if __name__ == "__main__":
    print("Test du calculateur de KPIs...")
    start_date_kpi = pd.to_datetime('2023-01-01 00:00:00')
    end_date_kpi = pd.to_datetime('2023-02-01 00:00:00') # Calcul pour janvier

    # Calcul de tous les KPIs pour tous les équipements pour janvier
    all_kpis_january = calculate_all_kpis(start_date_kpi, end_date_kpi)

    print("\nRécapitulatif des KPIs pour tous les équipements (Janvier 2023) :")
    print(all_kpis_january)

    # Calcul des arrêts par raison pour janvier
    downtimes_raw_for_count = get_downtime_data(start_time=start_date_kpi, end_time=end_date_kpi) # Get raw downtime data again for the count logic
    downtime_counts_january = count_downtimes_by_reason(
        downtimes_raw_for_count,
        start_date_kpi,
        end_date_kpi
    )
    print("\nNombre d'arrêts par raison par équipement (Janvier 2023) :")
    print(downtime_counts_january)

    # Exemple : Calcul pour un seul équipement pour une période plus courte
    start_date_single_equip = pd.to_datetime('2023-03-15 07:00:00')
    end_date_single_equip = pd.to_datetime('2023-12-31 17:00:00') # Une semaine
    equip_to_analyze = 'MCH002' # Remplacez par un ID d'équipement valide de vos données

    kpis_single_equip_week = calculate_all_kpis(start_date_single_equip, end_date_single_equip, equipment_id=equip_to_analyze)
    print(f"\nRécapitulatif des KPIs pour {equip_to_analyze} (Semaine du 15 au 22 mars 2023) :")
    print(kpis_single_equip_week)

    downtimes_raw_for_count_single = get_downtime_data(start_time=start_date_single_equip, end_time=end_date_single_equip, equipment_id=equip_to_analyze)
    downtime_counts_single_equip = count_downtimes_by_reason(
         downtimes_raw_for_count_single,
         start_date_single_equip,
         end_date_single_equip,
         equipment_id=equip_to_analyze
    )
    print(f"\nNombre d'arrêts par raison pour {equip_to_analyze} (Semaine du 15 au 22 mars 2023) :")
    print(downtime_counts_single_equip)
    
    print("\nTest de récupération des données de capteurs...")
    start_date_sensor_test = pd.to_datetime('2023-01-01 07:00:00')
    end_date_sensor_test = pd.to_datetime('2023-01-01 08:00:00') # Une heure de données
    sensor_data_mch001_temp = get_sensor_data(start_time=start_date_sensor_test, end_time=end_date_sensor_test, equipment_id='MCH001', sensor_type='Temperature_Motor')
    print(f"Capteur MCH001 Temperature_Motor (premières 5 lignes) :")
    print(sensor_data_mch001_temp.head())

    sensor_data_all_mch001 = get_sensor_data(start_time=start_date_sensor_test, end_time=end_date_sensor_test, equipment_id='MCH001')
    print(f"\nTous les capteurs MCH001 (premières 5 lignes) :")
    print(sensor_data_all_mch001.head())