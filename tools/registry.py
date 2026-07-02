"""
Registry semua tools Ferxvis - termasuk Telegram.
"""

from tools import file_tools
from tools import office_tools
from tools import web_tools
from tools import email_tools
from tools import whatsapp_tools
from tools import telegram_tools

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "change_directory",
            "description": (
                "Pindah 'folder kerja saat ini' ke subfolder tertentu di dalam workspace "
                "(home folder laptop user). Setelah dipanggil, semua tool file lain yang "
                "memakai relative_path BIASA (tanpa diawali '/') akan bekerja relatif "
                "terhadap folder baru ini — mirip perintah 'cd' di terminal. "
                "Gunakan relative_path='' untuk kembali ke folder utama workspace. "
                "TETAP TIDAK BISA keluar dari home folder user; ini hanya berpindah "
                "SUBFOLDER di dalamnya, bukan drive atau folder lain di laptop."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Subfolder tujuan, relatif terhadap current directory saat ini. Kosongkan untuk kembali ke folder utama workspace."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "Lihat daftar file dan folder di dalam suatu folder workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Path folder relatif terhadap workspace. Kosongkan untuk folder utama."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_folder",
            "description": "Buat folder baru di dalam workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Path folder yang ingin dibuat."}
                },
                "required": ["relative_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_note",
            "description": "Buat file catatan teks baru, atau timpa isi file yang sudah ada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string", "description": "Path file."},
                    "content": {"type": "string", "description": "Isi teks yang akan ditulis."}
                },
                "required": ["relative_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "append_note",
            "description": "Tambahkan teks ke akhir file catatan yang sudah ada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["relative_path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Baca isi sebuah file teks di workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"}
                },
                "required": ["relative_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "move_file",
            "description": "Pindahkan atau ganti nama file/folder ke lokasi lain di dalam workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_relative_path": {"type": "string"},
                    "destination_relative_path": {"type": "string"}
                },
                "required": ["source_relative_path", "destination_relative_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "delete_file",
            "description": "Hapus file atau folder di workspace. Tidak bisa dibatalkan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"}
                },
                "required": ["relative_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_word_document",
            "description": "Buat dokumen Microsoft Word (.docx) baru.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"},
                    "title": {"type": "string"},
                    "paragraphs": {"type": "array", "items": {"type": "string"}}
                },
                "required": ["relative_path", "title", "paragraphs"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_word_document",
            "description": "Baca seluruh isi teks dari dokumen Word (.docx).",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"}
                },
                "required": ["relative_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_excel_sheet",
            "description": "Buat file Excel (.xlsx) baru dengan judul kolom dan baris data.",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"},
                    "headers": {"type": "array", "items": {"type": "string"}},
                    "rows": {"type": "array", "items": {"type": "array"}}
                },
                "required": ["relative_path", "headers", "rows"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_excel_sheet",
            "description": "Baca isi sheet pertama dari file Excel (.xlsx).",
            "parameters": {
                "type": "object",
                "properties": {
                    "relative_path": {"type": "string"}
                },
                "required": ["relative_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Cari informasi terkini di internet.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_inbox",
            "description": "Baca email terbaru dari inbox Gmail Ferdinand.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer"}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_email",
            "description": "Cari email di Gmail berdasarkan kriteria.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "max_results": {"type": "integer"}
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_whatsapp_message",
            "description": "Kirim pesan WhatsApp ke nomor tujuan. Selalu minta konfirmasi dulu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string", "description": "Nomor tujuan format internasional tanpa +, contoh 6281234567890"},
                    "message": {"type": "string", "description": "Isi pesan yang akan dikirim"}
                },
                "required": ["to", "message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_email",
            "description": "Kirim email lewat Gmail Ferdinand. Selalu minta konfirmasi dulu.",
            "parameters": {
                "type": "object",
                "properties": {
                    "to": {"type": "string"},
                    "subject": {"type": "string"},
                    "body": {"type": "string"}
                },
                "required": ["to", "subject", "body"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "send_telegram_to_me",
            "description": "Kirim pesan Telegram ke Ferdinand. Gunakan untuk notifikasi atau reminder.",
            "parameters": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Isi pesan yang ingin dikirim ke Ferdinand via Telegram."}
                },
                "required": ["message"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_telegram_messages",
            "description": "Ambil pesan terbaru yang masuk ke bot Telegram Ferdinand.",
            "parameters": {
                "type": "object",
                "properties": {
                    "max_results": {"type": "integer", "description": "Jumlah pesan (default 5)."}
                },
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_bot_info",
            "description": "Cek info dan link bot Telegram Ferdinand.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
]

TOOL_FUNCTIONS = {
    "change_directory": file_tools.change_directory,
    "list_files": file_tools.list_files,
    "create_folder": file_tools.create_folder,
    "write_note": file_tools.write_note,
    "append_note": file_tools.append_note,
    "read_file": file_tools.read_file,
    "move_file": file_tools.move_file,
    "delete_file": file_tools.delete_file,
    "create_word_document": office_tools.create_word_document,
    "read_word_document": office_tools.read_word_document,
    "create_excel_sheet": office_tools.create_excel_sheet,
    "read_excel_sheet": office_tools.read_excel_sheet,
    "search_web": web_tools.search_web,
    "read_inbox": email_tools.read_inbox,
    "search_email": email_tools.search_email,
    "send_email": email_tools.send_email,
    "send_whatsapp_message": whatsapp_tools.send_whatsapp_message,
    "send_telegram_to_me": telegram_tools.send_telegram_to_me,
    "get_telegram_messages": telegram_tools.get_telegram_messages,
    "get_bot_info": telegram_tools.get_bot_info,
}


def execute_tool(name: str, arguments: dict) -> str:
    func = TOOL_FUNCTIONS.get(name)
    if func is None:
        return f"ERROR: tool '{name}' tidak dikenali."
    try:
        return func(**arguments)
    except TypeError as e:
        return f"ERROR: argumen tidak sesuai untuk tool '{name}': {e}"
    except Exception as e:
        return f"ERROR saat menjalankan tool '{name}': {e}"
