"use client";

import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

type CountDatum = {
  name: string;
  total: number;
};

type PerformanceDatum = {
  name: string;
  engagement: number;
  inquiry: number;
  purchase: number;
};

export function DashboardCharts({
  regionChartData,
  channelChartData,
  healthByCategory,
  performanceChartData
}: {
  regionChartData: CountDatum[];
  channelChartData: CountDatum[];
  healthByCategory: CountDatum[];
  performanceChartData: PerformanceDatum[];
}) {
  return (
    <div className="grid gap-5 xl:grid-cols-[1.15fr_0.85fr]">
      <div className="h-80 rounded-2xl border border-border bg-white/88 p-5 shadow-soft">
        <p className="mb-1 font-serif text-2xl">Campaign Performance</p>
        <p className="mb-4 text-sm text-foreground/58">Engagement, inquiry, and purchase conversion by campaign.</p>
        <ResponsiveContainer width="100%" height="82%">
          <AreaChart data={performanceChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#d4dccf" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis tickFormatter={(value) => `${value}%`} />
            <Tooltip formatter={(value) => `${value}%`} />
            <Legend />
            <Area type="monotone" dataKey="engagement" stroke="#2d6440" fill="#86b56d" fillOpacity={0.24} />
            <Area type="monotone" dataKey="inquiry" stroke="#c08946" fill="#e2c08c" fillOpacity={0.28} />
            <Area type="monotone" dataKey="purchase" stroke="#2563eb" fill="#93c5fd" fillOpacity={0.2} />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      <div className="h-80 rounded-2xl border border-border bg-white/88 p-5 shadow-soft">
        <p className="mb-1 font-serif text-2xl">Data Health Issues</p>
        <p className="mb-4 text-sm text-foreground/58">Open issue volume by validation category.</p>
        <ResponsiveContainer width="100%" height="82%">
          <BarChart data={healthByCategory} layout="vertical" margin={{ left: 18 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#d4dccf" />
            <XAxis type="number" allowDecimals={false} />
            <YAxis dataKey="name" type="category" width={110} tick={{ fontSize: 12 }} />
            <Tooltip />
            <Bar dataKey="total" fill="#8a6f3d" radius={[0, 8, 8, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="h-72 rounded-2xl border border-border bg-white/88 p-5 shadow-soft">
        <p className="mb-4 font-serif text-2xl">Campaigns by Region</p>
        <ResponsiveContainer width="100%" height="86%">
          <BarChart data={regionChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#d4dccf" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="total" fill="#2d6440" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>

      <div className="h-72 rounded-2xl border border-border bg-white/88 p-5 shadow-soft">
        <p className="mb-4 font-serif text-2xl">Campaigns by Channel</p>
        <ResponsiveContainer width="100%" height="86%">
          <BarChart data={channelChartData}>
            <CartesianGrid strokeDasharray="3 3" stroke="#d4dccf" />
            <XAxis dataKey="name" tick={{ fontSize: 12 }} />
            <YAxis allowDecimals={false} />
            <Tooltip />
            <Bar dataKey="total" fill="#c08946" radius={[8, 8, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
