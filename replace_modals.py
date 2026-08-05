import re

with open('frontend/src/components/ejecutivos/EjecutivosDashboard.tsx', 'r') as f:
    content = f.read()

# Replace the stock modal
stock_modal_regex = re.compile(r'<Dialog open=\{bodegaSeleccionada !== null\}.*?</Dialog>', re.DOTALL)
content = stock_modal_regex.sub(r'''<StockBodegaModal 
              bodegaSeleccionada={bodegaSeleccionada}
              onClose={() => setBodegaSeleccionada(null)}
              stock={stock}
            />''', content)

# Replace the ventas modals
ventas_modals_regex = re.compile(r'\{\/\* Modales de Interacción de Ventas \*\/}.*?</TabsContent>', re.DOTALL)
content = ventas_modals_regex.sub(r'''{/* Modales de Interacción de Ventas (Separados para cumplir SRP / ISO 25010) */}
          <PedidosEstadoModal
            estado={modalEstadoPedido}
            onClose={() => setModalEstadoPedido(null)}
            pedidos={pedidos}
          />
          <VentasVendedorModal
            vendedor={modalVendedor}
            onClose={() => setModalVendedor(null)}
            pedidos={pedidos}
          />
          <ClienteComprasModal
            cliente={modalClienteCompras}
            onClose={() => setModalClienteCompras(null)}
            pedidos={pedidos}
          />
          <ClienteDeudorModal
            clienteNombre={modalClienteDeudor}
            onClose={() => setModalClienteDeudor(null)}
            topDeudores={topDeudores as any}
          />
        </TabsContent>''', content)

# Add imports
import_statement = """import apiClient from '../../lib/axios';
import {
  StockBodegaModal,
  PedidosEstadoModal,
  VentasVendedorModal,
  ClienteComprasModal,
  ClienteDeudorModal,
} from './DrillDownModals';"""
content = content.replace("import apiClient from '../../lib/axios';", import_statement)

with open('frontend/src/components/ejecutivos/EjecutivosDashboard.tsx', 'w') as f:
    f.write(content)
print("Replaced!")
