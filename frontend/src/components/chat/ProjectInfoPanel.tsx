import React from 'react';
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
  SheetTrigger
} from '@/components/ui/sheet';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Separator } from '@/components/ui/separator';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  Info,
  Database,
  Server,
  Globe,
  Cpu,
  FileText,
  Zap
} from 'lucide-react';

interface TechItem {
  name: string;
  category: 'frontend' | 'backend' | 'database' | 'ai' | 'infra';
}

const techStack: TechItem[] = [
  // Frontend
  { name: 'React 18', category: 'frontend' },
  { name: 'TypeScript', category: 'frontend' },
  { name: 'Vite', category: 'frontend' },
  { name: 'Tailwind CSS', category: 'frontend' },
  { name: 'Shadcn/UI', category: 'frontend' },
  // Backend
  { name: 'FastAPI', category: 'backend' },
  { name: 'Pydantic AI', category: 'backend' },
  { name: 'Python', category: 'backend' },
  // AI/ML
  { name: 'GPT-5-mini', category: 'ai' },
  { name: 'RAG Pipeline', category: 'ai' },
  { name: 'Vector Embeddings', category: 'ai' },
  // Database
  { name: 'Supabase', category: 'database' },
  { name: 'PostgreSQL', category: 'database' },
  { name: 'pgvector', category: 'database' },
  // Infrastructure
  { name: 'Docker', category: 'infra' },
  { name: 'Docker Compose', category: 'infra' },
];

const categoryColors: Record<TechItem['category'], string> = {
  frontend: 'bg-blue-500/20 text-blue-300 border-blue-500/30',
  backend: 'bg-green-500/20 text-green-300 border-green-500/30',
  database: 'bg-purple-500/20 text-purple-300 border-purple-500/30',
  ai: 'bg-orange-500/20 text-orange-300 border-orange-500/30',
  infra: 'bg-slate-500/20 text-slate-300 border-slate-500/30',
};

const features = [
  { icon: Zap, title: 'Real-time Streaming', desc: 'Server-sent events for live AI responses' },
  { icon: FileText, title: 'RAG Pipeline', desc: 'Document ingestion from local files & Google Drive' },
  { icon: Database, title: 'Vector Search', desc: 'Semantic search with pgvector embeddings' },
  { icon: Globe, title: 'Web Search', desc: 'Brave/SearXNG integration for current information' },
  { icon: Cpu, title: 'Code Execution', desc: 'Sandboxed Python code interpreter' },
  { icon: Server, title: 'Microservices', desc: 'Independently deployable components' },
];

export const ProjectInfoPanel: React.FC = () => {
  return (
    <Sheet>
      <SheetTrigger asChild>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8 text-muted-foreground hover:text-foreground"
          title="About this project"
        >
          <Info className="h-4 w-4" />
          <span className="sr-only">About this project</span>
        </Button>
      </SheetTrigger>
      <SheetContent side="right" className="w-[340px] sm:w-[400px] p-0" showCloseButton={true}>
        <ScrollArea className="h-full">
          <div className="p-6">
            <SheetHeader className="text-left">
              <SheetTitle className="text-xl">PeppeGPT</SheetTitle>
              <SheetDescription>
                A full-stack AI agent deployment system built to showcase modern software engineering practices.
              </SheetDescription>
            </SheetHeader>

            <Separator className="my-6" />

            {/* Architecture Overview */}
            <section className="mb-6">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Server className="h-4 w-4" />
                Architecture
              </h3>
              <div className="bg-secondary/50 rounded-lg p-4 text-sm space-y-2">
                <div className="flex items-start gap-2">
                  <span className="text-blue-400 font-mono text-xs">FE</span>
                  <span className="text-muted-foreground">React SPA with real-time streaming</span>
                </div>
                <div className="flex items-center justify-center text-muted-foreground">
                  <span className="text-xs">↓ REST + SSE ↓</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-green-400 font-mono text-xs">API</span>
                  <span className="text-muted-foreground">FastAPI + Pydantic AI Agent</span>
                </div>
                <div className="flex items-center justify-center text-muted-foreground">
                  <span className="text-xs">↓ SQL + Vector ↓</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-purple-400 font-mono text-xs">DB</span>
                  <span className="text-muted-foreground">Supabase (Postgres + pgvector)</span>
                </div>
                <div className="flex items-center justify-center text-muted-foreground">
                  <span className="text-xs">↑ Embeddings ↑</span>
                </div>
                <div className="flex items-start gap-2">
                  <span className="text-orange-400 font-mono text-xs">RAG</span>
                  <span className="text-muted-foreground">Document pipeline (Local/GDrive)</span>
                </div>
              </div>
            </section>

            {/* Key Features */}
            <section className="mb-6">
              <h3 className="text-sm font-semibold mb-3 flex items-center gap-2">
                <Zap className="h-4 w-4" />
                Key Features
              </h3>
              <div className="grid gap-3">
                {features.map((feature) => (
                  <div key={feature.title} className="flex items-start gap-3">
                    <feature.icon className="h-4 w-4 text-muted-foreground mt-0.5 shrink-0" />
                    <div>
                      <p className="text-sm font-medium">{feature.title}</p>
                      <p className="text-xs text-muted-foreground">{feature.desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </section>

            <Separator className="my-6" />

            {/* Tech Stack */}
            <section className="mb-6">
              <h3 className="text-sm font-semibold mb-3">Tech Stack</h3>
              <div className="flex flex-wrap gap-2">
                {techStack.map((tech) => (
                  <Badge
                    key={tech.name}
                    variant="outline"
                    className={`text-xs ${categoryColors[tech.category]}`}
                  >
                    {tech.name}
                  </Badge>
                ))}
              </div>
              <div className="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-blue-500/50" /> Frontend
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-green-500/50" /> Backend
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-orange-500/50" /> AI/ML
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-purple-500/50" /> Database
                </span>
                <span className="flex items-center gap-1">
                  <span className="w-2 h-2 rounded-full bg-slate-500/50" /> Infra
                </span>
              </div>
            </section>

            {/* Footer */}
            <div className="mt-8 pt-4 border-t text-center">
              <p className="text-xs text-muted-foreground">
                Built by Giuseppe Rumore
              </p>
            </div>
          </div>
        </ScrollArea>
      </SheetContent>
    </Sheet>
  );
};
