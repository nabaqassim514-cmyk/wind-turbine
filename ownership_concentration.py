import pandas as pd
import numpy as np

def run_ownership_analysis():
    print("Loading cleaned turbine and EIA-923 datasets...")
    df_turb = pd.read_csv("turbines_cleaned.csv", low_memory=False)
    df_eia = pd.read_csv("eia923_2020_2024_cleaned.csv", low_memory=False)

    # Filter EIA-923 to 2024 only for single-year ownership snapshot
    df_eia_2024 = df_eia[df_eia['year'] == 2024].copy()

    # Ensure join keys are compatible
    df_turb['eia_id'] = pd.to_numeric(df_turb['eia_id'], errors='coerce')
    df_eia_2024['plant_id'] = pd.to_numeric(df_eia_2024['plant_id'], errors='coerce')

    print("Merging turbine data with 2024 EIA-923 data on eia_id = plant_id (left join)...")
    merged_2024 = pd.merge(
        df_turb,
        df_eia_2024,
        left_on='eia_id',
        right_on='plant_id',
        how='left',
        indicator=True
    )

    # 1. Coverage & Missing Operator Analysis
    total_capacity = merged_2024['t_cap'].sum()
    missing_operator_mask = merged_2024['operator_name'].isna() | (merged_2024['operator_name'].astype(str).str.strip() == '') | (merged_2024['operator_name'].astype(str).str.lower() == 'nan')
    missing_op_capacity = merged_2024.loc[missing_operator_mask, 't_cap'].sum()
    missing_op_pct = (missing_op_capacity / total_capacity) * 100 if total_capacity > 0 else 0

    print(f"\n--- Coverage Analysis ---")
    print(f"Total Turbine Capacity: {total_capacity:,.2f} kW")
    print(f"Capacity with no matched operator: {missing_op_capacity:,.2f} kW ({missing_op_pct:.2f}%)")

    # Filter out missing operators for concentration analysis
    df_valid = merged_2024[~missing_operator_mask].copy()
    valid_capacity = df_valid['t_cap'].sum()

    # 2. National Ungrouped Market Share & HHI
    op_national = df_valid.groupby('operator_name', as_index=False)['t_cap'].sum()
    op_national['market_share_pct'] = (op_national['t_cap'] / valid_capacity) * 100
    op_national = op_national.sort_values(by='t_cap', ascending=False).reset_index(drop=True)

    national_hhi_ungrouped = (op_national['market_share_pct'] ** 2).sum()
    top5_share_ungrouped = op_national.head(5)['market_share_pct'].sum()
    top10_share_ungrouped = op_national.head(10)['market_share_pct'].sum()

    print(f"\n--- National Concentration (Ungrouped) ---")
    print(f"Ungrouped National HHI: {national_hhi_ungrouped:.2f}")
    print(f"Top 5 Operators Market Share: {top5_share_ungrouped:.2f}%")
    print(f"Top 10 Operators Market Share: {top10_share_ungrouped:.2f}%")

    # 3. Parent Company Grouping Dictionary
    # Map common subsidiaries / spelling variants to unified parent names
    parent_mapping = {
        'NextEra Energy Resources': 'NextEra Energy',
        'NextEra Energy Resources, LLC': 'NextEra Energy',
        'NextEra Energy Operating Services': 'NextEra Energy',
        'NextEra': 'NextEra Energy',
        'Berkshire Hathaway Energy': 'Berkshire Hathaway',
        'BHE Renewables': 'Berkshire Hathaway',
        'MidAmerican Energy Co': 'Berkshire Hathaway',
        'PacifiCorp': 'Berkshire Hathaway',
        'Invenergy LLC': 'Invenergy',
        'Invenergy Services LLC': 'Invenergy',
        'Pattern Energy Group': 'Pattern Energy',
        'Pattern Energy': 'Pattern Energy',
        'EDF Renewables': 'EDF Renewables',
        'EDF Renewable Energy': 'EDF Renewables',
        'Apex Clean Energy': 'Apex Clean Energy',
        'Apex Clean Energy Management': 'Apex Clean Energy',
        'AES Corporation': 'AES',
        'AES Wind Generation': 'AES',
        'Ormat Technologies': 'Ormat',
        'Enel Green Power': 'Enel',
        'Enel Green Power North America': 'Enel',
        'Avangrid Renewables': 'Avangrid',
        'Avangrid': 'Avangrid',
        'Iberdrola': 'Avangrid',
        'Duke Energy': 'Duke Energy',
        'Duke Energy Renewables': 'Duke Energy',
        'Southern Company': 'Southern Company',
        'Southern Power': 'Southern Company',
        'Xcel Energy': 'Xcel Energy',
        'Ørsted': 'Ørsted',
        'Orsted': 'Ørsted',
        'Clearway Energy': 'Clearway Energy',
        'Clearway Energy Group': 'Clearway Energy',
        'RWE Clean Energy': 'RWE',
        'RWE Renewables': 'RWE',
        'E.ON Climate & Renewables': 'RWE'
    }

    def map_parent(op_name):
        if pd.isna(op_name):
            return np.nan
        op_clean = str(op_name).strip()
        # Check direct match or case-insensitive match
        for k, v in parent_mapping.items():
            if k.lower() in op_clean.lower():
                return v
        return op_clean

    df_valid['operator_grouped'] = df_valid['operator_name'].apply(map_parent)

    # 4. National Grouped Market Share & HHI
    op_grouped = df_valid.groupby('operator_grouped', as_index=False)['t_cap'].sum()
    op_grouped['market_share_pct'] = (op_grouped['t_cap'] / valid_capacity) * 100
    op_grouped = op_grouped.sort_values(by='t_cap', ascending=False).reset_index(drop=True)

    national_hhi_grouped = (op_grouped['market_share_pct'] ** 2).sum()
    top5_share_grouped = op_grouped.head(5)['market_share_pct'].sum()
    top10_share_grouped = op_grouped.head(10)['market_share_pct'].sum()

    print(f"\n--- National Concentration (Grouped Parents) ---")
    print(f"Grouped National HHI: {national_hhi_grouped:.2f}")
    print(f"Top 5 Parents Market Share: {top5_share_grouped:.2f}%")
    print(f"Top 10 Parents Market Share: {top10_share_grouped:.2f}%")

    # Save operator-level market share (national)
    op_national_export = op_grouped.rename(columns={
        'operator_grouped': 'parent_operator',
        't_cap': 'total_capacity_kw',
        'market_share_pct': 'market_share_percent'
    })
    operator_csv = "operator_market_share_national.csv"
    op_national_export.to_csv(operator_csv, index=False)
    print(f"Saved national operator market shares to {operator_csv}")

    # 5. State-Level HHI Summary
    # Group by t_state and operator_grouped
    state_op = df_valid.groupby(['t_state', 'operator_grouped'], as_index=False)['t_cap'].sum()
    
    # Calculate state total capacity for market share within each state
    state_totals = state_op.groupby('t_state', as_index=False)['t_cap'].sum().rename(columns={'t_cap': 'state_total_cap'})
    state_op = pd.merge(state_op, state_totals, on='t_state')
    state_op['state_market_share_pct'] = (state_op['t_cap'] / state_op['state_total_cap']) * 100

    # Calculate HHI per state
    state_hhi = state_op.groupby('t_state').apply(
        lambda g: pd.Series({
            'state_hhi': (g['state_market_share_pct'] ** 2).sum(),
            'total_state_capacity_kw': g['state_total_cap'].iloc[0],
            'unique_operators': g['operator_grouped'].nunique(),
            'top_operator': g.loc[g['t_cap'].idxmax(), 'operator_grouped'] if not g.empty else np.nan,
            'top_operator_share_pct': g['state_market_share_pct'].max() if not g.empty else 0
        })
    ).reset_index()

    state_hhi = state_hhi.sort_values(by='state_hhi', ascending=False).reset_index(drop=True)
    state_csv = "state_hhi_summary.csv"
    state_hhi.to_csv(state_csv, index=False)
    print(f"Saved state-level HHI summary to {state_csv}")

    # 6. Tableau Turbine Mapping Table
    # Turbine-level table with t_state, operator_name, operator_grouped, t_cap, xlong, ylat
    tableau_df = merged_2024[['t_state', 'operator_name', 't_cap', 'xlong', 'ylat']].copy()
    tableau_df['operator_grouped'] = tableau_df['operator_name'].apply(map_parent)
    tableau_csv = "tableau_turbine_mapping.csv"
    tableau_df.to_csv(tableau_csv, index=False)
    print(f"Saved Tableau turbine mapping table to {tableau_csv}")

    print("\nOwnership concentration analysis completed successfully!")

if __name__ == "__main__":
    run_ownership_analysis()
