import * as React from "react";

const MOBILE_BREAKPOINT = 768;

function suscribirAlAncho(alCambiar: () => void) {
  const mql = window.matchMedia(`(max-width: ${MOBILE_BREAKPOINT - 1}px)`);
  mql.addEventListener("change", alCambiar);
  return () => mql.removeEventListener("change", alCambiar);
}

const esMovil = () => window.innerWidth < MOBILE_BREAKPOINT;

/** `true` bajo el breakpoint móvil; se suscribe al media query del navegador. */
export function useIsMobile() {
  return React.useSyncExternalStore(suscribirAlAncho, esMovil, () => false);
}
