# Data Dictionary: US Wind Turbine & EIA-923 Analysis Pipeline

This document provides a comprehensive data dictionary for all datasets generated and processed across the US wind turbine and EIA-923 ownership concentration data pipeline (`2020–2024`).

---

## 1. Cleaned Turbine Dataset (`turbines_cleaned.csv` / `.xlsx`)
Source: `wind_turbine_20220114.csv` (USGS / US Wind Turbine Database)  
Description: Cleaned turbine-level inventory with sentinel values (`-9999`) replaced by `NaN`.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `case_id` | Integer / String | Unique USGS turbine record identifier. |
| `eia_id` | Float / Integer | EIA Plant ID linking turbines to EIA-923 generation data (`NaN` if unmatched). |
| `t_state` | String | Two-letter state postal abbreviation where the turbine is located. |
| `t_county` | String | County name where the turbine is located. |
| `p_name` | String | Project / wind farm name. |
| `p_year` | Integer | Project commercial operation start year. |
| `p_tnum` | Integer | Total number of turbines in the project. |
| `p_cap` | Float | Project capacity in kilowatts (kW). |
| `t_manu` | String | Turbine manufacturer (e.g., Vestas, GE, Siemens Gamesa). |
| `t_model` | String | Turbine model designation. |
| `t_cap` | Float | Individual turbine capacity in kilowatts (kW) (`-9999` missing values converted to `NaN`). |
| `t_hh` | Float | Turbine hub height in meters. |
| `t_rd` | Float | Rotor diameter in meters. |
| `t_ttlh` | Float | Total tip height (hub height + rotor radius) in meters. |
| `retrofit` | Integer / Boolean | Indicator for whether the turbine has been retrofitted (`1` = Yes, `0` = No). |
| `retrofit_year` | Float | Year of turbine retrofit (if applicable). |
| `t_conf_atr` | Integer | Confidence score for attribute attribution. |
| `t_conf_loc` | Integer | Confidence score for spatial location accuracy. |
| `xlong` | Float | Turbine longitude coordinate in decimal degrees. |
| `ylat` | Float | Turbine latitude coordinate in decimal degrees. |

---

## 2. Multi-Year EIA-923 Generation Data (`eia923_2020_2024_cleaned.csv` / `.xlsx`)
Source: EIA-923 Schedules 2/3/4/5 (`2020–2024`)  
Description: Combined multi-year plant-level generation data filtered to wind prime movers (`WT`), with normalized column names and coerced numeric generation values.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `plant_id` | Integer | EIA plant identification number (primary join key with turbine `eia_id`). |
| `plant_name` | String | Name of the electric generation plant. |
| `operator_name` | String | Name of the operating company / utility. |
| `operator_id` | Integer | EIA operator identification number. |
| `plant_state` | String | State where the plant is located. |
| `census_region` | String | US Census region classification. |
| `nerc_region` | String | NERC electricity reliability region. |
| `sector_name` | String | Economic sector classification (e.g., `Electric Utility`, `NAICS-22 Non-Cogen`). |
| `naics_code` | Integer | North American Industry Classification System (NAICS) code. |
| `prime_mover` | String | Energy source prime mover code (`WT` for wind turbine). |
| `net_gen_mwh` | Float | Net electricity generation in Megawatthours (MWh) (`.` and missing values coerced to `NaN`). |
| `year` | Integer | Reporting year (`2020`, `2021`, `2022`, `2023`, or `2024`). |

---

## 3. National Ownership Concentration (`operator_market_share_national.csv`)
Description: National operator-level market shares and capacity totals for `2024` (with parent company subsidiary groupings).

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `parent_operator` | String | Unified parent company name (grouped from operator subsidiaries). |
| `total_capacity_kw` | Float | Total attributable wind turbine capacity in kilowatts (kW). |
| `market_share_percent` | Float | Percentage share of total national attributable wind capacity. |

---

## 4. State-Level Concentration Summary (`state_hhi_summary.csv`)
Description: State-by-state wind ownership concentration and Herfindahl-Hirschman Index (HHI) for `2024`.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `t_state` | String | State postal abbreviation. |
| `state_hhi` | Float | Herfindahl-Hirschman Index for the state ($\sum (\text{state market share \%})^2$). |
| `total_state_capacity_kw` | Float | Total installed wind turbine capacity in the state (kW). |
| `unique_operators` | Integer | Number of distinct active operators in the state. |
| `top_operator` | String | Largest operator in the state by installed capacity. |
| `top_operator_share_pct` | Float | Market share percentage of the top operator within that state. |

---

## 5. Tableau GIS Mapping Table (`tableau_turbine_mapping.csv`)
Description: Turbine-level spatial mapping table optimized for Tableau visualization.

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `t_state` | String | State abbreviation. |
| `operator_name` | String | Raw operator name. |
| `operator_grouped` | String | Grouped parent company name. |
| `t_cap` | Float | Individual turbine capacity (kW). |
| `xlong` | Float | Longitude coordinate (decimal degrees). |
| `ylat` | Float | Latitude coordinate (decimal degrees). |

---

## 6. Operator Scoring & Acquirability (`operator_summary_scored.csv`)
Description: Multi-year operator scoring table combining capacity, footprint, sector classification, capacity factor trends, and market share (`2020–2024`).

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `operator_name` | String | Operator name. |
| `total_cap_mw` | Float | Total installed capacity in Megawatts (MW) (`2024` snapshot). |
| `num_states` | Integer | Number of distinct states the operator operates in. |
| `sector_name` | String | Primary EIA sector classification (e.g., `NAICS-22 Non-Cogen`). |
| `avg_capacity_factor_2024` | Float | Average capacity factor in `2024`. |
| `capacity_factor_trend` | Float | Capacity factor trend ($CF_{2024} - CF_{2020}$; positive = improving). |
| `market_share_pct` | Float | National market share percentage (`2024`). |

---

## 7. Acquisition Shortlist (`operator_shortlist.csv`)
Description: Top 10 shortlisted mid-size Independent Power Producers (IPPs) meeting acquisition criteria (sector = IPP, capacity = 500–5,000 MW, trend $\ge 0$).

| Column Name | Data Type | Description |
| :--- | :--- | :--- |
| `operator_name` | String | Shortlisted operator name. |
| `total_cap_mw` | Float | Total installed capacity (MW). |
| `num_states` | Integer | Number of operational states. |
| `sector_name` | String | EIA sector classification. |
| `avg_capacity_factor_2024` | Float | `2024` average capacity factor. |
| `capacity_factor_trend` | Float | 5-year capacity factor trend. |
| `market_share_pct` | Float | National market share percentage. |
| `rationale` | String | Analytical acquisition rationale summarizing operational scale, footprint, and performance stability. |
