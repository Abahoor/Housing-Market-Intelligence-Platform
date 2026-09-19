CREATE DATABASE IF NOT EXISTS housing_market_intelligence_platform;

USE housing_market_intelligence_platform;

SHOW GLOBAL VARIABLES LIKE 'local_infile';

SET SQL_SAFE_UPDATES = 0;

SET GLOBAL local_infile = ON;

create table geography_bridge(
geo_id CHAR(5) primary key,

redfin_region_id CHAR(5) UNIQUE,
zillow_region_id VARCHAR(10) UNIQUE,

geo_name VARCHAR(150),
geography_type VARCHAR(10),
parent_metro_code CHAR(5)
);
ALTER TABLE geography_bridge
MODIFY COLUMN latitude DECIMAL(10,7),
MODIFY COLUMN longitude DECIMAL(10,7);
CREATE TABLE geography_bridge_updated (
    redfin_region_id CHAR(5),
    zillow_region_id VARCHAR(10),
    geo_id CHAR(5),
    region_name_redfin VARCHAR(150),
    region_name_zillow VARCHAR(150),
    geo_name VARCHAR(150),
    geography_type VARCHAR(10),
    parent_metro_code CHAR(5),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6)
);

DROP TABLE geography_coordinates_stage;
CREATE TABLE geography_coordinates_stage (
    geo_id CHAR(5) PRIMARY KEY,
    latitude DECIMAL(10,7),
    longitude DECIMAL(10,7)
);

create table census_income(
geo_id CHAR (5),     -- PK part 1 / FK
income_year YEAR,    -- PK part 2
median_household_income INT,
primary key(geo_id,income_year),

foreign key(geo_id)
	references geography_bridge(geo_id)
	
);
TRUNCATE TABLE redfin_housing_monthly;
create table redfin_housing_monthly(
geo_id CHAR(5),            -- PK part 1 / FK
period_begin DATE,         -- PK part 2
redfin_region_id CHAR(5),

median_sale_price decimal(12,2),
median_sale_price_per_sqft decimal(10,2),

homes_sold INT,
inventory INT,
median_days_on_market INT,
months_of_supply decimal(6,2),
percent_off_market_two_weeks DECIMAL(6,4),
primary key(geo_id,period_begin),

foreign key(geo_id)
	references geography_bridge(geo_id)

);
ALTER TABLE redfin_housing_monthly
MODIFY COLUMN percent_off_market_two_weeks DECIMAL(7,4);


create table zillow_rent_monthly(
geo_id CHAR(5),                  -- PK part 1 / FK
rent_date DATE,                  -- PK part 2
zillow_region_id varchar(10),
rent DECIMAL(8,2),
primary key(geo_id,rent_date),
foreign key(geo_id)
	references geography_bridge(geo_id)
);

create table mortgage_rates_monthly(
month  DATE primary key,             -- PK
mortgage_rate decimal(5,2)
);


select count(*) 
from redfin_housing_monthly;

SELECT
    SUM(inventory IS NULL) AS missing_inventory,
    SUM(median_days_on_market IS NULL) AS missing_days_on_market,
    SUM(months_of_supply IS NULL) AS missing_months_of_supply,
    SUM(percent_off_market_two_weeks IS NULL) AS missing_percent
FROM redfin_housing_monthly;


UPDATE redfin_housing_monthly
SET percent_off_market_two_weeks = NULL
WHERE percent_off_market_two_weeks < 0;

SET SQL_SAFE_UPDATES = 1;

SELECT COUNT(*) AS negative_percent_values
FROM redfin_housing_monthly
WHERE percent_off_market_two_weeks < 0;

SELECT COUNT(*) FROM geography_bridge;
SELECT COUNT(*) FROM census_income;
SELECT COUNT(*) FROM redfin_housing_monthly;
SELECT COUNT(*) FROM zillow_rent_monthly;
SELECT COUNT(*) FROM mortgage_rates_monthly;

SELECT COUNT(*)
FROM zillow_rent_monthly r
LEFT JOIN geography_bridge g
    ON r.geo_id = g.geo_id
WHERE g.geo_id IS NULL;
    
SELECT
    g.geo_name,

    c.income_year,
    c.median_household_income,

    r.period_begin,
    r.median_sale_price,

    z.rent,

    f.mortgage_rate
FROM redfin_housing_monthly r
JOIN geography_bridge g
-- ON is a condition that must be true for two rows to match during a JOIN.
    ON r.geo_id = g.geo_id
JOIN census_income c
    ON r.geo_id = c.geo_id
    AND YEAR(r.period_begin) = c.income_year
JOIN zillow_rent_monthly z
    ON r.geo_id = z.geo_id
    AND r.period_begin = z.rent_date
JOIN mortgage_rates_monthly f
    ON r.period_begin = f.month;
    
CREATE OR REPLACE VIEW market_affordability_base AS

SELECT
    r.geo_id,
    g.geo_name,
    g.geography_type,
    g.latitude,
    g.longitude,

    c.income_year,
    m.month AS analysis_month,

    c.median_household_income,
    r.median_sale_price,
    z.rent,
    m.mortgage_rate

FROM redfin_housing_monthly r

JOIN geography_bridge g
    ON r.geo_id = g.geo_id

JOIN census_income c
    ON c.geo_id = r.geo_id
    AND c.income_year = YEAR(r.period_begin)

JOIN zillow_rent_monthly z
    ON z.geo_id = r.geo_id
    AND r.period_begin = z.rent_date

JOIN mortgage_rates_monthly m
    ON m.month = r.period_begin;
    
SELECT *
FROM market_affordability_base
LIMIT 10;

SELECT COUNT(*)
FROM market_affordability_base;

SELECT *
FROM market_affordability_base;

CREATE OR REPLACE VIEW market_map_2024 AS

WITH affordability AS (
    SELECT
        geo_id,
        geo_name,
        geography_type,
        latitude,
        longitude,

        MAX(median_household_income)AS median_household_income,
        ROUND(AVG(median_sale_price), 2)AS avg_sale_price,
        ROUND(AVG(rent), 2)AS avg_rent

    FROM market_affordability_base

    GROUP BY
        geo_id,
        geo_name,
        geography_type,
        latitude,
        longitude
),

redfin_activity AS (
    SELECT
        geo_id,
        ROUND(AVG(homes_sold), 2)AS avg_monthly_homes_sold,
        ROUND(SUM(homes_sold), 2)AS total_homes_sold_2024,
        ROUND(AVG(inventory), 2)AS avg_inventory,
        ROUND(AVG(median_days_on_market), 2)vg_days_on_market,
        ROUND(AVG(months_of_supply), 2)vg_months_of_supply

    FROM redfin_housing_monthly

    WHERE period_begin >= '2024-01-01'
      AND period_begin <  '2025-01-01'

    GROUP BY geo_id
)

SELECT
    a.geo_id,
    a.geo_name,
    a.geography_type,
    a.latitude,
    a.longitude,
    a.median_household_income,
    a.avg_sale_price,
    a.avg_rent,
    r.avg_monthly_homes_sold,
    r.total_homes_sold_2024,
    r.avg_inventory,
    r.avg_days_on_market,
    r.avg_months_of_supply

FROM affordability AS a

LEFT JOIN redfin_activity AS r
    ON a.geo_id = r.geo_id;
    
select *
from market_map_2024;



-- 1.Which 10 housing markets had the highest and lowest average median sale prices in 2024?
create view vw_2024_sale_price_extremes as
(
select
	'Highest' AS price_group,
	geo_id,
    geo_name,
	avg_sale_price
from market_map_2024
where avg_sale_price is not null
order by avg_sale_price desc
limit 10
)
UNION ALL
(
    SELECT
        'Lowest' AS price_group,
        geo_id,
        geo_name,
        avg_sale_price
    FROM market_map_2024
    WHERE avg_sale_price IS NOT NULL
    ORDER BY avg_sale_price ASC
    LIMIT 10
);

	
-- 2.Which 10 housing markets had the highest and lowest average rents in 2024?
create view vw_2024_rent_extremes as
(
	select
		'Highest' AS rent_group,
		geo_id,
		geo_name,
		avg_rent
	from market_map_2024
    where avg_rent is not null
    order by avg_rent desc
    limit 10
)
UNION ALL
(
	select
		'Lowest' AS rent_group,
		geo_id,
		geo_name,
		avg_rent
	from market_map_2024
    where avg_rent is not null
    order by avg_rent ASC
    limit 10
);
-- 3.Which markets have the highest and lowest home-price-to-income ratios?
create view vw_2024_price_income_ratio_extremes as
(
    SELECT
        'Highest' AS ratio_group,
        geo_id,
        geo_name,
        ROUND(avg_sale_price / median_household_income, 2) AS home_price_to_income_ratio
    FROM market_map_2024
    WHERE avg_sale_price IS NOT NULL
      AND median_household_income IS NOT NULL
      AND median_household_income > 0
    ORDER BY home_price_to_income_ratio DESC
    LIMIT 10
)

UNION ALL

(
    SELECT
        'Lowest' AS ratio_group,
        geo_id,
        geo_name,
        ROUND(avg_sale_price / median_household_income, 2) AS home_price_to_income_ratio
    FROM market_map_2024
    WHERE avg_sale_price IS NOT NULL
      AND median_household_income IS NOT NULL
      AND median_household_income > 0
    ORDER BY home_price_to_income_ratio ASC
    LIMIT 10
);
-- 4.In which markets is renting cheaper or more expensive than an estimated monthly mortgage payment?
create or replace view vw_2024_rent_vs_est_mortgage as
WITH mortgage_values AS (
    SELECT
        AVG(mortgage_rate) AS avg_annual_rate,
        AVG(mortgage_rate) / 100 / 12 AS monthly_rate
    FROM mortgage_rates_monthly
    WHERE month >= '2024-01-01'
  AND month <  '2025-01-01'
),

market_comparison AS (
    SELECT
        m.geo_id,
        m.geo_name,
        m.avg_sale_price,
        m.avg_rent,
        r.avg_annual_rate,

        ROUND(
            (m.avg_sale_price * 0.80) *
            (r.monthly_rate * POWER(1 + r.monthly_rate, 360)) /(POWER(1 + r.monthly_rate, 360) - 1),2
        ) AS estimated_monthly_mortgage

    FROM market_map_2024 AS m
    CROSS JOIN mortgage_values AS r

    WHERE m.avg_sale_price IS NOT NULL
      AND m.avg_rent IS NOT NULL
)

SELECT
    geo_id,
    geo_name,
    avg_sale_price,
    avg_rent,
    ROUND(avg_annual_rate, 2) AS mortgage_rate,
    estimated_monthly_mortgage,

    ROUND(estimated_monthly_mortgage - avg_rent,2) AS mortgage_minus_rent,

    CASE
        WHEN avg_rent < estimated_monthly_mortgage
            THEN 'Renting is cheaper'
        WHEN avg_rent > estimated_monthly_mortgage
            THEN 'Renting is more expensive'
        ELSE 'Same monthly cost'
    END AS affordability_result

FROM market_comparison
ORDER BY mortgage_minus_rent DESC;


-- 5.What does the average housing market in the dataset look like in 2024?
create or replace view vw_2024_average_market_profile as
  WITH avg_mortgage_rate_2024 AS (
    SELECT
        AVG(mortgage_rate) AS avg_mortgage_rate
    FROM mortgage_rates_monthly
    WHERE month >= '2024-01-01'
  AND month <  '2025-01-01'
)

SELECT
    'Average 2024 Housing Market' AS market_summary,
    COUNT(*) AS markets_included,
    ROUND(AVG(m.avg_sale_price), 2) AS avg_sale_price,
    ROUND(AVG(m.avg_rent), 2) AS avg_rent,
    ROUND(AVG(m.median_household_income), 2)AS avg_median_household_income,
    ROUND(AVG(m.avg_monthly_homes_sold), 2)AS avg_monthly_homes_sold,
    ROUND(AVG(m.avg_inventory), 2) AS avg_inventory,
    ROUND(AVG(m.avg_days_on_market), 2) AS avg_days_on_market,
    ROUND(AVG(m.avg_months_of_supply), 2) AS avg_months_of_supply,
    ROUND(MAX(r.avg_mortgage_rate), 2) AS avg_mortgage_rate

FROM market_map_2024 AS m
CROSS JOIN avg_mortgage_rate_2024 AS r

WHERE m.avg_sale_price IS NOT NULL
  AND m.avg_rent IS NOT NULL
  AND m.median_household_income IS NOT NULL;

-- 6.Which housing markets are the most and least affordable based on household income and home prices?
create view vw_2024_mortgage_income_burden_extremes as
WITH mortgage_rate_2024 AS (
    SELECT
        AVG(mortgage_rate) / 100 / 12 AS monthly_rate
    FROM mortgage_rates_monthly
    WHERE month >= '2024-01-01'
      AND month<  '2025-01-01'
),

market_payments AS (
    SELECT
        m.geo_id,
        m.geo_name,
        m.avg_sale_price,
        m.median_household_income,

        (m.avg_sale_price * 0.80) *
        (r.monthly_rate * POWER(1 + r.monthly_rate, 360)) /(POWER(1 + r.monthly_rate, 360) - 1) AS monthly_mortgage_payment

    FROM market_map_2024 AS m
    CROSS JOIN mortgage_rate_2024 AS r
    WHERE m.avg_sale_price > 0
      AND m.median_household_income > 0
      AND r.monthly_rate > 0
),

market_affordability AS (
    SELECT
        geo_id,
        geo_name,
        avg_sale_price,
        median_household_income,
        ROUND(monthly_mortgage_payment, 2)AS estimated_monthly_mortgage,

        100 * monthly_mortgage_payment /(median_household_income / 12) AS mortgage_income_pct

    FROM market_payments
)

(
    SELECT
        'Most affordable' AS affordability_group,
        geo_id,
        geo_name,
        avg_sale_price,
        median_household_income,
        estimated_monthly_mortgage,
        ROUND(mortgage_income_pct, 2) AS mortgage_income_pct
    FROM market_affordability
    ORDER BY mortgage_income_pct ASC
    LIMIT 10
)
UNION ALL
(
    SELECT
        'Least affordable' AS affordability_group,
        geo_id,
        geo_name,
        avg_sale_price,
        median_household_income,
        estimated_monthly_mortgage,
        ROUND(mortgage_income_pct, 2) AS mortgage_income_pct
    FROM market_affordability
    ORDER BY mortgage_income_pct DESC
    LIMIT 10
);
-- 7.Which markets have the highest and lowest rent-to-income ratios?
create view vw_2024_rent_income_ratio_extremes as
(
    SELECT
        'Lowest rent-to-income' AS ratio_group,
        geo_id,
        geo_name,
        avg_rent,
        median_household_income,
        -- pct is short for percent.
        ROUND(avg_rent * 12 / median_household_income * 100, 2) AS rent_to_income_pct
    FROM market_map_2024
    WHERE avg_rent > 0
      AND median_household_income > 0
    ORDER BY avg_rent * 12 / median_household_income ASC
    LIMIT 10
)

UNION ALL

(
    SELECT
        'Highest rent-to-income' AS ratio_group,
        geo_id,
        geo_name,
        avg_rent,
        median_household_income,
		-- pct is short for percent.
        ROUND(avg_rent * 12 / median_household_income * 100, 2) AS rent_to_income_pct
    FROM market_map_2024
    WHERE avg_rent > 0
      AND median_household_income > 0
    ORDER BY avg_rent * 12 / median_household_income DESC
    LIMIT 10
);
-- 8.Where is the gap between estimated mortgage payments and rent the largest?
create view vw_2024_est_mortgage_rent_gap_extremes as
WITH mortgage_rate_2024 AS (
    SELECT
        AVG(mortgage_rate) / 100 / 12 AS monthly_rate
    FROM mortgage_rates_monthly
    WHERE month >= '2024-01-01'
      AND month <  '2025-01-01'
),

market_payments AS (
    SELECT
        m.geo_id,
        m.geo_name,
        m.avg_sale_price,
        m.avg_rent,

        (m.avg_sale_price * 0.80) *(r.monthly_rate * POWER(1 + r.monthly_rate, 360)) /(POWER(1 + r.monthly_rate, 360) - 1) AS monthly_mortgage

    FROM market_map_2024 AS m
    CROSS JOIN mortgage_rate_2024 AS r
    WHERE m.avg_sale_price > 0
      AND m.avg_rent > 0
      AND r.monthly_rate > 0
),

market_gaps AS (
    SELECT
        geo_id,
        geo_name,
        avg_rent,
        ROUND(monthly_mortgage, 2) AS estimated_monthly_mortgage,
        monthly_mortgage - avg_rent AS mortgage_minus_rent
    FROM market_payments
)

(
    SELECT
        'Mortgage costs more' AS gap_direction,
        geo_id,
        geo_name,
        avg_rent,
        estimated_monthly_mortgage,
        ROUND(mortgage_minus_rent, 2) AS monthly_gap
    FROM market_gaps
    WHERE mortgage_minus_rent > 0
    ORDER BY mortgage_minus_rent DESC
    LIMIT 10
)

UNION ALL

(
    SELECT
        'Rent costs more' AS gap_direction,
        geo_id,
        geo_name,
        avg_rent,
        estimated_monthly_mortgage,
        ROUND(mortgage_minus_rent, 2) AS monthly_gap
    FROM market_gaps
    WHERE mortgage_minus_rent < 0
    ORDER BY mortgage_minus_rent ASC
    LIMIT 10
);

-- 9.How strongly are household income, home prices, and rent related across markets?
-- look at three relationships: income ↔ home price, income ↔ rent, and home price ↔ rent.
create view vw_2024_market_correlations as
(
SELECT
	'Income vs price' AS relationship,
    COUNT(*) AS markets_included,

    ROUND(
        (
            AVG(median_household_income * avg_sale_price)- AVG(median_household_income) * AVG(avg_sale_price)
            )/(STDDEV_POP(median_household_income)* STDDEV_POP(avg_sale_price)),3) AS correlation

FROM market_map_2024

WHERE median_household_income > 0
  AND avg_sale_price > 0
)
union all
(
SELECT
	'Income vs rent' AS relationship,
    COUNT(*) AS markets_included,

    ROUND(
        (
            AVG(median_household_income * avg_rent)- AVG(median_household_income) * AVG(avg_rent)
            )/(STDDEV_POP(median_household_income)* STDDEV_POP(avg_rent)),3) AS income_rent_correlation

FROM market_map_2024

WHERE median_household_income > 0
  AND avg_rent > 0
)
union all
(
SELECT
	'rent vs price' AS relationship,
    COUNT(*) AS markets_included,

    ROUND(
        (
            AVG(avg_sale_price * avg_rent)
            - AVG(avg_sale_price) * AVG(avg_rent))/(STDDEV_POP(avg_sale_price)* STDDEV_POP(avg_rent)),3
    ) AS price_rent_correlation

FROM market_map_2024

WHERE avg_sale_price > 0
  AND avg_rent > 0
);
-- 10.Which markets appear hottest or coolest based on inventory, months of supply, days on market, and homes sold?
create view vw_2024_supply_heat_candidates as
(
SELECT
	'Hot candidate' AS market_group,
    geo_id,
    geo_name,
    avg_inventory,
    avg_months_of_supply,
    avg_days_on_market,
    avg_monthly_homes_sold
FROM market_map_2024
WHERE avg_months_of_supply > 0
  AND avg_days_on_market IS NOT NULL
  AND avg_monthly_homes_sold > 0
  AND avg_inventory IS NOT NULL
ORDER BY avg_months_of_supply asc
LIMIT 10
)
UNION ALL
(
SELECT
	'Cool candidate' AS market_group,
    geo_id,
    geo_name,
    avg_inventory,
    avg_months_of_supply,
    avg_days_on_market,
    avg_monthly_homes_sold
FROM market_map_2024
WHERE avg_months_of_supply > 0
  AND avg_days_on_market IS NOT NULL
  AND avg_monthly_homes_sold > 0
  AND avg_inventory IS NOT NULL
ORDER BY avg_months_of_supply desc
LIMIT 10
);

