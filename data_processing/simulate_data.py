import pandas as pd
import numpy as np
import random
from datetime import datetime, timedelta
from faker import Faker
import simpy # A lightweight simulation framework might help structure this later, but let's stick to pandas/datetime for now.

fake = Faker()

NUM_MACHINES = 10
PROJECT_START_DATE = datetime(2023, 1, 1, 7, 0, 0) # Start at a typical shift time
PROJECT_END_DATE = datetime(2023, 12, 31, 17, 0, 0) # Simulate data for a year


AVG_MTBF_HOURS = 150 # Average Mean Time Between Failures (time machine runs before an unplanned stop)
AVG_MTTR_HOURS_BREAKDOWN = 4 # Average Mean Time To Repair (unplanned breakdown)
AVG_MTTR_HOURS_PROCESS = 1 # Average MTTR for process issues
AVG_MTTR_HOURS_CHANGEOVER = 0.5 # Average MTTR for changeovers
AVG_MTTR_HOURS_MAINTENANCE = 8 # Average MTTR for planned maintenance

PROB_STOP_IS_PLANNED_MAINT = 0.05 # Probability a scheduled stop is for planned maint (rest are breakdowns/process/changeover)
PROB_BREAKDOWN_IS_PROCESS = 0.3 # Probability an unplanned stop is a process issue vs hard breakdown
PROB_CHANGEOVER = 0.15 # Probability a stop is a planned changeover (needs specific handling)

# Sensor Simulation Parameters 
SENSOR_PROFILES = {
    'Temperature_Motor': {'base': 60, 'noise_std': 2, 'unit': '°C', 'trend_type': 'linear', 'trend_strength': 8, 'related_downtime_cat': 'Unplanned - Breakdown', 'related_downtime_reason': 'Electrical Fault'},
    'Vibration_Bearing': {'base': 3.0, 'noise_std': 0.8, 'unit': 'g', 'trend_type': 'exponential', 'trend_strength': 1.5, 'related_downtime_cat': 'Unplanned - Breakdown', 'related_downtime_reason': 'Mechanical Failure'},
    'Pressure_Hydraulic': {'base': 10.0, 'noise_std': 0.5, 'unit': 'bar', 'trend_type': 'linear', 'trend_strength': -4, 'related_downtime_cat': 'Unplanned - Breakdown', 'related_downtime_reason': 'Hydraulic Leak'},
    'Current_Consumption': {'base': 15.0, 'noise_std': 1.0, 'unit': 'A', 'trend_type': 'linear', 'trend_strength': 5, 'related_downtime_cat': 'Unplanned - Process', 'related_downtime_reason': 'Tooling Issue'} # Process issue leading to higher load
}
SENSOR_READING_FREQUENCY_SECONDS = 30 # How often sensor data is recorded
ALARM_PRE_TREND_WINDOW_HOURS = 8 # Window before an alarm/unplanned stop to simulate sensor trend

# Production Simulation Parameters
IDEAL_CYCLE_TIME_SECONDS_MEAN = 15 # Mean time to produce one unit
IDEAL_CYCLE_TIME_SECONDS_STD = 5
PERFORMANCE_FACTOR_MEAN = 0.98 # Ideal cycle time / Actual cycle time (should be close to 1)
PERFORMANCE_FACTOR_STD = 0.02
PERFORMANCE_DROP_FACTOR = 0.15 # How much performance drops before an unplanned stop (e.g., 15% drop)
PERFORMANCE_DROP_WINDOW_HOURS = 2 # Window before an unplanned stop for performance to drop
QUALITY_REJECT_RATE_BASE = 0.01 # Base probability of a unit being rejected
QUALITY_REJECT_RATE_INCREASE = 0.03 # Additional reject rate before an unplanned stop
QUALITY_REJECT_WINDOW_HOURS = 1 # Window before an unplanned stop for reject rate to increase

# Downtime Categories and Reasons (must match related_downtime_cat/reason in sensors)
DOWNTIME_REASONS = {
    'Planned Maintenance': ['Routine Check', 'Calibration', 'Software Update'],
    'Unplanned - Breakdown': ['Mechanical Failure', 'Electrical Fault', 'Hydraulic Leak', 'Sensor Error', 'Other Breakdown'], # Ensure these match sensor related_reasons or have defaults
    'Unplanned - Process': ['Material Shortage', 'Tooling Issue', 'Operator Error', 'Quality Issue'], # Ensure these match sensor related_reasons or have defaults
    'Changeover': ['Product Changeover', 'Setup Adjustment']
}


# --- Data Generation Functions ---

def generate_equipment_data(num_machines):
    equipments = []
    for i in range(num_machines):
        equipments.append({
            'equipment_id': f'MCH{i+1:03d}',
            'equipment_name': f'{fake.word().capitalize()} Machine {fake.random_letter().upper()}-{i+1}',
            'equipment_type': random.choice(['Assemblage', 'Emballage', 'Usinage', 'Peinture', 'Contrôle', 'Soudage']),
            'production_line_id': f'LINE_{random.choice(["A", "B", "C", "D"])}',
            'ideal_cycle_time_seconds': max(1, int(np.random.normal(IDEAL_CYCLE_TIME_SECONDS_MEAN, IDEAL_CYCLE_TIME_SECONDS_STD))),
            'location': fake.city(),
            'installation_date': fake.date_time_between(start_date='-5y', end_date='-1y') # Machines installed earlier
        })
    return pd.DataFrame(equipments)

def generate_machine_lifecycle(equip_df, start_date, end_date, params):
    all_events = []
    all_downtimes = []
    all_planned_maintenance = [] # Separate for clarity

    event_id_counter = 0
    downtime_id_counter = 0

    machine_states = {}
    scheduled_events = [] # List of (timestamp, event_type, equip_id, details/cause)

    # Initialize machines
    for i, equip in equip_df.iterrows():
        equip_id = equip['equipment_id']
        machine_states[equip_id] = {
            'state': 'STOPPED',
            'state_start_time': start_date - timedelta(seconds=1), # Assume stopped just before start
            'current_product': f'PROD_{random.randint(100, 999)}',
            'next_event_cause': None,
            'planned_downtime_end': None # For changeover/planned maintenance
        }
        # Schedule initial START shortly after project start
        initial_start_time = start_date + timedelta(minutes=random.randint(1, 60))
        scheduled_events.append((initial_start_time, 'START', equip_id, 'Initial startup'))

    # Sort initial events
    scheduled_events.sort()

    # --- Simulate Chronological Events ---
    current_sim_time = start_date
    while scheduled_events and current_sim_time <= end_date:
        # Get the earliest scheduled event across all machines
        next_event_time, event_type, equip_id, details = scheduled_events.pop(0)

        if next_event_time > end_date:
            # If the next event is beyond the simulation end date, stop processing for this machine's future
            # We still need to process events up to end_date, so we continue the loop
            # but events scheduled after end_date are discarded when we pop them.
            continue # This event is too late, move to the next scheduled event

        # Ensure time moves forward
        if next_event_time < current_sim_time:
             next_event_time = current_sim_time # Should not happen with sorted list, but as a safeguard

        current_sim_time = next_event_time # Advance simulation time

        # Record the event
        event_id_counter += 1
        all_events.append({
            'event_id': event_id_counter,
            'timestamp': current_sim_time,
            'equipment_id': equip_id,
            'event_type': event_type,
            'details': details
        })

        # --- Update State and Schedule Next Event ---
        current_state = machine_states[equip_id]['state']
        state_start_time = machine_states[equip_id]['state_start_time']
        downtime_end_override = machine_states[equip_id]['planned_downtime_end'] # For planned events

        if event_type == 'START':
            if current_state == 'STOPPED':
                machine_states[equip_id]['state'] = 'RUNNING'
                machine_states[equip_id]['state_start_time'] = current_sim_time
                machine_states[equip_id]['planned_downtime_end'] = None # Clear planned end

                # Schedule next STOP event (Mean Time Between Failures)
                # Use exponential distribution for time between failures (common model)
                time_until_next_stop_hours = random.expovariate(1.0 / params['AVG_MTBF_HOURS'])
                next_stop_time = current_sim_time + timedelta(hours=time_until_next_stop_hours)

                # Decide *why* it will stop - pre-determine the cause for sensor trending
                is_planned = random.random() < params['PROB_STOP_IS_PLANNED_MAINT']
                if is_planned:
                     next_stop_cause_cat = 'Planned Maintenance'
                     next_stop_cause_reason = random.choice(params['DOWNTIME_REASONS']['Planned Maintenance'])
                else:
                    # Unplanned stop - breakdown, process, or changeover
                    if random.random() < params['PROB_CHANGEOVER']:
                         next_stop_cause_cat = 'Changeover'
                         next_stop_cause_reason = random.choice(params['DOWNTIME_REASONS']['Changeover'])
                         # Change product upon next start after changeover
                         new_product = f'PROD_{random.randint(100, 999)}'
                         # Note: Simulating product change precisely requires linking this to the *next* START event details
                         # Let's store it with the *stop* cause for now and handle at the next START
                         machine_states[equip_id]['next_product_after_changeover'] = new_product

                    elif random.random() < params['PROB_BREAKDOWN_IS_PROCESS']:
                         next_stop_cause_cat = 'Unplanned - Process'
                         # Choose a reason related to a sensor type if possible, otherwise pick from general reasons
                         potential_reasons = [p['related_downtime_reason'] for p in params['SENSOR_PROFILES'].values() if p['related_downtime_cat'] == 'Unplanned - Process']
                         next_stop_cause_reason = random.choice(potential_reasons + [r for r in params['DOWNTIME_REASONS']['Unplanned - Process'] if r not in potential_reasons])

                    else: # Hard Breakdown
                         next_stop_cause_cat = 'Unplanned - Breakdown'
                         # Choose a reason related to a sensor type if possible
                         potential_reasons = [p['related_downtime_reason'] for p in params['SENSOR_PROFILES'].values() if p['related_downtime_cat'] == 'Unplanned - Breakdown']
                         next_stop_cause_reason = random.choice(potential_reasons + [r for r in params['DOWNTIME_REASONS']['Unplanned - Breakdown'] if r not in potential_reasons])

                    # If it's an unplanned breakdown, schedule an ALARM event right at the STOP time
                    if next_stop_cause_cat == 'Unplanned - Breakdown':
                         scheduled_events.append((next_stop_time, 'ALARM', equip_id, f'Pre-stop alarm: {next_stop_cause_reason}'))


                # Schedule the actual STOP event
                scheduled_events.append((next_stop_time, 'STOP', equip_id, f'Stop: {next_stop_cause_reason}'))
                machine_states[equip_id]['next_event_cause'] = {'category': next_stop_cause_cat, 'reason': next_stop_cause_reason, 'time': next_stop_time}


        elif event_type == 'STOP':
            if current_state == 'RUNNING':
                machine_states[equip_id]['state'] = 'STOPPED'
                machine_states[equip_id]['state_start_time'] = current_sim_time

                # Log Downtime (start time is the current time)
                downtime_id_counter += 1
                # The cause was determined when the STOP was scheduled
                cause_info = machine_states[equip_id].get('next_event_cause', {'category': 'Unknown', 'reason': 'Unknown'})
                all_downtimes.append({
                    'downtime_id': downtime_id_counter,
                    'equipment_id': equip_id,
                    'start_time': current_sim_time,
                    'downtime_category': cause_info['category'],
                    'downtime_reason': cause_info['reason']
                })
                machine_states[equip_id]['next_event_cause'] = None # Clear cause after logging

                # Schedule next START event based on downtime reason (MTTR)
                downtime_category = cause_info['category']
                if downtime_category == 'Planned Maintenance':
                    mttr_hours = params['AVG_MTTR_HOURS_MAINTENANCE']
                elif downtime_category == 'Unplanned - Breakdown':
                     mttr_hours = params['AVG_MTTR_HOURS_BREAKDOWN']
                elif downtime_category == 'Unplanned - Process':
                     mttr_hours = params['AVG_MTTR_HOURS_PROCESS']
                elif downtime_category == 'Changeover':
                    mttr_hours = params['AVG_MTTR_HOURS_CHANGEOVER']
                else:
                    mttr_hours = params['AVG_MTTR_HOURS_PROCESS'] # Default

                # Use exponential distribution for repair time
                time_until_next_start_hours = random.expovariate(1.0 / mttr_hours)
                next_start_time = current_sim_time + timedelta(hours=time_until_next_start_hours)

                # For planned events (Changeover, Planned Maintenance), the end time might be fixed/planned
                if downtime_category in ['Planned Maintenance', 'Changeover']:
                     # Let's assume planned downtime has a slightly more predictable duration, but still with variation
                     planned_duration = timedelta(hours=mttr_hours * random.uniform(0.8, 1.2))
                     next_start_time = current_sim_time + planned_duration


                scheduled_events.append((next_start_time, 'START', equip_id, f'Restart after {downtime_category}'))
                machine_states[equip_id]['planned_downtime_end'] = next_start_time # Store planned end time

                # Handle product change if it was a Changeover
                if 'next_product_after_changeover' in machine_states[equip_id]:
                     machine_states[equip_id]['current_product'] = machine_states[equip_id]['next_product_after_changeover']
                     del machine_states[equip_id]['next_product_after_changeover']


        elif event_type == 'ALARM':
             # ALARM events happen at the same time as a STOP event for unplanned breakdowns.
             # No state change here, just an event log entry. State change is handled by the corresponding STOP.
             pass # Already logged the event entry above


        # Remove events scheduled after the end date (no need to process them)
        scheduled_events = [e for e in scheduled_events if e[0] <= end_date]
        # Keep the loop efficient by sorting after adding new events
        scheduled_events.sort()


    # Finalize any open downtime logs at the end of simulation
    for dt in all_downtimes:
        if 'duration_seconds' not in dt: # If end_time wasn't set by a START event
            dt['end_time'] = end_date
            dt['duration_seconds'] = (dt['end_time'] - dt['start_time']).total_seconds()

    events_df = pd.DataFrame(all_events).sort_values(by=['equipment_id', 'timestamp']).reset_index(drop=True)
    downtimes_df = pd.DataFrame(all_downtimes).sort_values(by=['equipment_id', 'start_time']).reset_index(drop=True)

    # Ensure downtime durations are non-negative (can happen due to edge cases / floating point)
    downtimes_df['duration_seconds'] = downtimes_df.apply(lambda row: max(0, (row['end_time'] - row['start_time']).total_seconds()), axis=1)


    return events_df, downtimes_df


def generate_production_data(equip_df, events_df, end_date, params):
    all_production = []
    # Calculate production output based on RUNNING intervals from events
    # We'll simulate reporting production every hour the machine was running

    # Ensure events are sorted for state tracking
    events_df = events_df.sort_values(by=['equipment_id', 'timestamp'])

    for equip_id in equip_df['equipment_id'].unique():
        equip_events = events_df[events_df['equipment_id'] == equip_id].copy()
        equip_ideal_cycle = equip_df[equip_df['equipment_id'] == equip_id]['ideal_cycle_time_seconds'].iloc[0]

        # Track state and product over time intervals
        state_product_intervals = []
        current_state = 'STOPPED' # Assume stopped before first event
        current_product = None
        last_event_time = equip_events['timestamp'].min() if not equip_events.empty else PROJECT_START_DATE # Start tracking from first event or project start

        if not equip_events.empty:
             # Add interval before the very first event
             if equip_events['timestamp'].iloc[0] > PROJECT_START_DATE:
                 state_product_intervals.append({
                     'start': PROJECT_START_DATE,
                     'end': equip_events['timestamp'].iloc[0],
                     'state': 'STOPPED', # State before first event
                     'product': None
                 })
             last_event_time = equip_events['timestamp'].iloc[0]


        for i in range(len(equip_events)):
             event = equip_events.iloc[i]
             if event['timestamp'] > last_event_time:
                 state_product_intervals.append({
                     'start': last_event_time,
                     'end': event['timestamp'],
                     'state': current_state,
                     'product': current_product # Product active *during* the interval ending now
                 })

             # Update state and product based on the event *at* this timestamp
             if event['event_type'] == 'START':
                 current_state = 'RUNNING'
                 # Try to find product change info from previous STOP if available
                 # Simplified: If the previous event was a STOP, and the reason was changeover, change product
                 if i > 0:
                      prev_event = equip_events.iloc[i-1]
                      if prev_event['event_type'] == 'STOP' and 'Changeover' in prev_event['details']:
                           current_product = f'PROD_{random.randint(100, 999)}' # Assign new product after changeover

             elif event['event_type'] == 'STOP':
                 current_state = 'STOPPED'
                 # Product remains the same until the *next* START if it's a changeover, otherwise it stops producing that product
                 # For simplicity, let's say the product is tied to the RUNNING state interval.
                 # We don't need to set current_product=None here, it's handled by checking the state in the interval loop.


             last_event_time = event['timestamp']

        # Add the final interval from the last event until the end date
        if end_date > last_event_time:
             state_product_intervals.append({
                 'start': last_event_time,
                 'end': end_date,
                 'state': current_state,
                 'product': current_product # Product active in the final interval
             })

        # Iterate through the state intervals and simulate production hourly if RUNNING
        for interval in state_product_intervals:
            if interval['state'] == 'RUNNING':
                start_time = interval['start']
                end_time = interval['end']
                product_id = interval['product'] # Product active during this running interval

                current_reporting_time = start_time.replace(minute=0, second=0, microsecond=0) # Start reporting from the top of the hour within the interval

                # Find the time of the next unplanned stop for this machine (to simulate performance/quality drop)
                next_unplanned_stop_time = events_df[(events_df['equipment_id'] == equip_id) & (events_df['timestamp'] > start_time) & (events_df['event_type'] == 'STOP') & (events_df['details'].str.contains('Unplanned'))]['timestamp'].min()


                while current_reporting_time < end_time:
                    # Ensure reporting time is within the running interval
                    report_interval_start = max(current_reporting_time, start_time)
                    report_interval_end = min(current_reporting_time + timedelta(hours=1), end_time)

                    if report_interval_end > report_interval_start:
                        duration_in_report_interval = (report_interval_end - report_interval_start).total_seconds()

                        if duration_in_report_interval > 0:
                            # Simulate performance factor for this micro-interval
                            performance_factor = np.random.normal(params['PERFORMANCE_FACTOR_MEAN'], params['PERFORMANCE_FACTOR_STD'])

                            # Introduce performance drop before unplanned stops
                            if next_unplanned_stop_time is not pd.NaT:
                                time_to_stop = (next_unplanned_stop_time - report_interval_end).total_seconds() / 3600 # Time in hours
                                if 0 <= time_to_stop < params['PERFORMANCE_DROP_WINDOW_HOURS']:
                                    # Linear drop: starts dropping at window_hours, reaches max drop at stop time
                                    drop_effect = (1 - (time_to_stop / params['PERFORMANCE_DROP_WINDOW_HOURS'])) * params['PERFORMANCE_DROP_FACTOR']
                                    performance_factor = max(0.1, performance_factor - drop_effect) # Ensure performance doesn't go below a minimum

                            performance_factor = max(0.1, min(1.0, performance_factor)) # Cap performance between 0.1 and 1

                            # Calculate quantity produced in this micro-interval
                            theoretical_max_units = duration_in_report_interval / equip_ideal_cycle
                            quantity_produced = int(theoretical_max_units * performance_factor * random.uniform(0.98, 1.02)) # Add slight random noise

                            # Simulate quality rejects
                            reject_rate = params['QUALITY_REJECT_RATE_BASE']

                            # Increase reject rate before unplanned stops
                            if next_unplanned_stop_time is not pd.NaT:
                                time_to_stop = (next_unplanned_stop_time - report_interval_end).total_seconds() / 3600
                                if 0 <= time_to_stop < params['QUALITY_REJECT_WINDOW_HOURS']:
                                    increase_effect = (1 - (time_to_stop / params['QUALITY_REJECT_WINDOW_HOURS'])) * params['QUALITY_REJECT_RATE_INCREASE']
                                    reject_rate = min(0.1, reject_rate + increase_effect) # Cap reject rate

                            quantity_rejected = int(quantity_produced * reject_rate * random.uniform(0.8, 1.5)) # Add variability to reject quantity
                            quantity_rejected = min(quantity_rejected, quantity_produced) # Ensure rejections <= production

                            if quantity_produced > 0 or quantity_rejected > 0: # Only log if something happened
                                all_production.append({
                                    'timestamp': report_interval_end - timedelta(seconds=1), # Timestamp slightly before interval end
                                    'equipment_id': equip_id,
                                    'product_id': product_id,
                                    'quantity_produced': quantity_produced,
                                    'quantity_rejected': quantity_rejected,
                                    'running_duration_seconds': duration_in_report_interval # Actual running time in this reported segment
                                })

                    current_reporting_time += timedelta(hours=1) # Move to the next hour


    production_df = pd.DataFrame(all_production).sort_values(by=['equipment_id', 'timestamp']).reset_index(drop=True)

    return production_df


def generate_sensor_readings_realistic(equip_df, events_df, start_date, end_date, params):
    all_sensor_data = []
    time_delta_sensor = timedelta(seconds=params['SENSOR_READING_FREQUENCY_SECONDS'])

    # Pre-calculate ALARM/Unplanned STOP event timestamps and their causes for linking sensors
    unplanned_stops = events_df[(events_df['event_type'] == 'STOP') & (events_df['details'].str.contains('Unplanned'))].copy()
    # Need to link back to the cause determined in generate_machine_lifecycle
    # A simpler way is to find the downtime log that starts at the same time as the STOP event
    downtime_causes = { (row['equipment_id'], row['start_time']): {'category': row['downtime_category'], 'reason': row['downtime_reason']} for index, row in generate_machine_lifecycle(equip_df, start_date, end_date, params)[1].iterrows() } # Regenerate just downtimes to get the mapping

    alarm_points = []
    for index, row in unplanned_stops.iterrows():
        equip_id = row['equipment_id']
        timestamp = row['timestamp']
        cause_info = downtime_causes.get((equip_id, timestamp), {'category': 'Unknown', 'reason': 'Unknown'})
        alarm_points.append({'equipment_id': equip_id, 'timestamp': timestamp, 'category': cause_info['category'], 'reason': cause_info['reason']})

    # Iterate through time and generate sensor data
    current_time = start_date
    while current_time <= end_date:
        for i, equip in equip_df.iterrows():
            equip_id = equip['equipment_id']

            # Find the machine's state at this timestamp (simplification: assume RUNNING or STOPPED is enough)
            # Need a more efficient way than querying events every sensor reading.
            # Let's build a state lookup *before* generating sensors.
            # --- Build State Lookup (similar to production function) ---
            # (Skip re-building state lookup here, assume it's available or done internally)
            # For simplicity in this script, let's assume sensors primarily trend when RUNNING.

            for sensor_type, s_params in params['SENSOR_PROFILES'].items():
                base_value = s_params['base']
                noise_std = s_params['noise_std']
                unit = s_params['unit']
                trend_type = s_params['trend_type']
                trend_strength = s_params['trend_strength']
                related_cat = s_params['related_downtime_cat']
                related_reason = s_params['related_downtime_reason']

                value = np.random.normal(base_value, noise_std)

                # Add trend if approaching a *related* unplanned stop
                for alarm_point in alarm_points:
                    if alarm_point['equipment_id'] == equip_id and alarm_point['category'] == related_cat and alarm_point['reason'] == related_reason:
                         alarm_ts = alarm_point['timestamp']
                         window_start = alarm_ts - timedelta(hours=params['ALARM_PRE_TREND_WINDOW_HOURS'])
                         window_end = alarm_ts # Trend peaks/drops right at the alarm time

                         if window_start <= current_time < window_end:
                             time_in_window = (current_time - window_start).total_seconds()
                             window_seconds = timedelta(hours=params['ALARM_PRE_TREND_WINDOW_HOURS']).total_seconds()
                             progress = time_in_window / window_seconds # 0 at window_start, 1 at window_end

                             if trend_type == 'linear':
                                 trend_amount = progress * trend_strength
                             elif trend_type == 'exponential':
                                 # Exponential trend, grows faster closer to the end
                                 # Example: value = base + trend_strength * (e^(k*progress) - 1)
                                 # Let's use a simpler power trend for demonstration: progress^power
                                 power = 2 # Make it accelerate
                                 trend_amount = (progress ** power) * trend_strength
                             else: # Default to linear
                                 trend_amount = progress * trend_strength

                             value += trend_amount
                             # Found the relevant trend for this timestamp/sensor/machine, move to next sensor
                             break

                all_sensor_data.append({
                    'timestamp': current_time,
                    'equipment_id': equip_id,
                    'sensor_type': sensor_type,
                    'value': max(0, value), # Ensure values don't go negative if base is low
                    'unit': unit
                })

        current_time += time_delta_sensor

    return pd.DataFrame(all_sensor_data).sort_values(by=['equipment_id', 'timestamp']).reset_index(drop=True)


def generate_all_data_realistic(num_machines, start_date, end_date, params):
    equip_df = generate_equipment_data(num_machines)
    print(f"Generated {len(equip_df)} equipment records.")

    events_df, downtimes_df = generate_machine_lifecycle(equip_df, start_date, end_date, params)
    print(f"Generated {len(events_df)} event records.")
    print(f"Generated {len(downtimes_df)} downtime records.")

    # Pass events_df to production and sensor generation for linking
    production_df = generate_production_data(equip_df, events_df, end_date, params)
    print(f"Generated {len(production_df)} production records.")

    sensor_df = generate_sensor_readings_realistic(equip_df, events_df, start_date, end_date, params)
    print(f"Generated {len(sensor_df)} sensor readings.")

    return equip_df, events_df, downtimes_df, production_df, sensor_df



# --- Main Execution ---
if __name__ == "__main__":
    print("Starting realistic data simulation...")

    # Pass all parameters in a dictionary for cleaner function calls
    sim_params = {
        'AVG_MTBF_HOURS': 150,
        'AVG_MTTR_HOURS_BREAKDOWN': 4,
        'AVG_MTTR_HOURS_PROCESS': 1,
        'AVG_MTTR_HOURS_CHANGEOVER': 0.5,
        'AVG_MTTR_HOURS_MAINTENANCE': 8,
        'PROB_STOP_IS_PLANNED_MAINT': 0.05,
        'PROB_BREAKDOWN_IS_PROCESS': 0.3,
        'PROB_CHANGEOVER': 0.15,
        'DOWNTIME_REASONS': DOWNTIME_REASONS, 
        'IDEAL_CYCLE_TIME_SECONDS_MEAN': IDEAL_CYCLE_TIME_SECONDS_MEAN,
        'IDEAL_CYCLE_TIME_SECONDS_STD': IDEAL_CYCLE_TIME_SECONDS_STD,
        'PERFORMANCE_FACTOR_MEAN': PERFORMANCE_FACTOR_MEAN,
        'PERFORMANCE_FACTOR_STD': PERFORMANCE_FACTOR_STD,
        'PERFORMANCE_DROP_FACTOR': PERFORMANCE_DROP_FACTOR,
        'PERFORMANCE_DROP_WINDOW_HOURS': PERFORMANCE_DROP_WINDOW_HOURS,
        'QUALITY_REJECT_RATE_BASE': QUALITY_REJECT_RATE_BASE,
        'QUALITY_REJECT_RATE_INCREASE': QUALITY_REJECT_RATE_INCREASE,
        'QUALITY_REJECT_WINDOW_HOURS': QUALITY_REJECT_WINDOW_HOURS,

        'SENSOR_PROFILES': SENSOR_PROFILES,
        'SENSOR_READING_FREQUENCY_SECONDS': SENSOR_READING_FREQUENCY_SECONDS,
        'ALARM_PRE_TREND_WINDOW_HOURS': ALARM_PRE_TREND_WINDOW_HOURS
    }


    equipments, events, downtimes, production, sensors = generate_all_data_realistic(
        NUM_MACHINES, PROJECT_START_DATE, PROJECT_END_DATE, sim_params
    )

    # Save to CSV
    output_dir = 'simulated_industrial_data_realistic'
    import os
    os.makedirs(output_dir, exist_ok=True)

    equipments.to_csv(f'{output_dir}/equipments.csv', index=False)
    events.to_csv(f'{output_dir}/machine_events.csv', index=False)
    downtimes.to_csv(f'{output_dir}/downtime_logs.csv', index=False)
    production.to_csv(f'{output_dir}/production_output.csv', index=False)
    sensors.to_csv(f'{output_dir}/sensor_readings.csv', index=False)

    print(f"\nRealistic data simulation finished. CSV files saved in '{output_dir}' directory.")
    print("Summary:")
    print(f"- Equipments: {len(equipments)} rows")
    print(f"- Machine Events: {len(events)} rows")
    print(f"- Downtime Logs: {len(downtimes)} rows")
    print(f"- Production Output: {len(production)} rows")
    print(f"- Sensor Readings: {len(sensors)} rows")
