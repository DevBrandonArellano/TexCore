import React, { useState, useMemo, useRef } from 'react';
import { useForm, useFieldArray, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import * as z from 'zod';
import { Card, CardContent, CardHeader, CardTitle } from '../ui/card';
import { Button } from '../ui/button';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { Badge } from '../ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../ui/table';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../ui/select';
import { toast } from 'sonner';
import {
  Plus,
  Pencil,
  Trash2,
  ChevronRight,
  ArrowLeft,
  Calculator,
  Search,
  CheckCircle2,
  Clock,
  GripVertical,
  X,
} from 'lucide-react';
import { useSearchParams } from 'react-router-dom';
import { Quimico } from '../../lib/types';

// --- Esquemas Zod de Validación para Producción ---
// Preprocesador para manejar inputs vacíos y números de forma segura
const NumberField = z.preprocess(
  (val) => (val === "" || val === null || val === undefined || Number.isNaN(Number(val)) ? undefined : Number(val)),
  z.number().min(0, "Debe ser >= 0").optional()
).optional();

const DetalleSchema = z.object({
  id: z.number().optional(),
  producto: z.number().min(1, "El insumo químico es obligatorio"),
  tipo_calculo: z.enum(['gr_l', 'pct']),
  concentracion_gr_l: NumberField,
  porcentaje: NumberField,
  orden_adicion: z.number().min(1, "Orden de adición requerido"),
  notas: z.string().optional(),
  _productoObj: z.any().optional()
}).superRefine((data, ctx) => {
  if (data.tipo_calculo === 'gr_l' && data.concentracion_gr_l === undefined) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Valor gr/L es obligatorio y debe ser >= 0",
      path: ["concentracion_gr_l"]
    });
  }
  if (data.tipo_calculo === 'pct' && data.porcentaje === undefined) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      message: "Valor % es obligatorio y debe ser >= 0",
      path: ["porcentaje"]
    });
  }
});

const FaseSchema = z.object({
  id: z.number().optional(),
  nombre: z.enum(['pre_tratamiento', 'tintura', 'lavado', 'suavizado', 'auxiliares']),
  orden: z.number().min(1),
  temperatura: NumberField,
  tiempo: NumberField,
  observaciones: z.string().optional(),
  detalles: z.array(DetalleSchema).min(1, "La fase debe tener al menos un insumo químico")
});
const FormulaSchema = z.object({
  id: z.number().optional(),
  codigo: z.string().min(1, "El código es requerido"),
  nombre_color: z.string().min(1, "El color es requerido"),
  description: z.string().optional(),
  tipo_sustrato: z.string().optional(),
  estado: z.enum(['en_pruebas', 'aprobada']),
  observaciones: z.string().optional(),
  fases: z.array(FaseSchema).min(1, "Debe agregar al menos una fase de tintura")
});

type FormulaFormValues = z.infer<typeof FormulaSchema>;

// --- Helpers de Cálculo ---
function calcularCantidad(
  tipo_calculo: 'gr_l' | 'pct',
  concentracion_gr_l: number | null | undefined,
  porcentaje: number | null | undefined,
  kgTela: number,
  relacionBano: number
): { kg: number; gr: number } | null {
  if (kgTela <= 0 || relacionBano <= 0) return null;
  const volumenLitros = kgTela * relacionBano;
  
  let cantidadKg = 0;
  if (tipo_calculo === 'gr_l') {
    cantidadKg = (volumenLitros * (concentracion_gr_l ?? 0)) / 1000;
  } else {
    cantidadKg = (kgTela * (porcentaje ?? 0)) / 100;
  }
  
  return { kg: cantidadKg, gr: cantidadKg * 1000 };
}

// --- Componente Buscador Optimizado ---
interface BuscadorQuimicoProps {
  quimicos: Quimico[];
  productoSeleccionado: Quimico | null | undefined;
  onSelect: (q: Quimico | null) => void;
  disabled?: boolean;
}

function BuscadorQuimico({ quimicos, productoSeleccionado, onSelect, disabled }: BuscadorQuimicoProps) {
  const [query, setQuery] = useState('');
  const [abierto, setAbierto] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  const filtrados = useMemo(() => {
    const q = query.toLowerCase();
    if (!q) return [];
    return quimicos.filter((qu) => 
      qu.descripcion?.toLowerCase().includes(q) || qu.codigo?.toLowerCase().includes(q)
    ).slice(0, 10);
  }, [query, quimicos]);

  if (productoSeleccionado) {
    return (
      <div className="flex items-center gap-2 text-[11px] bg-primary/5 px-2 py-1 rounded-md border border-primary/20 w-fit">
        <div className="flex flex-col flex-1 truncate">
          <span className="font-bold text-primary uppercase truncate">{productoSeleccionado.descripcion}</span>
          <span className="opacity-60 font-mono">{productoSeleccionado.codigo}</span>
        </div>
        {!disabled && (
          <button type="button" onClick={() => onSelect(null)} className="p-1 hover:text-destructive">
            <X className="w-3 h-3" />
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="relative w-full min-w-[200px]" ref={ref}>
      <div className="flex items-center gap-2 border rounded-md px-2 py-1 bg-background text-xs">
        <Search className="w-3 h-3 text-muted-foreground" />
        <input
          className="flex-1 bg-transparent outline-none w-full"
          placeholder="Buscar insumo..."
          value={query}
          onFocus={() => setAbierto(true)}
          onChange={(e) => setQuery(e.target.value)}
        />
      </div>
      {abierto && query && (
        <div className="absolute z-[100] top-full mt-1 w-72 bg-popover border rounded-md shadow-xl max-h-48 overflow-auto">
          {filtrados.length === 0 ? (
            <div className="p-2 text-xs text-muted-foreground text-center">No se encontraron resultados</div>
          ) : (
            filtrados.map((q) => (
              <div 
                key={q.id} 
                className="p-2 hover:bg-accent cursor-pointer text-[11px] border-b" 
                onMouseDown={(e) => { e.preventDefault(); onSelect(q); setAbierto(false); setQuery(''); }}
              >
                <div className="font-bold">{q.descripcion}</div>
                <div className="text-[10px] opacity-50 font-mono">{q.codigo}</div>
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}

function EstadoBadge({ estado }: { estado: string }) {
  if (estado === 'aprobada') {
    return (
      <Badge className="bg-emerald-100 text-emerald-700 border-emerald-200 gap-1 hover:bg-emerald-100">
        <CheckCircle2 className="w-3 h-3" /> Aprobada
      </Badge>
    );
  }
  return (
    <Badge variant="secondary" className="gap-1">
      <Clock className="w-3 h-3" /> En Pruebas
    </Badge>
  );
}

interface FormulaQuimicaProps {
  formulas: any[];
  quimicos: Quimico[];
  loading?: boolean;
  canDelete?: boolean;
  onFormulaCreate: (f: FormulaFormValues) => Promise<boolean>;
  onFormulaUpdate: (id: number, f: FormulaFormValues) => Promise<boolean>;
  onFormulaDuplicate?: (id: number) => void;
  onFormulaDelete?: (id: number) => void;
  onExportDosificador?: (id: number) => void;
}

export function FormulaQuimica({ 
  formulas, quimicos, loading, onFormulaCreate, onFormulaUpdate, 
  onFormulaDuplicate, onFormulaDelete, onExportDosificador 
}: FormulaQuimicaProps) {
  const [searchParams, setSearchParams] = useSearchParams();
  const [vista, setVista] = useState<'lista' | 'editor'>('lista');
  const [guardando, setGuardando] = useState(false);
  const busqueda = searchParams.get('q') || '';

  const setBusqueda = (val: string) => {
    const next = new URLSearchParams(searchParams);
    if (val) next.set('q', val);
    else next.delete('q');
    setSearchParams(next, { replace: true });
  };
  
  // Estado local para la calculadora puramente UI
  const [calculadora, setCalculadora] = useState({ kg_tela: '', relacion_bano: '10' });

  // --- Integración React Hook Form ---
  const form = useForm<FormulaFormValues>({
    resolver: zodResolver(FormulaSchema as any),
    mode: 'onChange',
    defaultValues: {
      codigo: '', nombre_color: '', description: '', tipo_sustrato: 'algodon', estado: 'en_pruebas', observaciones: '', fases: []
    }
  });

  const { fields: phaseFields, append: appendPhase, remove: removePhase } = useFieldArray({
    control: form.control,
    name: "fases"
  });

  // Watcher for reactive calculations
  const fasesWatcher = form.watch("fases");

  const abrirEditar = (formula: any) => {
    form.reset({
      id: formula.id,
      codigo: formula.codigo,
      nombre_color: formula.nombre_color,
      description: formula.description || '',
      tipo_sustrato: formula.tipo_sustrato || 'algodon',
      estado: formula.estado,
      observaciones: formula.observaciones || '',
      fases: formula.fases?.map((f: any) => ({
        id: f.id,
        nombre: f.nombre,
        orden: f.orden,
        temperatura: f.temperatura,
        tiempo: f.tiempo,
        observaciones: f.observaciones || '',
        detalles: f.detalles.map((d: any) => ({
          id: d.id,
          producto: d.producto,
          tipo_calculo: d.tipo_calculo,
          concentracion_gr_l: d.concentracion_gr_l,
          porcentaje: d.porcentaje,
          orden_adicion: d.orden_adicion,
          notas: d.notas || '',
          _productoObj: quimicos.find((q) => q.id === d.producto)
        }))
      })) || []
    });
    setVista('editor');
  };

  const abrirNuevo = () => {
    form.reset({
      codigo: '', nombre_color: '', description: '', tipo_sustrato: 'algodon', estado: 'en_pruebas', observaciones: '', fases: [
        { nombre: 'pre_tratamiento', orden: 1, temperatura: undefined, tiempo: undefined, detalles: [] }
      ]
    });
    setVista('editor');
  };

  const onSubmit = async (data: FormulaFormValues) => {
    try {
      setGuardando(true);
      
      // Limpiar data para backend
      const dataToSubmit = {
        ...data,
        fases: data.fases.map((f, i) => ({
          ...f,
          orden: i + 1,
          detalles: f.detalles.map((d, j) => ({
            ...d,
            orden_adicion: j + 1
          }))
        }))
      };

      const exito = data.id 
        ? await onFormulaUpdate(data.id, dataToSubmit) 
        : await onFormulaCreate(dataToSubmit);
      
      if (exito) {
        setVista('lista');
      }
    } catch (err: any) {
      toast.error('Error al guardar la fórmula', { description: err.message });
    } finally {
      setGuardando(false);
    }
  };

  const onInvalid = (errors: any) => {
    toast.error('Error de validación', { description: 'Revisa los campos marcados en rojo' });
    console.log("Validation Errors:", errors);
  };

  if (vista === 'lista') {
    return (
      <Card>
        <CardHeader>
          <div className="flex justify-between items-center">
            <CardTitle>Fórmulas Químicas</CardTitle>
            <Button onClick={abrirNuevo}>
              <Plus className="w-4 h-4 mr-2" /> Nueva Fórmula
            </Button>
          </div>
          <Input 
            placeholder="Buscar por código o color..." 
            value={busqueda} 
            onChange={(e) => setBusqueda(e.target.value)} 
            className="max-w-sm" 
          />
        </CardHeader>
        <CardContent>
          <Table>
            <TableHeader><TableRow><TableHead>Código</TableHead><TableHead>Nombre</TableHead><TableHead>Estado</TableHead><TableHead className="text-right">Acciones</TableHead></TableRow></TableHeader>
            <TableBody>
              {formulas
                .filter(f => 
                  f.codigo.toLowerCase().includes(busqueda.toLowerCase()) || 
                  f.nombre_color.toLowerCase().includes(busqueda.toLowerCase())
                )
                .map((f: any) => (
                <TableRow key={f.id}>
                  <TableCell className="font-mono text-xs font-bold">{f.codigo}</TableCell>
                  <TableCell className="uppercase">{f.nombre_color}</TableCell>
                  <TableCell><EstadoBadge estado={f.estado} /></TableCell>
                  <TableCell className="text-right">
                    <Button variant="outline" size="sm" onClick={() => abrirEditar(f)}>
                      <Pencil className="w-4 h-4" />
                    </Button>
                  </TableCell>
                </TableRow>
              ))}
              {formulas.length === 0 && !loading && (
                <TableRow>
                  <TableCell colSpan={4} className="text-center text-muted-foreground py-8">No hay fórmulas registradas</TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    );
  }

  const isEditing = !!form.getValues('id');
  return (
    <div className="flex flex-col min-h-screen">
      <div className="mb-4 flex items-center justify-between text-sm text-muted-foreground flex-shrink-0">
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={() => setVista('lista')}><ArrowLeft className="w-4 h-4 mr-2"/> Volver</Button>
          <ChevronRight className="w-4 h-4" />
          <span className="font-medium text-foreground">{isEditing ? 'Editando Fórmula' : 'Nueva Fórmula'}</span>
        </div>
        {isEditing && onExportDosificador && (
          <Button variant="outline" size="sm" className="bg-blue-50 text-blue-700 border-blue-200" onClick={() => onExportDosificador(form.getValues('id')!)}>
            <Calculator className="w-4 h-4 mr-2" /> Exportar Dosificador (Infotint)
          </Button>
        )}
      </div>

      <form onSubmit={form.handleSubmit(onSubmit as any, onInvalid)} className="flex flex-col flex-1 min-h-0">
        
        <div className="flex flex-col lg:flex-row gap-4 flex-1 min-h-0 pb-4">
          
          {/* PANEL IZQUIERDO */}
          <div className="flex-1 flex flex-col space-y-4 overflow-y-auto pr-2">
            <Card className="flex-shrink-0">
              <CardContent className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-6">
                <div className="space-y-2">
                  <Label>Código <span className="text-red-500">*</span></Label>
                  <Input {...form.register('codigo')} placeholder="Ej: FQ-1002" />
                  {form.formState.errors.codigo && <span className="text-xs text-red-500">{form.formState.errors.codigo.message}</span>}
                </div>
                <div className="space-y-2">
                  <Label>Nombre del Color <span className="text-red-500">*</span></Label>
                  <Input {...form.register('nombre_color')} placeholder="ROJO INTENSO" className="uppercase" />
                  {form.formState.errors.nombre_color && <span className="text-xs text-red-500">{form.formState.errors.nombre_color.message}</span>}
                </div>
                <div className="space-y-2">
                  <Label>Estado</Label>
                  <Controller
                    control={form.control}
                    name="estado"
                    render={({ field }) => (
                      <Select value={field.value} onValueChange={field.onChange}>
                        <SelectTrigger><SelectValue /></SelectTrigger>
                        <SelectContent>
                          <SelectItem value="en_pruebas">En Pruebas</SelectItem>
                          <SelectItem value="aprobada">Aprobada</SelectItem>
                        </SelectContent>
                      </Select>
                    )}
                  />
                </div>
              </CardContent>
            </Card>

            <div className="space-y-4">
              <div className="flex justify-between items-center px-1">
                <h3 className="text-lg font-bold flex items-center gap-2">
                  <Clock className="w-5 h-5 text-primary" /> Fases del Proceso (Dyeing Tool)
                </h3>
                <Button 
                  type="button" 
                  size="sm" 
                  variant="outline" 
                  onClick={() => appendPhase({ nombre: 'tintura', orden: phaseFields.length + 1, temperatura: undefined, tiempo: undefined, detalles: [] })}
                >
                  <Plus className="w-4 h-4 mr-1" /> Agregar Fase
                </Button>
              </div>

              {phaseFields.map((phase, pIndex) => (
                <Card key={phase.id} className="border-l-4 border-l-primary/50">
                  <CardHeader className="py-3 px-4 bg-muted/30 flex flex-row items-center justify-between gap-4">
                    <div className="flex flex-1 items-center gap-4">
                      <div className="flex items-center gap-2">
                        <Badge variant="outline" className="h-6 w-6 flex items-center justify-center p-0 rounded-full">{pIndex + 1}</Badge>
                        <Controller
                          control={form.control}
                          name={`fases.${pIndex}.nombre`}
                          render={({ field }) => (
                            <Select value={field.value} onValueChange={field.onChange}>
                              <SelectTrigger className="h-8 w-44">
                                <SelectValue />
                              </SelectTrigger>
                              <SelectContent>
                                <SelectItem value="pre_tratamiento">Pre-Tratamiento / Blanqueo</SelectItem>
                                <SelectItem value="tintura">Tintura Principal</SelectItem>
                                <SelectItem value="lavado">Lavado / Jabonado</SelectItem>
                                <SelectItem value="suavizado">Suavizado / Acabado Final</SelectItem>
                                <SelectItem value="auxiliares">Baño de Auxiliares Extras</SelectItem>
                              </SelectContent>
                            </Select>
                          )}
                        />
                      </div>
                      <div className="flex items-center gap-2">
                        <Label className="text-[10px] uppercase opacity-60">Temp (°C)</Label>
                        <Input type="number" className="h-7 w-16 text-xs px-1" {...form.register(`fases.${pIndex}.temperatura`, { valueAsNumber: true })} />
                        <Label className="text-[10px] uppercase opacity-60">Tiempo (min)</Label>
                        <Input type="number" className="h-7 w-16 text-xs px-1" {...form.register(`fases.${pIndex}.tiempo`, { valueAsNumber: true })} />
                      </div>
                    </div>
                    <Button type="button" variant="ghost" size="sm" onClick={() => removePhase(pIndex)} className="text-destructive hover:bg-destructive/10">
                      <Trash2 className="w-4 h-4"/>
                    </Button>
                  </CardHeader>
                  <CardContent className="p-0">
                    <InnerChemicalsList 
                      pIndex={pIndex} 
                      control={form.control} 
                      register={form.register} 
                      quimicos={quimicos}
                      setValue={form.setValue}
                      errors={form.formState.errors.fases?.[pIndex]?.detalles as any}
                      detallesWatcher={fasesWatcher[pIndex]?.detalles || []}
                    />
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>

          {/* PANEL DERECHO - CALCULADORA EN VIVO */}
          <div className="lg:w-80 flex-shrink-0 flex flex-col min-h-0">
            <Card className="bg-slate-50 border-slate-200 shadow-inner flex flex-col flex-1 min-h-0">
              <CardHeader className="py-3 px-4 bg-slate-100 border-b flex-shrink-0">
                <CardTitle className="text-sm uppercase flex items-center gap-2 text-slate-700">
                  <Calculator className="w-4 h-4 text-emerald-600"/> Pesaje en Laboratorio
                </CardTitle>
              </CardHeader>
              <CardContent className="space-y-4 p-4 flex flex-col flex-1 min-h-0">
                <div className="grid grid-cols-2 gap-3 flex-shrink-0 bg-white p-3 rounded-md border shadow-sm">
                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold text-slate-600">Volumen (Kg Tela)</Label>
                    <Input 
                      className="h-8 text-right font-mono font-bold text-slate-700" type="number" 
                      value={calculadora.kg_tela} onChange={(e) => setCalculadora(p => ({...p, kg_tela: e.target.value}))} placeholder="Ej: 15"
                    />
                  </div>
                  <div className="space-y-1.5">
                    <Label className="text-xs font-semibold text-slate-600">Relación Baño</Label>
                    <div className="relative">
                      <span className="absolute left-2 top-1.5 text-xs font-mono opacity-50">1 :</span>
                      <Input 
                        className="h-8 text-right pl-6 font-mono font-bold text-slate-700" type="number" 
                        value={calculadora.relacion_bano} onChange={(e) => setCalculadora(p => ({...p, relacion_bano: e.target.value}))} 
                      />
                    </div>
                  </div>
                </div>

                <div className="flex-1 overflow-y-auto space-y-4 pr-1">
                  {fasesWatcher.map((fase, fi) => (
                    <div key={fi} className="space-y-1">
                      <div className="text-[10px] uppercase font-bold text-slate-400 border-b pb-0.5 mb-1 flex justify-between">
                        <span>Fase {fi + 1}: {fase.nombre}</span>
                        <span>{fase.temperatura}°C / {fase.tiempo}'</span>
                      </div>
                      {fase.detalles.map((det, di) => {
                        if (!det.producto) return null;
                        const kg = parseFloat(calculadora.kg_tela) || 0;
                        const rb = parseFloat(calculadora.relacion_bano) || 0;
                        const c_grl = det.tipo_calculo === 'gr_l' ? Number(det.concentracion_gr_l) : null;
                        const c_pct = det.tipo_calculo === 'pct' ? Number(det.porcentaje) : null;
                        const calc = calcularCantidad(det.tipo_calculo, c_grl, c_pct, kg, rb);
                        const valTexto = det.tipo_calculo === 'gr_l' ? `${c_grl || 0}g/l` : `${c_pct || 0}%`;

                        return (
                          <div key={di} className="flex justify-between items-center bg-white p-2 rounded border border-slate-100 shadow-sm gap-2">
                            <div className="flex flex-col flex-1 truncate">
                              <span className="text-xs font-bold truncate text-slate-700">
                                {det._productoObj?.descripcion || 'Insumo'}
                              </span>
                              <span className="text-[10px] text-slate-400 font-mono">({valTexto})</span>
                            </div>
                            <div className="font-mono font-bold text-sm text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded flex-shrink-0">
                              {calc ? (calc.gr >= 1000 ? `${calc.kg.toFixed(3)}kg` : `${calc.gr.toFixed(2)}g`) : '0.00g'}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  ))}
                  
                  {fasesWatcher.length === 0 && (
                    <div className="text-xs text-center text-slate-400 py-4">Sin insumos para pesar</div>
                  )}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>

        {/* CONTROLES / FOOTER STICKY */}
        <div className="flex justify-end gap-3 pt-3 pb-2 border-t bg-background mt-auto flex-shrink-0">
          <Button type="button" variant="outline" onClick={() => setVista('lista')}>Cancelar</Button>
          <Button type="submit" disabled={guardando} className="bg-emerald-600 hover:bg-emerald-700 text-white min-w-[150px]">
            {guardando ? 'Guardando...' : (isEditing ? 'Actualizar Fórmula' : 'Crear Fórmula')}
          </Button>
        </div>

      </form>
    </div>
  );
}

// NUEVO COMPONENTE INTERNO PARA MANEJAR QUIMICOS POR FASE
function InnerChemicalsList({ pIndex, control, register, quimicos, setValue, errors, detallesWatcher }: any) {
  const { fields, append, remove, swap } = useFieldArray({
    control,
    name: `fases.${pIndex}.detalles`
  });

  return (
    <Table>
      <TableHeader className="bg-background/50">
        <TableRow>
          <TableHead className="w-8"></TableHead>
          <TableHead className="w-8">#</TableHead>
          <TableHead className="min-w-[200px]">Insumo (Infotint Sync)</TableHead>
          <TableHead className="w-24 text-center">Cálculo</TableHead>
          <TableHead className="w-32">Valor</TableHead>
          <TableHead className="w-[50px]"></TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {fields.map((field, index) => {
          const error = errors?.[index] as any;
          const watchTipoCalculo = detallesWatcher[index]?.tipo_calculo;

          return (
            <TableRow key={field.id} className={error ? "bg-red-50/50" : "group"}>
              <TableCell className="py-1">
                <div className="flex flex-col gap-0.5 opacity-0 group-hover:opacity-100">
                  <button type="button" onClick={() => index > 0 && swap(index, index - 1)} disabled={index === 0} className="disabled:opacity-20 hover:text-primary"><Plus className="w-3 h-3 rotate-45" /></button>
                  <button type="button" onClick={() => index < fields.length - 1 && swap(index, index + 1)} disabled={index === fields.length - 1} className="disabled:opacity-20 hover:text-primary"><Plus className="w-3 h-3 rotate-[135deg]" /></button>
                </div>
              </TableCell>
              <TableCell className="font-mono text-[10px] opacity-50 py-1">{index + 1}</TableCell>
              <TableCell className="py-1">
                <Controller
                  control={control}
                  name={`fases.${pIndex}.detalles.${index}.producto`}
                  render={({ field: controllerField }) => (
                    <div className="flex flex-col">
                      <BuscadorQuimico 
                        quimicos={quimicos}
                        productoSeleccionado={detallesWatcher[index]?._productoObj}
                        onSelect={(q) => {
                          controllerField.onChange(q?.id || 0);
                          setValue(`fases.${pIndex}.detalles.${index}._productoObj`, q);
                        }}
                      />
                      {error?.producto && <span className="text-[10px] text-red-500 mt-1">{error.producto.message}</span>}
                    </div>
                  )}
                />
              </TableCell>
              <TableCell className="py-1">
                <Controller
                  control={control}
                  name={`fases.${pIndex}.detalles.${index}.tipo_calculo`}
                  render={({ field: controllerField }) => (
                    <Select value={controllerField.value} onValueChange={(val) => {
                        controllerField.onChange(val);
                        if (val === 'gr_l') setValue(`fases.${pIndex}.detalles.${index}.porcentaje`, undefined);
                        else setValue(`fases.${pIndex}.detalles.${index}.concentracion_gr_l`, undefined);
                      }}>
                      <SelectTrigger className="h-7 text-[11px]"><SelectValue /></SelectTrigger>
                      <SelectContent>
                        <SelectItem value="gr_l">g/L</SelectItem>
                        <SelectItem value="pct">% (Agot.)</SelectItem>
                      </SelectContent>
                    </Select>
                  )}
                />
              </TableCell>
              <TableCell className="py-1">
                 <div className="flex flex-col">
                  {watchTipoCalculo === 'gr_l' ? (
                    <div className="relative">
                      <Input 
                        type="number" step="0.0001" className="h-7 text-xs pr-7"
                        {...register(`fases.${pIndex}.detalles.${index}.concentracion_gr_l`, { valueAsNumber: true })}
                      />
                      <span className="absolute right-1 top-1.5 text-[9px] opacity-40">g/L</span>
                    </div>
                  ) : (
                    <div className="relative">
                      <Input 
                        type="number" step="0.0001" className="h-7 text-xs pr-7"
                        {...register(`fases.${pIndex}.detalles.${index}.porcentaje`, { valueAsNumber: true })}
                      />
                      <span className="absolute right-1 top-1.5 text-[9px] opacity-40">%</span>
                    </div>
                  )}
                  {error?.concentracion_gr_l && <span className="text-[10px] text-red-500 mt-0.5">{error.concentracion_gr_l.message}</span>}
                  {error?.porcentaje && <span className="text-[10px] text-red-500 mt-0.5">{error.porcentaje.message}</span>}
                 </div>
              </TableCell>
              <TableCell className="py-1 text-right">
                <button type="button" onClick={() => remove(index)} className="text-muted-foreground hover:text-red-500 p-1">
                  <Trash2 className="w-3.5 h-3.5"/>
                </button>
              </TableCell>
            </TableRow>
          );
        })}
        <TableRow className="bg-muted/5 hover:bg-muted/10">
          <TableCell colSpan={6} className="py-1 text-center">
            <Button 
              type="button" size="sm" variant="ghost" className="text-[10px] h-6 w-full text-primary"
              onClick={() => append({ producto: 0, tipo_calculo: 'gr_l', concentracion_gr_l: undefined, porcentaje: undefined, orden_adicion: fields.length + 1, notas: '' })}
            >
              <Plus className="w-3 h-3 mr-1" /> Insertar Químico / Colorante
            </Button>
          </TableCell>
        </TableRow>
      </TableBody>
    </Table>
  );
}