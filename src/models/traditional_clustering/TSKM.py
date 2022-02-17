"""
Define Model Class for SVMAll model. SVM is fit to concatenated trajectories.
"""

import os, json

import numpy as np
import pandas as pd

from tslearn.clustering import TimeSeriesKMeans

KMEANS_INPUT_PARAMS = ["n_clusters", "init", "n_init", "verbose", "random_state", "metric"]


class TSKM(TimeSeriesKMeans):
    """
    Model Class Wrapper for a KMeans clustering model.
    """

    def __init__(self, data_info: dict = {}, metric="euclidean", verbose=True, **kwargs):
        """
        Initialise object with model configuration.

        Params:
        - data_info: dict, dictionary containing dataset information, including objects and properties.
        - kwargs: model configuration parameters
        """

        # Get proper model_config
        self.model_config = {key: value for key, value in kwargs.items() if key in KMEANS_INPUT_PARAMS}

        if "seed" in kwargs.keys():
            self.model_config["random_state"] = kwargs["seed"]

        # Initialise other useful information
        self.run_num = 1
        self.model_name = "TSKM"

        # Useful for consistency
        self.training_params = {}

        # Initialise SVM object with this particular model config
        super().__init__(**self.model_config, verbose=verbose)

    def train(self, data_info, **kwargs):
        """
        Wrapper method for fitting the model to input data.

        Params:
        - probability: bool value, indicating whether model should output hard outcome assignments, or probabilistic.
        - data_info: dictionary with data information, objects and parameters.
        """

        # Unpack relevant data information
        X_train, X_val, X_test = data_info["X"]
        data_name = data_info["data_load_config"]["data_name"]

        # Update run_num to make space for new experiment
        run_num = self.run_num
        save_fd = f"experiments/{data_name}/{self.model_name}/"

        while os.path.exists(save_fd + f"run{run_num}/"):
            run_num += 1

        # make new folder and update run num
        os.makedirs(save_fd + f"run{run_num}/")
        self.run_num = run_num

        # Fit to concatenated X_train, X_val
        X = np.concatenate((X_train, X_val), axis=0)

        # Fit model
        self.fit(X)

        return None

    def analyse(self, data_info):
        """
        Evaluation method to compute and save output results.

        Params:
        - data_info: dictionary with data information, objects and parameters.

        Returns:
            - y_pred: dataframe of shape (N, output_dim) with outcome probability prediction.
            - outc_pred: Series of shape (N, ) with predicted outcome based on most likely outcome prediction.
            - y_true: dataframe of shape (N, output_dim) ith one-hot encoded true outcome.

        Saves a variety of model information, as well.
        """

        # Unpack test data
        _, _, X_test = data_info["X"]

        # Get basic data information
        data_load_config = data_info["data_load_config"]
        data_name = data_load_config["data_name"]

        # Obtain the ids for patients in test set
        id_info = data_info["ids"][-1]
        pat_ids = id_info[:, 0, 0]

        # Define save_fd, track_fd
        save_fd = f"results/{data_name}/{self.model_name}/run{self.run_num}/"
        track_fd = f"experiments/{data_name}/{self.model_name}/run{self.run_num}/"

        if not os.path.exists(save_fd):
            os.makedirs(save_fd)

        if not os.path.exists(track_fd):
            os.makedirs(track_fd)

        # Make predictions
        K = self.cluster_centers_.shape[0]
        clus_pred = self.predict(X_test)
        pis_pred = np.eye(K)[clus_pred]
        cluster_names = [f"Clus {k}" for k in range(1, K + 1)]

        # Convert to DataFrame
        pis_pred = pd.DataFrame(pis_pred, index=pat_ids, columns=cluster_names)
        clus_pred = pd.Series(clus_pred, index=pat_ids)


        # ----------------------------- Save Output Data --------------------------------
        # Useful objects
        pis_pred.to_csv(save_fd + "pis_pred.csv", index=True, header=True)
        clus_pred.to_csv(save_fd + "clus_pred.csv", index=True, header=True)

        # save model parameters
        save_params = {**data_info["data_load_config"], **self.model_config, **self.training_params}
        with open(save_fd + "config.json", "w+") as f:
            json.dump(save_params, f, indent=4)

        with open(save_fd + "model_config_length.json", "w+") as f:
            json.dump(self.model_config, f, indent=4)

        # Return objects
        outputs_dic = {
            "pis_pred": pis_pred, "clus_pred": clus_pred, "save_fd": save_fd, "model_config": self.model_config
        }

        # Print Data
        print(f"\n\n Experiments saved under {track_fd} and {save_fd}")

        return outputs_dic
