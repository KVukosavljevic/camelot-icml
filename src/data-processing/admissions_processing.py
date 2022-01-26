# File description

import os
import pandas as pd

import src as utils

####################################################
"""
ROW SUBSETTING COULD BE IMPROVED SOMEHOW

DOUBLE CHECK ON ELECTIVE VS SURGICAL ADMISSIONS
"""

# ------------------------------------ // --------------------------------------
"General Variables for Processing"
DATA_FD = "data/MIMIC/"
SAVE_FD = DATA_FD + "interim/"
ID_COLUMNS = ["subject_id", "hadm_id", "stay_id"]
TIME_COLUMNS = ["intime", "outtime", "charttime", "deathtime"]
WARDS_TO_REMOVE = ["Unknown", "Emergency Department", "Obstetrics Postpartum",
                   "Obstetrics Antepartum", "Obstetrics (Postpartum & Antepartum)",
                   "Psychiatry", "Labor & Delivery", "Observation", "Emergency Department Observation"]
AGE_LOWERBOUND = 18
PATIENT_INFO = ["gender", "anchor_age", "anchor_year", "dod"]
NEXT_TRANSFER_INFO = ["transfer_id", "eventtype", "careunit", "intime", "outtime"]

if not os.path.exists(SAVE_FD):
    os.makedirs(SAVE_FD)

# ------------------------------------- // -------------------------------------
if __name__ == "__main__":
    "Load Tables"

    # Hospital Core
    patients_core = pd.read_csv(DATA_FD + "core/patients.csv", index_col=None, header=0, low_memory=False)
    transfers_core = pd.read_csv(DATA_FD + "core/transfers.csv", index_col=None, header=0, low_memory=False,
                                 parse_dates=["intime", "outtime"])

    # ED Admission
    admissions_ed = pd.read_csv(DATA_FD + "ed/edstays.csv", index_col=None, header=0, low_memory=False,
                                parse_dates=["intime", "outtime"])
    triage_ed = pd.read_csv(DATA_FD + "ed/triage.csv", index_col=None, header=0, low_memory=False)

    # ------------------------------------- // -------------------------------------
    "Process Admission Data"

    # Compute recorded admission intimes and outtimes. Respectively, select latest intime and outtime.
    admissions_intime_ed = utils.endpoint_target_ids(admissions_ed, "subject_id", "intime")
    admissions_outtime_ed = utils.endpoint_target_ids(admissions_intime_ed, "subject_id", "outtime")

    admissions_ed_S1 = utils.subsetted_by(admissions_ed, admissions_outtime_ed,
                                          ["stay_id"])  # last admission information
    admissions_ed_S1.to_csv(SAVE_FD + "admissions_S1.csv", index=True, header=True)

    # Identify first wards for all admissions to hospital
    transfers_first_ward = utils.endpoint_target_ids(transfers_core, "subject_id", "intime", mode="min")
    ed_first_transfer = transfers_first_ward[(transfers_first_ward["eventtype"] == "ED") &
                                             (transfers_first_ward["careunit"] == "Emergency Department")]

    # Subset to admissions with ED as first transfer
    admissions_ed_S2 = utils.subsetted_by(admissions_ed_S1, ed_first_transfer,
                                          ["subject_id", "hadm_id", "intime", "outtime"])
    transfers_ed_S2 = utils.subsetted_by(transfers_core, admissions_ed_S2, ["subject_id", "hadm_id"])
    admissions_ed_S2.to_csv(SAVE_FD + "admissions_S2.csv", index=True, header=True)

    # Remove admissions transferred to irrelevant wards (Partum, Psychiatry). Furthermore, EDObs is also special.
    # Missing check that second intime is after ED outtime
    transfers_second_ward = utils.compute_second_transfer(transfers_ed_S2, "subject_id", "intime",
                                                          transfers_ed_S2.columns)
    transfers_to_relevant_wards = transfers_second_ward[~ transfers_second_ward.careunit.isin(WARDS_TO_REMOVE)]
    admissions_ed_S3 = utils.subsetted_by(admissions_ed_S2, transfers_to_relevant_wards, ["subject_id", "hadm_id"])

    # ADD patient core information and next Transfer Information.
    patients_S3 = admissions_ed_S3.subject_id.values
    admissions_ed_S3.loc[:, PATIENT_INFO] = patients_core.set_index("subject_id").loc[patients_S3, PATIENT_INFO].values
    for col in NEXT_TRANSFER_INFO:
        admissions_ed_S3.loc[:, "next_" + col] = transfers_to_relevant_wards.set_index("subject_id").loc[
            patients_S3, col].values
    admissions_ed_S3.to_csv(SAVE_FD + "admissions_S3.csv", index=True, header=True)

    # Compute age and Remove below AGE LOWERBOUND
    admissions_ed_S3["age"] = admissions_ed_S3.intime.dt.year - admissions_ed_S3["anchor_year"] + admissions_ed_S3[
        "anchor_age"]
    admissions_ed_S4 = admissions_ed_S3[admissions_ed_S3["age"] >= AGE_LOWERBOUND]
    admissions_ed_S4.to_csv(SAVE_FD + "admissions_S4.csv", index=True, header=True)

    # Compute and remove ESI NAN and save
    admissions_ed_S4["ESI"] = triage_ed.set_index("stay_id").loc[admissions_ed_S4.stay_id.values, "acuity"].values
    admissions_ed_S5 = admissions_ed_S4[~ admissions_ed_S4["ESI"].isna()]

    # Save data
    admissions_ed_S5.to_csv(SAVE_FD + "admissions_intermediate.csv", index=True, header=True)