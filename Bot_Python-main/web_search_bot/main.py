from flask import Flask, request, jsonify, send_from_directory
from playwright.sync_api import sync_playwright
from achar import search_and_scroll
import os
import time
import threading
import json
import asyncio


def check_timeout(start_time, timeout_seconds):
    if time.time() - start_time > timeout_seconds:
        raise TimeoutError(f"Tempo limite de {timeout_seconds}s excedido")



# Configurar o aplicativo Flask
app = Flask(__name__)

# Garantir que o diretório 'static' exista
os.makedirs('static', exist_ok=True)

# Definir o tempo limite para processamento de cada site (em segundos)
SITE_PROCESSING_TIMEOUT = 30

# Variável global para armazenar resultados em tempo real
current_results = []
processing_complete = False
processing_error = None

def process_sites(sites):
    global current_results, processing_complete, processing_error
    
    # Reiniciar variáveis globais
    current_results = []
    processing_complete = False
    processing_error = None
    
    total_sites = len(sites)
    
    try:
        with sync_playwright() as playwright:
            # Iniciar o navegador com configurações específicas
            browser = playwright.chromium.launch(
                headless=False,  # Navegador visível
                slow_mo=300,     # Desacelerar para visualização
                args=['--start-maximized'
                      '--disable-notifications',  # Bloqueia popups de notificação
                      '--disable-infobars']      # Remove barras de aviso]  # Iniciar maximizado
            )
            
            print(f"Navegador iniciado, processando {total_sites} sites...")
            
            for i in range(total_sites):
                site_data = sites[i]
                site_url = site_data.get("url", "")
                search_term = site_data.get("term", "Giramille")  # default "Giramille" if não tiver

                current_index = i + 1
                result = {
                    "url": site_url, 
                    "status": "Processando...", 
                    "status_search_bar": "Processando...",
                    "status_content_search": "Processando...",  
                    "progress": f"({current_index} de {total_sites})"
                }
                
                # Adicionar ao array de resultados para atualização em tempo real
                current_results.append(result)
                
                try:
                    # Criar uma nova página para cada site
                    page = browser.new_page()
                    
                    # Configurar timeout para navegação
                    page.set_default_timeout(SITE_PROCESSING_TIMEOUT * 1000)
                    start_time = time.time()
                    
                    # Navegação e processamento
                    #print(f"Processando site {current_index}/{total_sites}: {site_url}")
                    
                    # Ir para DuckDuckGo
                    page.goto('https://duckduckgo.com', wait_until="load")
                                        
                    # Preencher e submeter a busca
                    page.click('#searchbox_input')
                    
                    page.fill('#searchbox_input', site_url)
                    
                    page.press('#searchbox_input', 'Enter')
                                                            
                    check_timeout(start_time, SITE_PROCESSING_TIMEOUT)
                        
                    # Esperar que os resultados da busca carreguem
                    page.wait_for_selector('h2', state='visible')
                    page.click('h2')
                    page.wait_for_load_state("load")
                                        
                    check_timeout(start_time, SITE_PROCESSING_TIMEOUT)
                    
                    # Tenta fazer a busca por "Giramille" na página
                    search_field_founded, search_success = search_and_scroll(page, search_term)

                    if not search_field_founded:
                        # Caso não tenha achado campo de busca
                        result["status_search_bar"] = "Campo de busca não encontrado"
                        result["status_content_search"] = "Não foi possível realizar a busca"
                    else:
                        # Achou campo de busca
                        result["status_search_bar"] = "Campo de busca encontrado"
                        if search_success:
                            result["status_content_search"] = "Termo encontrado"
                        else:
                            result["status_content_search"] = "Termo não encontrado"


                except TimeoutError as e:
                    result["status"] = f"Timeout: {str(e)}"
                    result["status_search_bar"] = f"Timeout: {str(e)}"
                    result["status_content_search"] = "-"

                    print(f"Timeout: {str(e)}")
                except Exception as e:
                    result["status"] = f"Erro: {str(e)}"
                    result["status_search_bar"] = f"Erro: {str(e)}"
                    result["status_content_search"] = "-"
                    print(f"Erro: {str(e)}")
                    
                finally:
                    # Atualizar o resultado atual
                    current_results[i] = result
                    
                    # Fechar a página
                    if 'page' in locals() and not page.is_closed():
                        page.close()

            browser.close()
            print("Navegador fechado, processamento concluído")
            
    except Exception as e:
        processing_error = str(e)
        print(f"Erro global: {str(e)}")
    
    # Marcar o processamento como concluído
    processing_complete = True


@app.route('/process-column', methods=['POST'])
def process_column():
    print("1. process column")
    try:
        # Receber os dados JSON enviados pelo frontend
        data = request.json
        print(data)
        if not data or 'columnData' not in data:
            return jsonify({'error': 'Dados ausentes ou formato inválido'}), 400
        
        column_array = data['columnData']
        
        # Iniciar o processamento em uma thread separada
        threading.Thread(target=process_sites, args=(column_array,)).start()
        
        return jsonify({"message": "Processamento iniciado"})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/check-progress', methods=['GET'])
def check_progress():
    global current_results, processing_complete, processing_error
    
    return jsonify({
        "results": current_results,
        "complete": processing_complete,
        "error": processing_error
    })

# Rota para servir o arquivo HTML principal
@app.route('/')
def index():
    return send_from_directory('static', 'index.html')

# Configurar a pasta estática para outros arquivos estáticos (CSS, JS, etc.)
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('static', path)

if __name__ == '__main__':
    print("Aplicação inicializada! Acesse http://localhost:5000 no seu navegador.")
    app.run(debug=True)