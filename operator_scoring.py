import pandas as pd
import numpy as np

def run_operator_scoring():
    print("Loading cleaned turbine and multi-year EIA-923 datasets...")
    df_turb = pd.read_csv("turbines_cleaned.csv", low_memory=False)
    df_eia_multi = pd.read_csv("eia923_2020_2024_cleaned.csv", low_memory=False)

    # Ensure join keys are compatible
    df_turb['eia_id'] = pd.to_numeric(df_turb['eia_id'], errors='coerce')
    df_eia_multi['plant_id'] = pd.to_numeric(df_eia_multi['plant_id'], errors='coerce')

    # Calculate total turbine capacity per plant (eia_id) in MW (t_cap is in kW)
    plant_cap = df_turb.groupby('eia_id', as_index=False)['t_cap'].sum()
    plant_cap['plant_total_cap_mw'] = plant_cap['t_cap'] / 1000.0

    # Merge turbine plant capacity into multi-year EIA data
    df_multi_merged = pd.merge(
        df_eia_multi,
        plant_cap[['eia_id', 'plant_total_cap_mw']],
        left_on='plant_id',
        right_on='eia_id',
        how='left'
    )

    # Define hours in year (accounting for leap years: 2020 and 2024 have 366 days = 8,784 hours)
    hours_map = {
        2020: 366 * 24, # 8784
        2021: 365 * 24, # 8760
        2022: 365 * 24, # 8760
        2023: 365 * 24, # 8760
        2024: 366 * 24  # 8784
    }
    df_multi_merged['hours_in_year'] = df_multi_merged['year'].map(hours_map)

    # Calculate capacity factor per plant per year
    # net_gen_mwh / (total t_cap for that plant in MW * hours in that year)
    df_multi_merged['capacity_factor'] = df_multi_merged['net_gen_mwh'] / (
        df_multi_merged['plant_total_cap_mw'] * df_multi_merged['hours_in_year']
    )

    # Clean operator_name
    df_multi_merged['operator_name'] = df_multi_merged['operator_name'].astype(str).str.strip()
    valid_op_mask = df_multi_merged['operator_name'].notna() & (df_multi_merged['operator_name'] != '') & (df_multi_merged['operator_name'].str.lower() != 'nan')
    df_valid = df_multi_merged[valid_op_mask].copy()

    # Group by operator_name and year, take mean capacity factor
    op_year_cf = df_valid.groupby(['operator_name', 'year'], as_index=False)['capacity_factor'].mean()

    # Pivot so years are columns
    cf_pivot = op_year_cf.pivot(index='operator_name', columns='year', values='capacity_factor')
    cf_pivot.columns = [f"cf_{int(y)}" for y in cf_pivot.columns]
    cf_pivot = cf_pivot.reset_index()

    # Calculate capacity factor trend: difference between 2024 and 2020 CF
    if 'cf_2024' in cf_pivot.columns and 'cf_2020' in cf_pivot.columns:
        cf_pivot['capacity_factor_trend'] = cf_pivot['cf_2024'] - cf_pivot['cf_2020']
    else:
        cf_pivot['capacity_factor_trend'] = np.nan

    # 2024 capacity factor as avg_capacity_factor_2024
    if 'cf_2024' in cf_pivot.columns:
        cf_pivot['avg_capacity_factor_2024'] = cf_pivot['cf_2024']
    else:
        cf_pivot['avg_capacity_factor_2024'] = np.nan

    # Get 2024 turbine snapshot for total_cap_mw, num_states, sector_name
    df_turb_2024_merged = pd.merge(
        df_turb,
        df_eia_multi[df_eia_multi['year'] == 2024],
        left_on='eia_id',
        right_on='plant_id',
        how='inner'
    )
    df_turb_2024_merged['operator_name'] = df_turb_2024_merged['operator_name'].astype(str).str.strip()
    df_turb_2024_valid = df_turb_2024_merged[
        df_turb_2024_merged['operator_name'].notna() & 
        (df_turb_2024_merged['operator_name'] != '') & 
        (df_turb_2024_merged['operator_name'].str.lower() != 'nan')
    ].copy()

    # Aggregate 2024 snapshot metrics per operator
    op_summary_2024 = df_turb_2024_valid.groupby('operator_name').agg(
        total_cap_mw=('t_cap', lambda x: x.sum() / 1000.0),
        num_states=('t_state', 'nunique'),
        sector_name=('sector_name', lambda x: x.mode()[0] if not x.mode().empty else np.nan)
    ).reset_index()

    # Merge operator summary with CF pivot & trend
    op_scored = pd.merge(op_summary_2024, cf_pivot[['operator_name', 'avg_capacity_factor_2024', 'capacity_factor_trend']], on='operator_name', how='left')

    # Load market share from Requirement 1 output if available, or compute
    try:
        df_ms = pd.read_csv("operator_market_share_national.csv")
        # Note: operator_market_share_national.csv uses parent_operator (grouped).
        # Let's map parent_operator back or merge by operator name if exact match exists.
        # Alternatively, compute exact operator market share from 2024 snapshot:
        total_valid_cap_2024 = df_turb_2024_valid['t_cap'].sum()
        op_ms = df_turb_2024_valid.groupby('operator_name', as_index=False)['t_cap'].sum()
        op_ms['market_share_pct'] = (op_ms['t_cap'] / total_valid_cap_2024) * 100
        op_scored = pd.merge(op_scored, op_ms[['operator_name', 'market_share_pct']], on='operator_name', how='left')
    except Exception as e:
        print(f"Notice: Could not load market share CSV directly ({e}), calculating inline.")
        total_valid_cap_2024 = df_turb_2024_valid['t_cap'].sum()
        op_ms = df_turb_2024_valid.groupby('operator_name', as_index=False)['t_cap'].sum()
        op_ms['market_share_pct'] = (op_ms['t_cap'] / total_valid_cap_2024) * 100
        op_scored = pd.merge(op_scored, op_ms[['operator_name', 'market_share_pct']], on='operator_name', how='left')

    # Reorder columns as requested:
    # operator_name, total_cap_mw, num_states, sector_name, avg_capacity_factor_2024, capacity_factor_trend, market_share_pct
    final_cols = [
        'operator_name', 'total_cap_mw', 'num_states', 'sector_name', 
        'avg_capacity_factor_2024', 'capacity_factor_trend', 'market_share_pct'
    ]
    
    # Ensure all columns exist
    for c in final_cols:
        if c not in op_scored.columns:
            op_scored[c] = np.nan

    op_scored = op_scored[final_cols].sort_values(by='total_cap_mw', ascending=False).reset_index(drop=True)

    # Export to CSV
    output_csv = "operator_summary_scored.csv"
    op_scored.to_csv(output_csv, index=False)
    print(f"Saved operator summary scored table to {output_csv}")
    print("\n--- Top 10 Operators Summary Scored ---")
    print(op_scored.head(10))

if __name__ == "__main__":
    run_operator_scoring()
