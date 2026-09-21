import { describe, it, expect } from 'vitest';
import {
  isChemicalType,
  chemicalToProduct,
  productToChemical,
  syncRemoveItemById,
  syncAddChemicalToProducts,
  syncUpdateChemicalInProducts,
  syncAddProductToChemicals,
  syncUpdateProductInChemicals,
} from './catalogSync';
import type { Producto, Quimico } from './types';

describe('catalogSync', () => {
  describe('isChemicalType', () => {
    it('dado quimico o insumo cuando se evalua entonces retorna true', () => {
      expect(isChemicalType('quimico')).toBe(true);
      expect(isChemicalType('insumo')).toBe(true);
      expect(isChemicalType('Quimico')).toBe(true);
      expect(isChemicalType('  INSUMO  ')).toBe(true);
    });

    it('dado otros tipos o valores nulos cuando se evalua entonces retorna false', () => {
      expect(isChemicalType('hilo')).toBe(false);
      expect(isChemicalType('tela')).toBe(false);
      expect(isChemicalType('colorante')).toBe(false);
      expect(isChemicalType(null)).toBe(false);
      expect(isChemicalType(undefined)).toBe(false);
      expect(isChemicalType('')).toBe(false);
    });
  });

  describe('chemicalToProduct & productToChemical', () => {
    const mockChemical: Quimico = {
      id: 10,
      codigo: 'Q-01',
      descripcion: 'Soda Caustica',
      tipo: 'quimico',
      unidad_medida: 'kg',
      stock_minimo: 50,
      presentacion: 'Saco 25kg',
      precio_base: 15.5,
    };

    it('dado un quimico cuando se convierte a producto entonces conserva atributos y define tipo quimico', () => {
      const prod = chemicalToProduct(mockChemical);
      expect(prod.id).toBe(10);
      expect(prod.codigo).toBe('Q-01');
      expect(prod.descripcion).toBe('Soda Caustica');
      expect(prod.tipo).toBe('quimico');
      expect(prod.unidad_medida).toBe('kg');
      expect(prod.stock_minimo).toBe(50);
      expect(prod.precio_base).toBe(15.5);
    });

    it('dado un producto quimico cuando se convierte a quimico entonces conserva atributos', () => {
      const mockProduct: Producto = {
        id: 20,
        codigo: 'INS-01',
        descripcion: 'Cono Plastico',
        tipo: 'insumo',
        unidad_medida: 'unidades',
        stock_minimo: 100,
        precio_base: 0.25,
      };
      const chem = productToChemical(mockProduct);
      expect(chem.id).toBe(20);
      expect(chem.codigo).toBe('INS-01');
      expect(chem.descripcion).toBe('Cono Plastico');
      expect(chem.tipo).toBe('quimico');
      expect(chem.unidad_medida).toBe('unidades');
      expect(chem.stock_minimo).toBe(100);
      expect(chem.precio_base).toBe(0.25);
    });
  });

  describe('syncRemoveItemById', () => {
    it('dado arreglo de items cuando se remueve por id entonces retorna nuevo arreglo sin mutar el original', () => {
      const items = [{ id: 1 }, { id: 2 }, { id: 3 }];
      const result = syncRemoveItemById(items, 2);
      expect(result).toEqual([{ id: 1 }, { id: 3 }]);
      expect(items).toHaveLength(3);
    });
  });

  describe('syncAddChemicalToProducts', () => {
    const prodExistente: Producto = {
      id: 1,
      codigo: 'HIL-01',
      descripcion: 'Hilo Algodon',
      tipo: 'hilo',
      unidad_medida: 'kg',
      stock_minimo: 10,
      precio_base: 5,
    };

    it('dado un quimico nuevo cuando se agrega a productos entonces lo incorpora al arreglo', () => {
      const nuevoQuimico: Quimico = {
        id: 2,
        codigo: 'Q-02',
        descripcion: 'Acido Acetico',
        tipo: 'quimico',
        unidad_medida: 'l',
        stock_minimo: 20,
        precio_base: 8,
      };
      const result = syncAddChemicalToProducts([prodExistente], nuevoQuimico);
      expect(result).toHaveLength(2);
      expect(result[1].codigo).toBe('Q-02');
      expect(result[1].tipo).toBe('quimico');
    });

    it('dado un quimico con id existente cuando se agrega entonces actualiza el producto existente', () => {
      const prodQuimico: Producto = {
        id: 2,
        codigo: 'Q-02',
        descripcion: 'Acido Acetico Previo',
        tipo: 'quimico',
        unidad_medida: 'l',
        stock_minimo: 10,
        precio_base: 7,
      };
      const quimicoActualizado: Quimico = {
        id: 2,
        codigo: 'Q-02-B',
        descripcion: 'Acido Acetico 80%',
        tipo: 'quimico',
        unidad_medida: 'l',
        stock_minimo: 25,
        precio_base: 9,
      };
      const result = syncAddChemicalToProducts([prodExistente, prodQuimico], quimicoActualizado);
      expect(result).toHaveLength(2);
      expect(result[1].descripcion).toBe('Acido Acetico 80%');
      expect(result[1].codigo).toBe('Q-02-B');
    });
  });

  describe('syncUpdateChemicalInProducts', () => {
    it('dado una modificacion de quimico cuando se sincroniza entonces actualiza los campos en productos', () => {
      const productos: Producto[] = [
        { id: 1, codigo: 'H-01', descripcion: 'Hilo', tipo: 'hilo', unidad_medida: 'kg', stock_minimo: 0, precio_base: 0 },
        { id: 2, codigo: 'Q-01', descripcion: 'Soda', tipo: 'quimico', unidad_medida: 'kg', stock_minimo: 5, precio_base: 3 },
      ];
      const result = syncUpdateChemicalInProducts(productos, 2, {
        descripcion: 'Soda Caustica Pura',
        precio_base: 4.5,
      });
      expect(result[0].descripcion).toBe('Hilo');
      expect(result[1].descripcion).toBe('Soda Caustica Pura');
      expect(result[1].precio_base).toBe(4.5);
    });
  });

  describe('syncAddProductToChemicals', () => {
    const quimicoExistente: Quimico = {
      id: 1,
      codigo: 'Q-01',
      descripcion: 'Cloro',
      tipo: 'quimico',
      unidad_medida: 'l',
      precio_base: 2,
    };

    it('dado un producto no quimico cuando se intenta agregar entonces no altera la lista de quimicos', () => {
      const prodTela: Producto = {
        id: 2,
        codigo: 'TEL-01',
        descripcion: 'Jersey Algodon',
        tipo: 'tela',
        unidad_medida: 'metros',
        stock_minimo: 0,
        precio_base: 10,
      };
      const result = syncAddProductToChemicals([quimicoExistente], prodTela);
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe(1);
    });

    it('dado un producto de tipo quimico o insumo cuando se agrega entonces lo incorpora a quimicos', () => {
      const prodQuim: Producto = {
        id: 3,
        codigo: 'Q-03',
        descripcion: 'Peroxido de Hidrogeno',
        tipo: 'quimico',
        unidad_medida: 'kg',
        stock_minimo: 15,
        precio_base: 12,
      };
      const result = syncAddProductToChemicals([quimicoExistente], prodQuim);
      expect(result).toHaveLength(2);
      expect(result[1].codigo).toBe('Q-03');
    });

    it('dado un producto quimico ya existente cuando se agrega entonces actualiza sus datos en quimicos', () => {
      const prodQuim: Producto = {
        id: 1,
        codigo: 'Q-01',
        descripcion: 'Cloro Liquido al 10%',
        tipo: 'quimico',
        unidad_medida: 'l',
        stock_minimo: 50,
        precio_base: 2.5,
      };
      const result = syncAddProductToChemicals([quimicoExistente], prodQuim);
      expect(result).toHaveLength(1);
      expect(result[0].descripcion).toBe('Cloro Liquido al 10%');
    });
  });

  describe('syncUpdateProductInChemicals', () => {
    it('dado producto que cambio de quimico a no quimico cuando se actualiza entonces lo retira de quimicos', () => {
      const quimicos: Quimico[] = [
        { id: 1, codigo: 'Q-01', descripcion: 'Quimico 1', tipo: 'quimico', unidad_medida: 'kg', precio_base: 5 },
      ];
      const prodCambiado: Producto = {
        id: 1,
        codigo: 'HIL-01',
        descripcion: 'Ahora es Hilo',
        tipo: 'hilo',
        unidad_medida: 'kg',
        stock_minimo: 0,
        precio_base: 5,
      };
      const result = syncUpdateProductInChemicals(quimicos, 1, prodCambiado);
      expect(result).toHaveLength(0);
    });

    it('dado producto que cambio de hilo a quimico cuando se actualiza entonces lo agrega a quimicos', () => {
      const quimicos: Quimico[] = [];
      const prodNuevoQuim: Producto = {
        id: 5,
        codigo: 'Q-05',
        descripcion: 'Nuevo Reactivo',
        tipo: 'quimico',
        unidad_medida: 'kg',
        stock_minimo: 0,
        precio_base: 10,
      };
      const result = syncUpdateProductInChemicals(quimicos, 5, prodNuevoQuim);
      expect(result).toHaveLength(1);
      expect(result[0].id).toBe(5);
      expect(result[0].codigo).toBe('Q-05');
    });

    it('dado producto que sigue siendo quimico cuando se actualiza entonces refresca sus datos', () => {
      const quimicos: Quimico[] = [
        { id: 5, codigo: 'Q-05', descripcion: 'Antiguo', tipo: 'quimico', unidad_medida: 'kg', precio_base: 10 },
      ];
      const prodActualizado: Producto = {
        id: 5,
        codigo: 'Q-05',
        descripcion: 'Actualizado',
        tipo: 'quimico',
        unidad_medida: 'kg',
        stock_minimo: 0,
        precio_base: 15,
      };
      const result = syncUpdateProductInChemicals(quimicos, 5, prodActualizado);
      expect(result).toHaveLength(1);
      expect(result[0].descripcion).toBe('Actualizado');
      expect(result[0].precio_base).toBe(15);
    });
  });
});
