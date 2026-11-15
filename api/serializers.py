from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers
from monografias.models import Curso, Monografia, Banca, MembroBanca, Avaliacao, Documento
from usuarios.models import PerfilAluno, PerfilProfessor


class CursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Curso
        fields = ['id', 'nome', 'codigo', 'coordenador']


class PublicaSerializer(serializers.ModelSerializer):
    autor_nome = serializers.CharField(source='autor.get_full_name', read_only=True)
    orientador_nome = serializers.CharField(source='orientador.get_full_name', read_only=True)
    class Meta:
        model = Monografia
        fields = ['id', 'titulo', 'resumo', 'palavras_chave', 'autor_nome', 'orientador_nome', 'curso', 'publicada_em']


class MonografiaSerializer(serializers.ModelSerializer):
    arquivo = serializers.FileField(write_only=True, required=False)
    class Meta:
        model = Monografia
        fields = ['id', 'titulo', 'resumo', 'palavras_chave', 'autor', 'orientador', 'curso', 'arquivo',
                  'status', 'hash_sha256', 'versao', 'submetida_em', 'aprovado_em', 'publicada_em']
        read_only_fields = ['autor', 'status', 'hash_sha256', 'versao', 'submetida_em', 'aprovado_em', 'publicada_em']


class BancaSerializer(serializers.ModelSerializer):
    monografia_titulo = serializers.CharField(source='monografia.titulo', read_only=True)
    class Meta:
        model = Banca
        fields = ['id', 'monografia', 'monografia_titulo', 'data_hora', 'fim', 'local', 'link', 'status', 'nota_final', 'encerrada_em']
        read_only_fields = ['status', 'nota_final', 'encerrada_em']


class MembroSerializer(serializers.ModelSerializer):
    class Meta:
        model = MembroBanca
        fields = ['id', 'banca', 'usuario', 'nome', 'email', 'confirmado', 'expira_em', 'revogado']
        read_only_fields = ['confirmado', 'expira_em', 'revogado']


class AvaliacaoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Avaliacao
        fields = ['id', 'membro', 'nota', 'parecer', 'recomendacao', 'atualizada_em']
        read_only_fields = ['atualizada_em']


class DocumentoSerializer(serializers.ModelSerializer):
    arquivo = serializers.FileField(write_only=True)
    class Meta:
        model = Documento
        fields = ['id', 'monografia', 'tipo', 'arquivo', 'hash_sha256', 'validado_em', 'validado_por']
        read_only_fields = ['hash_sha256', 'validado_em', 'validado_por']


class UsuarioSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    class Meta:
        model = get_user_model()
        fields = ['id', 'username', 'first_name', 'last_name', 'email', 'is_active', 'groups', 'password']

    def validate(self, attrs):
        if not self.instance and not attrs.get('password'):
            raise serializers.ValidationError({'password': 'Informe uma senha.'})
        if 'password' in attrs:
            validate_password(attrs['password'], self.instance or get_user_model()(username=attrs.get('username', '')))
        return attrs

    def create(self, validated_data):
        groups = validated_data.pop('groups', [])
        usuario = get_user_model().objects.create_user(**validated_data)
        usuario.groups.set(groups)
        return usuario

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        instance = super().update(instance, validated_data)
        if password:
            instance.set_password(password)
            instance.save(update_fields=['password'])
        return instance


class AlunoSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilAluno
        fields = ['id', 'usuario', 'matricula', 'curso', 'orientador_atual']


class ProfessorSerializer(serializers.ModelSerializer):
    class Meta:
        model = PerfilProfessor
        fields = ['id', 'usuario', 'departamento', 'area_pesquisa']


class AuditoriaSerializer(serializers.ModelSerializer):
    class Meta:
        from monografias.models import Auditoria
        model = Auditoria
        fields = ['id', 'ator', 'acao', 'entidade', 'registro_id', 'detalhes', 'criado_em']


class EventoSerializer(serializers.ModelSerializer):
    class Meta:
        from monografias.models import Evento
        model = Evento
        fields = ['id', 'tipo', 'dados', 'criado_em', 'processado_em', 'erro', 'tentativas']
