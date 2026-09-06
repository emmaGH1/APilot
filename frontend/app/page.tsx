import { ArrowUpRight, FileText, ShieldCheck, TriangleAlert } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";

const metrics = [{ label: "Invoices processed", value: "1,284", icon: FileText }, { label: "Exceptions to review", value: "24", icon: TriangleAlert }, { label: "Straight-through rate", value: "87.4%", icon: ShieldCheck }];

export default function Home() {
  return <main className="min-h-screen bg-background text-foreground"><div className="mx-auto max-w-6xl space-y-8 p-8"><header className="flex items-center justify-between"><div><p className="text-sm font-medium text-muted-foreground">Accounts payable</p><h1 className="text-3xl font-semibold tracking-tight">Good morning, finance team.</h1></div><Badge variant="secondary">Live workspace</Badge></header><section className="grid gap-4 md:grid-cols-3">{metrics.map(({ label, value, icon: Icon }) => <Card key={label}><CardContent className="flex items-center justify-between p-6"><div><p className="text-sm text-muted-foreground">{label}</p><p className="mt-2 text-3xl font-semibold">{value}</p></div><Icon className="size-5 text-primary" /></CardContent></Card>)}</section><Card><CardHeader><CardTitle>Recent activity</CardTitle></CardHeader><CardContent><div className="flex items-center justify-between py-3"><div><p className="font-medium">Dashboard scaffold ready</p><p className="text-sm text-muted-foreground">Connect your APilot API to see invoice activity.</p></div><ArrowUpRight className="size-4 text-muted-foreground" /></div><Separator /><p className="pt-4 text-sm text-muted-foreground">API requests use the local development rewrite at <code>/api</code>.</p></CardContent></Card></div></main>;
}
