import React from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { AlertTriangle } from 'lucide-react';

interface KpiCardProps {
  titulo: string;
  valor: string | number;
  subtitulo?: string;
  icon: React.ReactNode;
  alerta?: boolean;
  alertaTexto?: string;
}

function KpiCardImpl({ titulo, valor, subtitulo, icon, alerta, alertaTexto }: KpiCardProps) {
  return (
    <Card className={`overflow-hidden transition-all duration-300 hover:shadow-2xl hover:-translate-y-1 group ${alerta ? 'border-red-300/70 bg-red-50/80 dark:bg-red-950/30 backdrop-blur-sm' : 'bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-slate-200/50 dark:border-slate-800/50'}`}>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2 relative z-10">
        <CardTitle className="text-xs font-bold uppercase tracking-wider text-slate-500 dark:text-slate-400">{titulo}</CardTitle>
        <div className={`p-2 rounded-xl transition-transform duration-300 group-hover:scale-110 ${alerta ? 'bg-red-100 text-red-600 dark:bg-red-900/40' : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300'}`}>{icon}</div>
      </CardHeader>
      <CardContent className="relative z-10">
        <div className={`text-3xl font-extrabold tracking-tight tabular-nums ${alerta ? 'text-red-600 dark:text-red-400' : 'text-slate-800 dark:text-slate-100'}`}>{valor}</div>
        {subtitulo && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-1">{subtitulo}</p>
        )}
        {alerta && alertaTexto && (
          <p className="text-xs text-red-500 font-semibold mt-2 flex items-center gap-1.5 bg-red-100/60 dark:bg-red-900/30 p-1.5 rounded-lg w-fit">
            <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
            {alertaTexto}
          </p>
        )}
        {!alerta && (
          <div className="absolute -right-4 -bottom-4 w-20 h-20 bg-gradient-to-br from-blue-100 to-indigo-100 dark:from-blue-900/20 dark:to-indigo-900/20 rounded-full blur-2xl -z-10 opacity-70 group-hover:opacity-100 transition-opacity duration-300" />
        )}
      </CardContent>
    </Card>
  );
}

export const KpiCard = React.memo(KpiCardImpl);
