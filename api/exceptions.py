from django.core.exceptions import ValidationError, PermissionDenied
from django.db import IntegrityError
from django.db.models.deletion import ProtectedError
from rest_framework.response import Response
from rest_framework.views import exception_handler


def tratar(exc, context):
    if isinstance(exc, ValidationError):
        return Response(getattr(exc, 'message_dict', None) or {'detail': exc.messages}, status=400)
    if isinstance(exc, ProtectedError):
        return Response({'detail': 'Existem registros vinculados. Exclusão bloqueada.'}, status=409)
    if isinstance(exc, IntegrityError):
        return Response({'detail': 'Operação conflita com um registro existente.'}, status=409)
    return exception_handler(exc, context)
