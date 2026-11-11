import hashlib
from django import forms
from .models import Curso, Monografia

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
        if self.instance.pk:
            # Consulte o estado persistido, mesmo se o formulário recebeu um objeto antigo.
            atual = Monografia.objects.only('status').filter(pk=self.instance.pk).first()
            if atual is not None and not atual.pode_editar:
                raise forms.ValidationError('Somente monografias em rascunho podem ser editadas.')
        arquivo = self.files.get("arquivo")

        if arquivo is not None and "arquivo" in dados:
            digest = hashlib.sha256()
            for bloco in arquivo.chunks():
                digest.update(bloco)
            arquivo.seek(0)
            self.instance.hash_sha256 = digest.hexdigest()
        return dados
