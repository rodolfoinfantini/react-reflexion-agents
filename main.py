from openai import OpenAI
from dotenv import load_dotenv
import subprocess
import time
import os
import re

load_dotenv()

# Configuração do cliente
client = OpenAI(
    api_key=os.environ['API_KEY'],
    base_url="https://api.groq.com/openai/v1"
)

MODEL = "llama-3.3-70b-versatile"

# ==========================================
# FERRAMENTA COMPARTILHADA
# ==========================================
def run_git_command(comando):
    comandos_proibidos = ["add", "commit", "push", "checkout", "reset", "rebase", "rm", "clean"]
    if any(proibido in comando for proibido in comandos_proibidos):
        return f"Acesso negado: Comando bloqueado por segurança."

    if not comando.startswith("git "):
        return "Erro: Apenas comandos 'git' são permitidos."

    try:
        resultado = subprocess.run(comando.split(), capture_output=True, text=True, check=True)
        output = resultado.stdout.strip()
        if len(output) > 2500:
            return output[:2500] + "\n... [Saída truncada]"
        return output if output else "Comando executado sem retorno."
    except subprocess.CalledProcessError as e:
        return f"Erro: {e.stderr.strip()}"
    except Exception as e:
        return f"Erro: {str(e)}"

# ==========================================
# 1. AGENTE REACT
# ==========================================
REACT_SYSTEM_PROMPT = """Você é um especialista em Git.
Sua tarefa é gerar uma mensagem no padrão Conventional Commits.
Você tem a ferramenta 'GitCLI' para investigar o repositório. Entrada: comando git (ex: git status, git diff).

Use EXATAMENTE este formato:
Pensamento: o que preciso descobrir
Ação: GitCLI
Entrada da Ação: comando git
Observação: [resultado será inserido pelo sistema]
...
Pensamento: Tenho o contexto.
Resposta Final: [mensagem de commit]
"""

def react_agent(pergunta, max_steps=8):
    total_tokens = 0
    total_chamadas = 0 # Inicializa o contador de chamadas

    mensagens = [
        {"role": "system", "content": REACT_SYSTEM_PROMPT},
        {"role": "user", "content": pergunta}
    ]

    print("\n🔍 [REACT] Iniciando investigação do repositório...")

    for step in range(max_steps):
        total_chamadas += 1 # Incrementa a chamada
        resposta = client.chat.completions.create(
            model=MODEL,
            messages=mensagens,
            stop=["Observação:"]
        )

        total_tokens += resposta.usage.total_tokens # Soma os tokens
        conteudo = resposta.choices[0].message.content.strip()
        mensagens.append({"role": "assistant", "content": conteudo})

        if "Resposta Final:" in conteudo:
            resposta_final = conteudo.split("Resposta Final:")[-1].strip()
            return resposta_final, total_tokens, total_chamadas

        acao_match = re.search(r"Ação:\s*(.*)", conteudo)
        entrada_match = re.search(r"Entrada da Ação:\s*(.*)", conteudo)

        if acao_match and entrada_match and acao_match.group(1).strip() == "GitCLI":
            comando = entrada_match.group(1).strip().replace('"', '').replace("'", "")
            print(f"   💻 ReAct executando: {comando}")

            resultado = run_git_command(comando)
            mensagens.append({"role": "user", "content": f"Observação: {resultado}"})
        else:
            mensagens.append({"role": "user", "content": "Observação: Formato inválido."})

    return "Falha: Limite de passos atingido.", total_tokens, total_chamadas

# ==========================================
# 2. AGENTE REFLEXION
# ==========================================
def reflexion_agent(pergunta):
    total_tokens = 0
    total_chamadas = 0 # Inicializa o contador de chamadas

    print("\n✍️ [REFLEXION] Coletando contexto para iniciar a escrita...")

    status = run_git_command("git status")
    diff = run_git_command("git diff")
    contexto_git = f"STATUS DO REPOSITÓRIO:\n{status}\n\nALTERAÇÕES (DIFF):\n{diff}"

    memoria_criticas = []
    resposta_final = ""

    for tentativa in range(3):
        print(f"\n   🔄 Reflexion - Iteração {tentativa + 1}")

        # --- PASSO A: GERAÇÃO DO DRAFT ---
        mensagens = [
            {"role": "system", "content": "Você é um especialista em gerar mensagens de Conventional Commits. Responda APENAS com a mensagem de commit, sem explicações extras."},
            {"role": "user", "content": f"Contexto do código:\n{contexto_git}\n\nPedido do usuário: {pergunta}"}
        ]

        if memoria_criticas:
            mensagens.append({
                "role": "user",
                "content": f"Baseado nas suas tentativas anteriores, corrija os seguintes defeitos: {memoria_criticas[-1]}"
            })

        total_chamadas += 1 # Incrementa a chamada do Draft
        draft_resposta = client.chat.completions.create(model=MODEL, messages=mensagens)
        total_tokens += draft_resposta.usage.total_tokens # Soma os tokens

        draft = draft_resposta.choices[0].message.content.strip()
        print(f"      📝 Draft gerado:\n      {draft}")

        # --- PASSO B: CRÍTICA (REFLEXÃO) ---
        prompt_critica = f"""
        Você é um revisor de código muito rígido. Avalie o commit abaixo usando a regra Conventional Commits (tipo(escopo opcional): descrição imperativa).

        Commit gerado:
        {draft}

        Perguntas:
        1. O tipo (feat, fix, chore, etc) está correto para o código alterado?
        2. A descrição está no imperativo (ex: "add login" e não "added login" ou "adicionando login")?
        3. Está conciso?

        Aponte O QUE DEVE SER MELHORADO. Se estiver perfeito, responda apenas "PERFEITO".
        """

        total_chamadas += 1 # Incrementa a chamada da Crítica
        critica_resposta = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": prompt_critica}]
        )
        total_tokens += critica_resposta.usage.total_tokens # Soma os tokens

        critica = critica_resposta.choices[0].message.content.strip()
        print(f"      🧐 Crítica interna:\n      {critica}")

        if "PERFEITO" in critica.upper():
            print("      ✅ O agente concluiu que a resposta está perfeita.")
            resposta_final = draft
            break

        memoria_criticas.append(critica)
        resposta_final = draft

    return resposta_final, total_tokens, total_chamadas

# ==========================================
# EXECUÇÃO E COMPARAÇÃO
# ==========================================
if __name__ == "__main__":
    pergunta = "Gere uma mensagem de commit seguindo o Conventional Commits baseado nas alterações atuais."

    print("="*50)
    start_react = time.perf_counter()
    resultado_react, tokens_react, chamadas_react = react_agent(pergunta)
    end_react = time.perf_counter()

    print("\n\n\n")
    print("="*50)

    start_reflexion = time.perf_counter()
    resultado_reflexion, tokens_reflexion, chamadas_reflexion = reflexion_agent(pergunta)
    end_reflexion = time.perf_counter()


    print("\n\n\n")
    print("="*50)
    print(f"\n🚀 RESULTADO REACT:\n{resultado_react}")
    print(f"⏱️ Tempo: {end_react-start_react:.1f}s | 🪙 Tokens: {tokens_react} | 📞 Chamadas à API: {chamadas_react}")
    print("="*50)
    print(f"\n🚀 RESULTADO REFLEXION:\n{resultado_reflexion}")
    print(f"⏱️ Tempo: _reflexion{end_reflexion-start_reflexion:.1f}s | 🪙 Tokens: {tokens_reflexion} | 📞 Chamadas à API: {chamadas_reflexion}")
    print("="*50)
