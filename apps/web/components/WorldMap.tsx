"use client";

import { useEffect, useMemo, useState } from "react";
import { Opportunity } from "@/types/market";

type Position = number[];
type PolygonCoordinates = Position[][];
type Geometry =
  | { type: "Polygon"; coordinates: PolygonCoordinates }
  | { type: "MultiPolygon"; coordinates: PolygonCoordinates[] };
type CountryFeature = {
  type: "Feature";
  properties: { ISO_A3?: string; NAME?: string };
  geometry: Geometry;
};
type CountryCollection = {
  type: "FeatureCollection";
  features: CountryFeature[];
};

type WorldMapProps = {
  data: Opportunity[];
  selected?: string;
  onSelect: (iso: string) => void;
};

function scoreColor(score: number | undefined) {
  if (score === undefined) return "#dfe6ec";
  if (score >= 80) return "#1559d9";
  if (score >= 65) return "#3d7ddd";
  if (score >= 50) return "#75a9e8";
  if (score >= 35) return "#a8c8ed";
  return "#dce7f7";
}

function project(position: Position) {
  const longitude = position[0] ?? 0;
  const latitude = position[1] ?? 0;
  return [((longitude + 180) / 360) * 1000, ((90 - latitude) / 180) * 500];
}

function ringPath(ring: Position[]) {
  return ring
    .map((position, index) => {
      const [x, y] = project(position);
      return `${index === 0 ? "M" : "L"}${x.toFixed(2)} ${y.toFixed(2)}`;
    })
    .join(" ") + " Z";
}

function geometryPath(geometry: Geometry) {
  const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
  return polygons.flatMap((polygon) => polygon.map(ringPath)).join(" ");
}

export default function WorldMap({ data, selected, onSelect }: WorldMapProps) {
  const [countries, setCountries] = useState<CountryFeature[]>([]);
  const [loadError, setLoadError] = useState("");
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    let active = true;
    fetch("/countries.geojson")
      .then((response) => {
        if (!response.ok) throw new Error(`HTTP ${response.status}`);
        return response.json() as Promise<CountryCollection>;
      })
      .then((collection) => {
        if (active) setCountries(collection.features);
      })
      .catch((error: unknown) => {
        if (active) {
          setLoadError(error instanceof Error ? error.message : "无法加载地图");
        }
      });
    return () => {
      active = false;
    };
  }, []);

  const scores = useMemo(
    () => new Map(data.map((country) => [country.destination_iso3, country.score])),
    [data],
  );
  const viewWidth = 1000 / zoom;
  const viewHeight = 500 / zoom;
  const viewBox = `${(1000 - viewWidth) / 2} ${(500 - viewHeight) / 2} ${viewWidth} ${viewHeight}`;

  if (loadError) {
    return <div className="map map-message">Map data failed to load: {loadError}</div>;
  }

  if (countries.length === 0) {
    return <div className="map map-message">正在加载世界地图…</div>;
  }

  return (
    <div className="map" aria-label="按市场吸引力着色的世界地图">
      <svg
        className="world-map-svg"
        viewBox={viewBox}
        role="img"
        aria-label="按市场吸引力着色的世界地图"
        preserveAspectRatio="xMidYMid meet"
      >
        <rect x="-500" y="-250" width="2000" height="1000" fill="#eef3f7" />
        <g>
          {countries.map((country, index) => {
            const iso = country.properties.ISO_A3 ?? `country-${index}`;
            const name = country.properties.NAME ?? iso;
            const isSelected = iso === selected;
            return (
              <path
                key={`${iso}-${index}`}
                d={geometryPath(country.geometry)}
                fill={scoreColor(scores.get(iso))}
                stroke={isSelected ? "#0b3b91" : "#ffffff"}
                strokeWidth={isSelected ? 2.2 / zoom : 0.65 / zoom}
                vectorEffect="non-scaling-stroke"
                fillRule="evenodd"
                className={scores.has(iso) ? "map-country map-country-active" : "map-country"}
                onClick={() => scores.has(iso) && onSelect(iso)}
              >
                <title>{name}{scores.has(iso) ? ` · Score ${scores.get(iso)?.toFixed(0)}` : ""}</title>
              </path>
            );
          })}
        </g>
      </svg>
      <div className="map-controls" aria-label="地图缩放控制">
        <button type="button" onClick={() => setZoom((value) => Math.min(3, value + 0.5))} aria-label="放大">+</button>
        <button type="button" onClick={() => setZoom((value) => Math.max(1, value - 0.5))} aria-label="缩小">−</button>
      </div>
    </div>
  );
}
