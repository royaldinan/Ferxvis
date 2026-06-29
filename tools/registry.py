"""
Registry semua tools Ferxvis - schema kompatibel Groq/Llama.
"""

from tools import file_tools, office_tools, web_tools, email_tools, whatsapp_tools

TOOL_DEFINITIONS = [
    {"type": "function", "function": {"name": "list_files", "description": "Lihat isi folder. Path bisa absolute atau relatif ke home.", "parameters": {"type": "object", "properties": {"relative_path": {"type": "string", "description": "Path folder, kosong untuk home directory."}}}}},
    {"type": "function", "function": {"name": "create_folder", "description": "Buat folder baru.", "parameters": {"type": "object", "properties": {"relative_path": {"type": "string"}}, "required": ["relative_path"]}}},
    {"type": "function", "function": {"name": "write_note", "description": "Buat atau timpa file teks.", "parameters": {"type": "object", "properties": {"relative_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["relative_path", "content"]}}},
    {"type": "function", "function": {"name": "append_note", "description": "Tambah teks ke file.", "parameters": {"type": "object", "properties": {"relative_path": {"type": "string"}, "content": {"type": "string"}}, "required": ["relative_path", "content"]}}},
    {"type": "function", "function": {"name": "read_file", "description": "Baca isi file teks.", "parameters": {"type": "object", "properties": {"relative_path": {"type": "string"}}, "required": ["relative_path"]}}},
    {"type": "function", "function": {"name": "move_file", "description": "Pindahkan file/folder.", "parameters": {"type": "object", "properties": {"source_relative_path": {"type": "string"}, "destination_relative_path": {"type": "string"}}, "required": ["source_relative_path", "destination_relative_path"]}}},
    {"type": "function", "function": {"name": "copy_file", "description": "Copy file atau folder.", "parameters": {"type": "object", "properties": {"source_relative_path": {"type": "string"}, "destination_relative_path": {"type": "string"}}, "required": ["source_relative_path", "destination_relative_path"]}}},
    {"type": "function", "function": {"name": "delete_file", "description": "Hapus file atau folder.", "parameters": {"type": "object", "properties": {"relative_path": {"type": "string"}}, "required": ["relative_path"]}}},
    {"type": "function", "function": {"name": "rename_file", "description": "Ganti nama file atau folder.", "parameters": {"type": "object", "properties": {"relative_path": {"type": "string"}, "new_name": {"type": "string"}}, "required": ["relative_path", "new_name"]}}},
    {"type": "function", "function": {"name": "search_files", "description": "Cari file berdasarkan nama.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "search_path": {"type": "string"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "create_word_document", "description": "Buat dokumen Word (.docx).", "parameters": {"type": "object", "properties": {"relative_path": {"type": "string"}, "title": {"type": "string"}, "paragraphs": {"type": "array", "items": {"type": "string"}}}, "required": ["relative_path", "title", "paragraphs"]}}},
    {"type": "function", "function": {"name": "read_word_document", "description": "Baca isi dokumen Word.", "parameters": {"type": "object", "properties": {"relative_path": {"type": "string"}}, "required": ["relative_path"]}}},
    {"type": "function", "function": {"name": "create_excel_sheet", "description": "Buat file Excel (.xlsx). headers adalah list nama kolom, rows adalah list of string (setiap baris dipisah koma).", "parameters": {"type": "object", "properties": {"relative_path": {"type": "string"}, "headers": {"type": "array", "items": {"type": "string"}}, "rows": {"type": "array", "items": {"type": "string"}}}, "required": ["relative_path", "headers", "rows"]}}},
    {"type": "function", "function": {"name": "read_excel_sheet", "description": "Baca isi file Excel.", "parameters": {"type": "object", "properties": {"relative_path": {"type": "string"}}, "required": ["relative_path"]}}},
    {"type": "function", "function": {"name": "search_web", "description": "Cari informasi terkini di internet.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "read_inbox", "description": "Baca email terbaru dari Gmail (ferdinandmanurungcr7@gmail.com).", "parameters": {"type": "object", "properties": {"max_results": {"type": "integer"}}}}},
    {"type": "function", "function": {"name": "search_email", "description": "Cari email di Gmail (ferdinandmanurungcr7@gmail.com).", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "max_results": {"type": "integer"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "send_email", "description": "Kirim email dari Gmail (ferdinandmanurungcr7@gmail.com).", "parameters": {"type": "object", "properties": {"to": {"type": "string"}, "subject": {"type": "string"}, "body": {"type": "string"}}, "required": ["to", "subject", "body"]}}},
    {"type": "function", "function": {"name": "send_whatsapp_message", "description": "Kirim pesan WhatsApp dari nomor pribadi user lewat WhatsApp Web. Browser dibuka sekali dan dipakai ulang (tidak membuka tab baru tiap kali). Hasil sudah diverifikasi nyata, bukan asumsi - kalau hasilnya bilang TIDAK BISA DIPASTIKAN atau GAGAL, anggap pesan BELUM terkirim dan jangan klaim sudah terkirim ke user.", "parameters": {"type": "object", "properties": {"to": {"type": "string"}, "message": {"type": "string"}}, "required": ["to", "message"]}}},
    {"type": "function", "function": {"name": "close_whatsapp_session", "description": "Tutup browser WhatsApp Web yang sedang aktif, kalau ada masalah dan perlu mulai sesi baru dari awal.", "parameters": {"type": "object", "properties": {}}}},
]


def _parse_excel_rows(rows: list) -> list:
    result = []
    for row in rows:
        if isinstance(row, list):
            result.append(row)
        elif isinstance(row, str):
            result.append([v.strip() for v in row.split(",")])
        else:
            result.append([str(row)])
    return result


TOOL_FUNCTIONS = {
    "list_files": file_tools.list_files,
    "create_folder": file_tools.create_folder,
    "write_note": file_tools.write_note,
    "append_note": file_tools.append_note,
    "read_file": file_tools.read_file,
    "move_file": file_tools.move_file,
    "copy_file": file_tools.copy_file,
    "delete_file": file_tools.delete_file,
    "rename_file": file_tools.rename_file,
    "search_files": file_tools.search_files,
    "create_word_document": office_tools.create_word_document,
    "read_word_document": office_tools.read_word_document,
    "read_excel_sheet": office_tools.read_excel_sheet,
    "search_web": web_tools.search_web,
    "read_inbox": email_tools.read_inbox,
    "search_email": email_tools.search_email,
    "send_email": email_tools.send_email,
    "send_whatsapp_message": whatsapp_tools.send_whatsapp_message,
    "close_whatsapp_session": whatsapp_tools.close_whatsapp_session,
}


def execute_tool(name: str, arguments: dict) -> str:
    if name == "create_excel_sheet":
        rows = arguments.get("rows", [])
        arguments["rows"] = _parse_excel_rows(rows)
        return office_tools.create_excel_sheet(**arguments)

    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"ERROR: tool '{name}' tidak dikenali."
    try:
        return func(**arguments)
    except TypeError as e:
        return f"ERROR: argumen tidak sesuai untuk '{name}': {e}"
    except Exception as e:
        return f"ERROR saat menjalankan '{name}': {e}"
