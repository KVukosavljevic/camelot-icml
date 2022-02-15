#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Sun Nov 21 10:48:57 2021

@author: henrique.aguiar@ds.ccrg.kadooriecentre.org
"""

import numpy as np
import pandas as pd

from typing import Union, List

from sklearn.metrics import silhouette_score, davies_bouldin_score, calinski_harabasz_score
from sklearn.metrics import adjusted_rand_score, normalized_mutual_info_score
from sklearn.metrics import roc_auc_score, f1_score, recall_score, precision_score
from sklearn.metrics.cluster import contingency_matrix

# List of ADMISSIBLE RESULTS SAVED KEYS
ADMISSIBLE_RESULT_KEYS = ["y_pred", "outc_pred", "y_true", "pis_pred", "clus_pred", "clus_phenotypes"]


def get_clus_outc_numbers(y_true: np.ndarray, clus_pred: np.ndarray):
    """
    Compute contingency matrix: entry (i,j) denotes the number of patients with true sample i and predicted clus j.

    Params:
    - y_true: array-like of true outcome one-hot assignments.
    - clus_pred: array-like of predicted cluster assignment probabilities. Also works for predicted outcome assignments.

    Returns:
        - cont_matrix: numpy ndarray of shape (num_outcs, num_clus) where entry (i,j) denotes the number of patients
        with outcome i and cluster j.
    """

    # Convert to categorical
    labels_true = np.argmax(y_true, axis=1)
    labels_pred = np.argmax(clus_pred, axis=1)

    # Compute contingency matrix
    cont_matrix = contingency_matrix(labels_true, labels_pred)

    return cont_matrix


def _get_outputs_dic(model_name: Union[List, None], run_num: Union[List, None]):
    """
    Get results dictionary given results_dictionary
    """

    # Save paths where data is saved.
    save_fd = f"results/{model_name}/run{run_num}/"
    output_dic = {}

    # Load results given admissible keys
    for key in ADMISSIBLE_RESULT_KEYS:

        # Try to load object and save to dictionary
        try:
            load_obj = pd.read_csv(save_fd + key + ".csv", index_col=0, header=0)
            output_dic[key] = load_obj

            print(f"Object {key} successfully loaded.")

        except FileNotFoundError:
            print(f"Object {key} not loaded.")
            pass

    return output_dic


def _convert_to_one_hot_from_probs(array_pred: Union[np.ndarray, pd.DataFrame]):
    """
    Convert array of predicted class/cluster probability assignments to one-hot encoding of the most common class/clus.

    Params: - array_pred: array-like of shape (N, K), where K is the number of target classes, with probability class
    assignments.

    Returns:
    - Output: array-like of shape (N, K) with one-hot encoded most likely class assignments.
    """

    # Convert to array if necessary
    if isinstance(array_pred, pd.DataFrame):
        array_pred = array_pred.values

    # Compute dimensionality
    _, K = array_pred.shape

    # Convert to categorical
    class_pred = np.eye(K)[np.argmax(array_pred, axis=1)]

    return class_pred


def purity(y_true: np.ndarray, clus_pred: np.ndarray) -> float:
    """
    Computes Purity Score from predicted and true outcome labels. Purity Score is an external cluster validation tool
    which computes the largest number of individuals from a given class in a given cluster, and consequently averages
    this values over the number of clusters.

    Params:
    - y_true: array-like of shape (N, num_outcs) of true outcome labels in one-hot encoded format.
    - clus_pred: array-like of shape (N, num_clus) of predicted outcome cluster assignments.

    Returns:
    - purity_score: float indicating purity score.
    """

    # Convert clus_pred to categorical cluster assignments
    confusion_matrix = _get_clus_outc_numbers(y_true, clus_pred)    # shape (num_outcs, num_clus)

    # Number of most common class in each cluster
    max_class_numbers = np.amax(confusion_matrix, axis=0)

    # Compute average
    purity_score = np.sum(max_class_numbers) / np.sum(confusion_matrix)

    return purity_score


def compute_scores(y_true: np.ndarray, y_pred: np.ndarray, avg=None):
    """
    Compute set of supervised classification scores between y_true and y_pred. List of metrics includes:
    a) AUROC, b) Recall, c) F1, d) Precision, e) Adjusted Rand Index and f) Normalised Mutual Information Score.

    Params:
    - y_true: array-like of shape (N, num_outcs) of one-hot encoded true class membership.
    - y_pred: array-like of shape (N, num_outcs) of predicted outcome probability assignments.
    - avg: parameter for a), b), c) and d) computation indicating whether class scores should be averaged, and how.
    (default = None, all scores reported).

    Returns:
        - Dictionary of performance scores:
            - "ROC-AUC": list of AUROC One vs Rest values.
            - "Recall": List of Recall One vs Rest values.
            - "F1": List of F1 score One vs Rest values.
            - "Precision": List of Precision One vs Rest values.
            - "ARI": Float value indicating Adjusted Rand Index performance.
            - "NMI": Float value indicating Normalised Mutual Information Score performance.
    """

    # Compute ROC-AUC first given y_pred and y_true format
    auc = roc_auc_score(y_true, y_pred, average=avg, multi_class="ovr")

    # Convert input arrays to categorical labels
    labels_true, labels_pred = np.argmax(y_true, axis=1), np.argmax(y_pred, axis=1)

    # Compute F1
    f1 = f1_score(labels_true, labels_pred, average=avg)

    # Compute Recall
    rec = recall_score(labels_true, labels_pred, average=avg)

    # Compute Precision
    prec = precision_score(labels_true, labels_pred, average=avg)

    # Compute ARI
    ari = adjusted_rand_score(labels_true, labels_pred)

    # Compute NMI
    nmi = normalized_mutual_info_score(labels_true, labels_pred)

    # Return Dictionary
    scores_dic = {
        "ROC-AUC": auc,
        "F1": f1,
        "Recall": rec,
        "Precision": prec,
        "ARI": ari,
        "NMI": nmi
    }

    return scores_dic


def compute_cluster_performance(X, clus_pred, y_true):
    """
    Compute cluster performance metrics given input data X and predicted cluster probability assignments clus_pred.
    Metrics computed include a) Silhouette Score, b) Davies Bouldin Score, c) Calinski Harabasz Score and d) Purity.
    Performance is computed averaged over features.

    Params:
    - X: array-like of shape (N, T, D_f) where N is the number of patients, T the number of time steps and D_f the
    number of features (+2, the id col and the time col).
    - clus_pred: array-like of shape (N, num_clus) with probability predictions for cluster assignment.
    - y_true: array-like of shape (N, num_outcs) with one-hot encoding of true class assignments.

    Returns:
        - Dictionary of output cluster performance metrics. Includes:
            - "Silhouette": Silhouette Score computation.
            - "DBI": Davies-Bouldin Index computation.
            - "VRI": Variance-Ratio Criterion (also known as Calinski Harabasz Index).
            - "Purity": Purity Score computation.
    """

    # Convert to one-hot encoding from probabilities.
    clus_pred = _convert_to_one_hot_from_probs(array_pred=clus_pred)

    # Compute the same taking average over each feature dimension
    sil_avg, dbi_avg, vri_avg = 0, 0, 0

    for feat in range(X.shape[-1]):
        sil_avg += silhouette_score(X[:, :, feat], clus_pred, metric="euclidean")
        dbi_avg += davies_bouldin_score(X[:, :, feat], clus_pred)
        vri_avg += calinski_harabasz_score(X[:, :, feat], clus_pred)

    # Compute Purity Score
    purity_score = purity(y_true, clus_pred)

    # Compute average factor
    num_feats = X.shape[-1]

    # Return Dictionary
    clus_perf_dic = {
        "Silhouette": sil_avg / num_feats,
        "DBI": dbi_avg / num_feats,
        "VRI": vri_avg / num_feats,
        "Purity": purity_score / num_feats
    }

    return clus_perf_dic
