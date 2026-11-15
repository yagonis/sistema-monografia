"""Histórico de campos acadêmicos, sem credenciais, tokens ou texto integral."""
from django.db.models.signals import pre_save, post_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .contexto import ator_atual
from .models import Auditoria

ENTIDADES = {'monografias.Curso', 'monografias.Monografia', 'monografias.Banca', 'monografias.MembroBanca',
             'monografias.Avaliacao', 'monografias.Documento', 'usuarios.PerfilAluno', 'usuarios.PerfilProfessor', 'usuarios.Usuario'}
EXCLUIR = {'password', 'token_hash', 'texto_extraido', 'last_login'}


def dados(instancia):
    return {campo.attname: str(getattr(instancia, campo.attname)) if getattr(instancia, campo.attname) is not None else None
            for campo in instancia._meta.concrete_fields if campo.name not in EXCLUIR}


def registrar(acao, instancia, detalhes):
    ator = ator_atual.get()
    if getattr(ator, 'is_authenticated', False) and not get_user_model().objects.filter(pk=ator.pk).exists():
        ator = None
    Auditoria.objects.create(ator=ator if getattr(ator, 'is_authenticated', False) else None,
        acao=acao, entidade=instancia._meta.label, registro_id=instancia.pk, detalhes=detalhes)


@receiver(pre_save)
def antes(sender, instance, raw=False, **kwargs):
    if raw or sender._meta.label not in ENTIDADES:
        return
    anterior = sender.objects.filter(pk=instance.pk).first() if instance.pk else None
    instance._auditoria_antes = dados(anterior) if anterior else {}


@receiver(post_save)
def depois(sender, instance, raw=False, created=False, **kwargs):
    if raw or sender._meta.label not in ENTIDADES:
        return
    anterior = getattr(instance, '_auditoria_antes', {})
    atual = dados(instance)
    alteracoes = {campo: {'antes': anterior.get(campo), 'depois': valor} for campo, valor in atual.items() if anterior.get(campo) != valor}
    if alteracoes:
        registrar('criacao_campos' if created else 'alteracao_campos', instance, alteracoes)


@receiver(post_delete)
def removido(sender, instance, **kwargs):
    if sender._meta.label in ENTIDADES:
        registrar('exclusao_campos', instance, dados(instance))


@receiver(m2m_changed, sender=get_user_model().groups.through)
def grupos(sender, instance, action, reverse=False, pk_set=None, **kwargs):
    if action in ['post_add', 'post_remove', 'post_clear'] and not reverse:
        registrar('grupos_usuario', instance, {'acao': action, 'grupos': list(pk_set or [])})
