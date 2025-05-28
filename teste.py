import asyncio
from gemini_webapi import GeminiClient # Certifique-se de que o nome do pacote está correto

# ATENÇÃO: Substitua pelos seus cookies REAIS obtidos do Google Gemini.
# Veja a documentação do projeto HanaokaYuzu/Gemini-API para detalhes sobre como obtê-los.
# O cookie __Secure-1PSID é essencial.
# O cookie __Secure-1PSIDTS pode não ser necessário para todas as contas ou configurações.
# Se não estiver disponível ou causar problemas, tente com uma string vazia ou None,
# ou consulte a documentação da biblioteca.
SECURE_1PSID = ""
SECURE_1PSIDTS = "" # Ou "", ou None se aplicável

async def testar_gemini_api():
    """
    Um pequeno teste de funcionalidade para a biblioteca HanaokaYuzu/Gemini-API.
    """
    print("Iniciando o teste com a Gemini-API (HanaokaYuzu)...")

    if SECURE_1PSID == "COLOQUE_SEU_COOKIE___SECURE_1PSID_AQUI" or \
       SECURE_1PSIDTS == "COLOQUE_SEU_COOKIE___SECURE_1PSIDTS_AQUI":
        print("\nAVISO IMPORTANTE:")
        print("Por favor, edite este script e substitua os placeholders dos cookies")
        print("pelos seus cookies reais do Google Gemini.")
        print("Sem os cookies corretos, o código não funcionará.\n")
        return

    client = None
    try:
        # Inicializa o cliente Gemini.
        # Você pode ajustar os parâmetros de proxy se necessário.
        print("Inicializando o GeminiClient...")
        client = GeminiClient(
            secure_1psid=SECURE_1PSID,
            secure_1psidts=SECURE_1PSIDTS,
            # proxy="http://seu_proxy_aqui:porta" # Exemplo se você precisar de um proxy
        )

        # Inicializa a conexão (necessário conforme o exemplo do projeto)
        # O timeout é para a inicialização.
        # auto_close=False significa que você precisará fechar a sessão manualmente.
        await client.init(timeout=30, auto_close=False, auto_refresh=True)
        print("Cliente inicializado com sucesso.")

        # Envia um prompt simples
        prompt = "Olá! Qual é a capital do Brasil?"
        print(f"\nEnviando prompt: \"{prompt}\"")

        # Tentativa de usar `generate_content` para enviar o prompt.
        # Se este método não funcionar, consulte a documentação do HanaokaYuzu/Gemini-API
        # para o método correto de envio de prompts de texto.
        response = await client.generate_content(prompt)

        print("\nResposta recebida do Gemini:")

        # A estrutura da resposta pode variar.
        # A biblioteca menciona "Classified Outputs", então a resposta pode ser um objeto.
        # Tentaremos acessar atributos comuns para texto.
        if hasattr(response, 'text') and response.text:
            print(response.text)
        elif hasattr(response, 'candidates') and response.candidates:
            # Estrutura similar à API oficial do Google
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        if hasattr(part, 'text'):
                            print(part.text)
        elif isinstance(response, str): # Caso a resposta seja uma string simples
            print(response)
        else:
            print("Não foi possível extrair o texto diretamente. Imprimindo a resposta completa:")
            print(response)
            print("\nPor favor, inspecione o objeto de resposta para encontrar o conteúdo de texto desejado.")
            print("Pode estar em atributos como `response.parts[0].text` ou similar,")
            print("dependendo da implementação exata da biblioteca.")

    except ImportError:
        print("Erro: A biblioteca 'gemini-webapi' não foi encontrada.")
        print("Por favor, instale-a com: pip install gemini-webapi")
    except Exception as e:
        print(f"\nOcorreu um erro durante o teste: {e}")
        print("Verifique se os seus cookies (__Secure-1PSID e __Secure-1PSIDTS) estão corretos e válidos.")
        print("Consulte a documentação do projeto para mais detalhes: https://github.com/HanaokaYuzu/Gemini-API")
    finally:
        if client and hasattr(client, 'close') and not client.auto_close: # client.auto_close é um atributo do client.init
            print("\nFechando a sessão do cliente...")
            await client.close()
            print("Sessão fechada.")
        elif client and not hasattr(client, 'auto_close'): # Fallback se auto_close não for um atributo direto do client
             print("\nFechando a sessão do cliente (fallback)...")
             await client.close()
             print("Sessão fechada.")


if __name__ == "__main__":
    # Para executar este código:
    # 1. Instale a biblioteca: pip install gemini-webapi
    # 2. (Opcional, mas pode ser útil) Instale browser-cookie3: pip install browser-cookie3
    #    Isso pode ajudar a biblioteca a encontrar os cookies automaticamente em alguns casos,
    #    mas para este exemplo, estamos configurando manualmente.
    # 3. Obtenha seus cookies __Secure-1PSID e __Secure-1PSIDTS do seu navegador ao usar o Google Gemini.
    #    Inspecione as ferramentas de desenvolvedor do seu navegador (geralmente na aba "Application" ou "Storage" -> "Cookies").
    # 4. Substitua os placeholders SECURE_1PSID e SECURE_1PSIDTS no código pelos seus valores reais.

    # Executa a função de teste assíncrona
    asyncio.run(testar_gemini_api())
