^XA
^PW800
^LL400
^FO50,30^ADN,36,20^FD{{ empresa | default('TexCore Industrial', true) }}^FS
^FO50,80^ADN,18,10^FDProducto: {{ producto_desc }}^FS
^FO50,120^ADN,18,10^FDLote: {{ lote_codigo }}^FS
^FO50,160^ADN,36,20^FDPeso Neto: {{ peso_neto }} {{ unidad | default('kg', true) }}^FS
^FO50,220^BY3
^BCN,100,Y,N,N
^FD{{ lote_codigo }}^FS
^FO550,50^BQN,2,5
^FDQA,{{ qr_data }}^FS
^XZ
