"use client";
import { useEffect, useMemo, useState } from "react";
import { getInvoices, getSummary } from "@/lib/api";
import type { Invoice } from "@/types/ap";
import { AppSidebar } from "@/components/app-sidebar";
import { DashboardHeader } from "@/components/dashboard-header";
import { SummaryCards } from "@/components/summary-cards";
import { InvoiceQueue } from "@/components/invoice-queue";
import { InvoiceDetail } from "@/components/invoice-detail";
import { ExtractDialog } from "@/components/extract-dialog";
export default function Home() { const [invoices,setInvoices]=useState<Invoice[]>([]); const [summary,setSummary]=useState({total:0,auto_post:0,human_review:0}); const [selected,setSelected]=useState<Invoice>(); const [error,setError]=useState(""); const [extractOpen,setExtractOpen]=useState(false); const load=async()=>{try{const [i,s]=await Promise.all([getInvoices(),getSummary()]);setInvoices(i);setSummary(s);setSelected(current=>i.find(x=>x.id===current?.id)||i[0])}catch(e){setError(e instanceof Error?e.message:"Unable to load dashboard")}}; useEffect(()=>{load()},[]); const reviewInvoices=useMemo(()=>invoices.filter(i=>!i.reviews?.length),[invoices]); return <main className="flex min-h-screen bg-[#fbfaf7] text-[#292b28]"><AppSidebar/><div className="min-w-0 flex-1"><DashboardHeader onExtract={()=>setExtractOpen(true)}/><div className="mx-auto max-w-[1500px] space-y-6 p-5 md:p-8">{error?<div role="alert" className="border border-red-200 bg-red-50 p-4 text-sm text-red-700">{error} <button className="ml-2 underline" onClick={load}>Retry</button></div>:<><SummaryCards summary={summary}/><div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(350px,0.8fr)_minmax(0,1.4fr)]"><InvoiceQueue invoices={reviewInvoices} selected={selected?.id} onSelect={setSelected}/><InvoiceDetail invoice={selected} onReviewed={load}/></div></>}</div></div><ExtractDialog open={extractOpen} onClose={()=>setExtractOpen(false)}/></main> }
