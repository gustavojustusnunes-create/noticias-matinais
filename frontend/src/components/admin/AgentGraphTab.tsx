"use client";

import React, { useState, useMemo, useEffect, useCallback } from "react";
import {
  ReactFlow,
  Controls,
  Background,
  MiniMap,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  Position,
  Handle,
  BackgroundVariant,
  MarkerType,
  ReactFlowInstance,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  CheckCircle2,
  Cpu,
  Radio,
  Terminal,
  X,
  Zap,
  Shield,
  Volume2,
  Send,
  Lock,
  Copy,
  Check,
  AlertOctagon,
  FileCode2,
  RotateCcw,
} from "lucide-react";
import { AgentNodeDetail } from "@/lib/adminData";

type GraphFilterLayer = "all" | "langgraph" | "multimodal" | "distribution";

interface CustomNodeData extends AgentNodeDetail {
  isSelected?: boolean;
  isEmergency?: boolean;
  isDimmed?: boolean;
  [key: string]: unknown;
}

function CustomAgentNode({ data }: { data: CustomNodeData }) {
  const isEmergency = Boolean(data.isEmergency);

  const getStatusStyle = () => {
    if (isEmergency) {
      return {
        border: "border-red-500/90 ring-2 ring-red-500/30 shadow-[0_0_25px_rgba(239,68,68,0.3)]",
        badge: "bg-red-500/20 text-red-300 border-red-500/50",
        dot: "bg-red-400 animate-ping",
        label: "SUSPENDED",
      };
    }
    if (data.layer === "langgraph") {
      return {
        border: "border-[#D1BA73]/50 hover:border-[#D1BA73]",
        badge: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
        dot: "bg-emerald-400 animate-pulse",
        label: "ONLINE",
      };
    }
    return {
      border: "border-[#38BDF8]/40 hover:border-[#38BDF8]",
      badge: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
      dot: "bg-emerald-400 animate-pulse",
      label: "ONLINE",
    };
  };

  const colors = getStatusStyle();

  const getIcon = () => {
    switch (data.category) {
      case "ingestion":
        return <Radio className="w-4 h-4 text-sky-400" />;
      case "orchestration":
        return <Cpu className="w-4 h-4 text-sky-400" />;
      case "cognitive":
        return <Zap className="w-4 h-4 text-[#D1BA73]" />;
      case "governance":
        return <Shield className="w-4 h-4 text-[#D1BA73]" />;
      case "multimodal":
        return <Volume2 className="w-4 h-4 text-emerald-400" />;
      case "hitl_gate":
        return <Lock className="w-4 h-4 text-amber-400" />;
      case "delivery":
        return <Send className="w-4 h-4 text-sky-400" />;
    }
  };

  return (
    <div
      className={`w-72 rounded-2xl bg-[#0D131C]/95 backdrop-blur-md border-2 transition-all p-4 shadow-xl cursor-grab active:cursor-grabbing ${
        data.isDimmed ? "opacity-25" : "opacity-100"
      } ${
        data.isSelected && !isEmergency
          ? "border-[#D1BA73] ring-2 ring-[#D1BA73]/40 shadow-[0_0_30px_rgba(209,186,115,0.25)]"
          : colors.border
      }`}
    >
      <Handle
        type="target"
        position={Position.Left}
        id="left-in"
        className="!w-2.5 !h-2.5 !bg-[#38BDF8] !border-2 !border-[#080B0F]"
      />
      <Handle
        type="target"
        position={Position.Top}
        id="top-in"
        className="!w-2.5 !h-2.5 !bg-[#38BDF8] !border-2 !border-[#080B0F]"
      />

      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2 min-w-0">
          <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center shrink-0">
            {getIcon()}
          </div>
          <div className="min-w-0">
            <div className="text-[9px] font-mono uppercase text-[#D1BA73] tracking-wider truncate">
              {data.layerLabel || data.category}
            </div>
            <h4 className="text-xs font-bold text-white tracking-tight leading-none truncate">
              {data.name}
            </h4>
          </div>
        </div>

        <span
          className={`px-2 py-0.5 rounded-full text-[8.5px] font-mono font-bold border flex items-center gap-1 shrink-0 ${colors.badge}`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
          {colors.label}
        </span>
      </div>

      <div className="px-2 py-1 rounded-lg bg-[#080B0F] border border-white/5 text-[10px] font-mono text-[#D1BA73] truncate mb-2">
        {data.modelOrEngine}
      </div>

      <p className="text-[10.5px] text-slate-300 font-medium line-clamp-2 leading-snug mb-2.5">
        {data.description}
      </p>

      {data.category === "delivery" && (
        <div className="grid grid-cols-2 gap-1 pt-2 mb-2 border-t border-white/10 text-[9px] font-mono">
          <span className="px-1.5 py-0.5 rounded bg-white/5 text-sky-300 truncate">📧 Resend API</span>
          <span className="px-1.5 py-0.5 rounded bg-white/5 text-amber-300 truncate">𝕏 Playwright</span>
          <span className="px-1.5 py-0.5 rounded bg-white/5 text-pink-300 truncate">📸 IG Poster</span>
          <span className="px-1.5 py-0.5 rounded bg-white/5 text-emerald-300 truncate">🚀 Vitrine Astro</span>
        </div>
      )}

      <div className="pt-2 border-t border-white/10 flex items-center justify-between text-[9.5px] font-mono text-slate-400">
        <span className="truncate max-w-[155px] text-slate-300">
          📄 {(data.sourceFile || "core/graph_engine.py").split(" ")[0]}
        </span>
        <span className="text-[#38BDF8] font-bold">{data.avgLatencyMs} ms</span>
      </div>

      <Handle
        type="source"
        position={Position.Bottom}
        id="bottom-out"
        className="!w-2.5 !h-2.5 !bg-[#D1BA73] !border-2 !border-[#080B0F]"
      />
      <Handle
        type="source"
        position={Position.Right}
        id="right-out"
        className="!w-2.5 !h-2.5 !bg-[#D1BA73] !border-2 !border-[#080B0F]"
      />
    </div>
  );
}

const nodeTypes = {
  agentNode: CustomAgentNode,
};

interface AgentGraphTabProps {
  nodesData: Record<string, AgentNodeDetail>;
}

const DEFAULT_POSITIONS: Record<string, { x: number; y: number }> = {
  "node-ingestion": { x: 40, y: 60 },
  "node-orchestration": { x: 40, y: 330 },
  "node-cognitive": { x: 390, y: 60 },
  "node-governance": { x: 390, y: 330 },
  "node-multimodal": { x: 740, y: 60 },
  "node-hitl-gate": { x: 740, y: 330 },
  "node-delivery": { x: 1090, y: 185 },
};

export function AgentGraphTab({ nodesData }: AgentGraphTabProps) {
  const [selectedNodeId, setSelectedNodeId] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<GraphFilterLayer>("all");
  const [killSwitchActive, setKillSwitchActive] = useState<boolean>(false);
  const [copiedJson, setCopiedJson] = useState<boolean>(false);
  const [rfInstance, setRfInstance] = useState<ReactFlowInstance | null>(null);

  const selectedNode = selectedNodeId ? nodesData[selectedNodeId] || null : null;

  const isNodeVisibleForFilter = useCallback(
    (node: AgentNodeDetail) => {
      if (activeFilter === "all") return true;
      if (activeFilter === node.layer) return true;
      if (activeFilter === "distribution" && node.id === "node-hitl-gate") return true;
      return false;
    },
    [activeFilter]
  );

  const computedNodes: Node[] = useMemo(() => {
    const orderedIds = [
      "node-ingestion",
      "node-orchestration",
      "node-cognitive",
      "node-governance",
      "node-multimodal",
      "node-hitl-gate",
      "node-delivery",
    ];
    return orderedIds
      .filter((id) => Boolean(nodesData[id]))
      .map((id) => {
        const detail = nodesData[id];
        return {
          id,
          type: "agentNode",
          position: DEFAULT_POSITIONS[id] || { x: 100, y: 100 },
          data: {
            ...detail,
            isSelected: selectedNodeId === id,
            isEmergency: killSwitchActive,
            isDimmed: !isNodeVisibleForFilter(detail),
          },
        };
      });
  }, [nodesData, selectedNodeId, killSwitchActive, isNodeVisibleForFilter]);

  const computedEdges: Edge[] = useMemo(() => {
    const alertStroke = "#EF4444";
    const animated = !killSwitchActive;

    return [
      {
        id: "e-ing-orch",
        source: "node-ingestion",
        sourceHandle: "bottom-out",
        target: "node-orchestration",
        targetHandle: "top-in",
        label: "RSS & Scraping (18)",
        animated,
        style: { stroke: killSwitchActive ? alertStroke : "#38BDF8", strokeWidth: 2.2 },
        labelStyle: { fill: "#E2E8F0", fontSize: 10, fontFamily: "monospace", fontWeight: 700 },
        labelBgStyle: { fill: "#0B0F14", stroke: "#38BDF8", strokeWidth: 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color: killSwitchActive ? alertStroke : "#38BDF8" },
      },
      {
        id: "e-orch-cog",
        source: "node-orchestration",
        sourceHandle: "right-out",
        target: "node-cognitive",
        targetHandle: "left-in",
        label: "Trigger 05:20 BRT",
        animated,
        style: { stroke: killSwitchActive ? alertStroke : "#38BDF8", strokeWidth: 2.2 },
        labelStyle: { fill: "#E2E8F0", fontSize: 10, fontFamily: "monospace", fontWeight: 700 },
        labelBgStyle: { fill: "#0B0F14", stroke: "#38BDF8", strokeWidth: 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color: killSwitchActive ? alertStroke : "#38BDF8" },
      },
      {
        id: "e-cog-gov",
        source: "node-cognitive",
        sourceHandle: "bottom-out",
        target: "node-governance",
        targetHandle: "top-in",
        label: "Draft JSON (85-105w)",
        animated,
        style: { stroke: killSwitchActive ? alertStroke : "#38BDF8", strokeWidth: 2.2 },
        labelStyle: { fill: "#E2E8F0", fontSize: 10, fontFamily: "monospace", fontWeight: 700 },
        labelBgStyle: { fill: "#0B0F14", stroke: "#38BDF8", strokeWidth: 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color: killSwitchActive ? alertStroke : "#38BDF8" },
      },
      {
        id: "e-gov-cog-loop",
        source: "node-governance",
        sourceHandle: "right-out",
        target: "node-cognitive",
        targetHandle: "top-in",
        label: "Rejeitado / Retry (≤ 2)",
        animated,
        style: {
          stroke: killSwitchActive ? alertStroke : "#D1BA73",
          strokeWidth: 2.4,
          strokeDasharray: "6 4",
        },
        labelStyle: { fill: "#D1BA73", fontSize: 10, fontFamily: "monospace", fontWeight: 800 },
        labelBgStyle: { fill: "#1C1608", stroke: "#D1BA73", strokeWidth: 1.2 },
        markerEnd: { type: MarkerType.ArrowClosed, color: killSwitchActive ? alertStroke : "#D1BA73" },
      },
      {
        id: "e-gov-multi",
        source: "node-governance",
        sourceHandle: "right-out",
        target: "node-multimodal",
        targetHandle: "left-in",
        label: "Aprovado (Jev Gate)",
        animated,
        style: { stroke: killSwitchActive ? alertStroke : "#10B981", strokeWidth: 2.2 },
        labelStyle: { fill: "#E2E8F0", fontSize: 10, fontFamily: "monospace", fontWeight: 700 },
        labelBgStyle: { fill: "#0B0F14", stroke: "#10B981", strokeWidth: 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color: killSwitchActive ? alertStroke : "#10B981" },
      },
      {
        id: "e-multi-hitl",
        source: "node-multimodal",
        sourceHandle: "bottom-out",
        target: "node-hitl-gate",
        targetHandle: "top-in",
        label: "Podcast + Card 1080p",
        animated,
        style: { stroke: killSwitchActive ? alertStroke : "#10B981", strokeWidth: 2.2 },
        labelStyle: { fill: "#E2E8F0", fontSize: 10, fontFamily: "monospace", fontWeight: 700 },
        labelBgStyle: { fill: "#0B0F14", stroke: "#10B981", strokeWidth: 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color: killSwitchActive ? alertStroke : "#10B981" },
      },
      {
        id: "e-hitl-deliv",
        source: "node-hitl-gate",
        sourceHandle: "right-out",
        target: "node-delivery",
        targetHandle: "left-in",
        label: "Founder Approved → Fan-out",
        animated,
        style: { stroke: killSwitchActive ? alertStroke : "#38BDF8", strokeWidth: 2.5 },
        labelStyle: { fill: "#E2E8F0", fontSize: 10, fontFamily: "monospace", fontWeight: 700 },
        labelBgStyle: { fill: "#0B0F14", stroke: "#38BDF8", strokeWidth: 1 },
        markerEnd: { type: MarkerType.ArrowClosed, color: killSwitchActive ? alertStroke : "#38BDF8" },
      },
    ];
  }, [killSwitchActive]);

  const [nodes, setNodes, onNodesChange] = useNodesState(computedNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(computedEdges);

  useEffect(() => {
    setNodes((prev) =>
      computedNodes.map((cn) => {
        const existing = prev.find((p) => p.id === cn.id);
        return existing ? { ...cn, position: existing.position } : cn;
      })
    );
  }, [computedNodes, setNodes]);

  useEffect(() => {
    setEdges(computedEdges);
  }, [computedEdges, setEdges]);

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    setSelectedNodeId(node.id);
  };

  const handleFitView = () => {
    setActiveFilter("all");
    setNodes(computedNodes);
    rfInstance?.fitView({ padding: 0.16, duration: 350 });
  };

  const handleCopyJson = async () => {
    if (!selectedNode) return;
    const payload = JSON.stringify(selectedNode.statePayload || {}, null, 2);
    await navigator.clipboard.writeText(payload);
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  return (
    <div className="space-y-5">
      {/* Barra Superior de Filtros Rápidos e Controles */}
      <div
        className={`rounded-2xl bg-[#0B0F14] border p-4 shadow-2xl flex flex-col lg:flex-row lg:items-center justify-between gap-4 transition-colors ${
          killSwitchActive ? "border-red-500/60" : "border-white/10"
        }`}
      >
        <div className="space-y-1">
          <div className="flex flex-wrap items-center gap-2.5">
            <span
              className={`w-2.5 h-2.5 rounded-full animate-ping ${
                killSwitchActive ? "bg-red-500" : "bg-emerald-400"
              }`}
            />
            <span className="text-xs sm:text-sm font-bold text-white font-mono uppercase">
              TOPOLOGIA DIRECIONAL LANGGRAPH & ECOSSISTEMA AUTÔNOMO
            </span>
            {killSwitchActive ? (
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-red-500/20 text-red-300 border border-red-500/50 animate-pulse">
                🚨 PIPELINE SUSPENSO - EMERGÊNCIA ATIVADA
              </span>
            ) : (
              <span className="px-2.5 py-0.5 rounded-full text-[10px] font-mono font-bold bg-emerald-500/15 text-emerald-400 border border-emerald-500/30">
                ● 7 NÓS ONLINE • FLUXO ATIVO
              </span>
            )}
          </div>
          <p className="text-[11px] text-slate-400">
            Arraste os nós (Drag & Drop), faça Pan/Zoom e clique em qualquer agente para inspecionar arquivo-fonte, política de retry e{" "}
            <code className="text-[#D1BA73]">GraphState</code>.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          {(
            [
              { id: "all", label: "[ Todos ]" },
              { id: "langgraph", label: "[ LangGraph Core ]" },
              { id: "multimodal", label: "[ Multimodal & HITL ]" },
              { id: "distribution", label: "[ Distribuição ]" },
            ] as const
          ).map((f) => (
            <button
              key={f.id}
              type="button"
              onClick={() => setActiveFilter(f.id)}
              className={`px-3 py-1.5 rounded-lg text-[11px] font-mono font-bold transition-all cursor-pointer ${
                activeFilter === f.id
                  ? "bg-[#D1BA73]/20 text-[#D1BA73] border border-[#D1BA73]/40"
                  : "bg-[#080B0F] text-slate-400 hover:text-white border border-white/10"
              }`}
            >
              {f.label}
            </button>
          ))}

          <button
            type="button"
            onClick={handleFitView}
            className="px-3 py-1.5 rounded-lg text-[11px] font-mono font-bold bg-sky-500/15 hover:bg-sky-500/25 text-sky-300 border border-sky-500/30 transition-all cursor-pointer flex items-center gap-1"
          >
            <RotateCcw className="w-3 h-3" />
            <span>[ Fit View ]</span>
          </button>
        </div>
      </div>

      {/* Canvas Interativo ReactFlow */}
      <div
        className={`relative w-full h-[660px] rounded-3xl bg-[#080B0F] border-2 overflow-hidden shadow-2xl transition-all ${
          killSwitchActive
            ? "border-red-500/80 shadow-[0_0_45px_rgba(239,68,68,0.25)]"
            : "border-white/10"
        }`}
      >
        {killSwitchActive && (
          <div className="absolute top-4 left-1/2 -translate-x-1/2 z-20 px-5 py-2 rounded-2xl bg-red-950/95 border-2 border-red-500 text-red-200 font-mono text-xs font-bold shadow-2xl flex items-center gap-2 pointer-events-none">
            <AlertOctagon className="w-4 h-4 text-red-400 animate-bounce" />
            <span>PIPELINE SUSPENSO - EMERGÊNCIA ATIVADA • PARTÍCULAS CONGELADAS</span>
          </div>
        )}

        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          nodeTypes={nodeTypes}
          onNodeClick={handleNodeClick}
          onInit={setRfInstance}
          fitView
          fitViewOptions={{ padding: 0.16 }}
          minZoom={0.45}
          maxZoom={1.6}
          className="bg-[#080B0F]"
        >
          <Background variant={BackgroundVariant.Dots} gap={24} size={1.2} color="#1E293B" />
          <Controls className="!bg-[#0D131C] !border-white/10 !fill-white !text-white rounded-xl shadow-xl overflow-hidden" />
          <MiniMap
            nodeColor={() => (killSwitchActive ? "#EF4444" : "#D1BA73")}
            maskColor="rgba(8, 11, 15, 0.78)"
            className="!bg-[#0D131C] !border-white/10 rounded-2xl overflow-hidden shadow-xl"
          />
        </ReactFlow>

        {/* Side-Drawer Lateral de Telemetria */}
        {selectedNode && (
          <div className="absolute inset-y-0 right-0 w-full sm:w-[420px] bg-[#0B0F14]/98 backdrop-blur-2xl border-l border-white/15 p-6 z-30 shadow-2xl flex flex-col justify-between overflow-y-auto animate-in slide-in-from-right duration-300">
            <div className="space-y-4">
              <div className="flex items-start justify-between border-b border-white/10 pb-3">
                <div>
                  <span className="text-[10px] font-mono uppercase tracking-widest text-[#D1BA73] font-bold">
                    {selectedNode.layerLabel || selectedNode.category}
                  </span>
                  <h3 className="text-lg font-bold text-white font-serif tracking-tight mt-0.5">
                    {selectedNode.name}
                  </h3>
                </div>
                <button
                  onClick={() => setSelectedNodeId(null)}
                  className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              {/* Arquivo-Fonte Associado */}
              <div className="bg-[#080B0F] p-3.5 rounded-xl border border-[#38BDF8]/30 space-y-1">
                <span className="text-[10px] text-[#38BDF8] font-mono uppercase font-bold flex items-center gap-1.5">
                  <FileCode2 className="w-3.5 h-3.5" />
                  Arquivo-Fonte Associado
                </span>
                <div className="text-xs font-mono font-bold text-white break-all">
                  {selectedNode.sourceFile}
                </div>
              </div>

              {/* Métricas Operacionais */}
              <div className="grid grid-cols-2 gap-2.5">
                <div className="bg-[#141C28] p-3 rounded-xl border border-white/5 space-y-1">
                  <span className="text-[10px] text-slate-400 font-mono">STATUS DO NÓ</span>
                  <div
                    className={`text-xs font-bold flex items-center gap-1.5 uppercase font-mono ${
                      killSwitchActive ? "text-red-400" : "text-emerald-400"
                    }`}
                  >
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    {killSwitchActive ? "SUSPENDED" : "ONLINE"}
                  </div>
                </div>

                <div className="bg-[#141C28] p-3 rounded-xl border border-white/5 space-y-1">
                  <span className="text-[10px] text-slate-400 font-mono">LATÊNCIA MÉDIA</span>
                  <div className="text-xs font-bold text-[#D1BA73] font-mono">
                    {selectedNode.avgLatencyMs} ms
                  </div>
                </div>
              </div>

              {/* Política de Retry / Fallback */}
              <div className="space-y-1.5">
                <span className="text-[10px] font-mono text-[#D1BA73] uppercase font-bold">
                  Política de Retry / Fallback
                </span>
                <p className="text-xs text-slate-200 leading-relaxed bg-[#141C28]/80 p-3 rounded-xl border border-[#D1BA73]/25">
                  {selectedNode.retryPolicy}
                </p>
              </div>

              {/* Visualizador Formatado do GraphState */}
              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="flex items-center gap-1.5 text-[10px] font-mono text-emerald-400 font-bold uppercase">
                    <Terminal className="w-3.5 h-3.5 text-[#D1BA73]" />
                    Payload do GraphState (JSON)
                  </span>
                  <button
                    type="button"
                    onClick={handleCopyJson}
                    className="px-2.5 py-1 rounded-lg bg-[#D1BA73]/15 hover:bg-[#D1BA73]/30 border border-[#D1BA73]/30 text-[10px] font-mono font-bold text-[#D1BA73] flex items-center gap-1 cursor-pointer"
                  >
                    {copiedJson ? <Check className="w-3 h-3" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedJson ? "Copiado!" : "Copiar JSON"}</span>
                  </button>
                </div>

                <pre className="bg-[#06080C] border border-white/10 rounded-xl p-3 font-mono text-[10.5px] text-sky-300 overflow-x-auto max-h-52 leading-relaxed">
                  {JSON.stringify(selectedNode.statePayload || {}, null, 2)}
                </pre>
              </div>
            </div>

            <div className="pt-4 border-t border-white/10 mt-4">
              <button
                onClick={() => setSelectedNodeId(null)}
                className="w-full py-2.5 px-4 rounded-xl bg-white/10 hover:bg-white/15 border border-white/10 text-xs font-semibold text-white transition-all cursor-pointer"
              >
                Fechar Inspeção de Telemetria
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Barra Inferior: Controle de Emergência & Kill Switch Geral */}
      <div className="rounded-2xl bg-red-950/20 border border-red-500/30 p-5 flex items-center justify-between gap-4 shadow-xl">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-red-500/20 border border-red-500/40 flex items-center justify-center text-red-400 text-lg">
            🚨
          </div>
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-xs font-bold uppercase tracking-wider text-red-300">
                CONTROLE DE EMERGÊNCIA & KILL SWITCH GERAL
              </h3>
              <span
                className={`px-2 py-0.5 rounded text-[9px] font-mono font-bold uppercase ${
                  killSwitchActive
                    ? "bg-red-500/25 text-red-300 border border-red-500/50 animate-pulse"
                    : "bg-emerald-500/15 text-emerald-400 border border-emerald-500/30"
                }`}
              >
                {killSwitchActive
                  ? "Pipeline Suspenso - Emergência Ativada"
                  : "Sistema Nominal"}
              </span>
            </div>
            <p className="text-[11px] text-slate-400">
              Ao ativar, transiciona o grafo para alerta vermelho e congela as animações de distribuição
            </p>
          </div>
        </div>

        <label className="relative inline-flex items-center cursor-pointer">
          <input
            type="checkbox"
            checked={killSwitchActive}
            onChange={(e) => setKillSwitchActive(e.target.checked)}
            className="sr-only peer"
          />
          <div className="w-12 h-6 bg-slate-800 rounded-full peer peer-checked:after:translate-x-full after:content-[''] after:absolute after:top-[2px] after:left-[2px] after:bg-white after:rounded-full after:h-5 after:w-5 after:transition-all peer-checked:bg-red-600" />
        </label>
      </div>
    </div>
  );
}
