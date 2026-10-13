import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
  type PointerEvent as ReactPointerEvent,
} from "react";
import {
  AlignCenterHorizontal,
  Box,
  Check,
  Copy,
  Download,
  Eye,
  EyeOff,
  Grid3X3,
  Hand,
  Layers3,
  Lock,
  Maximize2,
  MousePointer2,
  Move3d,
  PenLine,
  Plus,
  Redo2,
  Ruler,
  ScanSearch,
  Scissors,
  Search,
  Settings2,
  Sparkles,
  ArrowRight,
  Trash2,
  Undo2,
  ZoomIn,
  ZoomOut,
  Wrench,
} from "lucide-react";
import type { ConceptConfig, InstalledMaterial } from "../lib/aeroEngine";
import { buildBillOfMaterialsCsv } from "../lib/engineeringExports";
import { droneCatalog, type DroneCatalogDesign } from "../lib/droneCatalog";
import { dronePartCatalog, type DronePartDefinition } from "../lib/droneParts";
import { manufacturerPartCatalog } from "../lib/manufacturerParts";
import { ParametricDronePreview } from "./ParametricDronePreview";
import { PhysicalDroneModel } from "./PhysicalDroneModel";
import { EngineeringDronePlate } from "./EngineeringDronePlate";
import { DroneBehaviorPanel } from "./DroneBehaviorPanel";
import { PayloadMissionWorkbench } from "./PayloadMissionWorkbench";
import "./design-studio-physical.css";

type Tool = "select" | "pan" | "measure" | "annotate" | "cut";
type ViewMode = "top" | "side" | "front";
type PartKind =
  | "body"
  | "wing"
  | "payload"
  | "motor"
  | "avionics"
  | "landing-gear";
type Constraint = "free" | "center-x" | "center-y" | "symmetric";
type StudioPart = {
  id: string;
  label: string;
  kind: PartKind;
  layer: string;
  x: number;
  y: number;
  width: number;
  height: number;
  rotation: number;
  scale: number;
  massKg: number;
  locked: boolean;
  visible: boolean;
  constraint: Constraint;
  manufacturer?: string;
  partNumber?: string;
  dimensions?: string;
  interfaces?: string;
  catalogSource?: string;
  manufacturerDataStatus?: string;
  dragAreaM2?: number;
  powerDrawW?: number;
  connectedTo?: string;
};
type Annotation = { id: string; x: number; y: number; text: string };
type Snapshot = {
  parts: StudioPart[];
  annotations: Annotation[];
  zoom: number;
  view: ViewMode;
  message: string;
};

const layerLabels = [
  "Structure",
  "Voilure",
  "Propulsion",
  "Avionique",
  "Charge utile",
  "Train",
];
const manualPartTemplates: Array<{
  kind: PartKind;
  label: string;
  width: number;
  height: number;
  massKg: number;
}> = [
  { kind: "body", label: "Fuselage", width: 190, height: 54, massKg: 0.45 },
  {
    kind: "wing",
    label: "Aile / plan porteur",
    width: 230,
    height: 44,
    massKg: 0.28,
  },
  {
    kind: "motor",
    label: "Moteur / rotor",
    width: 74,
    height: 52,
    massKg: 0.16,
  },
  {
    kind: "avionics",
    label: "Avionique / contrôleur",
    width: 76,
    height: 46,
    massKg: 0.12,
  },
  {
    kind: "payload",
    label: "Capteur / charge utile",
    width: 88,
    height: 56,
    massKg: 0.25,
  },
  {
    kind: "landing-gear",
    label: "Train / support",
    width: 94,
    height: 38,
    massKg: 0.1,
  },
];
const kindLabels: Record<PartKind, string> = {
  body: "Structure",
  wing: "Voilure",
  payload: "Charge utile",
  motor: "Propulsion",
  avionics: "Avionique",
  "landing-gear": "Train",
};
const estimatedDragArea = (kind: PartKind) => ({ body: 0.012, wing: 0.035, payload: 0.014, motor: 0.006, avionics: 0.003, "landing-gear": 0.01 })[kind];
const estimatedAuxPower = (kind: PartKind) => ({ body: 0, wing: 0, payload: 8, motor: 0, avionics: 4, "landing-gear": 0 })[kind];
const defaultBus = (kind: PartKind) => kind === "payload" ? "BUS-PAYLOAD" : kind === "avionics" ? "BUS-DATA" : kind === "motor" ? "BUS-POWER" : "FRAME";
const clamp = (value: number, min: number, max: number) =>
  Math.max(min, Math.min(max, value));
function starterPartsFor(
  config: ConceptConfig,
  profile?: DroneCatalogDesign
): StudioPart[] {
  const motorCount = Math.max(
    1,
    Math.round(config.motorCount ?? profile?.configuration.motorCount ?? 1)
  );
  const architecture =
    profile?.family ??
    config.modelType ??
    config.airframe ??
    "Architecture à configurer";
  const fixedWing =
    config.airframe === "fixed-wing" || config.airframe === "vtol";
  return [
    {
      id: "studio-fuselage",
      label: `${architecture} · fuselage`,
      kind: "body",
      layer: "Structure",
      x: 50,
      y: 52,
      width: 220,
      height: 58,
      rotation: 0,
      scale: 1,
      massKg: Math.max(0.4, config.fuselageLength * 0.45),
      locked: false,
      visible: true,
      constraint: "center-x",
    },
    ...(fixedWing
      ? [
          {
            id: "studio-wing",
            label: "Voilure principale",
            kind: "wing" as PartKind,
            layer: "Structure",
            x: 50,
            y: 43,
            width: 360,
            height: 32,
            rotation: 0,
            scale: 1,
            massKg: Math.max(0.25, config.wingspan * 0.22),
            locked: false,
            visible: true,
            constraint: "center-x" as Constraint,
          },
        ]
      : []),
    {
      id: "studio-propulsion",
      label: `${motorCount} moteur(s) · propulsion`,
      kind: "motor",
      layer: "Propulsion",
      x: 50,
      y: fixedWing ? 57 : 50,
      width: 100,
      height: 42,
      rotation: 0,
      scale: 1,
      massKg: Math.max(0.15, motorCount * 0.12),
      locked: false,
      visible: true,
      constraint: "free",
    },
    {
      id: "studio-avionics",
      label: "Avionique de bord",
      kind: "avionics",
      layer: "Avionique",
      x: 50,
      y: 67,
      width: 86,
      height: 38,
      rotation: 0,
      scale: 1,
      massKg: 0.18,
      locked: false,
      visible: true,
      constraint: "free",
    },
    {
      id: "studio-payload",
      label: "Charge utile",
      kind: "payload",
      layer: "Charge utile",
      x: 50,
      y: 76,
      width: 76,
      height: 42,
      rotation: 0,
      scale: 1,
      massKg: Math.max(0.1, config.payloadKg),
      locked: false,
      visible: true,
      constraint: "free",
    },
  ];
}
function kindForCategory(category?: InstalledMaterial["category"]): PartKind {
  return category === "payload"
    ? "payload"
    : category === "propulsion"
      ? "motor"
      : category === "avionics"
        ? "avionics"
        : category === "landing-gear" || category === "safety"
          ? "landing-gear"
          : category === "airframe"
            ? "body"
            : "body";
}
function materialToPart(
  material: InstalledMaterial,
  index: number
): StudioPart {
  const kind: PartKind = kindForCategory(material.category);
  return {
    id: material.id,
    label: material.label,
    kind,
    layer: material.layer ?? kindLabels[kind],
    x: material.offsetX === undefined ? 50 + index * 5 : 50 + material.offsetX,
    y: material.offsetY === undefined ? 50 : 50 + material.offsetY,
    width: kind === "payload" ? 70 : 150,
    height: kind === "payload" ? 42 : 54,
    rotation: 0,
    scale: material.scale ?? 1,
    massKg: material.massKg,
    locked: false,
    visible: true,
    constraint: "free",
    manufacturer: material.manufacturer,
    partNumber: material.partNumber,
    dimensions: material.dimensions,
    interfaces: material.interfaces,
    catalogSource: material.catalogSource,
    manufacturerDataStatus: material.manufacturerDataStatus,
    dragAreaM2: material.dragAreaM2 ?? estimatedDragArea(kind),
    powerDrawW: material.powerDrawW ?? estimatedAuxPower(kind),
    connectedTo: material.connectedTo ?? defaultBus(kind),
  };
}
function materialsSignature(materials?: InstalledMaterial[]) {
  return JSON.stringify(
    (materials ?? []).map(item => ({
      id: item.id,
      label: item.label,
      massKg: item.massKg,
      quantity: item.quantity ?? 1,
      category: item.category,
      layer: item.layer,
      offsetX: item.offsetX ?? 0,
      offsetY: item.offsetY ?? 0,
      scale: item.scale ?? 1,
      manufacturer: item.manufacturer,
      partNumber: item.partNumber,
      dragAreaM2: item.dragAreaM2 ?? null,
      powerDrawW: item.powerDrawW ?? null,
      connectedTo: item.connectedTo ?? null,
    }))
  );
}
function partsToMaterials(parts: StudioPart[]): InstalledMaterial[] {
  return parts.map(part => ({
    id: part.id,
    label: part.label,
    layer: part.layer,
    use: "Objet constructible dans la nomenclature",
    massKg: part.massKg,
    quantity: 1,
    geometry:
      part.kind === "wing"
        ? "skin"
        : part.kind === "payload"
          ? "mount"
          : "core",
    category:
      part.kind === "payload"
        ? "payload"
        : part.kind === "motor"
          ? "propulsion"
          : part.kind === "avionics"
            ? "avionics"
            : "airframe",
    manufacturer: part.manufacturer,
    partNumber: part.partNumber,
    dimensions: part.dimensions,
    interfaces: part.interfaces,
    catalogSource:
      part.catalogSource === "manufacturer"
        ? "manufacturer"
        : part.catalogSource === "user"
          ? "user"
          : "concept",
    manufacturerDataStatus:
      part.manufacturerDataStatus === "verified" ? "verified" : "estimate",
    dragAreaM2: part.dragAreaM2 ?? estimatedDragArea(part.kind),
    powerDrawW: part.powerDrawW ?? estimatedAuxPower(part.kind),
    connectedTo: part.connectedTo ?? defaultBus(part.kind),
    offsetX: Number((part.x - 50).toFixed(2)),
    offsetY: Number((part.y - 50).toFixed(2)),
    scale: part.scale,
  }));
}
function download(filename: string, content: string, type: string) {
  const blob = new Blob([content], { type });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  window.setTimeout(() => URL.revokeObjectURL(url), 800);
}

export function DesignStudioView({
  config,
  setConfig,
  activeProfile,
  onSelectProfile,
}: {
  config: ConceptConfig;
  setConfig: (value: ConceptConfig) => void;
  activeProfile?: DroneCatalogDesign;
  onSelectProfile?: (design: DroneCatalogDesign) => void;
}) {
  const initialParts = useMemo(
    () =>
      config.installedMaterials?.length
        ? config.installedMaterials.map(materialToPart)
        : starterPartsFor(config, activeProfile),
    [config, activeProfile]
  );
  const [parts, setParts] = useState<StudioPart[]>(initialParts);
  const [architectureQuery, setArchitectureQuery] = useState("");
  const [partQuery, setPartQuery] = useState("");
  const profileRef = useRef(config.platformProfile ?? config.airframe);
  const publishedMaterialsRef = useRef(
    materialsSignature(config.installedMaterials)
  );
  const publishedLayersRef = useRef(JSON.stringify(config.studioLayers ?? []));
  const [selectedId, setSelectedId] = useState(initialParts[0]?.id ?? "body");
  const [layerVisibility, setLayerVisibility] = useState<
    Record<string, boolean>
  >(() => Object.fromEntries(layerLabels.map(label => [label, true])));
  const [customLayers, setCustomLayers] = useState<string[]>(() => [
    ...new Set(
      [
        ...(config.studioLayers ?? []),
        ...(config.installedMaterials ?? []).map(
          material => material.layer ?? ""
        ),
      ].filter(layer => layer && !layerLabels.includes(layer))
    ),
  ]);
  const [layerLocks, setLayerLocks] = useState<Record<string, boolean>>({});
  const [layerNameDraft, setLayerNameDraft] = useState("");
  const [addingLayer, setAddingLayer] = useState(false);
  const documentLayers = [...layerLabels, ...customLayers];
  const [tool, setTool] = useState<Tool>("select");
  const [view, setView] = useState<ViewMode>("top");
  const [renderMode, setRenderMode] = useState<"3d" | "plan">("3d");
  const [zoom, setZoom] = useState(1);
  const [snap, setSnap] = useState(true);
  const [gridSize, setGridSize] = useState(5);
  const [annotations, setAnnotations] = useState<Annotation[]>([]);
  const [history, setHistory] = useState<string[]>([]);
  const [past, setPast] = useState<Snapshot[]>([]);
  const [future, setFuture] = useState<Snapshot[]>([]);
  const [drag, setDrag] = useState<{
    id: string;
    dx: number;
    dy: number;
  } | null>(null);
  const [measureStart, setMeasureStart] = useState<{
    x: number;
    y: number;
  } | null>(null);
  const [measure, setMeasure] = useState("");
  const [activeLayer, setActiveLayer] = useState("Structure");
  const stageRef = useRef<SVGSVGElement | null>(null);
  const panOrigin = useRef<{
    x: number;
    y: number;
    ox: number;
    oy: number;
  } | null>(null);
  const [panOffset, setPanOffset] = useState({ x: 0, y: 0 });
  const announce = useCallback(
    (message: string) =>
      setHistory(current =>
        [
          `${new Date().toLocaleTimeString("fr-FR")} · ${message}`,
          ...current,
        ].slice(0, 12)
      ),
    []
  );
  const fileRef = useRef<HTMLInputElement | null>(null);
  useEffect(() => {
    const profile = config.platformProfile ?? config.airframe;
    const profileChanged = profileRef.current !== profile;
    const incomingSignature = materialsSignature(config.installedMaterials);
    const incomingLayersSignature = JSON.stringify(config.studioLayers ?? []);
    const externalLayersChanged =
      incomingLayersSignature !== publishedLayersRef.current;
    const currentSignature = materialsSignature(partsToMaterials(parts));
    const externalMaterialsChanged =
      incomingSignature !== publishedMaterialsRef.current &&
      incomingSignature !== currentSignature;
    if (profileChanged || externalMaterialsChanged || externalLayersChanged) {
      profileRef.current = profile;
      const next = config.installedMaterials?.length
        ? config.installedMaterials.map(materialToPart)
        : starterPartsFor(config, activeProfile);
      publishedMaterialsRef.current = incomingSignature;
      publishedLayersRef.current = incomingLayersSignature;
      const incomingLayers = [
        ...(config.studioLayers ?? []),
        ...(config.installedMaterials ?? []).map(
          material => material.layer ?? ""
        ),
      ];
      const nextCustomLayers = [
        ...new Set(
          incomingLayers.filter(label => label && !layerLabels.includes(label))
        ),
      ];
      setCustomLayers(nextCustomLayers);
      setLayerVisibility(current => ({
        ...current,
        ...Object.fromEntries(nextCustomLayers.map(label => [label, true])),
      }));
      setParts(next);
      setSelectedId(next[0]?.id ?? "");
      setAnnotations([]);
      setPast([]);
      setFuture([]);
      announce(
        profileChanged
          ? "Profil de conception actualisé depuis l’espace de travail"
          : "Nomenclature actualisée depuis l’espace de travail"
      );
    }
  }, [
    config.platformProfile,
    config.airframe,
    config.installedMaterials,
    config.studioLayers,
    activeProfile,
    parts,
    announce,
  ]);
  const selected = parts.find(part => part.id === selectedId) ?? parts[0];
  const visibleParts = parts.filter(
    part => part.visible && layerVisibility[part.layer] !== false
  );
  const totalMass = parts.reduce(
    (sum, part) => sum + part.massKg * part.scale ** 3,
    0
  );
  const realPartCatalog = useMemo(
    () => [...manufacturerPartCatalog, ...dronePartCatalog],
    []
  );
  const filteredParts = useMemo(() => {
    const query = partQuery.trim().toLocaleLowerCase("fr-FR");
    if (!query) return realPartCatalog;
    return realPartCatalog.filter(item =>
      [
        item.label,
        item.manufacturer,
        item.partNumber,
        item.category,
        item.use,
        item.dimensions,
      ].some(value => value?.toLocaleLowerCase("fr-FR").includes(query))
    );
  }, [partQuery, realPartCatalog]);
  const filteredArchitectures = useMemo(() => {
    const query = architectureQuery.trim().toLocaleLowerCase("fr-FR");
    if (!query) return droneCatalog;
    return droneCatalog.filter(item =>
      [item.label, item.family, item.modelType, item.mission, item.id].some(
        value => value?.toLocaleLowerCase("fr-FR").includes(query)
      )
    );
  }, [architectureQuery]);
  const snapshot = useCallback(
    (message: string): Snapshot => ({
      parts,
      annotations,
      zoom,
      view,
      message,
    }),
    [annotations, parts, view, zoom]
  );
  const syncConfig = useCallback(
    (next: StudioPart[]) => {
      const materials = partsToMaterials(next);
      publishedMaterialsRef.current = materialsSignature(materials);
      setConfig({
        ...config,
        studioLayers: customLayers,
        installedMaterials: materials,
        constructionMassKg: next.reduce(
          (sum, part) => sum + part.massKg * part.scale ** 3,
          0
        ),
      });
    },
    [config, customLayers, setConfig]
  );
  const commit = useCallback(
    (next: StudioPart[], message: string, nextAnnotations = annotations) => {
      setPast(current => [...current.slice(-39), snapshot(message)]);
      setFuture([]);
      setParts(next);
      setAnnotations(nextAnnotations);
      syncConfig(next);
      announce(message);
    },
    [announce, annotations, snapshot, syncConfig]
  );
  const undo = useCallback(() => {
    const previous = past[past.length - 1];
    if (!previous) return;
    setFuture(current => [...current, snapshot("Rétablissement")]);
    setPast(current => current.slice(0, -1));
    setParts(previous.parts);
    setAnnotations(previous.annotations);
    setZoom(previous.zoom);
    setView(previous.view);
    syncConfig(previous.parts);
    announce(`Annulation · ${previous.message}`);
  }, [announce, past, snapshot, syncConfig]);
  const redo = useCallback(() => {
    const next = future[future.length - 1];
    if (!next) return;
    setPast(current => [...current, snapshot("Annulation")]);
    setFuture(current => current.slice(0, -1));
    setParts(next.parts);
    setAnnotations(next.annotations);
    setZoom(next.zoom);
    setView(next.view);
    syncConfig(next.parts);
    announce(`Rétablissement · ${next.message}`);
  }, [announce, future, snapshot, syncConfig]);
  const pointFromEvent = (event: ReactPointerEvent<SVGSVGElement>) => {
    const rect =
      stageRef.current?.getBoundingClientRect() ??
      event.currentTarget.getBoundingClientRect();
    return {
      x: clamp(((event.clientX - rect.left) / rect.width) * 100, 0, 100),
      y: clamp(((event.clientY - rect.top) / rect.height) * 100, 0, 100),
    };
  };
  const snapPoint = (value: number) =>
    snap ? Math.round(value / gridSize) * gridSize : Number(value.toFixed(1));
  const onStagePointerDown = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (tool === "pan") {
      panOrigin.current = {
        x: event.clientX,
        y: event.clientY,
        ox: panOffset.x,
        oy: panOffset.y,
      };
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }
    const point = pointFromEvent(event);
    if (tool === "annotate") {
      const text = window.prompt("Texte de l’annotation", "Point à vérifier");
      if (text) {
        const next = [
          ...annotations,
          { id: String(Date.now()), ...point, text },
        ];
        setPast(current => [
          ...current.slice(-39),
          snapshot("Annotation précédente"),
        ]);
        setAnnotations(next);
        announce(`Annotation ajoutée · ${text}`);
      }
      return;
    }
    if (tool === "measure") {
      if (!measureStart) setMeasureStart(point);
      else {
        const distance = Math.hypot(
          point.x - measureStart.x,
          point.y - measureStart.y
        );
        setMeasure(
          `${distance.toFixed(1)} unités écran · ${((distance / 100) * Math.max(config.wingspan, 1)).toFixed(2)} m estimés`
        );
        setMeasureStart(null);
        announce(`Mesure créée · ${distance.toFixed(1)} unités écran`);
      }
    }
  };
  const onPartPointerDown = (
    event: ReactPointerEvent<SVGGElement>,
    part: StudioPart
  ) => {
    event.stopPropagation();
    setSelectedId(part.id);
    if (part.locked || layerLocks[part.layer]) return;
    if (tool === "cut") {
      if (parts.length > 1)
        commit(
          parts.filter(item => item.id !== part.id),
          `Élément retiré · ${part.label}`
        );
      return;
    }
    if (tool !== "select") return;
    const point = pointFromEvent(
      event as unknown as ReactPointerEvent<SVGSVGElement>
    );
    setDrag({ id: part.id, dx: point.x - part.x, dy: point.y - part.y });
    (event.currentTarget as SVGGElement).setPointerCapture(event.pointerId);
  };
  const onStagePointerMove = (event: ReactPointerEvent<SVGSVGElement>) => {
    if (panOrigin.current) {
      setPanOffset({
        x: panOrigin.current.ox + event.clientX - panOrigin.current.x,
        y: panOrigin.current.oy + event.clientY - panOrigin.current.y,
      });
      return;
    }
    if (!drag) return;
    const point = pointFromEvent(event);
    const next = parts.map(part =>
      part.id === drag.id
        ? {
            ...part,
            x: clamp(snapPoint(point.x - drag.dx), 5, 95),
            y: clamp(snapPoint(point.y - drag.dy), 8, 92),
          }
        : part
    );
    setParts(next);
  };
  const onStagePointerUp = () => {
    if (panOrigin.current) {
      panOrigin.current = null;
      return;
    }
    if (drag) {
      syncConfig(parts);
      setPast(current => [
        ...current.slice(-39),
        snapshot("Position précédente"),
      ]);
      setFuture([]);
      announce("Pièce repositionnée avec accrochage");
    }
    setDrag(null);
  };
  const changeSelected = (patch: Partial<StudioPart>, message: string) => {
    if (!selected) return;
    commit(
      parts.map(part =>
        part.id === selected.id ? { ...part, ...patch } : part
      ),
      message
    );
  };
  const addCatalogPart = (item: DronePartDefinition) => {
    const kind = kindForCategory(item.category);
    const index = parts.length;
    const part: StudioPart = {
      id: `${item.id}-${Date.now()}`,
      label: item.label,
      kind,
      layer: kindLabels[kind],
      x: clamp(50 + ((index % 3) - 1) * 12, 5, 95),
      y: clamp(32 + ((index * 9) % 55), 8, 92),
      width:
        kind === "body"
          ? 170
          : kind === "payload"
            ? 92
            : kind === "motor"
              ? 84
              : 110,
      height: kind === "body" ? 58 : kind === "motor" ? 46 : 42,
      rotation: 0,
      scale: 1,
      massKg: item.massKg,
      locked: false,
      visible: true,
      constraint: kind === "body" ? "center-x" : "free",
      manufacturer: item.manufacturer,
      partNumber: item.partNumber,
      dimensions: item.dimensions,
      interfaces: item.interfaces,
      catalogSource: item.catalogSource ?? "concept",
      manufacturerDataStatus: item.manufacturerDataStatus ?? "estimate",
    };
    commit([...parts, part], `Référence ajoutée · ${item.label}`);
    setSelectedId(part.id);
  };
  const addManualPart = (template: (typeof manualPartTemplates)[number]) => {
    if (layerLocks[activeLayer]) {
      announce(`Ajout refusé · le calque ${activeLayer} est verrouillé`);
      return;
    }
    const ordinal =
      parts.filter(part => part.kind === template.kind).length + 1;
    const part: StudioPart = {
      id: `user-${template.kind}-${Date.now()}`,
      label: `${template.label} ${ordinal}`,
      kind: template.kind,
      layer: activeLayer,
      x: 50,
      y: clamp(37 + ((parts.length * 11) % 45), 8, 92),
      width: template.width,
      height: template.height,
      rotation: 0,
      scale: 1,
      massKg: template.massKg,
      locked: false,
      visible: true,
      constraint:
        template.kind === "body" || template.kind === "wing"
          ? "center-x"
          : "free",
      catalogSource: "user",
      manufacturerDataStatus: "estimate",
    };
    commit(
      [...parts, part],
      `Composant manuel ajouté · ${part.label} · masse à qualifier`
    );
    setSelectedId(part.id);
  };
  const createCustomLayer = () => {
    const name = layerNameDraft.trim();
    if (!name) return;
    if (
      documentLayers.some(
        label =>
          label.toLocaleLowerCase("fr-FR") === name.toLocaleLowerCase("fr-FR")
      )
    ) {
      announce(`Calque non créé · « ${name} » existe déjà`);
      return;
    }
    setCustomLayers(current => [...current, name]);
    setConfig({ ...config, studioLayers: [...customLayers, name] });
    setLayerVisibility(current => ({ ...current, [name]: true }));
    setActiveLayer(name);
    setLayerNameDraft("");
    setAddingLayer(false);
    announce(`Calque personnalisé créé · ${name}`);
  };
  const duplicateSelected = () => {
    if (!selected) return;
    const copy = {
      ...selected,
      id: `${selected.id}-copy-${Date.now()}`,
      label: `${selected.label} copie`,
      x: clamp(selected.x + gridSize, 5, 95),
      y: clamp(selected.y + gridSize, 8, 92),
      locked: false,
    };
    commit([...parts, copy], `Pièce dupliquée · ${selected.label}`);
    setSelectedId(copy.id);
  };
  const deleteSelected = () => {
    if (!selected || parts.length <= 1) return;
    const next = parts.filter(part => part.id !== selected.id);
    commit(next, `Pièce supprimée · ${selected.label}`);
    setSelectedId(next[0].id);
  };
  const exportStudio = () => {
    download(
      "aeromind-studio-design.json",
      JSON.stringify(
        {
          schema: "aeromind-studio-v3",
          config,
          parts,
          annotations,
          view,
          customLayers,
          exportedAt: new Date().toISOString(),
        },
        null,
        2
      ),
      "application/json"
    );
    announce("Document paramétrique exporté");
  };
  const exportBom = () => {
    download(
      "aeromind-studio-bom.csv",
      buildBillOfMaterialsCsv(config, partsToMaterials(parts)),
      "text/csv;charset=utf-8"
    );
    announce("Nomenclature CSV exportée");
  };
  const harmonizeAssembly = () => {
    if (!parts.length) {
      announce("Harmonisation impossible · aucune pièce dans le document");
      return;
    }
    const next = parts.map((part, index) => ({
      ...part,
      x: 50,
      y: clamp(34 + index * 10, 8, 92),
      constraint:
        part.kind === "body" || part.kind === "wing"
          ? ("center-x" as Constraint)
          : part.constraint,
    }));
    commit(next, "Assemblage harmonisé · axes et espacement recalculés");
  };
  const assemblyReview = () => {
    const missingLayers = documentLayers.filter(
      label => !parts.some(part => part.layer === label)
    );
    announce(
      missingLayers.length
        ? `Revue fabrication · calques à compléter : ${missingLayers.join(", ")}`
        : "Revue fabrication · calques couverts, nomenclature prête"
    );
  };
  const centerSelected = () => {
    if (!selected) {
      announce("Centrage impossible · aucune pièce sélectionnée");
      return;
    }
    changeSelected({ x: 50, y: 50 }, `Pièce centrée · ${selected.label}`);
  };
  const fitAssembly = () => {
    setZoom(1);
    setView("top");
    announce("Vue ajustée · assemblage complet");
  };
  const toggleAllParts = () => {
    const nextVisible = parts.some(
      part => !part.visible || layerVisibility[part.layer] === false
    );
    setParts(current =>
      current.map(part => ({ ...part, visible: nextVisible }))
    );
    setLayerVisibility(
      Object.fromEntries(documentLayers.map(label => [label, true]))
    );
    announce(
      nextVisible ? "Toutes les pièces affichées" : "Toutes les pièces masquées"
    );
  };
  const importStudio = async (file?: File) => {
    if (!file) {
      announce("Import annulé");
      return;
    }
    try {
      const payload = JSON.parse(await file.text()) as {
        parts?: StudioPart[];
        annotations?: Annotation[];
        config?: ConceptConfig;
        zoom?: number;
        view?: ViewMode;
        customLayers?: string[];
      };
      if (!Array.isArray(payload.parts)) throw new Error("parts absent");
      setParts(payload.parts);
      setAnnotations(payload.annotations ?? []);
      setZoom(payload.zoom ?? 1);
      setView(payload.view ?? "top");
      setCustomLayers(payload.customLayers ?? []);
      setLayerVisibility(
        Object.fromEntries(
          [...layerLabels, ...(payload.customLayers ?? [])].map(label => [
            label,
            true,
          ])
        )
      );
      setLayerLocks({});
      const importedMaterials = partsToMaterials(payload.parts);
      publishedMaterialsRef.current = materialsSignature(importedMaterials);
      setConfig({
        ...config,
        ...(payload.config ?? {}),
        installedMaterials: importedMaterials,
        constructionMassKg: payload.parts.reduce(
          (sum, part) => sum + part.massKg * part.scale ** 3,
          0
        ),
      });
      setPast([]);
      setFuture([]);
      announce(`Document chargé · ${file.name}`);
    } catch {
      announce("Import refusé · document Studio non conforme");
    }
  };
  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.target as HTMLElement)?.tagName === "INPUT") return;
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === "z") {
        event.preventDefault();
        event.shiftKey ? redo() : undo();
      } else if (
        (event.ctrlKey || event.metaKey) &&
        event.key.toLowerCase() === "y"
      ) {
        event.preventDefault();
        redo();
      } else if (event.key === "Delete") deleteSelected();
      else if (event.key === "Escape") setDrag(null);
      else if (event.key.toLowerCase() === "g") setSnap(current => !current);
      else if (event.key.toLowerCase() === "r" && selected)
        changeSelected({ rotation: selected.rotation + 15 }, "Rotation +15°");
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  });
  const tools: Array<{ id: Tool; label: string; icon: typeof MousePointer2 }> =
    [
      { id: "select", label: "Sélection", icon: MousePointer2 },
      { id: "pan", label: "Pan", icon: Hand },
      { id: "measure", label: "Mesurer", icon: Ruler },
      { id: "annotate", label: "Annoter", icon: PenLine },
      { id: "cut", label: "Section", icon: Scissors },
    ];
  const dimensions = [
    { label: "Envergure", value: config.wingspan, field: "wingspan" as const },
    {
      label: "Fuselage",
      value: config.fuselageLength,
      field: "fuselageLength" as const,
    },
    { label: "Corde", value: config.chord, field: "chord" as const },
    {
      label: "Hélice",
      value: config.propDiameter,
      field: "propDiameter" as const,
    },
  ];
  return (
    <div className="view-stack design-studio-view">
      <section className="panel studio-architecture-search-panel">
        <div className="panel-header">
          <div>
            <p className="eyebrow">POSTE CAO / ARCHITECTURES DISPONIBLES</p>
            <h3>Constructeur de maquettes</h3>
            <p className="section-description">
              Recherchez une architecture du catalogue pour l’utiliser comme
              référence de départ. La sélection charge ses paramètres dans le
              Studio et remplace la grande palette.
            </p>
          </div>
          <Search size={16} />
        </div>
        <label className="studio-architecture-search">
          <Search size={16} />
          <input
            value={architectureQuery}
            onChange={event => setArchitectureQuery(event.target.value)}
            placeholder="Rechercher une architecture, une famille ou une mission…"
            aria-label="Rechercher une architecture de drone"
          />
          <span>
            {filteredArchitectures.length} / {droneCatalog.length}
          </span>
        </label>
        <div
          className="studio-architecture-results"
          role="listbox"
          aria-label="Architectures de drones disponibles"
        >
          {filteredArchitectures.map(item => (
            <button
              key={item.id}
              type="button"
              role="option"
              aria-selected={activeProfile?.id === item.id}
              className={activeProfile?.id === item.id ? "is-active" : ""}
              onClick={() => onSelectProfile?.(item)}
            >
              <span className="studio-architecture-result-mark">
                {item.key === "fixed-wing"
                  ? "FW"
                  : item.key === "vtol"
                    ? "VT"
                    : "MR"}
              </span>
              <span>
                <strong>{item.label}</strong>
                <small>
                  {item.family} · {item.modelType}
                </small>
              </span>
              <em>{item.configuration.motorCount ?? 0} moteurs</em>
            </button>
          ))}
          {!filteredArchitectures.length && (
            <p className="studio-architecture-empty">
              Aucune architecture ne correspond à cette recherche.
            </p>
          )}
        </div>
        <div className="studio-search-status">
          <span>
            <strong>
              {activeProfile?.label ?? "Aucune référence sélectionnée"}
            </strong>{" "}
            ·{" "}
            {activeProfile
              ? "référence active"
              : "mode exploration · aucune donnée injectée"}
          </span>
          <span>
            {parts.length} éléments construits · {totalMass.toFixed(2)} kg
          </span>
        </div>
        <div className="studio-suggestion-bar" aria-label="Propositions de constructeur">
          <span><Sparkles size={13} /> PROPOSITIONS RAPIDES</span>
          {["Inspection longue portée", "Multirotor redondant", "VTOL terrain contraint"].map(suggestion => (
            <button key={suggestion} type="button" onClick={() => setArchitectureQuery(suggestion.split(" ")[0])}>
              {suggestion} <ArrowRight size={12} />
            </button>
          ))}
          <span className="studio-filter-hint"><EyeOff size={12} /> Les architectures filtrées restent masquées, jamais supprimées.</span>
        </div>
        <div className="studio-parts-library">
          <div className="studio-parts-library-header">
            <div>
              <p className="eyebrow">BIBLIOTHÈQUE DE PIÈCES RÉELLES</p>
              <strong>Ajouter une référence au modèle</strong>
              <small>
                Les fiches fabricant conservent leur masse documentée ; les
                modules conceptuels sont explicitement marqués comme
                estimations.
              </small>
            </div>
            <span>
              {filteredParts.length} / {realPartCatalog.length}
            </span>
          </div>
          <label className="studio-architecture-search studio-parts-search">
            <Search size={15} />
            <input
              value={partQuery}
              onChange={event => setPartQuery(event.target.value)}
              placeholder="Rechercher une pièce, un fabricant ou une référence…"
              aria-label="Rechercher une pièce réelle"
            />
          </label>
          <div className="studio-part-results">
            {filteredParts.map(item => (
              <button
                key={item.id}
                type="button"
                onClick={() => addCatalogPart(item)}
              >
                <span
                  className={`studio-part-source ${item.catalogSource === "manufacturer" ? "is-verified" : "is-concept"}`}
                >
                  {item.catalogSource === "manufacturer" ? "FAB" : "MOD"}
                </span>
                <span>
                  <strong>{item.label}</strong>
                  <small>
                    {item.manufacturer ?? "AeroMind catalogue"} ·{" "}
                    {item.partNumber ?? item.use}
                  </small>
                </span>
                <em>{item.massKg.toFixed(3)} kg</em>
              </button>
            ))}
            {!filteredParts.length && (
              <p className="studio-architecture-empty">
                Aucune pièce ne correspond à cette recherche.
              </p>
            )}
          </div>
        </div>
      </section>
      <div className="studio-header">
        <div>
          <p className="eyebrow">CONSTRUCTION INSPECTOR / CONFIGURATION CONTROL</p>
          <h2>Inspecteur de construction avancé</h2>
          <p className="section-description">
            Poste d’ingénierie de configuration : nomenclature, calques,
            contraintes, preuves de provenance, inspection 3D, historique et
            export contrôlé.
          </p>
        </div>
        <div className="studio-header-actions">
          <button
            className="secondary-button"
            onClick={() => fileRef.current?.click()}
          >
            <Box size={14} /> Importer document
          </button>
          <button className="secondary-button" onClick={exportBom}>
            <Download size={14} /> BOM CSV
          </button>
          <button className="primary-button" onClick={exportStudio}>
            <Download size={14} /> Export document
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".json,application/json"
            hidden
            onChange={event => void importStudio(event.target.files?.[0])}
          />
        </div>
      </div>
      <section className="construction-command-panel" aria-label="Console de contrôle de construction">
        <div className="construction-command-heading">
          <div><p className="eyebrow">INDUSTRIAL BUILD AUTHORITY / READINESS</p><h3>Tableau de maîtrise de la configuration</h3><span>La décision reste humaine · aucune pièce n’est certifiée automatiquement</span></div>
          <div className={`construction-command-state ${activeProfile ? "is-live" : "is-waiting"}`}><i />{activeProfile ? "CONFIGURATION ACTIVE" : "EN ATTENTE D’ARCHITECTURE"}</div>
        </div>
        <div className="construction-command-kpis">
          <div><small>RÉFÉRENCE CELLULE</small><strong>{activeProfile?.id ?? "—"}</strong><span>{activeProfile?.family ?? "Sélection requise"}</span></div>
          <div><small>NOMENCLATURE</small><strong>{String(parts.length).padStart(2, "0")}</strong><span>{totalMass.toFixed(2)} kg déclarés</span></div>
          <div><small>SOURCES FABRICANT</small><strong>{parts.filter(part => part.catalogSource === "manufacturer").length}/{parts.length || 0}</strong><span>références vérifiables</span></div>
          <div><small>ÉTAT DE REVUE</small><strong>{parts.length && activeProfile ? "REVIEW" : "LOCKED"}</strong><span>validation humaine requise</span></div>
        </div>
        <div className="construction-control-rail"><span><b>01</b> CELLULE</span><i /><span><b>02</b> PIÈCES</span><i /><span><b>03</b> INTERFACES</span><i /><span><b>04</b> PREUVES</span><i /><span><b>05</b> REVUE</span></div>
      </section>
      <div className="studio-engineering-reference">
        <div className="studio-reference-glyph" aria-hidden="true">
          <span />
          <i />
          <b />
        </div>
        <div>
          <p className="eyebrow">RÉFÉRENCE D’INGÉNIERIE INTERNE</p>
          <strong>
            {activeProfile?.label ??
              (config.platformProfile === "deluge-e"
                ? "DELUGE-E"
                : "AEROMIND")}{" "}
            · modèle paramétrique synchronisé
          </strong>
          <small>
            La même fiche, le même identifiant et la même géométrie sont
            utilisés par la Bibliothèque et le Poste de construction.
          </small>
        </div>
        <div className="studio-reference-specs">
          <span>
            {activeProfile?.family ??
              config.modelType?.toUpperCase() ??
              "NON CONFIGURÉ"}
          </span>
          <span>{config.motorCount ?? 0} moteur(s)</span>
          <span>{config.wingspan.toFixed(2)} m d’envergure</span>
        </div>
      </div>
      {activeProfile && (
        <section className="panel studio-source-preview">
          <div className="panel-header">
            <div>
              <p className="eyebrow">APERÇU SOURCE / RÉFÉRENCE ACTIVE</p>
              <h3>
                {activeProfile.label} · {activeProfile.family}
              </h3>
            </div>
            <strong className="calculated-badge">ID {activeProfile.id}</strong>
          </div>
          <div className="studio-source-preview-3d">
            <EngineeringDronePlate
              design={activeProfile}
              status="flying"
              construction={{ parts: parts.length, massKg: totalMass }}
            />
          </div>
        </section>
      )}
      <PayloadMissionWorkbench
        installed={partsToMaterials(parts.filter(part => part.kind === "payload"))}
        onInstall={id => {
          const item = dronePartCatalog.find(part => part.id === id);
          if (item) addCatalogPart(item);
        }}
      />
      <div className="studio-guide-console">
        <div>
          <span className="eyebrow">CONSOLE OPÉRATEUR / STUDIO</span>
          <strong>
            Ordre conseillé : structure → propulsion → avionique → charge utile
          </strong>
          <small>
            Les repères ci-dessous guident l’opérateur ; aucune pièce ou valeur
            n’est ajoutée automatiquement.
          </small>
        </div>
        <div>
          <span>Raccourcis</span>
          <b>G grille</b>
          <b>R rotation</b>
          <b>Del supprimer</b>
          <b>Ctrl+Z annuler</b>
        </div>
      </div>
      <div className="studio-toolbar">
        <div className="studio-tool-group">
          {tools.map(item => {
            const Icon = item.icon;
            return (
              <button
                key={item.id}
                className={`studio-tool ${tool === item.id ? "is-active" : ""}`}
                onClick={() => setTool(item.id)}
              >
                <Icon size={15} />
                {item.label}
              </button>
            );
          })}
          <button
            className={`studio-tool ${snap ? "is-active" : ""}`}
            onClick={() => setSnap(value => !value)}
          >
            <Grid3X3 size={15} /> Grille {snap ? "ON" : "OFF"}
          </button>
        </div>
        <div className="studio-tool-group">
          <button className="studio-tool" onClick={harmonizeAssembly}>
            <Check size={15} /> Harmoniser
          </button>
          <button className="studio-tool" onClick={centerSelected}>
            <AlignCenterHorizontal size={15} /> Centrer
          </button>
          <button className="studio-tool" onClick={fitAssembly}>
            <ScanSearch size={15} /> Ajuster vue
          </button>
          <button className="studio-tool" onClick={toggleAllParts}>
            <Eye size={15} /> Tout afficher
          </button>
          <button className="studio-tool" onClick={assemblyReview}>
            <Box size={15} /> Revue fabrication
          </button>
          <button
            className="studio-tool"
            onClick={undo}
            disabled={!past.length}
          >
            <Undo2 size={15} /> Annuler
          </button>
          <button
            className="studio-tool"
            onClick={redo}
            disabled={!future.length}
          >
            <Redo2 size={15} /> Rétablir
          </button>
          <button className="studio-tool" onClick={duplicateSelected}>
            <Copy size={15} /> Dupliquer
          </button>
          <button className="studio-tool" onClick={deleteSelected}>
            <Trash2 size={15} /> Supprimer
          </button>
          <button
            className="studio-tool"
            onClick={() => setZoom(value => Math.max(0.5, value - 0.1))}
            aria-label="Réduire le modèle"
          >
            <ZoomOut size={15} />
          </button>
          <span className="studio-readout">{Math.round(zoom * 100)}%</span>
          <input
            className="studio-zoom-slider"
            type="range"
            min="0.5"
            max="2.5"
            step="0.05"
            value={zoom}
            onChange={event => setZoom(Number(event.target.value))}
            aria-label="Agrandissement du modèle dans le panneau de construction"
          />
          <button
            className="studio-tool"
            onClick={() => setZoom(value => Math.min(2.5, value + 0.1))}
            aria-label="Agrandir le modèle"
          >
            <ZoomIn size={15} />
          </button>
        </div>
      </div>
      <div className="studio-subtoolbar">
        <div className="studio-view-tabs" role="group" aria-label="Mode de rendu de l’atelier">
          <button className={renderMode === "3d" ? "is-active" : ""} onClick={() => setRenderMode("3d")}>3D · Assemblage</button>
          <button className={renderMode === "plan" ? "is-active" : ""} onClick={() => setRenderMode("plan")}>Plan 2D</button>
        </div>
        <div className="studio-view-tabs">
          {(["top", "side", "front"] as ViewMode[]).map(mode => (
            <button
              key={mode}
              className={view === mode ? "is-active" : ""}
              onClick={() => setView(mode)}
            >
              {mode === "top" ? "Plan" : mode === "side" ? "Profil" : "Face"}
            </button>
          ))}
        </div>
        <label>
          Pas grille{" "}
          <select
            value={gridSize}
            onChange={event => setGridSize(Number(event.target.value))}
          >
            <option value={2.5}>2,5%</option>
            <option value={5}>5%</option>
            <option value={10}>10%</option>
          </select>
        </label>
        <span className="studio-status">
          <Check size={13} /> {past.length} versions · {parts.length} éléments
          choisis · {totalMass.toFixed(2)} kg estimés
        </span>
      </div>
      <div className="studio-workspace studio-workspace-advanced">
        <aside className="studio-layer-panel panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">DOCUMENT DE CONSTRUCTION</p>
              <h3>Calques &amp; pièces</h3>
            </div>
            <button
              type="button"
              className="studio-layer-add-button"
              onClick={() => setAddingLayer(value => !value)}
              aria-label="Créer un calque personnalisé"
              title="Créer un calque personnalisé"
            >
              <Plus size={15} />
            </button>
          </div>
          <div className="studio-layer-stack">
            {documentLayers.map(label => {
              const visible = layerVisibility[label] !== false;
              const locked = layerLocks[label] === true;
              return (
                <div
                  key={label}
                  className={`studio-layer-item ${activeLayer === label ? "is-active" : ""}`}
                >
                  <button
                    type="button"
                    className="studio-layer-row"
                    onClick={() => setActiveLayer(label)}
                    aria-pressed={activeLayer === label}
                    title={`Rendre actif le calque ${label}`}
                  >
                    <span className="studio-layer-icon">
                      <Layers3 size={13} />
                    </span>
                    <span className="studio-layer-name">
                      <strong>{label}</strong>
                      <small>
                        {parts.filter(part => part.layer === label).length}{" "}
                        objets
                      </small>
                    </span>
                  </button>
                  <button
                    type="button"
                    className="studio-layer-quick-button"
                    aria-label={`${visible ? "Masquer" : "Afficher"} ${label}`}
                    title={`${visible ? "Masquer" : "Afficher"} ${label}`}
                    onClick={event => {
                      setLayerVisibility(current => ({
                        ...current,
                        [label]: !visible,
                      }));
                    }}
                  >
                    {visible ? <Eye size={14} /> : <EyeOff size={14} />}
                  </button>
                  <button
                    type="button"
                    className={`studio-layer-quick-button ${locked ? "is-locked" : ""}`}
                    aria-label={`${locked ? "Déverrouiller" : "Verrouiller"} ${label}`}
                    title={`${locked ? "Déverrouiller" : "Verrouiller"} ${label}`}
                    onClick={() =>
                      setLayerLocks(current => ({
                        ...current,
                        [label]: !locked,
                      }))
                    }
                  >
                    <Lock size={13} />
                  </button>
                </div>
              );
            })}
          </div>
          {addingLayer && (
            <form
              className="studio-layer-create"
              onSubmit={event => {
                event.preventDefault();
                createCustomLayer();
              }}
            >
              <input
                autoFocus
                value={layerNameDraft}
                onChange={event => setLayerNameDraft(event.target.value)}
                placeholder="Ex. Câblage, composites…"
                aria-label="Nom du nouveau calque"
              />
              <button type="submit" disabled={!layerNameDraft.trim()}>
                <Plus size={13} /> Ajouter
              </button>
            </form>
          )}
          <div className="studio-layer-note">
            Calque actif : <strong>{activeLayer}</strong>
            <br />
            {layerLocks[activeLayer]
              ? "Verrouillé · déverrouillez-le pour ajouter ou déplacer une pièce."
              : "Les pièces masquées restent incluses dans la nomenclature."}
          </div>
          <section className="studio-construction-palette">
            <div className="studio-palette-header">
              <p className="eyebrow">OUTILS DE CONSTRUCTION</p>
              <span>MANUEL</span>
            </div>
            <p>
              Créer une géométrie de travail dans le calque actif, puis la
              déplacer et l’ajuster.
            </p>
            <div className="studio-manual-part-grid">
              {manualPartTemplates.map(template => (
                <button
                  key={template.kind}
                  type="button"
                  disabled={Boolean(layerLocks[activeLayer])}
                  onClick={() => addManualPart(template)}
                  title={`Ajouter ${template.label} au calque ${activeLayer}`}
                >
                  <Plus size={12} />
                  <span>{template.label}</span>
                </button>
              ))}
            </div>
            <small>
              Géométries utilisateur · masses initiales indicatives · à
              qualifier avant fabrication.
            </small>
          </section>
        </aside>
        <section className="panel studio-canvas-panel">
          {!activeProfile ? (
            <div className="studio-unselected-state" role="status"><Box size={30} /><strong>Aucun drone actif dans le Studio</strong><span>Recherchez puis sélectionnez une architecture dans le registre ci-dessus pour initialiser le poste de construction.</span><em>USER ACTION REQUIRED · NO MODEL LOADED</em></div>
          ) : renderMode === "plan" ? (
          <svg
            ref={stageRef}
            className="studio-svg-canvas"
            viewBox="0 0 1000 600"
            onWheel={event => {
              event.preventDefault();
              setZoom(value =>
                clamp(value + (event.deltaY < 0 ? 0.1 : -0.1), 0.5, 2.5)
              );
            }}
            onPointerDown={onStagePointerDown}
            onPointerMove={onStagePointerMove}
            onPointerUp={onStagePointerUp}
            style={{
              transform: `translate(${panOffset.x}px, ${panOffset.y}px) scale(${zoom})`,
              transformOrigin: "50% 50%",
              cursor:
                tool === "pan"
                  ? "grab"
                  : tool === "cut"
                    ? "crosshair"
                    : undefined,
            }}
          >
            <defs>
              <pattern
                id="studio-grid-advanced"
                width={gridSize * 2}
                height={gridSize * 2}
                patternUnits="userSpaceOnUse"
              >
                <path
                  d={`M ${gridSize * 2} 0 L 0 0 0 ${gridSize * 2}`}
                  fill="none"
                  stroke="rgba(117,226,220,.14)"
                  strokeWidth="1"
                />
              </pattern>
            </defs>
            <rect width="1000" height="600" fill="#061319" />
            <rect width="1000" height="600" fill="url(#studio-grid-advanced)" />
            <line
              x1="500"
              y1="35"
              x2="500"
              y2="565"
              className="studio-centerline"
            />
            <line
              x1="35"
              y1="300"
              x2="965"
              y2="300"
              className="studio-centerline"
            />
            {visibleParts.length ? (
              visibleParts.map(part => (
                <g
                  key={part.id}
                  transform={`translate(${part.x * 10} ${part.y * 6}) rotate(${part.rotation}) scale(${part.scale})`}
                  onPointerDown={event => onPartPointerDown(event, part)}
                  className={`studio-svg-part ${selectedId === part.id ? "is-selected" : ""}`}
                >
                  {part.kind === "wing" ? (
                    <path
                      d={`M ${-part.width / 2} 0 L ${-part.width * 0.27} ${-part.height / 2} L ${part.width / 2} ${-part.height * 0.34} L ${part.width * 0.34} 0 L ${part.width / 2} ${part.height * 0.34} L ${-part.width * 0.27} ${part.height / 2} Z`}
                      className="studio-shape studio-shape-wing"
                    />
                  ) : part.kind === "motor" ? (
                    <g className="studio-shape studio-shape-motor">
                      <circle r={Math.min(part.width, part.height) / 2} />
                      <circle r={Math.min(part.width, part.height) / 4} />
                      <path
                        d={`M ${-part.width * 0.4} 0 H ${part.width * 0.4}`}
                      />
                    </g>
                  ) : part.kind === "landing-gear" ? (
                    <g className="studio-shape studio-shape-landing-gear">
                      <path
                        d={`M ${-part.width / 2} ${-part.height * 0.3} L ${part.width * 0.28} ${part.height * 0.3} L ${part.width / 2} ${part.height * 0.3}`}
                      />
                      <path
                        d={`M ${-part.width * 0.28} ${-part.height / 2} L ${-part.width * 0.05} ${part.height / 2} M ${part.width * 0.28} ${-part.height / 2} L ${part.width * 0.05} ${part.height / 2}`}
                      />
                    </g>
                  ) : (
                    <rect
                      x={-part.width / 2}
                      y={-part.height / 2}
                      width={part.width}
                      height={part.height}
                      rx={
                        part.kind === "body"
                          ? part.height / 2
                          : part.kind === "avionics"
                            ? 4
                            : 9
                      }
                      className={`studio-shape studio-shape-${part.kind}`}
                    />
                  )}
                  <text
                    x="0"
                    y="4"
                    textAnchor="middle"
                    className="studio-part-label"
                  >
                    {part.label}
                  </text>
                  <circle
                    cx={part.width / 2}
                    cy="0"
                    r="6"
                    className="studio-grip"
                  />
                  {selectedId === part.id && (
                    <rect
                      x={-part.width / 2 - 8}
                      y={-part.height / 2 - 8}
                      width={part.width + 16}
                      height={part.height + 16}
                      className="studio-selection-box"
                    />
                  )}
                </g>
              ))
            ) : (
              <text
                x="500"
                y="300"
                textAnchor="middle"
                className="studio-empty-label"
              >
                PLAN VIDE · ajoutez un élément depuis la palette
              </text>
            )}
            {annotations.map(annotation => (
              <g key={annotation.id}>
                <circle
                  cx={annotation.x * 10}
                  cy={annotation.y * 6}
                  r="8"
                  className="studio-annotation-dot"
                />
                <text
                  x={annotation.x * 10 + 12}
                  y={annotation.y * 6 + 4}
                  className="studio-annotation-text"
                >
                  {annotation.text}
                </text>
              </g>
            ))}
            {measure && (
              <text x="24" y="570" className="studio-measure-text">
                MESURE : {measure}
              </text>
            )}
            <text x="24" y="30" className="studio-hud-text">
              AEROMIND STUDIO · {view.toUpperCase()} · {tool.toUpperCase()} ·
              SNAP {snap ? gridSize + "%" : "OFF"}
            </text>
          </svg>
          ) : (
            <div className="studio-physical-stage">
              <div className="studio-physical-stage-hud"><span>ASSEMBLAGE PHYSIQUE · WEBGL</span><small>{visibleParts.length} pièces visibles · masse estimée {totalMass.toFixed(2)} kg · matériaux PBR</small></div>
              <EngineeringDronePlate
                design={activeProfile}
                status="flying"
                construction={{ parts: visibleParts.length, massKg: totalMass }}
              />
              <div className="studio-3d-selection-list" aria-label="Sélectionner une pièce pour la configurer">
                {visibleParts.map(part => <button key={part.id} className={selectedId === part.id ? "is-active" : ""} onClick={() => setSelectedId(part.id)}><span>{part.label}</span><small>{part.massKg.toFixed(2)} kg · {part.connectedTo ?? defaultBus(part.kind)}</small></button>)}
                {!visibleParts.length && <small>Ajoutez une pièce dans la palette pour commencer l’assemblage.</small>}
              </div>
            </div>
          )}
          <DroneBehaviorPanel configuration={config} context="studio" state="ASSEMBLAGE NUMÉRIQUE" />
          <div className="studio-canvas-footer">
            <span>
              Vue : <strong>{renderMode === "3d" ? "3D isométrique" : view}</strong>
            </span>
            <span>
              Objet : <strong>{selected?.label ?? "aucun"}</strong>
            </span>
            <span>
              Raccourcis : G grille · R rotation · Del supprimer · Ctrl+Z
              annuler
            </span>
          </div>
        </section>
        <aside className="studio-inspector panel">
          <div className="panel-header">
            <div>
              <p className="eyebrow">INSPECTEUR PARAMÉTRIQUE</p>
              <h3>{selected?.label ?? "Aucune sélection"}</h3>
            </div>
            <Settings2 size={16} />
          </div>
          {selected && (
            <>
              <div className="studio-inspector-actions">
                <button
                  onClick={() =>
                    changeSelected(
                      { locked: !selected.locked },
                      selected.locked
                        ? "Pièce déverrouillée"
                        : "Pièce verrouillée"
                    )
                  }
                >
                  {selected.locked ? <Lock size={14} /> : <Lock size={14} />}{" "}
                  {selected.locked ? "Déverrouiller" : "Verrouiller"}
                </button>
                <button
                  onClick={() =>
                    changeSelected(
                      { visible: !selected.visible },
                      selected.visible ? "Pièce masquée" : "Pièce affichée"
                    )
                  }
                >
                  {selected.visible ? <EyeOff size={14} /> : <Eye size={14} />}{" "}
                  {selected.visible ? "Masquer" : "Afficher"}
                </button>
              </div>
              <label className="studio-field">
                Nom
                <input
                  value={selected.label}
                  onChange={event =>
                    changeSelected({ label: event.target.value }, "Nom modifié")
                  }
                />
              </label>
              <label className="studio-field">
                Calque de construction
                <select
                  value={selected.layer}
                  onChange={event => {
                    const nextLayer = event.target.value;
                    if (layerLocks[nextLayer]) {
                      announce(
                        `Déplacement refusé · le calque ${nextLayer} est verrouillé`
                      );
                      return;
                    }
                    changeSelected(
                      { layer: nextLayer },
                      `Calque affecté · ${nextLayer}`
                    );
                  }}
                >
                  {documentLayers.map(label => (
                    <option
                      key={label}
                      value={label}
                      disabled={layerLocks[label]}
                    >
                      {label}
                    </option>
                  ))}
                </select>
              </label>
              <div className="studio-property-grid">
                <label>
                  X %
                  <input
                    type="number"
                    value={selected.x.toFixed(1)}
                    onChange={event =>
                      changeSelected(
                        { x: clamp(Number(event.target.value), 0, 100) },
                        "Position X modifiée"
                      )
                    }
                  />
                </label>
                <label>
                  Y %
                  <input
                    type="number"
                    value={selected.y.toFixed(1)}
                    onChange={event =>
                      changeSelected(
                        { y: clamp(Number(event.target.value), 0, 100) },
                        "Position Y modifiée"
                      )
                    }
                  />
                </label>
                <label>
                  Largeur visuelle · u.d.
                  <input
                    type="number"
                    min="12"
                    max="520"
                    step="4"
                    value={Math.round(selected.width)}
                    onChange={event =>
                      changeSelected(
                        { width: clamp(Number(event.target.value), 12, 520) },
                        "Largeur graphique modifiée"
                      )
                    }
                  />
                </label>
                <label>
                  Hauteur visuelle · u.d.
                  <input
                    type="number"
                    min="12"
                    max="260"
                    step="4"
                    value={Math.round(selected.height)}
                    onChange={event =>
                      changeSelected(
                        { height: clamp(Number(event.target.value), 12, 260) },
                        "Hauteur graphique modifiée"
                      )
                    }
                  />
                </label>
                <label>
                  Échelle
                  <input
                    type="number"
                    min=".5"
                    max="2"
                    step=".05"
                    value={selected.scale}
                    onChange={event =>
                      changeSelected(
                        { scale: clamp(Number(event.target.value), 0.5, 2) },
                        "Échelle modifiée"
                      )
                    }
                  />
                </label>
                <label>
                  Rotation°
                  <input
                    type="number"
                    value={selected.rotation}
                    onChange={event =>
                      changeSelected(
                        { rotation: Number(event.target.value) },
                        "Rotation modifiée"
                      )
                    }
                  />
                </label>
                <label>
                  Masse kg
                  <input
                    type="number"
                    min="0"
                    step=".01"
                    value={selected.massKg}
                    onChange={event =>
                      changeSelected(
                        { massKg: Math.max(0, Number(event.target.value)) },
                        "Masse modifiée"
                      )
                    }
                  />
                </label>
                <label>
                  Contrainte
                  <select
                    value={selected.constraint}
                    onChange={event =>
                      changeSelected(
                        { constraint: event.target.value as Constraint },
                        "Contrainte modifiée"
                      )
                    }
                  >
                    <option value="free">Libre</option>
                    <option value="center-x">Centré X</option>
                    <option value="center-y">Centré Y</option>
                    <option value="symmetric">Symétrique</option>
                  </select>
                </label>
              </div>
              <label className="studio-field">
                Aire de traînée équivalente estimée · m²
                <input type="number" min="0" step="0.001" value={selected.dragAreaM2 ?? estimatedDragArea(selected.kind)} onChange={event => changeSelected({ dragAreaM2: Math.max(0, Number(event.target.value)) }, "Aire de traînée mise à jour · estimation locale")} />
              </label>
              <label className="studio-field">
                Puissance auxiliaire estimée · W
                <input type="number" min="0" step="0.5" value={selected.powerDrawW ?? estimatedAuxPower(selected.kind)} onChange={event => changeSelected({ powerDrawW: Math.max(0, Number(event.target.value)) }, "Consommation auxiliaire mise à jour · estimation locale")} />
              </label>
              <label className="studio-field">
                Bus logique simulé
                <select value={selected.connectedTo ?? defaultBus(selected.kind)} onChange={event => changeSelected({ connectedTo: event.target.value }, "Connexion logique simulée mise à jour")}>
                  <option value="FRAME">FRAME · structure</option>
                  <option value="BUS-POWER">BUS-POWER · alimentation</option>
                  <option value="BUS-DATA">BUS-DATA · avionique</option>
                  <option value="BUS-PAYLOAD">BUS-PAYLOAD · équipement</option>
                  <option value="ISOLATED">ISOLÉ · non connecté</option>
                </select>
              </label>
              <div
                className={`studio-part-provenance ${selected.catalogSource === "manufacturer" ? "is-catalog" : selected.catalogSource === "user" ? "is-user" : "is-concept"}`}
              >
                {selected.catalogSource === "manufacturer"
                  ? "RÉFÉRENCE FABRICANT · métadonnées produit distinctes de l’échelle graphique."
                  : selected.catalogSource === "user"
                    ? "GÉOMÉTRIE UTILISATEUR · dessin et masse à qualifier, non validés fabrication."
                    : "CONCEPT · paramètres préliminaires, non validés fabrication."}
              </div>
            </>
          )}
          <div className="studio-dimension-list">
            {dimensions.map(item => (
              <div className="studio-dimension" key={item.field}>
                <span>{item.label}</span>
                <strong>
                  {item.value > 0
                    ? `${item.value.toFixed(2)} m`
                    : "À renseigner"}
                </strong>
                <div>
                  <button
                    onClick={() =>
                      setConfig({
                        ...config,
                        [item.field]: Math.max(
                          0,
                          Number((item.value - 0.05).toFixed(2))
                        ),
                      })
                    }
                  >
                    −
                  </button>
                  <button
                    onClick={() =>
                      setConfig({
                        ...config,
                        [item.field]: Number((item.value + 0.05).toFixed(2)),
                      })
                    }
                  >
                    +
                  </button>
                </div>
              </div>
            ))}
          </div>
          <div className="studio-actions">
            <button
              className="secondary-button"
              onClick={() => announce("Instantané versionné créé")}
            >
              <Maximize2 size={14} /> Instantané
            </button>
            <button
              className="secondary-button"
              onClick={undo}
              disabled={!past.length}
            >
              <Undo2 size={14} /> Annuler
            </button>
            <button
              className="secondary-button"
              onClick={redo}
              disabled={!future.length}
            >
              <Redo2 size={14} /> Rétablir
            </button>
          </div>
          <div className="studio-history">
            <p className="eyebrow">JOURNAL / {history.length}</p>
            {history.length ? (
              history.map(item => <span key={item}>{item}</span>)
            ) : (
              <span>Aucune action récente</span>
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}
