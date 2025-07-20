# Tremor Monitoring: Parkinson's Disease

## Panoramica

Questo progetto nasce per fornire un supporto al personale sanitario per il monitoraggio a distanza delle condizioni di un paziente domiciliarizzato
affetto dal disturbo di Parkinson.

Durante la realizzazione, i punti chiave che hanno poi influenzato la scelta dell'architettura sono stati:
- L'attenzione al paziente: rendere l'applicazione il meno invasiva ed il meno onerosa possibile a livello di interazione umana.
- Creare una struttura facilmente scalabile, sia orizzontalmente che verticalmente, favorendo il disaccoppiamennto più completo tra le varie componenti
- Fornire una struttura sicura, in quanto a che vedere con dati sensibili
- Garantire ad un medico che si interfaccia con l'applicazione di poter modificare le funzioni in base a varie esigenze diagnostiche.

Per poter sviluppare un' architettura del genere, i dati vengono prelevati tramite sensori **IMU** (Inertial MeasurementSensors) e attraverso il **BLE** (Bluetooth Low Energy), trasmessi ad un *raspberry Pi 5*, il quale si occupa della conversione e preparazione dei dati per l'algoritmo di Machine Learning. Questi dati sono poi passati ad una piattaforma cloud (**AWS**), dove risiedono oltre all'algoritmo di intelligenza artificiale, anche i microservizi per la gestione utenti e l'interfaccia frontend

Per la persistenza dei dati forniti dai sensori, e i risultati dell'inferenza, si è scelto di sfruttare il servizio cloud **S3** (Simple storage service), per disaccoppiare l'accesso dei dati, dall'inferenza in sé.


## Architettura generale

L'architettura si basa sull'utilizzo di microservizi, indipendenti, modulari e scalabili. Questi risiedono sull'infrastruttura cloud e l'accesso è fornito dai routing di **API GATEWAY**, il quale sfrutta anche il paradigma serverless (**Lambda functions**) per determinate operazioni.
Il tutto è stato poi containerizzato tramite Docker.

<div align="center">
  <img src="img/FullProject.png" alt="Descrizione" width="400"/>
</div>


### Backend
- **UserService**: responsabile per la  gestione utenti. Fornisce operazioni CRUD sulle due entità principali della soluzione, cioè *Doctor* e *Patient*. Inoltre gestisce  registrazione, autenticazione e autorizzazione per gli utenti per cui è predisposto il servizio (*Doctor*).
- **SmartWatchService**: servizio installato localmente sul dispositivo, il quale tramite BLE si occupa di comunicare col raspberry Pi, responsabile dell'invio dei dati sul cloud
- **BLEserver**: servizio installato localmente sul raspberry, si occupa di fornire un server per la ricezione dei dati sensoriali, la conversione in un formato dati valido e l'invio di questi sul database remoto (*S3*)
- **TremorAnalysis**: Si occupa dell'esecuzione dell'algoritmo di intelligenza artificiale, basato sulla libreria di ParaDigMa. Fornisce dei rest controller per poter avviare l'inferenza su richiesta, e si interfaccia col gateway per gestire autonomamente il recupero/invio dei dati sul database remoto

### Frontend

L'interfaccia web, esposta da un microservizio sul cloud, e sviluppata con React + Vite, permette l'accesso ai medici autorizzati nel sistema. Questi possono visualizzare le informazioni sui pazienti e gestirli nel database, nonchè visualizzare in una pagina dedicata, le statistiche sul tremore rilevato nel tempo per un determinato paziente.

## Repositories dei componenti
- UserService: [UserService](https://github.com/UniSalento-IDALab-IoTCourse-2024-2025/wot-project-UserService-PiccinnoFesta)
- TremorAnalisys: [Tremor Analisys](https://github.com/UniSalento-IDALab-IoTCourse-2024-2025/wot-project-TremorAnalysis-PiccinnoFesta)
- SmartWatchService: [Smartwatch](https://github.com/UniSalento-IDALab-IoTCourse-2024-2025/wot-project-smartwatch-PiccinnoFesta)
- BLE server: [BLE Server](https://github.com/UniSalento-IDALab-IoTCourse-2024-2025/wot-project-BLEserver-PiccinnoFesta)
- Frontend: [Frontend](https://github.com/UniSalento-IDALab-IoTCourse-2024-2025/wot-project-Frontend-PiccinnoFesta)
- Presentation: [Presentation](https://github.com/UniSalento-IDALab-IoTCourse-2024-2025/wot-project-presentation-PiccinnoFesta)

## BLE GATT SERVER (BlueZ Python Server)

Questo progetto realizza un server BLE completo in Python su Linux, basato su BlueZ e D-Bus. Il server riceve dati JSON da un dispositivo remoto (uno smartwatch Android), li bufferizza, li decodifica e li salva in file JSON batchizzati da 400 campioni ciascuno. In seguito li converte in un formato dati adatto all'analisi del modello di machine learning e li carica sul database remoto (*S3*).

### Funzionamento

Il server pubblicizza la propria presenza (**Advertising**) come periferica BLE usando un `Service UUID` personalizzato ed espone una **caratteristica scrivibile** con `UUID` specifico.
I dati inviati da un client BLE vengono interpretati come stringhe JSON codificate in UTF-8.
I pacchetti ricevuti vengono bufferizzati e una volta raggiunti i **400 campioni** viene creato un file JSON `segment<batch_id>_raw.json`, salvato poi in una directory locale.


Oltre all'esposizione del servizio, ci sono due altri script concorrenti che operano periodicamente per controllare la presenza di file da convertire/inviare e procedere con l'operazione.
Questi sono:

#### 1) `transform_to_tsdf.py`

Trasforma i dati JSON ricevuti  in un formato binario strutturato (TSDF):

a. **Estrae i dati** da ciascun file, ignorando quelli malformati o incompleti.
b. **Crea una tabella temporale** dei campioni, convertendo i timestamp assoluti in delta temporali in millisecondi rispetto al primo campione.
c. **Applica un fattore di scala** ai valori di accelerazione e giroscopio per convertirli in unità fisiche reali.
d. **Genera tre file binari** per ogni batch:
   - `IMU_time.bin`: tempi relativi
   - `IMU_values.bin`: dati accelerometro + giroscopio
   - `IMU_meta.json`: metadati (soggetto, dispositivo, intervallo temporale, ecc.)
e. **Svuota la cartella d'origine** cancellando i file processati.




  #### 2) `send_tsdf.py`

**Invia automaticamente i dati dei file  binari** generati dallo script precedente verso un database remoto

La logica è la seguente:

1. **Scansiona** alla ricerca di nuove directory contenenti file binari.
2. **Comprime ciascun segmento** in un file ZIP (`segmentX.zip`).
3. **Contatta API GATEWAY** passando l’ID del paziente (letto da un file di configurazione) per richiedere un **presigned URL**, ovvero un link temporaneo autorizzato per l’upload.
4. **Effettua l’upload del file ZIP** direttamente su Amazon S3 usando il presigned URL ricevuto.
5. Se l’upload ha successo:
   - **Sposta il file ZIP nella cartella `sent/`** come archivio.
   - **Cancella la cartella `segmentX/` originale**.
6. In caso di errore (es. URL non valido, connessione assente, o fallimento S3):
   - Attende 30 secondi e riprova automaticamente.

Il file di configurazione `patient_config.json` infine tiene l'informazione sull'identificativo del paziente, per poter caricare i dati sul cloud in directory separate

