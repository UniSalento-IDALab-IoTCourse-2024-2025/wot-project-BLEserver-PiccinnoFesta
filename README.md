# Server raspberry che funge da gateway

la pipeline si compone di 3 script:

1) ble-gatt-server / server.js : 
    implementa il server, nel primo caso tramite ble, nel secondo tramite http.
    riceve i dati dallo smartwatch e forma il file segment{batch_id}_raw.json all'interno di una cartella
    (nel caso del ble, aspetta l'arrivo di 400 snapshot prima di creare il file, mentre http riceve già il
    blocco completo di 400 snapshot)

2) transform_to_tsdf.py:
    prende i file all'interno di toSendData/buffer e li trasforma nel formato (tsdf) richiesto per l'inferenza
    sposta i risultati in toSendData/tsdf_output
3) send_tsdf.py
    prende i file da toSendData/tsdf_output e li invia tramite post al server, (per ora locale).
    sposta i file già inviati in toSendData/sent
    