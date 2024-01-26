import re
import os
import json
import numpy as np
import pandas as pd

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__)

CORS(app)

# in memory cache of dataframes loaded for each dataset
# used in returning rows for a given index (indexed, get_tags)
DATAFRAMES = {}

from jobs import jobs_bp
app.register_blueprint(jobs_bp, url_prefix='/api/jobs') 

from search import search_bp
app.register_blueprint(search_bp, url_prefix='/api/search') 


# ===========================================================
# File based routes for reading data and metadata  from disk
# ===========================================================

"""
Allow fetching of dataset files directly from disk
"""
@app.route('/api/files/<path:datasetPath>', methods=['GET'])
def send_file(datasetPath):
    print("req url", request.url)
    return send_from_directory(os.path.join(os.getcwd(), '../data/'), datasetPath)

@app.route('/api/embedding_models', methods=['GET'])
def get_embedding_models():
    directory_path = os.path.join(os.getcwd(), '../models/') 
    file_path = os.path.join(directory_path, 'embedding_models.json')   
    with open(file_path, 'r', encoding='utf-8') as file:
        models = json.load(file)
    return jsonify(models)

@app.route('/api/chat_models', methods=['GET'])
def get_chat_models():
    directory_path = os.path.join(os.getcwd(), '../models/') 
    file_path = os.path.join(directory_path, 'chat_models.json')   
    with open(file_path, 'r', encoding='utf-8') as file:
        models = json.load(file)
    return jsonify(models)


"""
Get the essential metadata for all available datasets.
Essential metadata is stored in meta.json
"""
@app.route('/api/datasets', methods=['GET'])
def get_datasets():
    directory_path = os.path.join(os.getcwd(), '../data/')  # Adjust the path as necessary
    datasets = []

    for dir in os.listdir(directory_path):
        file_path = os.path.join(directory_path, dir, 'meta.json')
        if os.path.isfile(file_path):
            with open(file_path, 'r', encoding='utf-8') as file:
                jsonData = json.load(file)
                jsonData['name'] = dir
                datasets.append(jsonData)

    return jsonify(datasets)

"""
Get all metadata files from the given a directory.
"""
def scan_for_json_files(directory_path):
    try:
        files = os.listdir(directory_path)
    except OSError as err:
        print('Unable to scan directory:', err)
        return jsonify({"error": "Unable to scan directory"}), 500

    json_files = [file for file in files if file.endswith('.json')]
    json_files.sort()
    print("files", files)
    print("json", json_files)

    json_contents = []
    for file in json_files:
        try:
            with open(os.path.join(directory_path, file), 'r', encoding='utf-8') as json_file:
                json_contents.append(json.load(json_file))
        except json.JSONDecodeError as err:
            print('Error parsing JSON string:', err)
    return jsonify(json_contents)

@app.route('/api/datasets/<dataset>/meta', methods=['GET'])
def get_dataset_meta(dataset):
    file_path = os.path.join(os.getcwd(), '../data/', dataset, "meta.json")
    with open(file_path, 'r', encoding='utf-8') as json_file:
        json_contents = json.load(json_file)
    return jsonify(json_contents)

@app.route('/api/datasets/<dataset>/meta/update', methods=['GET'])
def update_dataset_meta(dataset):
    key = request.args.get('key')
    value = request.args.get('value')
    file_path = os.path.join(os.getcwd(), '../data/', dataset, "meta.json")
    with open(file_path, 'r', encoding='utf-8') as json_file:
        json_contents = json.load(json_file)
    json_contents[key] = value
    # write the file back out
    with open(file_path, 'w', encoding='utf-8') as json_file:
        json.dump(json_contents, json_file)
    return jsonify(json_contents)


@app.route('/api/datasets/<dataset>/embeddings', methods=['GET'])
def get_dataset_embeddings(dataset):
    directory_path = os.path.join(os.getcwd(), '../data/', dataset, "embeddings")
    print("dataset", dataset, directory_path)
    try:
        files = sorted(os.listdir(directory_path), key=lambda x: os.path.getmtime(os.path.join(directory_path, x)), reverse=True)
    except OSError as err:
        print('Unable to scan directory:', err)
        return jsonify({"error": "Unable to scan directory"}), 500

    npy_files = [file.replace(".npy", "") for file in files if file.endswith('.npy')]
    print("files", files)
    print("npy", npy_files)
    return jsonify(npy_files)


@app.route('/api/datasets/<dataset>/umaps', methods=['GET'])
def get_dataset_umaps(dataset):
    directory_path = os.path.join(os.getcwd(), '../data/', dataset, "umaps")
    print("dataset", dataset, directory_path)
    return scan_for_json_files(directory_path)

@app.route('/api/datasets/<dataset>/umaps/<umap>/points', methods=['GET'])
def get_dataset_umap_points(dataset, umap):
    file_path = os.path.join(os.getcwd(), '../data/', dataset, "umaps", umap + ".parquet")
    df = pd.read_parquet(file_path)
    return df.to_json(orient="records")

@app.route('/api/datasets/<dataset>/clusters', methods=['GET'])
def get_dataset_clusters(dataset):
    directory_path = os.path.join(os.getcwd(), '../data/', dataset, "clusters")
    print("dataset", dataset, directory_path)
    return scan_for_json_files(directory_path)

@app.route('/api/datasets/<dataset>/clusters/<cluster>/labels', methods=['GET'])
def get_dataset_cluster_labels_default(dataset, cluster):
    file_name = cluster + "-labels.parquet"
    file_path = os.path.join(os.getcwd(), '../data/', dataset, "clusters", file_name)
    df = pd.read_parquet(file_path)
    return df.to_json(orient="records")

@app.route('/api/datasets/<dataset>/clusters/<cluster>/labels/<model>', methods=['GET'])
def get_dataset_cluster_labels(dataset, cluster, model):
    file_name = cluster + "-labels-" + model + ".parquet"
    file_path = os.path.join(os.getcwd(), '../data/', dataset, "clusters", file_name)
    df = pd.read_parquet(file_path)
    return df.to_json(orient="records")

@app.route('/api/datasets/<dataset>/clusters/<cluster>/labels_available', methods=['GET'])
def get_dataset_cluster_labels_available(dataset, cluster):
    directory_path = os.path.join(os.getcwd(), '../data/', dataset, "clusters")
    try:
        files = sorted(os.listdir(directory_path), key=lambda x: os.path.getmtime(os.path.join(directory_path, x)), reverse=True)
    except OSError as err:
        print('Unable to scan directory:', err)
        return jsonify({"error": "Unable to scan directory"}), 500

    pattern = re.compile(r'^' + cluster + '-labels-(.*).parquet$')
    model_names = [pattern.match(file).group(1) for file in files if pattern.match(file)]
    return jsonify(model_names)


def get_next_scopes_number(dataset):
    # figure out the latest scope number
    scopes_files = [f for f in os.listdir(f"../data/{dataset}/scopes") if re.match(r"scopes-\d+\.json", f)]
    if len(scopes_files) > 0:
        last_scopes = sorted(scopes_files)[-1]
        last_scopes_number = int(last_scopes.split("-")[1].split(".")[0])
        next_scopes_number = last_scopes_number + 1
    else:
        next_scopes_number = 1
    return next_scopes_number

@app.route('/api/datasets/<dataset>/scopes', methods=['GET'])
def get_dataset_scopes(dataset):
    directory_path = os.path.join(os.getcwd(), '../data/', dataset, "scopes")
    print("dataset", dataset, directory_path)
    return scan_for_json_files(directory_path)

@app.route('/api/datasets/<dataset>/scopes/save', methods=['POST'])
def save_dataset_scope(dataset):
    if not request.json:
        return jsonify({"error": "Invalid data format, JSON expected"}), 400
    name = request.json.get('name')
    embeddings = request.json.get('embeddings')
    umap = request.json.get('umap')
    cluster = request.json.get('cluster')
    cluster_labels = request.json.get('cluster_labels')
    label = request.json.get('label')
    description = request.json.get('description')
    scope = {
        "embeddings": embeddings,
        "umap": umap,
        "cluster": cluster,
        "cluster_labels": cluster_labels,
        "label": label,
        "description": description
    }
    if not name:
        next_scopes_number = get_next_scopes_number(dataset)
        # make the umap name from the number, zero padded to 3 digits
        name = f"scopes-{next_scopes_number:03d}"
    scope["name"] = name
    file_path = os.path.join(os.getcwd(), '../data/', dataset, "scopes", name + ".json")
    with open(file_path, 'w') as f:
        json.dump(scope, f, indent=2)
    return jsonify(scope)


"""
Given a list of indices (passed as a json array), return the rows from the dataset
"""
@app.route('/api/indexed', methods=['GET'])
def indexed():
    dataset = request.args.get('dataset')
    indices = json.loads(request.args.get('indices'))
    if dataset not in DATAFRAMES:
        df = pd.read_parquet(os.path.join("../data", dataset, "input.parquet"))
        DATAFRAMES[dataset] = df
    else:
        df = DATAFRAMES[dataset]
    
    # get the indexed rows
    rows = df.iloc[indices]
    # send back the rows as json
    return rows.to_json(orient="records")

# ===========================================================
# Tags
# ===========================================================

tagsets = {}

"""
Return the tagsets for a given dataset
This is a JSON object with the tag name as the key and an array of indices as the value
"""
@app.route("/tags", methods=['GET'])
def tags():
    dataset = request.args.get('dataset')
    tagdir = os.path.join("../data", dataset, "tags")
    if not os.path.exists(tagdir):
        os.makedirs(tagdir)
    if dataset not in tagsets:
        tagsets[dataset] = {}
    # search the dataset directory for all files ending in .indices
    for f in os.listdir(tagdir):
        if f.endswith(".indices"):
            tag = f.split(".")[0]
            indices = np.loadtxt(os.path.join("../data", dataset, "tags", tag + ".indices"), dtype=int).tolist()
            if type(indices) == int:
                indices = [indices]
            tagsets[dataset][tag] = indices

    # return an object with the tags for a given dataset
    return jsonify(tagsets[dataset])

"""
Create a new tag for a given dataset
"""
@app.route("/tags/new", methods=['GET'])
def new_tag():
    dataset = request.args.get('dataset')
    tag = request.args.get('tag')
    if dataset not in tagsets:
        tagsets[dataset] = {}
    # search the dataset directory for all files ending in .indices
    tags = []
    for f in os.listdir(os.path.join("../data", dataset)):
        if f.endswith(".indices"):
            dtag = f.split(".")[0]
            indices = np.loadtxt(os.path.join("../data", dataset, "tags", dtag + ".indices"), dtype=int).tolist()
            if type(indices) == int:
                indices = [indices]
            tagsets[dataset][dtag] = indices

    if tag not in tagsets[dataset]:
        tagsets[dataset][tag] = []
        # create an empty file
        filename = os.path.join("../data", dataset, "tags", tag + ".indices")
        with open(filename, 'w') as f:
            f.write("")
            f.close()


    # return an object with the tags for a given dataset
    return jsonify(tagsets[dataset])

"""
Add a data index to a tag
"""
@app.route("/tags/add", methods=['GET'])
def add_tag():
    dataset = request.args.get('dataset')
    tag = request.args.get('tag')
    index = request.args.get('index')
    if dataset not in tagsets:
        ts = tagsets[dataset] = {}
    else:
        ts = tagsets[dataset]
    if tag not in ts:
        # read a tag file, which is just a csv with a single column into an array of integers
        indices = np.loadtxt(os.path.join("../data", dataset, "tags", tag + ".indices"), dtype=int).tolist()
        if type(indices) == int:
            indices = [indices]
        ts[tag] = indices
    else:
        indices = ts[tag]

    if not indices:
        indices = []
    if index not in indices:
        indices.append(int(index))
        ts[tag] = indices
        # save the indices to a file
        np.savetxt(os.path.join("../data", dataset, "tags", tag + ".indices"), indices, fmt='%d')
    # return an object with the tags for a given dataset
    return jsonify(tagsets[dataset])

"""
Remove a data index from a tag
"""
@app.route("/tags/remove", methods=['GET'])
def remove_tag():
    dataset = request.args.get('dataset')
    tag = request.args.get('tag')
    index = request.args.get('index')
    if dataset not in tagsets:
        tagsets[dataset] = {}
    else:
        ts = tagsets[dataset]
    if tag not in ts:
        # read a tag file, which is just a csv with a single column into an array of integers
        indices = np.loadtxt(os.path.join("../data", dataset, "tags", tag + ".indices"), dtype=int).tolist()
        if type(indices) == int:
            indices = [indices]
        ts[tag] = indices
    else:
        indices = ts[tag]
    if index in indices:
        indices = indices.remove(int(index))
        ts[tag] = indices
        # save the indices to a file
        np.savetxt(os.path.join("../data", dataset, "tags", tag + ".indices"), indices, fmt='%d')
    # return an object with the tags for a given dataset
    return jsonify(tagsets[dataset])

"""
Return the data rows for a given tag
"""
@app.route("/tags/rows", methods=['GET'])
def tag_rows():
    dataset = request.args.get('dataset')
    tag = request.args.get('tag')

    if dataset not in tagsets:
        tagsets[dataset] = {}
    else:
        ts = tagsets[dataset]
    if tag not in ts:
        # read a tag file, which is just a csv with a single column into an array of integers
        indices = np.loadtxt(os.path.join("../data", dataset, "tags", tag + ".indices"), dtype=int).tolist()
        ts[tag] = indices
    else:
        indices = ts[tag]
    if dataset not in DATAFRAMES:
        df = pd.read_parquet(os.path.join("../data", dataset, "input.parquet"))
        DATAFRAMES[dataset] = df
    else:
        df = DATAFRAMES[dataset]
    
    # get the indexed rows
    rows = df.iloc[indices]
    # send back the rows as json
    return rows.to_json(orient="records")


# ===========================================================
# Slides
# ===========================================================

"""
Return the slides for a given dataset
"""
@app.route("/slides", methods=['GET'])
def slides():
    dataset = request.args.get('dataset')
    # get the active_slides from meta.json
    meta = json.load(open(os.path.join("../data", dataset, "meta.json")))
    # search the dataset directory for all files ending in .indices
    # read the slides parquet file
    slide = meta["active_slides"].replace("cluster", "slides")
    slides_df = pd.read_parquet(os.path.join("../data", dataset, "slides", slide + ".parquet"))
    # return an object with the tags for a given dataset
    return slides_df.to_json(orient="records")


# TODO: configure this
MODE = "production" # or read_only

dist_dir = '../web/dist/' + MODE

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    if path != "" and os.path.exists(os.path.join(dist_dir, path)):
        return send_from_directory(dist_dir, path)
    else:
        return send_from_directory(dist_dir, 'index.html')

# set port
port = int(os.environ.get('PORT', 5001))
print("running app", port)
app.run(host="0.0.0.0", port=port, debug=True)