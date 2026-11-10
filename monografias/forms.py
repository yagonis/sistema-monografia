import hashlib
from django import forms
from .models import Curso, Monografia, Banca

class CursoForm(forms.ModelForm):
    class Meta:
        model = Curso
        fields = ["nome", "codigo"]

class MonografiaForm(forms.ModelForm):
    class Meta:
        model = Monografia
        fields = ["titulo", "resumo", "curso", "orientador", "arquivo"]
        widgets = {"arquivo": forms.FileInput(),}
    
    def clean(self):
        dados = super().clean()
        arquivo = self.files.get("arquivo")

        if arquivo is not None and "arquivo" in dados:
            digest = hashlib.sha256()
            for bloco in arquivo.chunks():
                digest.update(bloco)
            arquivo.seek(0)
            self.instance.hash_sha256 = digest.hexdigest()
        return dados

class BancaForm(forms.ModelForm):
    class Meta:
        model = Banca
        fields = ["data_hora", "local", "link"]
        widgets = {
            "data_hora": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={"type": "datetime-local"},
            ),
        }
    
    def clean(self):
        dados = super().clean()
        if not dados.get("local") and not dados.get("link"):
            raise forms.ValidationError(
                "É necessário informar o local presencial ou o link de videoconferência."
            )
        return dados