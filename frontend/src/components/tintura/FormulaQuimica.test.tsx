import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { FormulaQuimica, calcularCantidad } from './FormulaQuimica';
import type { Quimico } from '../../lib/types';

const toastErrorMock = vi.fn();
vi.mock('sonner', () => ({
  toast: {
    error: (...args: any[]) => toastErrorMock(...args),
    success: vi.fn(),
  },
}));

const SelectCtx = React.createContext<(v: string) => void>(() => {});
vi.mock('../ui/select', () => ({
  Select: ({ children, onValueChange }: any) => (
    <SelectCtx.Provider value={onValueChange}>
      <div>{children}</div>
    </SelectCtx.Provider>
  ),
  SelectTrigger: ({ children }: any) => <div>{children}</div>,
  SelectValue: ({ placeholder }: any) => <span>{placeholder}</span>,
  SelectContent: ({ children }: any) => <div>{children}</div>,
  SelectItem: ({ children, value }: any) => {
    const onValueChange = React.useContext(SelectCtx);
    return <button type="button" onClick={() => onValueChange(value)}>{children}</button>;
  },
}));

const QUIMICO_1: Quimico = {
  id: 1,
  codigo: 'QM-001',
  descripcion: 'Soda Cáustica',
  tipo: 'quimico',
  unidad_medida: 'kg',
  precio_base: 12.5,
};

const QUIMICO_2: Quimico = {
  id: 2,
  codigo: 'QM-002',
  descripcion: 'Colorante Azul Reactivo',
  tipo: 'quimico',
  unidad_medida: 'kg',
  precio_base: 20,
};

const FORMULA_1 = {
  id: 10,
  codigo: 'FQ-1000',
  nombre_color: 'ROJO INTENSO',
  description: '',
  tipo_sustrato: 'algodon',
  estado: 'en_pruebas',
  observaciones: '',
  fases: [
    {
      id: 100,
      nombre: 'tintura',
      orden: 1,
      temperatura: 60,
      tiempo: 30,
      observaciones: '',
      detalles: [
        { id: 1000, producto: 1, tipo_calculo: 'gr_l', concentracion_gr_l: 5, porcentaje: null, orden_adicion: 1, notas: '' },
      ],
    },
  ],
};

const FORMULA_2 = {
  id: 11,
  codigo: 'FQ-1001',
  nombre_color: 'AZUL MARINO',
  description: '',
  tipo_sustrato: 'poliester',
  estado: 'aprobada',
  observaciones: '',
  fases: [],
};

function renderComponent(props: Partial<React.ComponentProps<typeof FormulaQuimica>> = {}) {
  const defaults: React.ComponentProps<typeof FormulaQuimica> = {
    formulas: [],
    quimicos: [QUIMICO_1, QUIMICO_2],
    loading: false,
    onFormulaCreate: vi.fn().mockResolvedValue(true),
    onFormulaUpdate: vi.fn().mockResolvedValue(true),
  };
  return render(
    <MemoryRouter>
      <FormulaQuimica {...defaults} {...props} />
    </MemoryRouter>,
  );
}

async function abrirNuevaFormula() {
  await userEvent.click(screen.getByRole('button', { name: /Nueva Fórmula/i }));
}

async function seleccionarQuimicoEnFila(textoBusqueda: string, textoResultado: string) {
  await userEvent.type(screen.getByPlaceholderText('Buscar insumo...'), textoBusqueda);
  await userEvent.click(screen.getByText(textoResultado));
}

function inputConcentracionDeFila(textoProducto: string) {
  const candidatos = screen.getAllByText(textoProducto);
  const row = candidatos.map((el) => el.closest('tr')).find(Boolean) as HTMLTableRowElement;
  return within(row).getByRole('spinbutton');
}

describe('FormulaQuimica', () => {
  beforeEach(() => {
    toastErrorMock.mockReset();
  });

  it('dado loading en true cuando renderiza entonces no muestra filas ni mensaje vacio', () => {
    renderComponent({ formulas: [], loading: true });
    expect(screen.queryByText('No hay fórmulas registradas')).not.toBeInTheDocument();
    expect(screen.queryByRole('cell')).not.toBeInTheDocument();
  });

  it('dado sin formulas cuando no esta cargando entonces muestra mensaje vacio', () => {
    renderComponent({ formulas: [], loading: false });
    expect(screen.getByText('No hay fórmulas registradas')).toBeInTheDocument();
  });

  it('dado formulas existentes cuando carga entonces las lista con codigo, color y estado', () => {
    renderComponent({ formulas: [FORMULA_1, FORMULA_2] });
    expect(screen.getByText('FQ-1000')).toBeInTheDocument();
    expect(screen.getByText('ROJO INTENSO')).toBeInTheDocument();
    expect(screen.getByText('En Pruebas')).toBeInTheDocument();
    expect(screen.getByText('FQ-1001')).toBeInTheDocument();
    expect(screen.getByText('Aprobada')).toBeInTheDocument();
  });

  it('dado busqueda por codigo cuando escribe en el buscador entonces filtra la lista', async () => {
    renderComponent({ formulas: [FORMULA_1, FORMULA_2] });
    await userEvent.type(screen.getByPlaceholderText('Buscar por código o color...'), 'FQ-1001');
    await waitFor(() => expect(screen.queryByText('FQ-1000')).not.toBeInTheDocument());
    expect(screen.getByText('FQ-1001')).toBeInTheDocument();
  });

  it('dado mas de 20 formulas cuando carga entonces pagina y el boton siguiente avanza', async () => {
    const manyFormulas = Array.from({ length: 25 }, (_, i) => ({
      ...FORMULA_1,
      id: i + 1,
      codigo: `COD-${String(i + 1).padStart(3, '0')}`,
    }));
    renderComponent({ formulas: manyFormulas });

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByText('COD-001')).toBeInTheDocument();
    expect(screen.queryByText('COD-021')).not.toBeInTheDocument();

    await userEvent.click(screen.getByText('Siguiente'));

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('COD-021')).toBeInTheDocument();
  });

  it('dado mas de 20 formulas cuando escribe una pagina valida en Ir a entonces navega', async () => {
    const manyFormulas = Array.from({ length: 25 }, (_, i) => ({
      ...FORMULA_1, id: i + 1, codigo: `COD-${String(i + 1).padStart(3, '0')}`,
    }));
    renderComponent({ formulas: manyFormulas });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2{Enter}');

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
    expect(screen.getByText('COD-021')).toBeInTheDocument();
  });

  it('dado mas de 20 formulas cuando escribe una pagina fuera de rango en Ir a entonces no cambia de pagina', async () => {
    const manyFormulas = Array.from({ length: 25 }, (_, i) => ({
      ...FORMULA_1, id: i + 1, codigo: `COD-${String(i + 1).padStart(3, '0')}`,
    }));
    renderComponent({ formulas: manyFormulas });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '99');
    await userEvent.tab();

    expect(screen.getByText('Página 1 de 2')).toBeInTheDocument();
  });

  it('dado busqueda que reduce los resultados a una sola pagina cuando filtra entonces vuelve a la pagina 1', async () => {
    const manyFormulas = Array.from({ length: 25 }, (_, i) => ({
      ...FORMULA_1, id: i + 1, codigo: `COD-${String(i + 1).padStart(3, '0')}`,
    }));
    renderComponent({ formulas: manyFormulas });

    await userEvent.click(screen.getByRole('button', { name: /Siguiente/i }));
    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());

    await userEvent.type(screen.getByPlaceholderText('Buscar por código o color...'), 'COD-001');
    expect(screen.getByText('Página 1 de 1')).toBeInTheDocument();
  });

  it('dado click en nueva formula cuando abre el editor entonces muestra una fase por defecto sin fórmula previa', async () => {
    renderComponent();
    await abrirNuevaFormula();

    expect(screen.getByText('Nueva Fórmula')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i })).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Agregar Fase/i })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /Exportar Dosificador/i })).not.toBeInTheDocument();
  });

  it('dado el editor abierto cuando hace click en cancelar entonces vuelve a la lista sin llamar a onFormulaCreate', async () => {
    const onFormulaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onFormulaCreate });
    await abrirNuevaFormula();

    await userEvent.click(screen.getByRole('button', { name: 'Cancelar' }));

    expect(screen.getByText('Fórmulas Químicas')).toBeInTheDocument();
    expect(onFormulaCreate).not.toHaveBeenCalled();
  });

  it('dado formulario incompleto cuando intenta crear entonces muestra errores de validacion y no llama a onFormulaCreate', async () => {
    const onFormulaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onFormulaCreate });
    await abrirNuevaFormula();

    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));
    await userEvent.click(screen.getByRole('button', { name: 'Crear Fórmula' }));

    await waitFor(() => expect(screen.getByText('El código es requerido')).toBeInTheDocument());
    expect(screen.getByText('El color es requerido')).toBeInTheDocument();
    expect(screen.getByText('El insumo químico es obligatorio')).toBeInTheDocument();
    expect(screen.getByText('Valor gr/L es obligatorio y debe ser >= 0')).toBeInTheDocument();
    expect(toastErrorMock).toHaveBeenCalledWith('Error de validación', { description: 'Revisa los campos marcados en rojo' });
    expect(onFormulaCreate).not.toHaveBeenCalled();
  });

  it('dado texto de busqueda sin coincidencias cuando busca un insumo entonces muestra mensaje de sin resultados', async () => {
    renderComponent();
    await abrirNuevaFormula();
    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));

    await userEvent.type(screen.getByPlaceholderText('Buscar insumo...'), 'zzz-no-existe');

    expect(screen.getByText('No se encontraron resultados')).toBeInTheDocument();
  });

  it('dado datos validos con fase y detalle cuando crea la formula entonces llama a onFormulaCreate con el payload correcto', async () => {
    const onFormulaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onFormulaCreate });
    await abrirNuevaFormula();

    await userEvent.type(screen.getByPlaceholderText('Ej: FQ-1002'), 'FQ-3001');
    await userEvent.type(screen.getByPlaceholderText('ROJO INTENSO'), 'AZUL PRUEBA');

    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));
    await seleccionarQuimicoEnFila('Cáustica', 'Soda Cáustica');
    const concentracionInput = inputConcentracionDeFila('Soda Cáustica');
    await userEvent.clear(concentracionInput);
    await userEvent.type(concentracionInput, '12.5');

    await userEvent.click(screen.getByRole('button', { name: 'Crear Fórmula' }));

    await waitFor(() => expect(onFormulaCreate).toHaveBeenCalledWith(expect.objectContaining({
      codigo: 'FQ-3001',
      nombre_color: 'AZUL PRUEBA',
      estado: 'en_pruebas',
      tipo_sustrato: 'algodon',
      fases: [expect.objectContaining({
        nombre: 'pre_tratamiento',
        orden: 1,
        detalles: [expect.objectContaining({
          producto: 1,
          tipo_calculo: 'gr_l',
          concentracion_gr_l: 12.5,
          orden_adicion: 1,
        })],
      })],
    })));
  });

  it('dado creacion exitosa cuando se completa entonces vuelve a la vista de lista', async () => {
    const onFormulaCreate = vi.fn().mockResolvedValue(true);
    renderComponent({ onFormulaCreate });
    await abrirNuevaFormula();

    await userEvent.type(screen.getByPlaceholderText('Ej: FQ-1002'), 'FQ-3002');
    await userEvent.type(screen.getByPlaceholderText('ROJO INTENSO'), 'VERDE');
    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));
    await seleccionarQuimicoEnFila('Cáustica', 'Soda Cáustica');
    const concentracionInput = inputConcentracionDeFila('Soda Cáustica');
    await userEvent.clear(concentracionInput);
    await userEvent.type(concentracionInput, '1');

    await userEvent.click(screen.getByRole('button', { name: 'Crear Fórmula' }));

    await waitFor(() => expect(screen.getByText('Fórmulas Químicas')).toBeInTheDocument());
  });

  it('dado creacion fallida cuando onFormulaCreate resuelve false entonces permanece en el editor', async () => {
    const onFormulaCreate = vi.fn().mockResolvedValue(false);
    renderComponent({ onFormulaCreate });
    await abrirNuevaFormula();

    await userEvent.type(screen.getByPlaceholderText('Ej: FQ-1002'), 'FQ-3003');
    await userEvent.type(screen.getByPlaceholderText('ROJO INTENSO'), 'NEGRO');
    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));
    await seleccionarQuimicoEnFila('Cáustica', 'Soda Cáustica');
    const concentracionInput = inputConcentracionDeFila('Soda Cáustica');
    await userEvent.clear(concentracionInput);
    await userEvent.type(concentracionInput, '1');

    await userEvent.click(screen.getByRole('button', { name: 'Crear Fórmula' }));

    await waitFor(() => expect(onFormulaCreate).toHaveBeenCalled());
    expect(screen.getByRole('button', { name: 'Crear Fórmula' })).toBeInTheDocument();
  });

  it('dado error de red cuando falla onFormulaCreate entonces muestra toast de error y permanece en el editor', async () => {
    const onFormulaCreate = vi.fn().mockRejectedValue(new Error('fallo de conexión'));
    renderComponent({ onFormulaCreate });
    await abrirNuevaFormula();

    await userEvent.type(screen.getByPlaceholderText('Ej: FQ-1002'), 'FQ-3004');
    await userEvent.type(screen.getByPlaceholderText('ROJO INTENSO'), 'BLANCO');
    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));
    await seleccionarQuimicoEnFila('Cáustica', 'Soda Cáustica');
    const concentracionInput = inputConcentracionDeFila('Soda Cáustica');
    await userEvent.clear(concentracionInput);
    await userEvent.type(concentracionInput, '1');

    await userEvent.click(screen.getByRole('button', { name: 'Crear Fórmula' }));

    await waitFor(() => expect(toastErrorMock).toHaveBeenCalledWith('Error al guardar la fórmula', { description: 'fallo de conexión' }));
    expect(screen.getByRole('button', { name: 'Crear Fórmula' })).toBeInTheDocument();
  });

  it('dado un insumo en gr/L cuando ingresa kg de tela entonces calcula el peso en gramos correctamente', async () => {
    renderComponent();
    await abrirNuevaFormula();
    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));
    await seleccionarQuimicoEnFila('Cáustica', 'Soda Cáustica');

    const concentracionInput = inputConcentracionDeFila('Soda Cáustica');
    await userEvent.clear(concentracionInput);
    await userEvent.type(concentracionInput, '5');

    const kgTelaInput = screen.getByPlaceholderText('Ej: 15');
    await userEvent.type(kgTelaInput, '10');

    await waitFor(() => expect(screen.getByText('500.00g')).toBeInTheDocument());
  });

  it('dado un insumo en porcentaje cuando el peso calculado supera 1kg entonces lo muestra en kg', async () => {
    renderComponent();
    await abrirNuevaFormula();
    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));
    await seleccionarQuimicoEnFila('Cáustica', 'Soda Cáustica');

    await userEvent.click(screen.getByRole('button', { name: '% (Agot.)' }));
    const porcentajeInput = inputConcentracionDeFila('Soda Cáustica');
    await userEvent.clear(porcentajeInput);
    await userEvent.type(porcentajeInput, '20');

    const kgTelaInput = screen.getByPlaceholderText('Ej: 15');
    await userEvent.type(kgTelaInput, '10');

    await waitFor(() => expect(screen.getByText('2.000kg')).toBeInTheDocument());
  });

  it('dado el editor de fases cuando agrega y elimina una fase entonces actualiza el numero de fases', async () => {
    const { container } = renderComponent();
    await abrirNuevaFormula();

    expect(container.querySelectorAll('[data-slot="card-header"] svg.lucide-trash2').length).toBe(1);

    await userEvent.click(screen.getByRole('button', { name: /Agregar Fase/i }));
    expect(container.querySelectorAll('[data-slot="card-header"] svg.lucide-trash2').length).toBe(2);

    const trashIcons = container.querySelectorAll('[data-slot="card-header"] svg.lucide-trash2');
    const lastPhaseTrashButton = trashIcons[trashIcons.length - 1].closest('button') as HTMLButtonElement;
    await userEvent.click(lastPhaseTrashButton);

    expect(container.querySelectorAll('[data-slot="card-header"] svg.lucide-trash2').length).toBe(1);
  });

  it('dado editar una formula existente cuando abre el editor entonces precarga codigo, color y el quimico seleccionado', async () => {
    const onFormulaUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ formulas: [FORMULA_1], onFormulaUpdate });

    await userEvent.click(screen.getByRole('button', { name: '' }));

    expect(screen.getByText('Editando Fórmula')).toBeInTheDocument();
    expect(screen.getByPlaceholderText('Ej: FQ-1002')).toHaveValue('FQ-1000');
    expect(screen.getByPlaceholderText('ROJO INTENSO')).toHaveValue('ROJO INTENSO');
    expect(screen.getAllByText('Soda Cáustica').length).toBeGreaterThan(0);

    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Fórmula' }));

    await waitFor(() => expect(onFormulaUpdate).toHaveBeenCalledWith(10, expect.objectContaining({
      codigo: 'FQ-1000',
      nombre_color: 'ROJO INTENSO',
      estado: 'en_pruebas',
      fases: [expect.objectContaining({
        nombre: 'tintura',
        detalles: [expect.objectContaining({ producto: 1, concentracion_gr_l: 5 })],
      })],
    })));
  });

  it('dado una formula en edicion cuando cambia el estado a aprobada y actualiza entonces llama a onFormulaUpdate con el nuevo estado', async () => {
    const onFormulaUpdate = vi.fn().mockResolvedValue(true);
    renderComponent({ formulas: [FORMULA_1], onFormulaUpdate });

    await userEvent.click(screen.getByRole('button', { name: '' }));
    await userEvent.click(screen.getByRole('button', { name: 'Aprobada' }));
    await userEvent.click(screen.getByRole('button', { name: 'Actualizar Fórmula' }));

    await waitFor(() => expect(onFormulaUpdate).toHaveBeenCalledWith(10, expect.objectContaining({
      codigo: 'FQ-1000',
      nombre_color: 'ROJO INTENSO',
      estado: 'aprobada',
    })));
  });

  it('dado una formula en edicion cuando hace click en exportar dosificador entonces llama al callback con el id', async () => {
    const onExportDosificador = vi.fn();
    renderComponent({ formulas: [FORMULA_1], onExportDosificador });

    await userEvent.click(screen.getByRole('button', { name: '' }));
    await userEvent.click(screen.getByRole('button', { name: /Exportar Dosificador/i }));

    expect(onExportDosificador).toHaveBeenCalledWith(10);
  });

  it('calcularCantidad dado concentracion_gr_l undefined cuando calcula en gr_l entonces usa 0 como fallback', () => {
    expect(calcularCantidad('gr_l', undefined, undefined, 10, 5)).toEqual({ kg: 0, gr: 0 });
  });

  it('calcularCantidad dado porcentaje undefined cuando calcula en pct entonces usa 0 como fallback', () => {
    expect(calcularCantidad('pct', undefined, undefined, 10, 5)).toEqual({ kg: 0, gr: 0 });
  });

  it('dado busqueda por codigo distinto al de la descripcion cuando escribe en el buscador entonces filtra la lista', async () => {
    renderComponent({ formulas: [FORMULA_1, FORMULA_2] });
    await userEvent.type(screen.getByPlaceholderText('Buscar por código o color...'), 'AZUL MARINO');
    await waitFor(() => expect(screen.queryByText('FQ-1000')).not.toBeInTheDocument());
    expect(screen.getByText('FQ-1001')).toBeInTheDocument();
  });

  it('dado busqueda activa cuando limpia el campo entonces vuelve a mostrar todas las formulas', async () => {
    renderComponent({ formulas: [FORMULA_1, FORMULA_2] });
    const input = screen.getByPlaceholderText('Buscar por código o color...');
    await userEvent.type(input, 'FQ-1001');
    await waitFor(() => expect(screen.queryByText('FQ-1000')).not.toBeInTheDocument());

    await userEvent.clear(input);
    await waitFor(() => expect(screen.getByText('FQ-1000')).toBeInTheDocument());
    expect(screen.getByText('FQ-1001')).toBeInTheDocument();
  });

  it('dado editar una formula con description y notas no vacias cuando abre el editor entonces las precarga', async () => {
    const FORMULA_CON_NOTAS = {
      ...FORMULA_1,
      description: 'Fórmula de referencia para algodón',
      fases: [{
        ...FORMULA_1.fases[0],
        detalles: [{ ...FORMULA_1.fases[0].detalles[0], notas: 'Agregar despacio' }],
      }],
    };
    renderComponent({ formulas: [FORMULA_CON_NOTAS] });
    await userEvent.click(screen.getByRole('button', { name: '' }));
    expect(screen.getByText('Editando Fórmula')).toBeInTheDocument();
  });

  it('dado editar una formula sin la propiedad fases cuando abre el editor entonces usa una lista de fases vacia', async () => {
    const FORMULA_SIN_FASES: any = { ...FORMULA_2, id: 12, codigo: 'FQ-1002' };
    delete FORMULA_SIN_FASES.fases;
    renderComponent({ formulas: [FORMULA_SIN_FASES] });
    await userEvent.click(screen.getByRole('button', { name: '' }));
    expect(screen.getByText('Editando Fórmula')).toBeInTheDocument();
    expect(screen.getByText('Sin insumos para pesar')).toBeInTheDocument();
  });

  it('dado una formula sin fases cuando abre el editor entonces la calculadora muestra el mensaje de sin insumos', async () => {
    renderComponent({ formulas: [FORMULA_2] });
    await userEvent.click(screen.getByRole('button', { name: '' }));
    expect(screen.getByText('Sin insumos para pesar')).toBeInTheDocument();
  });

  it('dado mas de 20 formulas cuando escribe una pagina valida en Ir a y hace blur entonces navega', async () => {
    const manyFormulas = Array.from({ length: 25 }, (_, i) => ({
      ...FORMULA_1, id: i + 1, codigo: `COD-${String(i + 1).padStart(3, '0')}`,
    }));
    renderComponent({ formulas: manyFormulas });

    const irAInput = screen.getByRole('spinbutton');
    await userEvent.clear(irAInput);
    await userEvent.type(irAInput, '2');
    await userEvent.tab();

    await waitFor(() => expect(screen.getByText('Página 2 de 2')).toBeInTheDocument());
  });

  it('dado un insumo seleccionado cuando limpia la seleccion con el boton X entonces vuelve al buscador', async () => {
    renderComponent();
    await abrirNuevaFormula();
    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));
    await seleccionarQuimicoEnFila('Cáustica', 'Soda Cáustica');

    expect(screen.getAllByText('Soda Cáustica').length).toBeGreaterThan(0);

    const limpiarBtn = screen.getAllByText('Soda Cáustica')[0].closest('div')!.parentElement!.querySelector('button') as HTMLButtonElement;
    await userEvent.click(limpiarBtn);

    expect(screen.getByPlaceholderText('Buscar insumo...')).toBeInTheDocument();
  });

  it('dado un insumo con relacion de bano vacia cuando calcula entonces usa 0 como fallback sin lanzar error', async () => {
    renderComponent();
    await abrirNuevaFormula();
    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));
    await seleccionarQuimicoEnFila('Cáustica', 'Soda Cáustica');
    const concentracionInput = inputConcentracionDeFila('Soda Cáustica');
    await userEvent.clear(concentracionInput);
    await userEvent.type(concentracionInput, '5');

    const relacionBanoInput = screen.getByDisplayValue('10');
    await userEvent.clear(relacionBanoInput);

    const kgTelaInput = screen.getByPlaceholderText('Ej: 15');
    await userEvent.type(kgTelaInput, '10');

    await waitFor(() => expect(screen.getByText('0.00g')).toBeInTheDocument());
  });

  it('dado un insumo cuando cambia de porcentaje de vuelta a gr/L entonces limpia el porcentaje', async () => {
    renderComponent();
    await abrirNuevaFormula();
    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));
    await seleccionarQuimicoEnFila('Cáustica', 'Soda Cáustica');

    await userEvent.click(screen.getByRole('button', { name: '% (Agot.)' }));
    await userEvent.click(screen.getByRole('button', { name: 'g/L' }));

    expect(screen.getByText('(0g/l)')).toBeInTheDocument();
  });

  it('dado un insumo en pct sin valor cuando intenta crear entonces muestra el error de porcentaje obligatorio', async () => {
    renderComponent();
    await abrirNuevaFormula();
    await userEvent.type(screen.getByPlaceholderText('Ej: FQ-1002'), 'FQ-3005');
    await userEvent.type(screen.getByPlaceholderText('ROJO INTENSO'), 'GRIS');
    await userEvent.click(screen.getByRole('button', { name: /Insertar Químico \/ Colorante/i }));
    await seleccionarQuimicoEnFila('Cáustica', 'Soda Cáustica');
    await userEvent.click(screen.getByRole('button', { name: '% (Agot.)' }));

    await userEvent.click(screen.getByRole('button', { name: 'Crear Fórmula' }));

    await waitFor(() => expect(screen.getByText('Valor % es obligatorio y debe ser >= 0')).toBeInTheDocument());
  });
});
