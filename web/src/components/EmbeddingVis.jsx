import React, { useEffect, useRef } from 'react';
import { scaleDiverging } from 'd3-scale';
import { interpolateRdBu } from 'd3-scale-chromatic';

// import "./EmbeddingVis.css"

const EmbeddingVis = ({ 
  embedding, 
  rows = 16,
  spacing = 0.5,
  height = 16*4,
  width = embedding ? Math.ceil(embedding.length / 16) * 4 : 0,
  minValues = [],
  maxValues = [],
}) => {
  const container = useRef();
  
  useEffect(() => {
    if(!embedding || !embedding.length) return
    const colorScale = scaleDiverging([-1, 0, 1], interpolateRdBu)

    const len = embedding.length
    const cols = Math.ceil(len / rows)
    const rh = height / rows - spacing
    const rw = width / cols - spacing

    const canvas = container.current
    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, width, height)
    embedding.forEach((d,i) => {
      const x = (i % cols) * (rw + spacing)
      const y = Math.floor(i / cols) * (rh + spacing)
      let c = colorScale(d)
      if(minValues.length && maxValues.length)
        c = scaleDiverging([minValues[i], 0, maxValues[i]], interpolateRdBu)(d)
      ctx.fillStyle = c
      ctx.fillRect(x, y, rw, rh)
    })
  }, [embedding, rows, width, height, spacing, minValues, maxValues])

  return <canvas 
    className="embedding-vis"
    ref={container} 
    width={width} 
    height={height} />;
};

export default EmbeddingVis;
