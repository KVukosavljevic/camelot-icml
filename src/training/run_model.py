"""
Single Run Training

Date Last updated: 24 Jan 2022
Author: Henrique Aguiar
Please contact via henrique.aguiar@eng.ox.ac.uk
"""
import json

import src.models.model_utils as model_utils
import src.results.evaluate as evaluate
from src.data_processing.data_loader import data_loader

# physical_devices = tf.config.list_physical_devices('GPU')
# tf.config.experimental.set_memory_growth(physical_devices[0], True)

# os.environ['CUDA_VISIBLE_DEVICES'] = '-1'

"""
Load configuration files and hyper-parameters.
"""
with open("src/training/data_config.json", "r") as f:
    data_config = json.load(f)
    f.close()

with open("src/training/model_config.json", "r") as f:
    model_config = json.load(f)
    f.close()

with open("src/training/training_config.json", "r") as f:
    training_config = json.load(f)
    f.close()


# Load data
data_info = data_loader(**data_config)
output_dim = data_info["y"][-1].shape[-1]

# Load model and fit
print("\n\n\n\n")
model = model_utils.get_model_from_str(**model_config)
model.train(data_info=data_info, **training_config)

# Compute data test
outputs_dic = model.analyse(data_info)

# Evaluate model
scores = evaluate(**outputs_dic, avg=None)

# Useful visualisations
