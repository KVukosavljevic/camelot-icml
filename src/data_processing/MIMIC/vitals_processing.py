# Processing script for vitals ED admissions.
import os

import pandas as pd

import src.data_processing.MIMIC.data_utils as utils
import src.data_processing.MIMIC.test as test

from src.data_processing.MIMIC.admissions_processing import SAVE_FD, DATA_FD

####################################################
"""

Run -admissions_processing.py first.

Processing Steps:

1. Identify patients computed from admissions_processing.py cohort.
2. Consider vitals only between intime and outtime of ED admission.
3. Consider only patients with not too much missingness.
4. Resample admissions hourly.
5. Apply Step 3 to blocked, re-sampled data.


Missing Test Functions for Admissions and vitals.
"""

# --------------------- Check admission intermediate previously processed --------------------------------------
"Check admissions processing has been run"

try:
    assert os.path.exists(SAVE_FD + "admissions_intermediate.csv")

except Exception:
    print("Current dir: ", os.getcwd())
    print("Path predicted: ", SAVE_FD + "admissions_intermediate.csv")
    raise ValueError(f"Run admissions_processing.py prior to running '{__file__}'")

# ------------------------------------ Configuration Params --------------------------------------
"Global and Argument variables for Vital sign processing"
TIME_VARS = ["intime", "outtime", "next_intime", "next_outtime", "dod"]
ID_COLUMNS = ["subject_id", "hadm_id", "stay_id"]
VITALS_NAMING_DIC = {"temperature": "TEMP", "heartrate": "HR", "resprate": "RR",
                     "o2sat": "SPO2", "sbp": "SBP", "dbp": "DBP"}

admission_min_count = 3
vitals_na_threshold = 0.6
resampling_rule = "1H"
admission_min_time_to_outtime = 1.5

# ------------------------------------ // --------------------------------------
"Load tables"

if __name__ == "__main__":
    admissions = pd.read_csv(SAVE_FD + "admissions_intermediate.csv", index_col=0, header=0, parse_dates=TIME_VARS)
    vital_signs_ed = pd.read_csv(DATA_FD + "ed/vitalsign.csv", index_col=0, header=0, low_memory=False,
                                 parse_dates=["charttime"])

    # Check correct computation of admissions
    test.admissions_processed_correctly(admissions)

    # ------------------------------------- // -------------------------------------
    "Process Vital Signs"

    # Subset to admission sub-cohort and add intime/outtime information
    vitals_S1 = utils.subsetted_by(vital_signs_ed, admissions, "stay_id")
    admissions.set_index("stay_id", inplace=True)
    vitals_S1[["intime", "outtime"]] = admissions.loc[vitals_S1.stay_id.values, ["intime", "outtime"]].values
    vitals_S1.to_csv(SAVE_FD + "vitals_S1.csv", index=True, header=True)

    # Subset Endpoints of vital observations according to ED endpoints
    vitals_S2 = vitals_S1[vitals_S1["charttime"].between(vitals_S1["intime"], vitals_S1["outtime"])]
    vitals_S2.rename(VITALS_NAMING_DIC, axis=1, inplace=True)
    vitals_S2.to_csv(SAVE_FD + "vitals_S2.csv", index=True, header=True)

    # Subset to patients with enough data
    vital_feats = list(VITALS_NAMING_DIC.values())
    vitals_S3 = utils.remove_adms_high_missingness(vitals_S2, vital_feats, "stay_id",
                                                   min_count=admission_min_count, min_frac=vitals_na_threshold)
    vitals_S3.to_csv(SAVE_FD + "vitals_S3.csv", index=True, header=True)

    # Resample admissions according to group length
    vitals_S4 = utils.compute_time_to_end(vitals_S3, id_key="stay_id", time_id="charttime", end_col="outtime")
    vitals_S4 = utils.conversion_to_block(vitals_S4, id_key="stay_id", rule=resampling_rule, time_vars=vital_feats,
                                          static_vars=["stay_id", "intime", "outtime"])
    vitals_S4.to_csv(SAVE_FD + "vitals_S4.csv", index=True, header=True)

    # Ensure blocks satisfy conditions - min counts, proportion of missingness AND time to final outcome
    vitals_S5 = utils.remove_adms_high_missingness(vitals_S4, vital_feats, "stay_id",
                                                   min_count=admission_min_count, min_frac=vitals_na_threshold)
    vitals_S5 = vitals_S5[vitals_S5["time_to_end_min"].dt.total_seconds() <= admission_min_time_to_outtime * 3600]
    vitals_S5.to_csv(SAVE_FD + "vitals_intermediate.csv", index=True, header=True)
