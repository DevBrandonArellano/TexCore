/**
 * Abre un PDF recibido como blob en una pestaña nueva.
 *
 * Se vuelve a construir el Blob con `application/pdf`: envolver `response.data`
 * en `new Blob([...])` sin tipo deja el blob sin MIME y el navegador lo muestra
 * como una página en blanco en lugar de renderizar el PDF.
 */
export function abrirPdfEnPestana(data: Blob): void {
  const url = URL.createObjectURL(new Blob([data], { type: 'application/pdf' }));
  window.open(url, '_blank');
  setTimeout(() => URL.revokeObjectURL(url), 60_000);
}
