import os
import time
import asyncio
from pyrogram import Client
from pyrogram.errors import FloodWait
import humanize
import signal
from rich.console import Console
from rich.progress import Progress, TextColumn, BarColumn, TransferSpeedColumn, TimeRemainingColumn
import mimetypes

# Configuración
API_ID = '26031104'
API_HASH = '5d1b64e2be5de7ff6df8624525169ef5'
PHONE_NUMBER = '+59174762587'
SESSION_NAME = 'mi_sesion'
CHANNEL_ID = -1002336806320
CHANNEL_USERNAME = 'childhubk'  # Reemplaza con el nombre de usuario real del canal

# Variables globales
total_files = 0
total_size = 0
start_time = 0
is_uploading = False
console = Console()
retry_intervals = [10, 20, 600, 14400]  # 10s, 20s, 10min, 4h en segundos
current_retry_index = 0

def signal_handler(sig, frame):
    global is_uploading
    console.print("\n[bold red]Detectada señal de interrupción. Finalizando el proceso de subida...[/bold red]")
    is_uploading = False

signal.signal(signal.SIGINT, signal_handler)

VIDEO_EXTENSIONS = [
    '.mp4', '.avi', '.mov', '.mkv', '.flv', '.wmv', '.webm', '.m4v', '.mpg', '.mpeg', '.3gp', '.3gpp',
    '.ts', '.mts', '.m2ts', '.vob', '.ogv', '.mxf', '.asf', '.rm', '.rmvb', '.m2v', '.mp2', '.mpeg1',
    '.mpeg2', '.mpeg4', '.gif', '.gifv', '.mng', '.qt', '.yuv', '.rm', '.rmvb', '.viv', '.asf', '.amv',
    '.m4p', '.mpv', '.m4v', '.svi', '.3g2', '.mxf', '.roq', '.nsv', '.f4v', '.f4p', '.f4a', '.f4b'
]

IMAGE_EXTENSIONS = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp']

def get_new_filename(index, original_filename):
    _, ext = os.path.splitext(original_filename)
    if ext.lower() in VIDEO_EXTENSIONS:
        prefix = 'VID'
    elif ext.lower() in IMAGE_EXTENSIONS:
        prefix = 'IMG'
    else:
        prefix = 'DOC'
    return f"({prefix}-{index})_Telegram-@{CHANNEL_USERNAME}{ext}"

async def upload_file(app, file_path, new_file_name, total_files_count, progress, task_id):
    global total_files, total_size, is_uploading, current_retry_index
    
    if not is_uploading:
        return

    file_size = os.path.getsize(file_path)
    _, ext = os.path.splitext(new_file_name)
    
    while is_uploading:
        try:
            async def progress_callback(current, total):
                if is_uploading:
                    progress.update(task_id, completed=current, total=total)

            if ext.lower() in VIDEO_EXTENSIONS:
                await app.send_video(chat_id=CHANNEL_ID, video=file_path, file_name=new_file_name, progress=progress_callback)
            elif ext.lower() in IMAGE_EXTENSIONS:
                await app.send_photo(chat_id=CHANNEL_ID, photo=file_path, caption=new_file_name, progress=progress_callback)
            else:
                await app.send_document(chat_id=CHANNEL_ID, document=file_path, file_name=new_file_name, progress=progress_callback)
            
            total_files += 1
            total_size += file_size
            current_retry_index = 0  # Reiniciar el índice de reintento al tener éxito
            return  # Salir de la función si la subida fue exitosa
        except FloodWait as e:
            console.print(f"[yellow]Límite de velocidad alcanzado. Esperando {e.x} segundos.[/yellow]")
            await asyncio.sleep(e.x)
        except (asyncio.TimeoutError, ConnectionError) as e:
            if current_retry_index >= len(retry_intervals):
                console.print("[bold red]Se han agotado todos los reintentos. Deteniendo el script...[/bold red]")
                is_uploading = False
                return

            retry_time = retry_intervals[current_retry_index]
            console.print(f"[yellow]Error de conexión. Reintentando en {retry_time} segundos...[/yellow]")
            await asyncio.sleep(retry_time)
            current_retry_index += 1
        except asyncio.CancelledError:
            console.print(f"[red]Subida de {new_file_name} cancelada.[/red]")
            return
        except Exception as e:
            console.print(f"[bold red]Error al subir {new_file_name}: {str(e)}[/bold red]")
            return

async def main():
    global total_files, total_size, start_time, is_uploading, current_retry_index
    
    async with Client(SESSION_NAME, api_id=API_ID, api_hash=API_HASH, phone_number=PHONE_NUMBER) as app:
        console.print("[green]Sesión iniciada correctamente.[/green]")
        
        # Verificar el ID del canal
        try:
            chat = await app.get_chat(CHANNEL_ID)
            console.print(f"[green]Canal verificado: {chat.title}[/green]")
            console.print(f"[green]ID del canal: {chat.id}[/green]")
            console.print(f"[green]Tipo de chat: {chat.type}[/green]")
        except Exception as e:
            console.print(f"[bold red]Error al verificar el canal: {str(e)}[/bold red]")
            return
        
        folder_path = console.input("[cyan]Ingresa la ruta de la carpeta que contiene los archivos a subir: [/cyan]")
        
        if not os.path.exists(folder_path):
            console.print("[bold red]La carpeta especificada no existe.[/bold red]")
            return
        
        files = [f for f in os.listdir(folder_path) if os.path.isfile(os.path.join(folder_path, f)) and not f.endswith('.part')]
        total_files_count = len(files)
        total_size = sum(os.path.getsize(os.path.join(folder_path, f)) for f in files)
        
        console.print(f"[green]Se encontraron {total_files_count} archivos válidos con un tamaño total de {humanize.naturalsize(total_size)}[/green]")
        
        start_time = time.time()
        is_uploading = True
        
        progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            "[progress.percentage]{task.percentage:>3.0f}%",
            "•",
            TransferSpeedColumn(),
            "•",
            TimeRemainingColumn(),
        )
        
        with progress:
            for index, file in enumerate(files, 1):
                if not is_uploading:
                    break
                file_path = os.path.join(folder_path, file)
                new_file_name = get_new_filename(index, file)
                file_size = os.path.getsize(file_path)
                file_description = f"[cyan]Subiendo[/cyan] [green]{index}/{total_files_count}[/green] [yellow]{new_file_name}[/yellow]"
                console.print(file_description)
                task_id = progress.add_task("", total=file_size)
                current_retry_index = 0  # Reiniciar el índice de reintento para cada nuevo archivo
                await upload_file(app, file_path, new_file_name, total_files_count, progress, task_id)
                progress.remove_task(task_id)
                console.print()  # Añade una línea en blanco después de cada archivo
        
        end_time = time.time()
        total_time = end_time - start_time
        
        console.print("\n[bold green]Resumen de la subida:[/bold green]")
        console.print(f"[green]Archivos subidos: {total_files}/{total_files_count}[/green]")
        console.print(f"[green]Tamaño total: {humanize.naturalsize(total_size)}[/green]")
        console.print(f"[green]Tiempo total: {humanize.naturaldelta(total_time)}[/green]")
        if total_time > 0:
            console.print(f"[green]Velocidad promedio: {humanize.naturalsize(total_size / total_time)}/s[/green]")

if __name__ == '__main__':
    asyncio.run(main())