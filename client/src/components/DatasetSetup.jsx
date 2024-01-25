import { useEffect, useState, useMemo, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

import './DatasetSetup.css';
import Embedding from './Setup/Embedding';
import Umap from './Setup/Umap';
import Cluster from './Setup/Cluster';
import ClusterLabels from './Setup/ClusterLabels';
import Scope from './Setup/Scope';

import IndexDataTable from './IndexDataTable';
import UmapScatter from './UmapScatter';

function DatasetSetup() {
  const [dataset, setDataset] = useState(null);
  const { dataset: datasetId, scope: scopeId } = useParams();

  const navigate = useNavigate();

  const scopeWidth = 640
  const scopeHeight = 640

  // Get the dataset meta data
  useEffect(() => {
    fetch(`http://localhost:5001/datasets/${datasetId}/meta`)
      .then(response => response.json())
      .then(data => setDataset(data));
  }, [datasetId]);

  // default text column from columns
  const textColumn = useMemo(() => {
    if (!dataset) return "";
    return dataset.text_column || dataset.columns[0];
  }, [dataset])

  // set the text column on our dataset
  const handleChangeTextColumn = useCallback((event) => {
    const column = event.target.value;
    console.log("setting column", column)
    fetch(`http://localhost:5001/datasets/${datasetId}/meta/update?key=text_column&value=${column}`)
      .then(response => response.json())
      .then(data => {
        // console.log("updated meta", data)
        setDataset(data)
      });
  }, [datasetId])
 

  // ====================================================================================================
  // embeddings 
  // ====================================================================================================
  // get the list of available embeddings, and refresh when a new one is created
  const [embeddings, setEmbeddings] = useState([]);
  // embedding is a string identifier
  const [embedding, setEmbedding] = useState(embeddings[0]);

  useEffect(() => {
    if(embeddings?.length && !embedding){
      setEmbedding(embeddings[0])
    }
  }, [embeddings, embedding])

  // ====================================================================================================
  // umaps
  // ====================================================================================================

  const [umaps, setUmaps] = useState([]);
  const [umap, setUmap] = useState(null);
  // the name of the umap selected by the user
  const [selectedUmap, setSelectedUmap] = useState(null);

  useEffect(() => {
      if(umaps.length) {
        const embeddingUmaps = umaps.filter(d => d.embeddings == embedding)
        const found = embeddingUmaps.find(d => d.name == selectedUmap)
        if(selectedUmap && found) {
          setUmap(found)
        } else {
          setUmap(embeddingUmaps[0])
        }
      }
  }, [selectedUmap, umaps, embedding])  

  // ====================================================================================================
  // clusters
  // ==================================================================================================== 

  const [clusters, setClusters] = useState([]);
  const [cluster, setCluster] = useState(null);
  const [selectedCluster, setSelectedCluster] = useState(null);

  useEffect(() => {
    if(clusters.length && umap) {
      const umapClusters = clusters.filter(d => d.umap_name == umap.name)
      const found = umapClusters.find(d => d.cluster_name == selectedCluster)
      if(selectedCluster && found) {
        setCluster(found)
      } else {
        setCluster(umapClusters[0])
      }
    } else {
      setCluster(null)
    }
  }, [selectedCluster, clusters, umap]) 

  // the currently chosen model used to label the active cluster
  const [clusterLabelModel, setClusterLabelModel] = useState(null); 

  // ====================================================================================================
  // scopes
  // ====================================================================================================
  const[scopes, setScopes] = useState([]);
  const[scope, setScope] = useState(null);

  // When the scopeId changes, update the scope and set all the default selections
  useEffect(() => {
    if(scopeId && scopes?.length) {
      const scope = scopes.find(d => d.name == scopeId)
      if(scope) {
        setScope(scope)
        setEmbedding(scope.embeddings)
        setSelectedUmap(scope.umap)
        setSelectedCluster(scope.cluster)
        setClusterLabelModel(scope.cluster_labels)
      }
    } else {
      setScope(null)
    } 
  }, [scopeId, scopes])


  // ====================================================================================================
  // selected points from the scatterplot 
  // ====================================================================================================
  const [selectedIndices, setSelectedIndices] = useState([]);
  const handleSelected = useCallback((indices) => {
    setSelectedIndices(indices);
  }, [setSelectedIndices])

  const [scatter, setScatter] = useState({})
 

  if (!dataset) return <div>Loading...</div>;

  return (
    <div className="dataset--setup">
      <div className="dataset--setup-summary">
        <div className="dataset--setup-info">
          <h2>{datasetId}</h2>
          [ {dataset.length} rows ]<br/>
          Columns: {dataset.columns.join(", ")}
          <div className="dataset--details-text-column">
            Set Text Column: 
            <select value={textColumn} onChange={handleChangeTextColumn}>
              {dataset.columns.map((column, index) => (
                <option key={index} value={column}>{column}</option>
              ))}
            </select>
          </div>
        </div>
        
        { scope ? <a href={`/datasets/${dataset?.id}/explore/${scope.name}`}>Explore {scope.label} ({scope.name})</a> : null }

        <div className="dataset--setup-scopes-list">
            {scopes && scopes.map((s, index) => {
              const cl = clusters.find(c => c.cluster_name == s.cluster) || {}
              return (
              <div 
                key={index} 
                className={ "dataset--setup-scopes-item" + (s.name == scope?.name ? " active" : "") }
                onClick={() => navigate(`/datasets/${datasetId}/setup/${s.name}`)}
                >
                <span>{s.name}</span>
                <span>{s.label} </span>
                <span>{s.description}</span>
                <img src={cl.url} alt={cl.name} /> 
                <span>{s.embeddings}</span>
              </div>
            )})}
            
        </div>
      </div>

      <div className="dataset--setup-layout">
        <div className="dataset--setup-left-column">
          <div className="dataset--setup-embeddings">
            <h3>1. Embeddings</h3> 
            <Embedding dataset={dataset} textColumn={textColumn} embedding={embedding} umaps={umaps} clusters={clusters} onNew={setEmbeddings} onChange={setEmbedding} />
          </div>
          <div className="dataset--setup-umaps">
            <h3>2. UMAP </h3>
            <Umap dataset={dataset} umap={umap} embedding={embedding} clusters={clusters} onNew={setUmaps} onChange={setUmap} />
          </div>

          <div className="dataset--setup-clusters">
            <h3>3. Clusters</h3>
            <Cluster dataset={dataset} cluster={cluster} umap={umap} onNew={setClusters} onChange={setCluster} />
          </div>
          {/* AUTO LABEL CLUSTERS */}
          <div className="dataset--setup-cluster-labels">
            <h3>4. Auto-Label Clusters</h3>
            {cluster ?
            <ClusterLabels dataset={dataset} cluster={cluster} selectedModel={clusterLabelModel} onChange={setClusterLabelModel} />
             : null}
          </div>
          <div className="dataset--setup-scopes">
            <h3>5. Save Scope</h3>
            <Scope dataset={dataset} scope={scope} embedding={embedding} umap={umap} cluster={cluster} onNew={setScopes} onChange={setScope} />
          </div>
        </div>

        {/* RIGHT COLUMN */}
        <div className="dataset--setup-right-column">
          <div className="dataset--setup-umap">
            <UmapScatter 
              dataset={dataset} 
              umap={umap}
              width={scopeWidth} 
              height={scopeHeight}
              onScatter={setScatter}
              onSelect={handleSelected}
              />
            </div>

            <div className="dataset--selected">
              <span>Points Selected: {selectedIndices.length} {!selectedIndices.length ? "(Hold shift and drag an area of the map to select)" : null}
                {selectedIndices.length > 0 ? 
                  <button className="deselect" onClick={() => {
                    setSelectedIndices([])
                    scatter?.select([])
                    scatter?.zoomToOrigin({ transition: true, transitionDuration: 1500 })
                  }
                  }>X</button> 
                : null}
              </span>
              {selectedIndices.length > 0 ? 
              <div className="dataset--selected-table">
                <IndexDataTable 
                  dataset={dataset}
                  indices={selectedIndices} 
                  datasetId={datasetId} 
                  maxRows={150} 
                  />
              </div>
              : null }
            </div>
        
        </div>
      </div>
        
    </div>
  );
}

export default DatasetSetup;