import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Package, LogIn, Send, Share2, History, FileText } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import type { Producto, Bodega, LoteProduccion, Proveedor } from '../../lib/types';
import { TransformationView } from './TransformationView';
import { StockView } from './StockView';
import { RegistrarEntradaView } from './RegistrarEntradaView';
import { TransferView } from './TransferView';
import { KardexView } from './KardexView';
import { ReportesView } from './ReportesView';
import type { StockItem } from './inventoryUtils';

interface InventoryDashboardProps {
  sedeId?: string;
  productos: Producto[];
  bodegas: Bodega[];
  lotesProduccion: LoteProduccion[];
  proveedores: Proveedor[];
  onDataRefresh: () => void;
}

export function InventoryDashboard({ sedeId, productos, bodegas, lotesProduccion, onDataRefresh, proveedores }: InventoryDashboardProps) {
  const [stock, setStock] = useState<StockItem[]>([]);
  const [loadingStock, setLoadingStock] = useState(true);
  const [, setSearchParams] = useSearchParams();

  const fetchStock = async () => {
    setLoadingStock(true);
    try {
      const response = await apiClient.get<any>('/inventory/stock/', { params: sedeId ? { sede_id: sedeId } : {} });
      const data = response.data;
      if (data && typeof data === 'object' && Array.isArray(data.results)) {
        setStock(data.results);
      } else if (Array.isArray(data)) {
        setStock(data);
      } else {
        setStock([]);
      }
    } catch (error) {
      toast.error('Error stock');
      setStock([]);
    } finally {
      setLoadingStock(false);
    }
  };

  useEffect(() => { fetchStock(); }, [sedeId]);

  return (
    <Tabs
      defaultValue="stock"
      onValueChange={() => {
        setSearchParams(prev => {
          prev.set('page', '1');
          return prev;
        }, { replace: true });
      }}
      className="space-y-4"
    >
      <TabsList className="grid w-full grid-cols-6">
        <TabsTrigger value="stock"><Package className="w-4 h-4 mr-2" />Stock</TabsTrigger>
        <TabsTrigger value="entrada"><LogIn className="w-4 h-4 mr-2" />Entrada</TabsTrigger>
        <TabsTrigger value="transfer"><Send className="w-4 h-4 mr-2" />Transfer</TabsTrigger>
        <TabsTrigger value="transform"><Share2 className="w-4 h-4 mr-2" />Transform</TabsTrigger>
        <TabsTrigger value="kardex"><History className="w-4 h-4 mr-2" />Kardex</TabsTrigger>
        <TabsTrigger value="reportes"><FileText className="w-4 h-4 mr-2" />Reportes</TabsTrigger>
      </TabsList>
      <TabsContent value="stock"><StockView stock={stock} loading={loadingStock} /></TabsContent>
      <TabsContent value="entrada"><RegistrarEntradaView productos={productos} bodegas={bodegas} proveedores={proveedores} onDataRefresh={fetchStock} /></TabsContent>
      <TabsContent value="transfer"><TransferView productos={productos} bodegas={bodegas} stock={stock} /></TabsContent>
      <TabsContent value="transform"><TransformationView productos={productos} bodegas={bodegas} stock={stock} /></TabsContent>
      <TabsContent value="kardex"><KardexView productos={productos} bodegas={bodegas} proveedores={proveedores} onDataRefresh={onDataRefresh} /></TabsContent>
      <TabsContent value="reportes"><ReportesView bodegas={bodegas} productos={productos} sedeId={sedeId} /></TabsContent>
    </Tabs>
  );
}
