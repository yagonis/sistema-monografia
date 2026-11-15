"""Teste de carga local; não é certificação de capacidade de produção."""
import argparse
import asyncio
import json
import time

async def executar(host, porta, total, concorrencia):
    limite = asyncio.Semaphore(concorrencia)
    tempos, falhas = [], []
    async def requisicao():
        async with limite:
            inicio = time.monotonic()
            writer = None
            try:
                reader, writer = await asyncio.wait_for(asyncio.open_connection(host, porta), 15)
                writer.write(b'GET /api/publicadas/ HTTP/1.0\r\nHost: repositorio\r\nConnection: close\r\n\r\n')
                await writer.drain()
                resposta = await asyncio.wait_for(reader.read(), 30)
                if b' 200 ' not in resposta.split(b'\r\n', 1)[0]:
                    raise ValueError('HTTP diferente de 200')
                tempos.append(time.monotonic()-inicio)
            except Exception as exc:
                falhas.append(type(exc).__name__)
            finally:
                if writer:
                    writer.close()
                    await writer.wait_closed()
    inicio = time.monotonic()
    await asyncio.gather(*(requisicao() for _ in range(total)))
    duracao = time.monotonic()-inicio
    tempos.sort()
    print(json.dumps({'requisicoes': total, 'concorrencia': concorrencia, 'sucessos': len(tempos), 'falhas': len(falhas),
        'duracao_segundos': round(duracao, 3), 'req_por_segundo': round(total/duracao, 2),
        'p95_segundos': round(tempos[min(len(tempos)-1, int(len(tempos)*.95))], 3) if tempos else None}, indent=2))
    return bool(falhas)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--host', default='repositorio')
    parser.add_argument('--porta', type=int, default=8001)
    parser.add_argument('--total', type=int, default=1000)
    parser.add_argument('--concorrencia', type=int, default=1000)
    args = parser.parse_args()
    raise SystemExit(asyncio.run(executar(args.host, args.porta, args.total, args.concorrencia)))
