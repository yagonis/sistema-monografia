from pathlib import Path

from django.core.exceptions import ValidationError
from pypdf import PdfReader
from pypdf.errors import PdfReadError

def validar_pdf(arquivo):
    if arquivo.size > 50 * 1024 * 1024: 
        raise ValidationError("O arquivo PDF não pode ter mais de 50MB.")

    if Path(arquivo.name).suffix.lower() != ".pdf":
        raise ValidationError("O arquivo deve ter a extensão .pdf.")
    
    try:
        arquivo.seek(0)
        if arquivo.read(5) != b"%PDF-":
            raise ValidationError("O arquivo não é um PDF válido.")
        
        arquivo.seek(0)
        leitor = PdfReader(arquivo)
        if leitor.is_encrypted:
            raise ValidationError("O arquivo PDF não pode estar protegido por senha.")
        if len(leitor.pages) == 0:
            raise ValidationError("O pdf não pode estar vazio.")
    except (PdfReadError, ValueError, OSError):
        raise ValidationError("O arquivo não é um PDF válido.")
    finally:
        arquivo.seek(0)
