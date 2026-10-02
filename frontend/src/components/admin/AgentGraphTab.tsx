"use client";

import React, { useState, useMemo } from "react";
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
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import {
  Activity,
  CheckCircle2,
  Clock,
  Cpu,
  Layers,
  Radio,
  RefreshCw,
  Terminal,
  X,
  Zap,
  Shield,
  Volume2,
  Send,
  Database,
} from "lucide-react";
import { AgentNodeDetail } from "@/lib/adminData";

// Custom Node Component com Design Executivo
function CustomAgentNode({ data }: { data: AgentNodeDetail & { isSelected?: boolean } }) {
  const getStatusColor = () => {
    switch (data.status) {
      case "healthy":
        return {
          bg: "bg-emerald-500/10",
          border: "border-emerald-500/40",
          badge: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
          dot: "bg-emerald-400",
          label: "Saudável",
        };
      case "processing":
        return {
          bg: "bg-amber-500/10",
          border: "border-amber-500/40",
          badge: "bg-amber-500/20 text-amber-400 border-amber-500/30",
          dot: "bg-amber-400 animate-ping",
          label: "Processando",
        };
      case "alert":
        return {
          bg: "bg-rose-500/10",
          border: "border-rose-500/40",
          badge: "bg-rose-500/20 text-rose-400 border-rose-500/30",
          dot: "bg-rose-400 animate-bounce",
          label: "Alerta",
        };
    }
  };

  const colors = getStatusColor();

  const getIcon = () => {
    switch (data.category) {
      case "ingestion":
        return <Radio className="w-4 h-4 text-sky-400" />;
      case "orchestration":
        return <Cpu className="w-4 h-4 text-purple-400" />;
      case "cognitive":
        return <Zap className="w-4 h-4 text-amber-400" />;
      case "governance":
        return <Shield className="w-4 h-4 text-emerald-400" />;
      case "multimodal":
        return <Volume2 className="w-4 h-4 text-pink-400" />;
      case "delivery":
        return <Send className="w-4 h-4 text-blue-400" />;
    }
  };

  return (
    <div
      className={`w-72 rounded-2xl bg-[#0D131C] border-2 transition-all p-4 shadow-xl hover:shadow-2xl cursor-pointer ${
        data.isSelected
          ? "border-amber-400 ring-2 ring-amber-400/30 shadow-amber-500/20"
          : `${colors.border} hover:border-slate-500`
      }`}
    >
      <Handle type="target" position={Position.Top} className="!w-2.5 !h-2.5 !bg-slate-400 !border-2 !border-slate-800" />

      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center">
            {getIcon()}
          </div>
          <div>
            <div className="text-[10px] font-mono uppercase text-slate-400 tracking-wider">
              {data.category}
            </div>
            <h4 className="text-xs font-bold text-white tracking-tight leading-none">
              {data.name}
            </h4>
          </div>
        </div>

        <span className={`px-2 py-0.5 rounded-full text-[9px] font-bold border flex items-center gap-1.5 ${colors.badge}`}>
          <span className={`w-1.5 h-1.5 rounded-full ${colors.dot}`} />
          {colors.label}
        </span>
      </div>

      <p className="text-[11px] text-slate-300 font-medium line-clamp-2 leading-relaxed mb-3">
        {data.description}
      </p>

      <div className="pt-2.5 border-t border-white/5 flex items-center justify-between text-[10px] font-mono text-slate-400">
        <span className="truncate max-w-[130px] text-slate-300">{data.modelOrEngine}</span>
        <span className="text-amber-400 font-semibold">{data.avgLatencyMs} ms</span>
      </div>

      <Handle type="source" position={Position.Bottom} className="!w-2.5 !h-2.5 !bg-amber-400 !border-2 !border-slate-800" />
    </div>
  );
}

const nodeTypes = {
  agentNode: CustomAgentNode,
};

interface AgentGraphTabProps {
  nodesData: Record<string, AgentNodeDetail>;
}

export function AgentGraphTab({ nodesData }: AgentGraphTabProps) {
  const [selectedNode, setSelectedNode] = useState<AgentNodeDetail | null>(null);

  // Layout dos 6 nós em fluxo lógico vertical/árvore
  const initialNodes: Node[] = useMemo(() => [
    {
      id: "node-ingestion",
      type: "agentNode",
      position: { x: 300, y: 30 },
      data: { ...nodesData["node-ingestion"], isSelected: selectedNode?.id === "node-ingestion" },
    },
    {
      id: "node-orchestration",
      type: "agentNode",
      position: { x: 300, y: 190 },
      data: { ...nodesData["node-orchestration"], isSelected: selectedNode?.id === "node-orchestration" },
    },
    {
      id: "node-cognitive",
      type: "agentNode",
      position: { x: 300, y: 350 },
      data: { ...nodesData["node-cognitive"], isSelected: selectedNode?.id === "node-cognitive" },
    },
    {
      id: "node-governance",
      type: "agentNode",
      position: { x: 300, y: 510 },
      data: { ...nodesData["node-governance"], isSelected: selectedNode?.id === "node-governance" },
    },
    {
      id: "node-multimodal",
      type: "agentNode",
      position: { x: 120, y: 670 },
      data: { ...nodesData["node-multimodal"], isSelected: selectedNode?.id === "node-multimodal" },
    },
    {
      id: "node-delivery",
      type: "agentNode",
      position: { x: 480, y: 670 },
      data: { ...nodesData["node-delivery"], isSelected: selectedNode?.id === "node-delivery" },
    },
  ], [nodesData, selectedNode]);

  const initialEdges: Edge[] = useMemo(() => [
    { id: "e1-2", source: "node-ingestion", target: "node-orchestration", animated: true, style: { stroke: "#38BDF8", strokeWidth: 2 } },
    { id: "e2-3", source: "node-orchestration", target: "node-cognitive", animated: true, style: { stroke: "#A855F7", strokeWidth: 2 } },
    { id: "e3-4", source: "node-cognitive", target: "node-governance", animated: true, style: { stroke: "#F59E0B", strokeWidth: 2 } },
    { id: "e4-5", source: "node-governance", target: "node-multimodal", animated: true, style: { stroke: "#10B981", strokeWidth: 2 } },
    { id: "e4-6", source: "node-governance", target: "node-delivery", animated: true, style: { stroke: "#10B981", strokeWidth: 2 } },
  ], []);

  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

  const handleNodeClick = (_: React.MouseEvent, node: Node) => {
    const detail = nodesData[node.id];
    if (detail) {
      setSelectedNode(detail);
    }
  };

  return (
    <div className="relative w-full h-[760px] rounded-3xl bg-[#090D14] border border-white/10 overflow-hidden shadow-2xl">
      
      {/* Top Banner Controls */}
      <div className="absolute top-4 left-4 z-10 flex flex-wrap items-center gap-3 bg-[#0D131C]/90 backdrop-blur-md px-4 py-2.5 rounded-2xl border border-white/10 shadow-lg">
        <div className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
          <span className="text-xs font-bold text-white font-mono">CLUSTER TOPOLOGY</span>
        </div>
        <span className="text-xs text-slate-500">|</span>
        <span className="text-xs text-slate-400">Clique em qualquer nó para inspecionar logs e telemetria</span>
      </div>

      {/* ReactFlow Interactive Canvas */}
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        nodeTypes={nodeTypes}
        onNodeClick={handleNodeClick}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        minZoom={0.5}
        maxZoom={1.6}
        className="bg-[#080B10]"
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1.2} color="#1E293B" />
        <Controls className="!bg-[#0D131C] !border-white/10 !fill-white !text-white rounded-xl shadow-xl overflow-hidden" />
        <MiniMap
          nodeColor={() => "#F59E0B"}
          maskColor="rgba(8, 11, 16, 0.75)"
          className="!bg-[#0D131C] !border-white/10 rounded-2xl overflow-hidden shadow-xl"
        />
      </ReactFlow>

      {/* Lateral Drawer / Slide-Over Modal para Inspeção de Nó */}
      {selectedNode && (
        <div className="absolute inset-y-0 right-0 w-full sm:w-96 bg-[#0D131C]/98 backdrop-blur-2xl border-l border-white/15 p-6 z-20 shadow-2xl flex flex-col justify-between animate-in slide-in-from-right duration-300">
          <div className="space-y-6">
            
            {/* Drawer Header */}
            <div className="flex items-start justify-between">
              <div>
                <span className="text-[10px] font-mono uppercase tracking-widest text-amber-400 font-bold">
                  {selectedNode.category}
                </span>
                <h3 className="text-lg font-bold text-white font-serif tracking-tight mt-0.5">
                  {selectedNode.name}
                </h3>
              </div>
              <button
                onClick={() => setSelectedNode(null)}
                className="p-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-slate-400 hover:text-white transition-colors cursor-pointer"
              >
                <X className="w-4 h-4" />
              </button>
            </div>

            {/* Status & Telemetry Metrics Grid */}
            <div className="grid grid-cols-2 gap-2.5">
              <div className="bg-[#141C28] p-3 rounded-xl border border-white/5 space-y-1">
                <span className="text-[10px] text-slate-400 font-mono">STATUS DO NÓ</span>
                <div className="text-xs font-bold text-emerald-400 flex items-center gap-1.5 uppercase">
                  <CheckCircle2 className="w-3.5 h-3.5" />
                  {selectedNode.status}
                </div>
              </div>

              <div className="bg-[#141C28] p-3 rounded-xl border border-white/5 space-y-1">
                <span className="text-[10px] text-slate-400 font-mono">LATÊNCIA MÉDIA</span>
                <div className="text-xs font-bold text-amber-300 font-mono">
                  {selectedNode.avgLatencyMs} ms
                </div>
              </div>

              <div className="bg-[#141C28] p-3 rounded-xl border border-white/5 space-y-1">
                <span className="text-[10px] text-slate-400 font-mono">DISPONIBILIDADE</span>
                <div className="text-xs font-bold text-sky-400 font-mono">
                  {selectedNode.uptimePct}%
                </div>
              </div>

              <div className="bg-[#141C28] p-3 rounded-xl border border-white/5 space-y-1">
                <span className="text-[10px] text-slate-400 font-mono">ÚLTIMO DISPARO</span>
                <div className="text-[11px] font-semibold text-slate-200 truncate">
                  {selectedNode.lastExecution}
                </div>
              </div>
            </div>

            {/* Description */}
            <div className="space-y-1.5">
              <span className="text-[10px] font-mono text-slate-400 uppercase font-semibold">
                Função na Arquitetura
              </span>
              <p className="text-xs text-slate-300 leading-relaxed bg-[#141C28]/60 p-3 rounded-xl border border-white/5">
                {selectedNode.description}
              </p>
            </div>

            {/* Live Logs Terminal */}
            <div className="space-y-2">
              <div className="flex items-center justify-between text-[10px] font-mono text-slate-400">
                <span className="flex items-center gap-1.5 text-slate-300 font-semibold uppercase">
                  <Terminal className="w-3.5 h-3.5 text-amber-400" />
                  Logs Recentes do Pipeline
                </span>
                <span className="text-emerald-400 font-mono">LIVE TAIL</span>
              </div>

              <div className="bg-[#080B10] border border-white/10 rounded-xl p-3 font-mono text-[10px] text-slate-300 space-y-1.5 max-h-48 overflow-y-auto">
                {selectedNode.logs.map((log, idx) => (
                  <div key={idx} className="leading-relaxed">
                    <span className="text-slate-500">{log.slice(0, 10)}</span>{" "}
                    <span className="text-slate-300">{log.slice(10)}</span>
                  </div>
                ))}
              </div>
            </div>

          </div>

          {/* Action Close */}
          <div className="pt-4 border-t border-white/10">
            <button
              onClick={() => setSelectedNode(null)}
              className="w-full py-2.5 px-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-xs font-semibold text-white transition-all cursor-pointer"
            >
              Fechar Inspeção
            </button>
          </div>
        </div>
      )}

    </div>
  );
}
