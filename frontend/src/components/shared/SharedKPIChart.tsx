import React from 'react';
import {
  ResponsiveContainer,
  BarChart, Bar,
  LineChart, Line,
  AreaChart, Area,
  PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend
} from 'recharts';

export type ChartType = 'bar' | 'line' | 'area' | 'pie';

export interface ChartConfig {
  dataKey: string;
  fill?: string;
  stroke?: string;
  name?: string;
}

export interface SharedKPIChartProps {
  type: ChartType;
  data: any[];
  config: ChartConfig[];
  xAxisKey?: string;
  height?: number;
  colors?: string[];
  yAxisTickFormatter?: (value: any) => string;
  tooltipFormatter?: (value: any, name: string, props: any) => any[];
}

const DEFAULT_COLORS = [
  '#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6',
  '#ec4899', '#14b8a6', '#f97316', '#6366f1', '#84cc16'
];

export function SharedKPIChart({
  type,
  data,
  config,
  xAxisKey = 'name',
  height = 280,
  colors = DEFAULT_COLORS,
  yAxisTickFormatter,
  tooltipFormatter
}: SharedKPIChartProps) {
  
  if (!data || data.length === 0) {
    return (
      <div className="flex items-center justify-center text-muted-foreground" style={{ height }}>
        Sin datos disponibles
      </div>
    );
  }

  const renderContent = () => {
    switch (type) {
      case 'bar':
        return (
          <BarChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xAxisKey} tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} width={50} tickFormatter={yAxisTickFormatter} />
            <Tooltip formatter={tooltipFormatter} />
            <Legend />
            {config.map((c, i) => (
              <Bar key={c.dataKey} dataKey={c.dataKey} fill={c.fill || colors[i % colors.length]} name={c.name} radius={[4, 4, 0, 0]} />
            ))}
          </BarChart>
        );
      case 'line':
        return (
          <LineChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xAxisKey} tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} width={50} tickFormatter={yAxisTickFormatter} />
            <Tooltip formatter={tooltipFormatter} />
            <Legend />
            {config.map((c, i) => (
              <Line key={c.dataKey} type="monotone" dataKey={c.dataKey} stroke={c.stroke || colors[i % colors.length]} name={c.name} strokeWidth={2} />
            ))}
          </LineChart>
        );
      case 'area':
        return (
          <AreaChart data={data} margin={{ top: 5, right: 10, left: 0, bottom: 5 }}>
            <defs>
               {config.map((c, i) => (
                 <linearGradient key={`grad-${c.dataKey}`} id={`grad-${c.dataKey}`} x1="0" y1="0" x2="0" y2="1">
                   <stop offset="5%" stopColor={c.fill || colors[i % colors.length]} stopOpacity={0.3} />
                   <stop offset="95%" stopColor={c.fill || colors[i % colors.length]} stopOpacity={0} />
                 </linearGradient>
               ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={xAxisKey} tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} width={50} tickFormatter={yAxisTickFormatter} />
            <Tooltip formatter={tooltipFormatter} />
            <Legend />
            {config.map((c, i) => (
              <Area key={c.dataKey} type="monotone" dataKey={c.dataKey} stroke={c.stroke || colors[i % colors.length]} fill={`url(#grad-${c.dataKey})`} name={c.name} strokeWidth={2} />
            ))}
          </AreaChart>
        );
      case 'pie':
        const valKey = config[0]?.dataKey || 'value';
        return (
          <PieChart>
            <Pie
              data={data}
              dataKey={valKey}
              nameKey={xAxisKey}
              cx="50%"
              cy="50%"
              innerRadius={height * 0.2}
              outerRadius={height * 0.35}
              label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}
            >
              {data.map((entry, index) => (
                <Cell key={`cell-${index}`} fill={entry.fill || colors[index % colors.length]} />
              ))}
            </Pie>
            <Tooltip formatter={tooltipFormatter} />
            <Legend />
          </PieChart>
        );
      default:
        return <React.Fragment />;
    }
  };

  return (
    <ResponsiveContainer width="100%" height={height}>
      {renderContent()}
    </ResponsiveContainer>
  );
}
