from django.contrib.auth import get_user_model, logout
from django.db import transaction
from django.db.models import Q, Count, Avg, F, ExpressionWrapper, DurationField
from django.http import FileResponse, Http404
from django.middleware.csrf import get_token
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from allauth.account.forms import LoginForm
from rest_framework import permissions, serializers, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiTypes
from .throttles import SubmissaoThrottle

from monografias.models import Curso, Monografia, Banca, MembroBanca, Avaliacao, Documento, Auditoria
from monografias.forms import MonografiaForm
from monografias import servicos as regras
from usuarios.models import PerfilAluno, PerfilProfessor
from .serializers import (CursoSerializer, PublicaSerializer, MonografiaSerializer, BancaSerializer,
    MembroSerializer, AvaliacaoSerializer, DocumentoSerializer, UsuarioSerializer, AlunoSerializer, ProfessorSerializer)


def visiveis(usuario):
    if not usuario.is_authenticated or not usuario.is_active:
        return Monografia.objects.none()
    if usuario.is_superuser:
        return Monografia.objects.all()
    filtro = Q(pk__in=[])
    if usuario.eh_aluno:
        filtro |= Q(autor=usuario)
    if usuario.eh_professor:
        filtro |= Q(orientador=usuario) & ~Q(status='rascunho')
        filtro |= Q(bancas__membros__usuario=usuario, bancas__status__in=['agendada', 'realizada'])
    if usuario.eh_coordenador:
        filtro |= Q(curso__coordenador=usuario) & ~Q(status='rascunho')
    return Monografia.objects.filter(filtro).distinct()


def pdf_resposta(arquivo, nome, hash_esperado=None):
    try:
        if hash_esperado:
            with arquivo.open('rb') as conteudo:
                if regras.sha256(conteudo) != hash_esperado:
                    raise serializers.ValidationError('Integridade do arquivo inválida.')
        return FileResponse(arquivo.open('rb'), as_attachment=True, filename=nome, content_type='application/pdf')
    except OSError as exc:
        raise Http404('Arquivo indisponível') from exc


class Administracao(permissions.BasePermission):
    def has_permission(self, request, view):
        from config.middleware import rede_autorizada
        return request.user.is_authenticated and request.user.is_active and request.user.is_superuser and rede_autorizada(request)


class BaseViewSet(viewsets.ModelViewSet):
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ['get', 'post', 'patch', 'delete', 'head', 'options']

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        return super().create(request, *args, **kwargs)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        return super().partial_update(request, *args, **kwargs)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        return super().destroy(request, *args, **kwargs)

    def perform_destroy(self, instance):
        with transaction.atomic():
            regras.auditar(self.request.user, 'exclusao', instance)
            instance.delete()


class Conta(APIView):
    permission_classes = [permissions.AllowAny]
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        usuario = request.user
        return Response({'csrfToken': get_token(request), 'autenticado': usuario.is_authenticated,
            'usuario': {'id': usuario.pk, 'username': usuario.username, 'grupos': list(usuario.groups.values_list('name', flat=True))}
            if usuario.is_authenticated else None})

    @method_decorator(csrf_protect)
    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        form = LoginForm(data=request.data, request=request._request)
        if not form.is_valid():
            return Response(form.errors, status=400)
        form.login(request._request)
        if not request.user.is_authenticated and not request._request.user.is_authenticated:
            return Response({'detail': 'Não foi possível autenticar.'}, status=403)
        return Response({'detail': 'Autenticado.', 'csrfToken': get_token(request)})

    @method_decorator(csrf_protect)
    @extend_schema(responses={204: None})
    def delete(self, request):
        logout(request)
        return Response(status=204)


class CursoViewSet(BaseViewSet):
    queryset = Curso.objects.order_by('nome')
    serializer_class = CursoSerializer
    def get_permissions(self):
        return [permissions.AllowAny()] if self.action in ['list', 'retrieve'] else [Administracao()]
    def perform_create(self, serializer):
        objeto = serializer.save()
        regras.auditar(self.request.user, 'criacao', objeto)
    def perform_update(self, serializer):
        objeto = serializer.save()
        regras.auditar(self.request.user, 'edicao', objeto)


class Publicas(viewsets.ReadOnlyModelViewSet):
    permission_classes = [permissions.AllowAny]
    serializer_class = PublicaSerializer
    def get_queryset(self):
        qs = Monografia.objects.filter(status='publicada').select_related('autor', 'orientador').order_by('-publicada_em', 'pk')
        params = self.request.query_params
        for campo in ['curso', 'autor', 'orientador']:
            if params.get(campo):
                try:
                    qs = qs.filter(**{campo + '_id': int(params[campo])})
                except ValueError:
                    raise serializers.ValidationError({campo: 'Identificador inválido.'})
        if params.get('ano_defesa'):
            try:
                ano = int(params['ano_defesa'])
                if not 1 <= ano <= 9999:
                    raise ValueError
                qs = qs.filter(bancas__status='realizada', bancas__data_hora__year=ano)
            except ValueError:
                raise serializers.ValidationError({'ano_defesa': 'Ano inválido.'})
        if params.get('palavras_chave'):
            qs = qs.filter(palavras_chave__icontains=params['palavras_chave'])
        if params.get('busca'):
            q = params['busca'][:200]
            qs = qs.filter(Q(titulo__icontains=q) | Q(resumo__icontains=q) | Q(palavras_chave__icontains=q)
                | Q(autor__first_name__icontains=q) | Q(autor__last_name__icontains=q) | Q(texto_extraido__icontains=q))
        return qs.distinct()

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        trabalho = self.get_object()
        regras.conferir_integridade(trabalho)
        corrigida = trabalho.documentos.filter(tipo='corrigida', validado_em__isnull=False).order_by('-validado_em').first()
        return pdf_resposta(corrigida.arquivo if corrigida else trabalho.arquivo, f'monografia-{trabalho.pk}.pdf',
                            corrigida.hash_sha256 if corrigida else trabalho.hash_sha256)


class Monografias(BaseViewSet):
    serializer_class = MonografiaSerializer
    def get_throttles(self):
        return [SubmissaoThrottle()] if self.action in ['create', 'submeter'] else super().get_throttles()
    def get_queryset(self):
        return visiveis(self.request.user).select_related('curso', 'autor', 'orientador').order_by('pk')

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        if not request.user.eh_aluno:
            self.permission_denied(request)
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        form = MonografiaForm(request.data, request.FILES)
        if not form.is_valid():
            return Response(form.errors, status=400)
        trabalho = form.save(commit=False)
        trabalho.autor = request.user
        if Monografia.objects.filter(autor=request.user, hash_sha256=trabalho.hash_sha256).exists():
            raise serializers.ValidationError({'arquivo': 'Este PDF já foi enviado por você.'})
        trabalho.save()
        regras.auditar(request.user, 'upload', trabalho, versao=trabalho.versao)
        return Response(self.get_serializer(trabalho).data, status=201)

    @transaction.atomic
    def partial_update(self, request, *args, **kwargs):
        get_user_model().objects.select_for_update().get(pk=request.user.pk)
        trabalho = get_object_or_404(Monografia.objects.select_for_update().filter(
            pk__in=self.get_queryset().values('pk')), pk=kwargs['pk'])
        if not request.user.eh_aluno or trabalho.autor_id != request.user.pk or not trabalho.pode_editar:
            self.permission_denied(request)
        dados = {campo: request.data.get(campo, getattr(trabalho, campo + '_id') if campo in ['curso', 'orientador'] else getattr(trabalho, campo))
                 for campo in ['titulo', 'resumo', 'palavras_chave', 'curso', 'orientador']}
        form = MonografiaForm(dados, request.FILES, instance=trabalho)
        if not form.is_valid():
            return Response(form.errors, status=400)
        trabalho = form.save(commit=False)
        if 'arquivo' in request.FILES:
            if Monografia.objects.filter(autor=request.user, hash_sha256=trabalho.hash_sha256).exclude(pk=trabalho.pk).exists():
                raise serializers.ValidationError({'arquivo': 'Este PDF já foi enviado por você.'})
            trabalho.versao += 1
        trabalho.save()
        regras.auditar(request.user, 'edicao_rascunho', trabalho, versao=trabalho.versao)
        return Response(self.get_serializer(trabalho).data)

    @transaction.atomic
    def destroy(self, request, *args, **kwargs):
        trabalho = get_object_or_404(Monografia.objects.select_for_update().filter(
            pk__in=self.get_queryset().values('pk')), pk=kwargs['pk'])
        if not trabalho.pode_editar or not (trabalho.autor_id == request.user.pk or request.user.is_superuser):
            self.permission_denied(request)
        self.perform_destroy(trabalho)
        return Response(status=204)

    @action(detail=True, methods=['post'])
    def submeter(self, request, pk=None):
        self.get_object()
        return Response(self.get_serializer(regras.submeter(request.user, int(pk))).data)

    @action(detail=True, methods=['post'])
    def aprovar(self, request, pk=None):
        self.get_object()
        return Response(self.get_serializer(regras.aprovar(request.user, int(pk))).data)

    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        trabalho = self.get_object()
        regras.conferir_integridade(trabalho)
        return pdf_resposta(trabalho.arquivo, f'monografia-{trabalho.pk}.pdf')


class Bancas(BaseViewSet):
    serializer_class = BancaSerializer
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Banca.objects.none()
        proprio = Q(membros__usuario=self.request.user) if self.request.user.eh_professor else Q(pk__in=[])
        return Banca.objects.filter(proprio | Q(monografia__in=visiveis(self.request.user))).distinct().order_by('pk')
    def perform_create(self, serializer):
        trabalho = serializer.validated_data['monografia']
        serializer.instance = regras.salvar_banca(self.request.user, trabalho, serializer.validated_data)
    def perform_update(self, serializer):
        if 'monografia' in serializer.validated_data and serializer.validated_data['monografia'].pk != serializer.instance.monografia_id:
            raise serializers.ValidationError('Não é permitido transferir a banca.')
        serializer.instance = regras.salvar_banca(self.request.user, serializer.instance.monografia, serializer.validated_data, serializer.instance)
    def perform_destroy(self, instance):
        instance = Banca.objects.select_for_update().get(pk=instance.pk)
        regras.exigir_gestor(self.request.user, instance.monografia)
        if instance.status != 'em_preparacao':
            raise serializers.ValidationError('Bancas agendadas devem ser canceladas, não excluídas.')
        super().perform_destroy(instance)
    @action(detail=True, methods=['post'])
    def agendar(self, request, pk=None):
        self.get_object()
        return Response(self.get_serializer(regras.agendar(request.user, int(pk))).data)
    @action(detail=True, methods=['post'])
    def cancelar(self, request, pk=None):
        self.get_object()
        return Response(self.get_serializer(regras.cancelar(request.user, int(pk))).data)


class Membros(BaseViewSet):
    serializer_class = MembroSerializer
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return MembroBanca.objects.none()
        proprio = Q(usuario=self.request.user) if self.request.user.eh_professor else Q(pk__in=[])
        return MembroBanca.objects.filter(proprio | Q(
            banca__monografia__in=visiveis(self.request.user))).distinct().order_by('pk')
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        membro, token = regras.convidar(request.user, serializer.validated_data['banca'], serializer.validated_data)
        return Response({'membro': self.get_serializer(membro).data, 'token_temporario': token}, status=201)
    def partial_update(self, request, *args, **kwargs):
        raise serializers.ValidationError('Remova o convite em preparação e faça um novo para alterar o membro.')
    def perform_destroy(self, instance):
        banca = Banca.objects.select_for_update().get(pk=instance.banca_id)
        regras.exigir_gestor(self.request.user, banca.monografia)
        if banca.status != 'em_preparacao':
            raise serializers.ValidationError('Composição bloqueada após agendamento.')
        super().perform_destroy(instance)
    @action(detail=True, methods=['post'])
    def confirmar(self, request, pk=None):
        membro = regras.confirmar(self.get_object(), request.user)
        return Response(self.get_serializer(membro).data)
    @action(detail=True, methods=['post'])
    @transaction.atomic
    def revogar(self, request, pk=None):
        membro = self.get_object()
        Banca.objects.select_for_update().get(pk=membro.banca_id)
        membro = MembroBanca.objects.select_for_update().get(pk=membro.pk)
        regras.exigir_gestor(request.user, membro.banca.monografia)
        membro.revogado = True
        membro.save(update_fields=['revogado'])
        regras.auditar(request.user, 'revogacao_convite', membro)
        return Response(status=204)

    @action(detail=True, methods=['post'])
    @transaction.atomic
    def renovar(self, request, pk=None):
        import hashlib
        import secrets
        from datetime import timedelta
        from django.conf import settings
        membro = self.get_object()
        Banca.objects.select_for_update().get(pk=membro.banca_id)
        membro = MembroBanca.objects.select_for_update().get(pk=membro.pk)
        regras.exigir_gestor(request.user, membro.banca.monografia)
        if membro.usuario_id or membro.banca.status not in ['em_preparacao', 'agendada']:
            raise serializers.ValidationError('Convite não pode ser renovado.')
        token = secrets.token_urlsafe(32)
        membro.token_hash = hashlib.sha256(token.encode()).hexdigest()
        membro.expira_em = timezone.now() + timedelta(hours=settings.CONVITE_VALIDADE_HORAS)
        membro.revogado = False
        membro.save(update_fields=['token_hash', 'expira_em', 'revogado'])
        regras.auditar(request.user, 'renovacao_convite', membro)
        return Response({'token_temporario': token, 'expira_em': membro.expira_em})


class Avaliacoes(BaseViewSet):
    serializer_class = AvaliacaoSerializer
    def get_queryset(self):
        if getattr(self, 'swagger_fake_view', False):
            return Avaliacao.objects.none()
        # Pareceres são privados do avaliador até o fechamento; gestores só após resultado.
        proprio = Q(membro__usuario=self.request.user) if self.request.user.eh_professor else Q(pk__in=[])
        return Avaliacao.objects.filter(proprio | Q(
            membro__banca__encerrada_em__isnull=False, membro__banca__monografia__in=visiveis(self.request.user))).distinct().order_by('pk')
    def perform_create(self, serializer):
        membro = serializer.validated_data['membro']
        serializer.instance = regras.avaliar(membro, serializer.validated_data, self.request.user)
    def perform_update(self, serializer):
        dados = {campo: serializer.validated_data.get(campo, getattr(serializer.instance, campo)) for campo in ['nota', 'parecer', 'recomendacao']}
        if 'membro' in serializer.validated_data and serializer.validated_data['membro'].pk != serializer.instance.membro_id:
            raise serializers.ValidationError('Avaliador não pode ser alterado.')
        serializer.instance = regras.avaliar(serializer.instance.membro, dados, self.request.user)
    def perform_destroy(self, instance):
        with transaction.atomic():
            banca = Banca.objects.select_for_update().get(pk=instance.membro.banca_id)
            if instance.membro.usuario_id != self.request.user.pk or banca.encerrada_em:
                self.permission_denied(self.request)
            super().perform_destroy(instance)


class Documentos(BaseViewSet):
    serializer_class = DocumentoSerializer
    def get_queryset(self):
        return Documento.objects.filter(monografia__in=visiveis(self.request.user)).order_by('pk')
    @transaction.atomic
    def perform_create(self, serializer):
        trabalho = Monografia.objects.select_for_update().get(pk=serializer.validated_data['monografia'].pk)
        if trabalho.status == 'publicada' or not (trabalho.autor_id == self.request.user.pk or regras.pode_gerir(self.request.user, trabalho)):
            self.permission_denied(self.request)
        arquivo = serializer.validated_data['arquivo']
        from monografias.validadores import validar_pdf
        validar_pdf(arquivo)
        documento = serializer.save(hash_sha256=regras.sha256(arquivo))
        regras.auditar(self.request.user, 'upload_documento', documento)
    def partial_update(self, request, *args, **kwargs):
        raise serializers.ValidationError('Envie um novo documento em vez de substituir a versão anterior.')
    def perform_destroy(self, instance):
        instance = Documento.objects.select_for_update().get(pk=instance.pk)
        Monografia.objects.select_for_update().get(pk=instance.monografia_id)
        regras.exigir_gestor(self.request.user, instance.monografia)
        if instance.validado_em or instance.monografia.status == 'publicada':
            raise serializers.ValidationError('Documento validado não pode ser excluído.')
        super().perform_destroy(instance)
    @action(detail=True, methods=['post'])
    def validar(self, request, pk=None):
        self.get_object()
        return Response(self.get_serializer(regras.validar_documento(request.user, int(pk))).data)
    @action(detail=True, methods=['get'])
    def pdf(self, request, pk=None):
        doc = self.get_object()
        return pdf_resposta(doc.arquivo, f'documento-{doc.pk}.pdf', doc.hash_sha256)


class Externo(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]
    def membro(self, request):
        return regras.membro_por_token(request.headers.get('X-Banca-Token', ''))
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        membro = self.membro(request)
        banca = membro.banca
        if banca.status == 'cancelada':
            raise Http404
        return Response({'membro': membro.pk, 'banca': banca.pk, 'titulo': banca.monografia.titulo,
                         'data_hora': banca.data_hora, 'fim': banca.fim, 'local': banca.local, 'link': banca.link})
    @extend_schema(request=OpenApiTypes.OBJECT, responses=OpenApiTypes.OBJECT)
    def post(self, request):
        membro = self.membro(request)
        if request.data.get('acao') == 'confirmar':
            regras.confirmar(membro)
        else:
            serializer = AvaliacaoSerializer(data={**request.data, 'membro': membro.pk})
            serializer.is_valid(raise_exception=True)
            regras.avaliar(membro, serializer.validated_data)
        return Response({'detail': 'Registrado.'})


class ExternoPDF(Externo):
    @extend_schema(responses=OpenApiTypes.BINARY)
    def get(self, request):
        membro = self.membro(request)
        if membro.banca.status not in ['agendada', 'realizada']:
            self.permission_denied(request)
        return pdf_resposta(membro.banca.monografia.arquivo, 'monografia.pdf', membro.banca.monografia.hash_sha256)
    http_method_names = ['get', 'head', 'options']


class Usuarios(BaseViewSet):
    permission_classes = [Administracao]
    serializer_class = UsuarioSerializer
    queryset = get_user_model().objects.order_by('pk')
    def perform_create(self, serializer):
        regras.auditar(self.request.user, 'criacao_usuario', serializer.save())
    def perform_update(self, serializer):
        regras.auditar(self.request.user, 'edicao_usuario', serializer.save())


class Alunos(Usuarios):
    serializer_class = AlunoSerializer
    queryset = PerfilAluno.objects.order_by('pk')


class Professores(Usuarios):
    serializer_class = ProfessorSerializer
    queryset = PerfilProfessor.objects.order_by('pk')


class Orientadores(APIView):
    permission_classes = [permissions.AllowAny]
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        return Response(list(get_user_model().objects.filter(groups__name='Professores', is_active=True).order_by('pk').values('id', 'first_name', 'last_name')))


class Relatorios(APIView):
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        qs = visiveis(request.user).exclude(status='rascunho')
        total = qs.filter(status__in=['aprovada', 'ressalvas', 'publicada', 'reprovada']).count()
        aprovadas = qs.filter(status__in=['aprovada', 'ressalvas', 'publicada']).count()
        duracao = Banca.objects.filter(monografia__in=qs, status='realizada', monografia__submetida_em__isnull=False).aggregate(
            media=Avg(ExpressionWrapper(F('data_hora') - F('monografia__submetida_em'), output_field=DurationField())))['media']
        return Response({'por_curso': list(qs.values('curso_id').annotate(total=Count('pk'))),
            'por_orientador': list(qs.values('orientador_id').annotate(total=Count('pk'))),
            'taxa_aprovacao': aprovadas / total if total else None,
            'tempo_medio_dias': duracao.total_seconds() / 86400 if duracao else None,
            'por_ano_defesa': list(Banca.objects.filter(monografia__in=qs, status='realizada').values('data_hora__year').annotate(total=Count('monografia_id', distinct=True)))})


class Auditorias(viewsets.ReadOnlyModelViewSet):
    from .serializers import AuditoriaSerializer
    serializer_class = AuditoriaSerializer
    permission_classes = [Administracao]
    queryset = Auditoria.objects.order_by('-criado_em', '-pk')


class Eventos(viewsets.ReadOnlyModelViewSet):
    from .serializers import EventoSerializer
    from monografias.models import Evento
    serializer_class = EventoSerializer
    permission_classes = [Administracao]
    queryset = Evento.objects.order_by('-pk')
    @action(detail=True, methods=['post'])
    def repetir(self, request, pk=None):
        from django.core.cache import cache
        ev = self.get_object()
        if ev.processado_em:
            raise serializers.ValidationError('Evento já processado.')
        ev.tentativas = 0
        ev.erro = ''
        ev.save(update_fields=['tentativas', 'erro'])
        cache.delete(f'evento_em_andamento:{ev.pk}')
        regras.auditar(request.user, 'repeticao_evento', ev)
        return Response({'detail': 'Evento disponível para reprocessamento.'})


class Health(APIView):
    permission_classes = [permissions.AllowAny]
    authentication_classes = []
    @extend_schema(responses=OpenApiTypes.OBJECT)
    def get(self, request):
        from django.db import connection
        from django.core.cache import cache
        with connection.cursor() as cursor:
            cursor.execute('SELECT 1')
        cache.set('health:probe', 'ok', 5)
        if cache.get('health:probe') != 'ok':
            return Response({'status': 'indisponivel'}, status=503)
        return Response({'status': 'ok', 'servico': 'academico'})
