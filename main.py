from openai import OpenAI
from dotenv import load_dotenv
import time
import os

load_dotenv()

groq = OpenAI(
    api_key=os.environ['API_KEY'],
    base_url="https://api.groq.com/openai/v1"
)

# models = groq.models.list()
# for m in models:
#     print(m.id)

def call_model(mensagens):
  return groq.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=mensagens
        )

def react_agent(pergunta):
    resposta_final = ""
    total_tokens_usados = 0

    mensagens = [{"role": "system", "content": "Quebre a pergunta do usuário em 3 passos lógicos. Resolva um passo de cada vez e aguarde o usuário pedir o próximo passo."}]
    mensagens.append({"role": "user", "content": pergunta})

    for i in range(3):
        resposta = call_model(mensagens)
        total_tokens_usados += resposta.usage.total_tokens
        conteudo = resposta.choices[0].message.content

        print(f"\nPasso {i+1}:\n{conteudo}\n")

        mensagens.append({"role": "assistant", "content": conteudo})
        mensagens.append({"role": "user", "content": "Excelente, prossiga para o próximo passo ou dê a conclusão final."})

        resposta_final = conteudo

    return resposta_final, total_tokens_usados

def reflexion_agent(pergunta):
    resposta_final = ""
    total_tokens_usados = 0
    memoria = []

    for tentativa in range(3):
        print(f"\n====== Tentativa {tentativa+1} ======")

        mensagens = [{"role": "user", "content": pergunta}]

        if memoria:
            mensagens.append({
                "role": "system",
                "content": f"Lições aprendidas: {memoria}"
            })

        resposta = call_model(mensagens)

        total_tokens_usados += resposta.usage.total_tokens

        conteudo = resposta.choices[0].message.content
        if not conteudo:
            break

        print("\nResposta:\n", conteudo)


        reflexao = call_model([
            {"role": "user", "content": f"O que pode melhorar nessa resposta?\n{conteudo}"}
        ])
        total_tokens_usados += reflexao.usage.total_tokens

        insight = reflexao.choices[0].message.content
        if not insight:
            break

        memoria.append(insight)

        print("\nReflexão:\n", insight)

        resposta_final = conteudo

    return resposta_final, total_tokens_usados



pergunta = "Pesquise os 3 países com maior PIB da América do Sul, calcule a média do PIB per capita deles, e responda: essa média é maior ou menor que a média mundial?"

print("\n===== REACT =====")
start = time.perf_counter()
resposta_react, tokens_react = react_agent(pergunta)
end = time.perf_counter()
print(f"\n\nRESPOSTA FINAL:\n{resposta_react}\n\n")
print(f"Levou: {end - start:0.4f} segundos e usou {tokens_react} tokens")

print("\n===== REFLEXION =====")
start = time.perf_counter()
resposta_reflexion, tokens_reflexion = reflexion_agent(pergunta)
end = time.perf_counter()
print(f"\n\nRESPOSTA FINAL:\n{resposta_reflexion}\n\n")
print(f"Levou: {end - start:0.4f} segundos e usou {tokens_reflexion} tokens")
