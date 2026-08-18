/**
 * F5: impresión real de etiquetas — Zebra Browser Print (ZPL nativo) con
 * fallback a PDF universal (cualquier impresora) y, en último caso, portapapeles.
 *
 * Zebra Browser Print expone `window.BrowserPrint` cuando la app cliente de
 * Zebra está instalada y corriendo (https://www.zebra.com/browserprint).
 */
import apiClient from './axios';

export type PrintOutcome = 'zebra' | 'pdf' | 'clipboard';

interface BrowserPrintDevice {
    name: string;
    uid: string;
    connection: string;
    send: (data: string, onSuccess?: () => void, onError?: (err: string) => void) => void;
}

interface BrowserPrintApi {
    getDefaultDevice: (
        type: 'printer',
        onSuccess: (device: BrowserPrintDevice) => void,
        onError: (err: string) => void
    ) => void;
}

declare global {
    interface Window {
        BrowserPrint?: BrowserPrintApi;
    }
}

function getDefaultZebraDevice(): Promise<BrowserPrintDevice | null> {
    return new Promise((resolve) => {
        if (!window.BrowserPrint) {
            resolve(null);
            return;
        }
        window.BrowserPrint.getDefaultDevice(
            'printer',
            (device) => resolve(device),
            () => resolve(null)
        );
    });
}

function sendZpl(device: BrowserPrintDevice, zpl: string): Promise<void> {
    return new Promise((resolve, reject) => {
        device.send(zpl, () => resolve(), (err) => reject(new Error(err)));
    });
}

export interface LabelGovernanceContext {
    tipo_evento: 'REIMPRESION' | 'REETIQUETADO';
    version: number;
}

async function abrirPdfParaImprimir(loteId: number, contexto?: LabelGovernanceContext): Promise<void> {
    const res = await apiClient.get(`/lotes-produccion/${loteId}/generate-pdf-label/`, {
        responseType: 'blob',
        params: contexto,
    });
    const blobUrl = URL.createObjectURL(res.data as Blob);
    const ventana = window.open(blobUrl, '_blank');
    if (ventana) {
        ventana.onload = () => {
            try { ventana.print(); } catch { /* el usuario puede imprimir manualmente */ }
        };
    }
    setTimeout(() => URL.revokeObjectURL(blobUrl), 60_000);
}

/**
 * Imprime una etiqueta: respeta la preferencia de impresora guardada en localStorage
 * ('auto' | 'zebra' | 'pdf'). Intenta Zebra Browser Print (ZPL directo);
 * si no hay impresora Zebra disponible o se prefiere PDF, pide el PDF universal al backend
 * y abre el diálogo de impresión del navegador; si todo falla, copia el
 * ZPL al portapapeles como último recurso.
 */
export async function printLabel(
    loteId: number,
    zpl: string,
    contexto?: LabelGovernanceContext,
): Promise<PrintOutcome> {
    let preferredMode = 'auto';
    if (typeof window !== 'undefined' && window.localStorage?.getItem) {
        try {
            preferredMode = window.localStorage.getItem('texcore_preferred_printer') || 'auto';
        } catch {
            preferredMode = 'auto';
        }
    }

    if (preferredMode === 'pdf') {

        try {
            await abrirPdfParaImprimir(loteId, contexto);
            return 'pdf';
        } catch {
            await navigator.clipboard.writeText(zpl);
            return 'clipboard';
        }
    }

    const device = await getDefaultZebraDevice();
    if (device) {
        try {
            await sendZpl(device, zpl);
            return 'zebra';
        } catch {
            // cae al fallback de PDF si el envío a la impresora Zebra falla
        }
    }

    try {
        await abrirPdfParaImprimir(loteId, contexto);
        return 'pdf';
    } catch {
        await navigator.clipboard.writeText(zpl);
        return 'clipboard';
    }
}

