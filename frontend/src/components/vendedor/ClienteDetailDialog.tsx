import React from 'react';
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle, DialogTrigger } from '../ui/dialog';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { Switch } from '../ui/switch';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { AlertCircle, DollarSign, History, Printer, CheckCircle, RotateCcw } from 'lucide-react';
import { format } from 'date-fns';
import type { Cliente, PedidoVenta, PagoCliente } from '../../lib/types';
import { parseFechaPedido } from './pedidoUtils';

interface PagoForm {
  monto: string;
  metodo_pago: string;
  comprobante: string;
  notas: string;
  es_anticipo: boolean;
}

interface ClienteDetailDialogProps {
  isOpen: boolean;
  onOpenChange: (open: boolean) => void;
  selectedCliente: Cliente | null;
  isPagoDialogOpen: boolean;
  setIsPagoDialogOpen: (open: boolean) => void;
  pagoForm: PagoForm;
  setPagoForm: React.Dispatch<React.SetStateAction<PagoForm>>;
  handleCreatePago: () => void;
  handlePrintOrder: (pedido: PedidoVenta) => void;
  handleInitiatePagoReversion: (pago: PagoCliente) => void;
}

function ClienteDetailDialogImpl({
  isOpen,
  onOpenChange,
  selectedCliente,
  isPagoDialogOpen,
  setIsPagoDialogOpen,
  pagoForm,
  setPagoForm,
  handleCreatePago,
  handlePrintOrder,
  handleInitiatePagoReversion,
}: ClienteDetailDialogProps) {
  return (
    <Dialog open={isOpen} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[600px] max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Expediente de Cliente: {selectedCliente?.nombre_razon_social}</DialogTitle>
        </DialogHeader>
        <div className="space-y-6 py-4">
          <div className="grid grid-cols-2 gap-4">
            <div className={`p-3 rounded border ${parseFloat(selectedCliente?.saldo_pendiente?.toString() || '0') > 0 ? 'bg-red-50 border-red-200' : 'bg-green-50 border-green-200'}`}>
              <p className="text-[10px] uppercase text-muted-foreground mb-1">
                {parseFloat(selectedCliente?.saldo_pendiente?.toString() || '0') >= 0 ? 'Saldo Pendiente' : 'Saldo a Favor'}
              </p>
              <div className="flex justify-between items-end">
                <p className={`text-xl font-bold ${parseFloat(selectedCliente?.saldo_pendiente?.toString() || '0') > 0 ? 'text-destructive' : 'text-green-600'}`}>
                  ${Math.abs(parseFloat(selectedCliente?.saldo_pendiente?.toString() || '0')).toFixed(3)}
                </p>
                {parseFloat(selectedCliente?.cartera_vencida?.toString() || '0') > 0 && (
                  <div className="text-right flex flex-col items-end">
                    <span className="text-[10px] text-destructive font-bold flex items-center gap-1"><AlertCircle className="w-3 h-3" /> Cartera Vencida</span>
                    <span className="text-sm font-bold text-destructive">${parseFloat(selectedCliente?.cartera_vencida?.toString() || '0').toFixed(3)}</span>
                  </div>
                )}
              </div>
            </div>
            <div className="bg-slate-50 p-3 rounded border">
              <p className="text-[10px] uppercase text-muted-foreground mb-1">Límite Crédito</p>
              <div className="flex items-center justify-between">
                <p className="text-xl font-bold">${parseFloat(selectedCliente?.limite_credito?.toString() || '0').toFixed(0)}</p>
                <Dialog open={isPagoDialogOpen} onOpenChange={setIsPagoDialogOpen}>
                  <DialogTrigger asChild>
                    <Button size="sm" className="h-7 gap-1 bg-primary">
                      <DollarSign className="w-3 h-3" /> Abonos
                    </Button>
                  </DialogTrigger>
                  <DialogContent className="sm:max-w-[400px]">
                    <DialogHeader>
                      <DialogTitle>Registrar Abono / Pago</DialogTitle>
                      <DialogDescription>Abona al saldo del cliente: {selectedCliente?.nombre_razon_social}</DialogDescription>
                    </DialogHeader>
                    <div className="grid gap-4 py-4">
                      <div className="grid gap-2">
                        <Label>Monto a Abonar ($) <span className="text-destructive">*</span></Label>
                        <Input type="number" step="0.01" value={pagoForm.monto} onChange={e => setPagoForm({ ...pagoForm, monto: e.target.value })} placeholder="0.00" />
                      </div>
                      <div className="grid gap-2">
                        <Label>Método de Pago</Label>
                        <Select value={pagoForm.metodo_pago} onValueChange={v => setPagoForm({ ...pagoForm, metodo_pago: v })}>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            <SelectItem value="transferencia">Transferencia</SelectItem>
                            <SelectItem value="efectivo">Efectivo</SelectItem>
                            <SelectItem value="cheque">Cheque</SelectItem>
                            <SelectItem value="otro">Otro</SelectItem>
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="grid gap-2">
                        <Label>Referencia / Comprobante</Label>
                        <Input value={pagoForm.comprobante} onChange={e => setPagoForm({ ...pagoForm, comprobante: e.target.value })} placeholder="# Transacción" />
                      </div>
                      <div className="flex items-center justify-between rounded-lg border p-3">
                        <div className="space-y-0.5">
                          <Label>Es Anticipo</Label>
                          <p className="text-xs text-muted-foreground">
                            Permite que el monto exceda la deuda actual; el excedente queda como saldo a favor del cliente.
                          </p>
                        </div>
                        <Switch
                          checked={pagoForm.es_anticipo}
                          onCheckedChange={(checked) => setPagoForm({ ...pagoForm, es_anticipo: checked })}
                        />
                      </div>
                    </div>
                    <DialogFooter>
                      <Button variant="outline" onClick={() => setIsPagoDialogOpen(false)}>Cancelar</Button>
                      <Button onClick={handleCreatePago}>{pagoForm.es_anticipo ? 'Confirmar Anticipo' : 'Confirmar Abono'}</Button>
                    </DialogFooter>
                  </DialogContent>
                </Dialog>
              </div>
            </div>
          </div>

          <section>
            <h3 className="text-sm font-semibold mb-3 flex items-center gap-2 underline decoration-primary">
              <History className="w-4 h-4" /> Historial Comercial
            </h3>
            <Tabs defaultValue="ventas" className="w-full">
              <TabsList className="grid w-full grid-cols-2 h-8">
                <TabsTrigger value="ventas" className="text-[10px]">Pedidos / Deuda</TabsTrigger>
                <TabsTrigger value="pagos" className="text-[10px]">Abonos / Recibos</TabsTrigger>
              </TabsList>

              <TabsContent value="ventas" className="pt-3">
                <div className="border rounded-md overflow-hidden">
                  <Table>
                    <TableHeader className="bg-slate-50">
                      <TableRow className="h-8">
                        <TableHead className="text-[10px]">Fecha</TableHead>
                        <TableHead className="text-[10px]">Guía</TableHead>
                        <TableHead className="text-[10px] text-right">Monto</TableHead>
                        <TableHead className="text-[10px] text-right">Acción</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {selectedCliente?.pedidos && Array.isArray(selectedCliente.pedidos) && selectedCliente.pedidos.length > 0 ? (
                        selectedCliente.pedidos.map(p => (
                          <TableRow key={p.id} className="h-10">
                            <TableCell className="py-2 text-[10px]">{format(parseFechaPedido(p.fecha_pedido), 'dd/MM/yy')}</TableCell>
                            <TableCell className="py-2 text-[10px] font-mono">{p.guia_remision}</TableCell>
                            <TableCell className="py-2 text-right font-mono text-xs font-bold">${parseFloat(p.total?.toString() || '0').toFixed(2)}</TableCell>
                            <TableCell className="py-2 text-right">
                              <Button variant="ghost" size="icon" className="h-6 w-6" onClick={() => handlePrintOrder(p)}>
                                <Printer className="w-3 h-3" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))
                      ) : <TableRow><TableCell colSpan={4} className="text-center py-4 text-xs italic">Sin registros</TableCell></TableRow>}
                    </TableBody>
                  </Table>
                </div>
              </TabsContent>

              <TabsContent value="pagos" className="pt-3">
                <div className="border rounded-md overflow-hidden">
                  <Table>
                    <TableHeader className="bg-slate-50">
                      <TableRow className="h-8">
                        <TableHead className="text-[10px]">Fecha</TableHead>
                        <TableHead className="text-[10px]">Método</TableHead>
                        <TableHead className="text-[10px] text-right">Monto</TableHead>
                        <TableHead className="text-[10px] text-right">Acciones</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {selectedCliente?.pagos && Array.isArray(selectedCliente.pagos) && selectedCliente.pagos.length > 0 ? (
                        selectedCliente.pagos.map(p => (
                          <TableRow key={p.id} className="h-10">
                            <TableCell className="py-2 text-[10px]">{format(new Date(p.fecha), 'dd/MM/yy')}</TableCell>
                            <TableCell className="py-2 text-[10px] flex items-center gap-1 capitalize">
                              <CheckCircle className="w-2.5 h-2.5 text-green-500" /> {p.metodo_pago}
                            </TableCell>
                            <TableCell className="py-2 text-right font-mono text-xs text-green-600 font-bold">+ ${parseFloat(p.monto.toString()).toFixed(2)}</TableCell>
                            <TableCell className="py-2 text-right">
                              <Button
                                variant="ghost"
                                size="icon"
                                className="h-6 w-6 text-red-500 hover:text-red-700 hover:bg-red-50"
                                onClick={() => handleInitiatePagoReversion(p)}
                                title="Revertir pago"
                              >
                                <RotateCcw className="w-4 h-4" />
                              </Button>
                            </TableCell>
                          </TableRow>
                        ))
                      ) : <TableRow><TableCell colSpan={4} className="text-center py-4 text-xs italic">No hay abonos aún</TableCell></TableRow>}
                    </TableBody>
                  </Table>
                </div>
              </TabsContent>
            </Tabs>
          </section>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export const ClienteDetailDialog = React.memo(ClienteDetailDialogImpl);
