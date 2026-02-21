from django.shortcuts import render
from rest_framework.response import Response
from rest_framework import status
import os
from pathlib import Path
import mimetypes
import zipfile
from django.http import HttpResponse, JsonResponse

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

# Create your views here.
# def server_stats(request):
#     """Get server resource statistics"""
    
#     if not PSUTIL_AVAILABLE:
#         return Response({
#             'error': 'psutil not installed. Install with: pip install psutil',
#             'cpu': {'percent': 0, 'count': 0},
#             'memory': {'total': 0, 'available': 0, 'used': 0, 'percent': 0},
#             'disk': {'total': 0, 'used': 0, 'free': 0, 'percent': 0},
#         })
    
#     try:
#         cpu_percent = psutil.cpu_percent(interval=0.1)  # Reduced interval for faster response
#         memory = psutil.virtual_memory()
        
#         # Try to get disk usage, but handle permission errors (common on PythonAnywhere)
#         disk_info = {'total': 0, 'used': 0, 'free': 0, 'percent': 0}
#         try:
#             # On PythonAnywhere, try user directory first
#             import os
#             home_dir = os.path.expanduser('~')
#             disk = psutil.disk_usage(home_dir)
#             disk_info = {
#                 'total': disk.total,
#                 'used': disk.used,
#                 'free': disk.free,
#                 'percent': (disk.used / disk.total) * 100 if disk.total > 0 else 0,
#             }
#         except (PermissionError, OSError):
#             # If we can't access disk, return zeros
#             disk_info = {'total': 0, 'used': 0, 'free': 0, 'percent': 0}
        
#         return Response({
#             'cpu': {
#                 'percent': cpu_percent,
#                 'count': psutil.cpu_count(),
#             },
#             'memory': {
#                 'total': memory.total,
#                 'available': memory.available,
#                 'used': memory.used,
#                 'percent': memory.percent,
#             },
#             'disk': disk_info,
#         })
#     except Exception as e:
#         import traceback
#         print(f"Server stats error: {str(e)}")
#         print(traceback.format_exc())
#         return Response({
#             'error': f'Failed to get server stats: {str(e)}',
#             'cpu': {'percent': 0, 'count': 0},
#             'memory': {'total': 0, 'available': 0, 'used': 0, 'percent': 0},
#             'disk': {'total': 0, 'used': 0, 'free': 0, 'percent': 0},
#         }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def home(request, path=''):
    """Home page with server stats and file browser"""
    
    # Get server stats
    if PSUTIL_AVAILABLE:
        try:
            cpu_percent = psutil.cpu_percent(interval=0.1)
            memory = psutil.virtual_memory()
            home_dir = os.path.expanduser('~')
            disk = psutil.disk_usage(home_dir)
            stats = {
                'cpu': {
                    'percent': cpu_percent,
                    'count': psutil.cpu_count(),
                },
                'memory': {
                    'percent': memory.percent,
                },
                'disk': {
                    'percent': (disk.used / disk.total) * 100 if disk.total > 0 else 0,
                },
            }
        except Exception as e:
            stats = {
                'cpu': {'percent': 0, 'count': 0},
                'memory': {'percent': 0},
                'disk': {'percent': 0},
            }
    else:
        stats = {
            'cpu': {'percent': 0, 'count': 0},
            'memory': {'percent': 0},
            'disk': {'percent': 0},
        }
    
    # Get file list
    base_path = os.path.join(os.path.expanduser('~'), path) if path else os.path.expanduser('~')
    try:
        items = []
        for item in sorted(os.listdir(base_path)):
            item_path = os.path.join(base_path, item)
            is_dir = os.path.isdir(item_path)
            items.append({
                'name': item, 
                'is_dir': is_dir, 
                'path': os.path.join(path, item) if path else item,
                'size': os.path.getsize(item_path) if not is_dir else 0,
            })
    except PermissionError:
        items = []
    
    # Build path parts for breadcrumbs
    path_parts = []
    if path:
        parts = path.rstrip('/').split('/')
        current = ''
        for part in parts:
            if part:  # skip empty
                current += part + '/'
                path_parts.append({'name': part, 'path': current})
    
    context = {
        'stats': stats, 
        'items': items, 
        'current_path': path,
        'path_parts': path_parts,
    }
    return render(request, 'home.html', context)


def download_folder(request, path):
    """Download a folder as zip"""
    folder_path = os.path.join(os.path.expanduser('~'), path)
    if not os.path.isdir(folder_path):
        raise Http404("Folder not found")
    
    # Create zip in memory
    from io import BytesIO
    zip_buffer = BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, folder_path)
                zip_file.write(file_path, arcname)
    
    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.read(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename="{os.path.basename(folder_path)}.zip"'
    return response


def download_file(request, path):
    """Download a single file"""
    file_path = os.path.join(os.path.expanduser('~'), path)
    if not os.path.isfile(file_path):
        raise Http404("File not found")
    
    with open(file_path, 'rb') as f:
        response = HttpResponse(f.read(), content_type='application/octet-stream')
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response


def view_file(request, path):
    """View a file content"""
    file_path = os.path.join(os.path.expanduser('~'), path)
    if not os.path.isfile(file_path):
        raise Http404("File not found")
    
    mime_type, _ = mimetypes.guess_type(file_path)
    if mime_type:
        if mime_type.startswith('image/'):
            with open(file_path, 'rb') as f:
                return HttpResponse(f.read(), content_type=mime_type)
        elif mime_type.startswith('text/'):
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            return HttpResponse(content, content_type=mime_type)
        elif mime_type == 'application/pdf' or mime_type.startswith('video/') or mime_type.startswith('audio/'):
            with open(file_path, 'rb') as f:
                return HttpResponse(f.read(), content_type=mime_type)
        else:
            # For other types, force download
            with open(file_path, 'rb') as f:
                response = HttpResponse(f.read(), content_type='application/octet-stream')
                response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
                return response
    else:
        # Unknown type, force download
        with open(file_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/octet-stream')
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response