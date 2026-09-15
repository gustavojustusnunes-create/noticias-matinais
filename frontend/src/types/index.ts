export interface NewsItem {
  titulo: string;
  link: string;
  imagem: string;
  resumo: string;
  categoria?: string;
}

export interface Edition {
  data: string;
  data_extenso: string;
  editorial: string;
  manchete: string;
  cadernos: Record<string, NewsItem[]>;
}

export interface AgentStatus {
  name: string;
  role: string;
  status: "idle" | "running" | "success" | "warning" | "error";
  lastRun?: string;
  details?: string;
}

export interface PodcastMetadata {
  date: string;
  audioUrl: string;
  title: string;
  hosts: string[];
  durationEstimate?: string;
}
