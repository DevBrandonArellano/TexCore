import React, { useState, useEffect, useCallback } from 'react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Badge } from '../ui/badge';
import { Package, Printer, Plus, Trash2, CheckCircle2 } from 'lucide-react';
import apiClient from '../../lib/axios';
import { toast } from 'sonner';
import { PedidoVenta, Producto, LoteProduccion, DetallePedido, EtiquetaDespacho } from '../../lib/types';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';

export function PackagingDashboard() {
  const [pedidos, setPedidos] = useState<PedidoVenta[]>([]);
  const [selectedPedidoId, setSelectedPedidoId] = useState<string>('');
  const [detalles, setDetalles] = useState<DetallePedido[]>([]);
  const [productos, setProductos] = useState<Record<number, Producto>>({});
  const [lotes, setLotes] = useState<LoteProduccion[]>([]);
  const [loading, setLoading] = useState(true);
  const [zplTemplate, setZplTemplate] = useState<string>('');
  
  // Form state for current bulto
  const [currentBulto, setCurrentBulto] = useState({
    productoId: '',
    loteId: '',
    peso: '',
  });

  const [etiquetas, setEtiquetas] = useState<EtiquetaDespacho[]>([]);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [pedidosRes, productosRes, lotesRes, configsRes] = await Promise.all([
        apiClient.get('/pedidos-venta/'),
        apiClient.get('/productos/'),
        apiClient.get('/lotes-produccion/'),
        apiClient.get('/configuracion-sistema/'),
      ]);
      
      const template = configsRes.data.find((c: any) => c.clave === 'ZPL_TEMPLATE')?.valor;
      if (template) setZplTemplate(template);
      
      // Filter for pending orders if API doesn't support filter
      setPedidos(pedidosRes.data.filter((p: PedidoVenta) => p.estado === 'pendiente'));
      
      const prodMap: Record<number, Producto> = {};
      productosRes.data.forEach((p: Producto) => prodMap[p.id] = p);
      setProductos(prodMap);
      setLotes(lotesRes.data);
    } catch (error) {
      console.error('Error fetching data:', error);
      toast.error('Error al cargar datos de empaquetado');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  useEffect(() => {
    if (selectedPedidoId) {
      const fetchDetalles = async () => {
        try {
          const detallesRes = await apiClient.get(`/detalles-pedido/?pedido_venta=${selectedPedidoId}`);
          setDetalles(detallesRes.data);
          
          const labelsRes = await apiClient.get(`/etiquetas-despacho/?pedido_venta=${selectedPedidoId}`);
          setEtiquetas(labelsRes.data);
        } catch (error) {
          toast.error('Error al cargar detalles del pedido');
        }
      };
      fetchDetalles();
    } else {
      setDetalles([]);
      setEtiquetas([]);
    }
  }, [selectedPedidoId]);

  const handleRegisterBulto = async () => {
    if (!selectedPedidoId || !currentBulto.productoId || !currentBulto.peso) {
      toast.error('Por favor complete todos los campos');
      return;
    }

    try {
      const nextBultoNum = etiquetas.length + 1;
      const payload = {
        pedido_venta: parseInt(selectedPedidoId),
        producto: parseInt(currentBulto.productoId),
        lote: currentBulto.loteId ? parseInt(currentBulto.loteId) : null,
        peso_neto: parseFloat(currentBulto.peso),
        numero_bulto: nextBultoNum,
      };

      const res = await apiClient.post('/etiquetas-despacho/', payload);
      setEtiquetas([...etiquetas, res.data]);
      toast.success(`Bulto ${nextBultoNum} registrado correctamente`);
      
      setCurrentBulto({
        ...currentBulto,
        peso: '',
      });
      
      generateZpl(res.data);
    } catch (error) {
      toast.error('Error al registrar el bulto');
    }
  };

  const generateZpl = (etiqueta: EtiquetaDespacho) => {
    const producto = productos[etiqueta.producto];
    const lote = lotes.find(l => l.id === etiqueta.lote);
    
    // Default template if none loaded
    const baseTemplate = zplTemplate || `^XA
^CF0,60
^FO50,50^FDPROYECTO: TEXCORE^FS
^CF0,40
^FO50,130^FDPRODUCTO: {{producto}}^FS
^FO50,180^FDLOTE: {{lote}}^FS
^FO50,230^FDPESO: {{peso}} KG^FS
^FO50,280^FDBULTO: {{bulto}}^FS
^FO50,330^FDFECHA: {{fecha}}^FS
^BY3,2,100
^FO50,380^BCN,100,Y,N,N^FD{{codigo}}^FS
^XZ`;

    const zpl = baseTemplate
      .replace(/{{producto}}/g, producto?.descripcion || 'N/A')
      .replace(/{{lote}}/g, lote?.codigo_lote || 'N/A')
      .replace(/{{peso}}/g, etiqueta.peso_neto.toString())
      .replace(/{{bulto}}/g, etiqueta.numero_bulto.toString())
      .replace(/{{fecha}}/g, new Date(etiqueta.fecha_creacion).toLocaleDateString())
      .replace(/{{codigo}}/g, `${etiqueta.pedido_venta}-${etiqueta.numero_bulto}`);
    
    toast.info(`Etiqueta ZPL generada (Bulto ${etiqueta.numero_bulto})`, {
      description: <pre className="text-[10px] mt-2 bg-slate-100 p-2 rounded">{zpl}</pre>
    });
  };

  const handleDeleteEtiqueta = async (id: number) => {
    try {
      await apiClient.delete(`/etiquetas-despacho/${id}/`);
      setEtiquetas(etiquetas.filter(e => e.id !== id));
      toast.success('Bulto eliminado');
    } catch (error) {
      toast.error('Error al eliminar bulto');
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">Panel de Empaquetado</h1>
          <p className="text-muted-foreground">Registra pesos y genera etiquetas para despachos.</p>
        </div>
        <Package className="w-10 h-10 text-primary" />
      </div>

      <div className="grid gap-6 md:grid-cols-3">
        <Card className="md:col-span-1 border-primary/20 bg-primary/5">
          <CardHeader>
            <CardTitle>Registro de Bulto</CardTitle>
            <CardDescription>Pesque el bulto y asigne al pedido.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label>Pedido Pendiente</Label>
              <Select value={selectedPedidoId} onValueChange={setSelectedPedidoId}>
                <SelectTrigger className="bg-white">
                  <SelectValue placeholder="Selecciona un pedido" />
                </SelectTrigger>
                <SelectContent>
                  {pedidos.map(p => (
                    <SelectItem key={p.id} value={p.id.toString()}>
                      Pedido #{p.id} - {p.guia_remision}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {selectedPedidoId && (
              <>
                <div className="space-y-2">
                  <Label>Producto en Pedido</Label>
                  <Select 
                    value={currentBulto.productoId} 
                    onValueChange={(v) => setCurrentBulto({...currentBulto, productoId: v})}
                  >
                    <SelectTrigger className="bg-white">
                      <SelectValue placeholder="Selecciona producto" />
                    </SelectTrigger>
                    <SelectContent>
                      {detalles.map(d => (
                        <SelectItem key={d.id} value={d.producto.toString()}>
                          {productos[d.producto]?.descripcion}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label>Lote de Producción (Opcional)</Label>
                  <Select 
                    value={currentBulto.loteId} 
                    onValueChange={(v) => setCurrentBulto({...currentBulto, loteId: v})}
                  >
                    <SelectTrigger className="bg-white">
                      <SelectValue placeholder="Selecciona lote" />
                    </SelectTrigger>
                    <SelectContent>
                      {lotes.slice(0, 15).map(l => (
                        <SelectItem key={l.id} value={l.id.toString()}>
                          {l.codigo_lote}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>

                <div className="space-y-2">
                  <Label className="text-lg font-bold">Peso Neto (KG)</Label>
                  <div className="flex gap-2">
                    <Input 
                      type="number" 
                      placeholder="0.00" 
                      className="text-xl h-12 bg-white font-mono"
                      value={currentBulto.peso}
                      onChange={(e) => setCurrentBulto({...currentBulto, peso: e.target.value})}
                    />
                    <Button className="h-12 px-6" onClick={handleRegisterBulto}>
                      <Plus className="w-5 h-5 mr-2" /> Registrar
                    </Button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>

        <Card className="md:col-span-2 shadow-lg">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div>
                <CardTitle>Bultos Registrados</CardTitle>
                <CardDescription>Relación de bultos pesados para el pedido seleccionado.</CardDescription>
              </div>
              {etiquetas.length > 0 && (
                <div className="text-right">
                  <div className="text-sm text-muted-foreground">Peso Total</div>
                  <Badge className="text-xl px-4 py-1" variant="secondary">
                    {etiquetas.reduce((acc, curr) => acc + parseFloat(curr.peso_neto.toString()), 0).toFixed(2)} KG
                  </Badge>
                </div>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {!selectedPedidoId ? (
              <div className="text-center py-16 text-muted-foreground border-2 border-dashed rounded-xl">
                <Package className="w-16 h-16 mx-auto mb-4 opacity-10" />
                <p className="text-lg">Seleccione un pedido para iniciar el empaque</p>
              </div>
            ) : etiquetas.length === 0 ? (
              <div className="text-center py-16 text-muted-foreground border-2 border-dashed rounded-xl">
                <p className="text-lg">No hay bultos registrados. Inicie el pesaje.</p>
              </div>
            ) : (
              <div className="rounded-md border">
                <Table>
                  <TableHeader className="bg-muted/50">
                    <TableRow>
                      <TableHead className="w-20 pl-4"># Bulto</TableHead>
                      <TableHead>Producto</TableHead>
                      <TableHead>Lote</TableHead>
                      <TableHead className="text-right">Peso Neto</TableHead>
                      <TableHead className="text-right pr-4">Acciones</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {etiquetas.map((e) => (
                      <TableRow key={e.id}>
                        <TableCell className="font-bold pl-4">#{e.numero_bulto}</TableCell>
                        <TableCell className="max-w-[150px] truncate">
                          {productos[e.producto]?.descripcion}
                        </TableCell>
                        <TableCell>
                          <Badge variant="outline">{lotes.find(l => l.id === e.lote)?.codigo_lote || 'N/A'}</Badge>
                        </TableCell>
                        <TableCell className="text-right font-mono font-medium">
                          {e.peso_neto} KG
                        </TableCell>
                        <TableCell className="text-right flex justify-end gap-2 pr-4">
                          <Button variant="outline" size="sm" onClick={() => generateZpl(e)}>
                            <Printer className="w-4 h-4 mr-2" /> Imprimir
                          </Button>
                          <Button variant="ghost" size="sm" className="text-destructive" onClick={() => handleDeleteEtiqueta(e.id)}>
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {selectedPedidoId && etiquetas.length > 0 && (
        <div className="flex justify-end gap-4 pt-4 border-t">
           <Button variant="outline" size="lg" onClick={() => setSelectedPedidoId('')}>
            Cerrar Pedido
          </Button>
          <Button size="lg" className="gap-2 bg-green-600 hover:bg-green-700" onClick={() => {
            toast.success('Despacho finalizado con éxito');
            setSelectedPedidoId('');
          }}>
            <CheckCircle2 className="w-5 h-5" /> Finalizar Despacho
          </Button>
        </div>
      )}
    </div>
  );
}
