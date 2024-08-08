# Usage: python umapper.py <dataset_id> <model> <neighbors> <min_dist>
# Example: python umapper.py dadabase-curated BAAI_bge-small-en-v1.5 50 0.075
import os
import re
import sys
import json
import argparse

from latentscope.util import get_data_dir

def main():
    parser = argparse.ArgumentParser(description='Generate SAE features from embeddings for a dataset')
    parser.add_argument('dataset_id', type=str, help='Dataset name (directory name in data/)')
    parser.add_argument('embedding_id', type=str, help='Name of embedding to use')
    parser.add_argument("model_id", type=str, nargs="?", help="HF id of model to use", default="enjalot/sae-nomic-text-v1.5-FineWeb-edu-10BT")
    parser.add_argument('k_expansion', type=str, nargs="?", help='Output file', default="64_32")
    parser.add_argument('device', type=str, nargs="?", help='Device to use')

    # Parse arguments
    args = parser.parse_args()
    saer(args.dataset_id, args.embedding_id, args.model_id, args.k_expansion, args.device)


def saer(dataset_id, embedding_id, model_id, k_expansion, device):
    DATA_DIR = get_data_dir()
    # read in the embeddings 

    sae_dir = os.path.join(DATA_DIR, dataset_id, "saes")
    if not os.path.exists(sae_dir):
        os.makedirs(sae_dir)

    # determine the index of the last sae run by looking in the dataset directory
    # for files named sae-<number>.json
    sae_files = [f for f in os.listdir(sae_dir) if re.match(r"sae-\d+\.json", f)]
    if len(sae_files) > 0:
        last_sae = sorted(sae_files)[-1]
        last_sae_number = int(last_sae.split("-")[1].split(".")[0])
        next_sae_number = last_sae_number + 1
    else:
        next_sae_number = 1

    # make the sae name from the number, zero padded to 3 digits
    sae_id = f"sae-{next_sae_number:03d}"
    print("RUNNING:", sae_id)

    from latentsae.sae import Sae
    import h5py
    import numpy as np
    import pandas as pd
    import torch

    print("loading embeddings")
    embedding_path = os.path.join(DATA_DIR, dataset_id, "embeddings", f"{embedding_id}.h5")
    with h5py.File(embedding_path, 'r') as f:
        dataset = f["embeddings"]
        embeddings = np.array(dataset)

    if device == "mps" or torch.backends.mps.is_available():
        device = torch.device("mps")
    elif device == "cuda" or torch.cuda.is_available():
        device = torch.device("cuda")
    else:
        device = torch.device("cpu")

    all_embeddings = torch.from_numpy(embeddings).float().to(device)
    model = Sae.load_from_hub(model_id, k_expansion, device)
    print("Encoding embeddings with SAE")
    all_features = model.encode(all_embeddings)
    print("encoding completed")
    all_acts = all_features.top_acts.detach().cpu().numpy()
    all_indices = all_features.top_indices.detach().cpu().numpy()

    print("saving to disk")
    # save the acts and indices to the sae directory
    with h5py.File(os.path.join(sae_dir, f"{sae_id}.h5"), 'w') as f:
        f.create_dataset("top_acts", data=all_acts)
        f.create_dataset("top_indices", data=all_indices)

    print("calculating summary statistics")
    # calculate the max activation per feature
    max_activations = np.full((model.num_latents,), -1.0)
    
    from tqdm import tqdm

    for feature_idx in tqdm(range(model.num_latents), desc="Calculating max activations"):
        feature_mask = all_indices == feature_idx
        if feature_mask.any():
            feature_activations = np.where(feature_mask, all_acts, 0.0)
            max_activation = np.max(feature_activations)
            max_activations[feature_idx] = max_activation

    dead_features = np.where(max_activations < 0)
    alive_features = np.where(max_activations >= 0)
    # Count the number of dead features
    num_dead_features = len(dead_features[0])
    print(f"Number of dead features: {num_dead_features}")

    # create the metadata json
    with open(os.path.join(sae_dir, f"{sae_id}.json"), 'w') as f:
        json.dump({
            "model_id": model_id,
            "k_expansion": k_expansion,
            "embedding_id": embedding_id,
            "dataset_id": dataset_id,
            "max_activations": max_activations.tolist(),
            "num_features": model.num_latents,
            "dead_features": num_dead_features,
            "alive_features": len(alive_features[0])
        }, f)

    print("done with", sae_id)


if __name__ == "__main__":
    main()
