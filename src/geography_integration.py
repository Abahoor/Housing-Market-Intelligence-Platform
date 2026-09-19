import pandas as pd
import geopandas as gpd


YEAR = 2024


def load_geography_sources():

    df_zillow = pd.read_csv("data/processed/zillow_monthly_rent.csv",dtype={"zillow_region_id": str})

    df_redfin = pd.read_csv("data/processed/redfin_monthly_housing.csv",dtype={"redfin_region_id": str})

    df_census = pd.read_csv(f"data/processed/census_geography_income_{YEAR}.csv",dtype={"geo_id": str,"parent_metro_code": str})

    return df_zillow, df_redfin, df_census

def load_tiger_coordinates():

    df_cbsa = gpd.read_file("data/raw/tl_2024_us_cbsa.zip")

    df_metdiv = gpd.read_file("data/raw/tl_2024_us_metdiv.zip")

    cbsa_coordinates = df_cbsa[
        [
            "GEOID",
            "INTPTLAT",
            "INTPTLON"
        ]
    ].copy()

    cbsa_coordinates = cbsa_coordinates.rename(columns={
        "GEOID": "geo_id",
        "INTPTLAT": "latitude",
        "INTPTLON": "longitude"
    })

    cbsa_coordinates["geography_type"] = "metro"


    division_coordinates = df_metdiv[
        [
            "METDIVFP",
            "INTPTLAT",
            "INTPTLON"
        ]
    ].copy()

    division_coordinates = division_coordinates.rename(columns={
        "METDIVFP": "geo_id",
        "INTPTLAT": "latitude",
        "INTPTLON": "longitude"
    })

    division_coordinates["geography_type"] = "division"


    geography_coordinates = pd.concat([cbsa_coordinates,division_coordinates],ignore_index=True)

    geography_coordinates["geo_id"] = (geography_coordinates["geo_id"].astype(str))

    geography_coordinates["latitude"] = pd.to_numeric(geography_coordinates["latitude"],errors="coerce")

    geography_coordinates["longitude"] = pd.to_numeric(geography_coordinates["longitude"],errors="coerce")

    return geography_coordinates
def build_zillow_redfin_bridge(df_zillow, df_redfin):

    # One row per Zillow geography
    zillow_geo = (df_zillow[["zillow_region_id", "region_name", "state_name"]].drop_duplicates().copy())

    # One row per Redfin geography
    redfin_geo = (df_redfin[["redfin_region_id", "region_name"]].drop_duplicates().copy())

    # Create normalized names for matching
    zillow_geo["match_name"] = (zillow_geo["region_name"].str.lower().str.strip())

    redfin_geo["match_name"] = (redfin_geo["region_name"].str.lower().str.replace(" metro area", "", regex=False).str.strip())

    # Manually verified Zillow / Redfin naming differences
    name_fixes = {
        "ca±on city, co": "cañon city, co",
        "urban honolulu, hi": "honolulu, hi",
        "winston, nc": "winston-salem, nc"
    }

    zillow_geo["match_name"] = (zillow_geo["match_name"].replace(name_fixes))

    # Attach Redfin ID to each Zillow geography
    bridge = zillow_geo.merge(
        redfin_geo[
            [
                "redfin_region_id",
                "region_name",
                "match_name"
            ]
        ],
        on="match_name",
        how="left",
        validate="one_to_one",
        suffixes=("_zillow", "_redfin")
    )

    return bridge


def build_redfin_census_bridge(df_redfin, df_census):

    redfin_geo = (df_redfin[["redfin_region_id", "region_name"]].drop_duplicates().copy())

    census_geo = (
        df_census[
            [
                "geo_id",
                "geo_name",
                "geography_type",
                "parent_metro_code"
            ]
        ]
        .drop_duplicates()
        .copy()
    )

    bridge = redfin_geo.merge(
        census_geo,
        left_on="redfin_region_id",
        right_on="geo_id",
        how="inner",
        validate="one_to_one"
    )

    return bridge


def combine_geography_bridges(zillow_redfin_bridge,redfin_census_bridge):

    df_bridge = zillow_redfin_bridge.merge(
        redfin_census_bridge[
            [
                "redfin_region_id",
                "geo_id",
                "geo_name",
                "geography_type",
                "parent_metro_code"
            ]
        ],
        on="redfin_region_id",
        how="inner",
        validate="one_to_one"
    )

    df_bridge = df_bridge[
        [
            "redfin_region_id",
            "zillow_region_id",
            "geo_id",
            "region_name_redfin",
            "region_name_zillow",
            "geo_name",
            "geography_type",
            "parent_metro_code"
        ]
    ]

    df_bridge = (df_bridge.sort_values("redfin_region_id").reset_index(drop=True))

    return df_bridge


def build_geography_bridge( df_zillow,df_redfin,df_census):

    zillow_redfin_bridge = (build_zillow_redfin_bridge(df_zillow,df_redfin))

    redfin_census_bridge = (build_redfin_census_bridge(df_redfin,df_census))

    df_bridge = combine_geography_bridges(zillow_redfin_bridge,redfin_census_bridge)

    return df_bridge


def add_geo_id(df,df_bridge,source_id):

    df_integrated = df.merge(df_bridge[["geo_id", source_id]],
        on=source_id,
        how="inner",
        validate="many_to_one"
    )

    return df_integrated


def integrate_geography_data(df_redfin,df_zillow,df_bridge):

    df_redfin = add_geo_id(df_redfin,df_bridge,"redfin_region_id")

    df_zillow = add_geo_id(df_zillow,df_bridge,"zillow_region_id")

    return df_redfin, df_zillow

def add_coordinates_to_bridge(df_bridge,geography_coordinates):

    df_bridge = df_bridge.merge(
        geography_coordinates[
            [
                "geo_id",
                "geography_type",
                "latitude",
                "longitude"]],
        on=["geo_id","geography_type"],how="left",validate="one_to_one"
    )

    return df_bridge

def validate_geography_bridge(df_redfin,df_zillow,df_bridge):

    # Integrated dataset checks
    assert df_redfin["geo_id"].notna().all(), \
        "Missing geo_id in Redfin"

    assert df_zillow["geo_id"].notna().all(), \
        "Missing geo_id in Zillow"

    assert df_redfin["geo_id"].nunique() == len(df_bridge), \
        "Redfin geography count does not match bridge"

    assert df_zillow["geo_id"].nunique() == len(df_bridge), \
        "Zillow geography count does not match bridge"

    # Monthly record checks
    assert not df_redfin.duplicated(
        subset=["period_begin", "redfin_region_id"]).any(), \
        "Duplicate Redfin market-month records"

    assert not df_zillow.duplicated(
        subset=["date", "zillow_region_id"]).any(), \
        "Duplicate Zillow market-month records"

    # Geography bridge missing-value checks
    assert df_bridge["redfin_region_id"].notna().all(), \
        "Missing Redfin IDs detected"

    assert df_bridge["zillow_region_id"].notna().all(), \
        "Missing Zillow IDs detected"

    assert df_bridge["geo_id"].notna().all(), \
        "Missing Census IDs detected"

    # Geography bridge uniqueness checks
    assert df_bridge["redfin_region_id"].is_unique, \
        "Duplicate Redfin geography mappings detected"

    assert df_bridge["zillow_region_id"].is_unique, \
        "Duplicate Zillow geography mappings detected"

    assert df_bridge["geo_id"].is_unique, \
        "Duplicate Census geography mappings detected"

    # Geography type check
    assert df_bridge["geography_type"].isin(["metro", "division"]).all(), \
        "Invalid Census geography type detected"

    assert df_bridge["latitude"].notna().all(), \
        "Missing latitude detected"

    assert df_bridge["longitude"].notna().all(), \
        "Missing longitude detected"


def load_geography_bridge(df_bridge):

    df_bridge.to_csv("data/processed/geography_bridge.csv",index=False)


def load_integrated_data(df_redfin,df_zillow):

    df_redfin.to_csv("data/processed/redfin_monthly_housing_integrated.csv",index=False)

    df_zillow.to_csv("data/processed/zillow_monthly_rent_integrated.csv",index=False)


def main():

    # Load clean source data
    df_zillow, df_redfin, df_census = (load_geography_sources())
    # Load coordinates
    geography_coordinates = (load_tiger_coordinates())
    # Build standard geography bridge
    df_bridge = build_geography_bridge(df_zillow,df_redfin,df_census)
    # Add the coordinates to the bridge
    df_bridge = add_coordinates_to_bridge(df_bridge,geography_coordinates
)
    # Add standard geo_id
    df_redfin, df_zillow = (integrate_geography_data(df_redfin,df_zillow,df_bridge))

    # Validate
    validate_geography_bridge(df_redfin,df_zillow,df_bridge)

    # Load
    load_geography_bridge(df_bridge)

    load_integrated_data(df_redfin,df_zillow)

    print(f"Integration completed successfully "f"for {len(df_bridge)} geographies.")


if __name__ == "__main__":
    main()