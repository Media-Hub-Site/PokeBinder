import urllib.request
import struct
import io

url = "https://github.com/Alan-Dave/TCG-Inventory/releases/download/assets/images.zip"

try:
    print("Obteniendo información del ZIP...")
    req = urllib.request.Request(url, method='HEAD')
    with urllib.request.urlopen(req) as resp:
        content_length = int(resp.headers.get('Content-Length', 0))
    
    print(f"Tamaño total del ZIP: {content_length} bytes")
    
    # Leer los últimos 65536 bytes del archivo (donde suele estar el Directorio Central del ZIP)
    range_start = max(0, content_length - 65536)
    req = urllib.request.Request(url, headers={'Range': f'bytes={range_start}-{content_length-1}'})
    
    with urllib.request.urlopen(req) as resp:
        zip_data = resp.read()
    
    # Buscar la firma del End of Central Directory (EOCD): 0x06054b50
    eocd_index = zip_data.rfind(b'\x50\x4b\x05\x06')
    if eocd_index == -1:
        print("No se encontró la firma EOCD al final del archivo. Intentando leer los archivos iniciales desde el principio...")
        # Si falla, leemos los primeros 5000 bytes para ver el primer Local File Header
        req = urllib.request.Request(url, headers={'Range': 'bytes=0-5000'})
        with urllib.request.urlopen(req) as resp:
            start_data = resp.read()
        
        idx = 0
        while True:
            lf_header = start_data.find(b'\x50\x4b\x03\x04', idx)
            if lf_header == -1:
                break
            # Nombre de archivo está en offset lf_header + 30
            fn_len = struct.unpack('<H', start_data[lf_header+26:lf_header+28])[0]
            fn = start_data[lf_header+30:lf_header+30+fn_len].decode('utf-8', errors='ignore')
            print(f"Archivo encontrado en ZIP: {fn}")
            idx = lf_header + 30 + fn_len
    else:
        # Encontramos EOCD
        eocd = zip_data[eocd_index:]
        num_records = struct.unpack('<H', eocd[10:12])[0]
        cd_size = struct.unpack('<I', eocd[12:16])[0]
        cd_offset = struct.unpack('<I', eocd[16:20])[0]
        
        print(f"Número de archivos: {num_records}")
        
        # Descargar el Directorio Central usando su offset y tamaño
        req = urllib.request.Request(url, headers={'Range': f'bytes={cd_offset}-{cd_offset+cd_size-1}'})
        with urllib.request.urlopen(req) as resp:
            cd_data = resp.read()
            
        # Imprimir los primeros 10 archivos del directorio central
        idx = 0
        for i in range(min(15, num_records)):
            cf_header = cd_data.find(b'\x50\x4b\x01\x02', idx)
            if cf_header == -1:
                break
            fn_len = struct.unpack('<H', cd_data[cf_header+28:cf_header+30])[0]
            fn = cd_data[cf_header+46:cf_header+46+fn_len].decode('utf-8', errors='ignore')
            print(f"Archivo en ZIP: {fn}")
            idx = cf_header + 46 + fn_len

except Exception as e:
    print(f"Error al analizar el ZIP: {e}")
