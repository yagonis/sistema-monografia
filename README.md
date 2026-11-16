# Repositório de Monografias

Backend Django para submissão, orientação, bancas, avaliação e publicação de trabalhos acadêmicos.

- [Execução, arquitetura, regras e validação](docs/BACKEND.md)
- [Interface e execução do frontend](docs/FRONTEND.md)
- [Contrato da API para o frontend](docs/API.md)
- [OpenAPI](docs/openapi.yaml)
- [Requisitos do trabalho](requisitos.md)

O serviço acadêmico e o repositório público têm bancos e APIs independentes. Redis e RabbitMQ/Celery dão suporte a cache, sessões e processamento assíncrono. A interface JavaScript integrada à API está disponível na página inicial.

Para iniciar em ambiente local, siga `docs/BACKEND.md`. As migrações do seu PostgreSQL pessoal não são aplicadas automaticamente por este repositório.
